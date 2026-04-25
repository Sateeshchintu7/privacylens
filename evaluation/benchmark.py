"""
evaluation/benchmark.py -- OPP-115 clause extraction benchmark for PrivacyLens.

Tests clause_extractor accuracy against manually annotated ground truth.
Produces Precision, Recall, F1 per category and macro averages.

Answers RQ1: "How accurately can NLP extract privacy policy clauses?"

Author: Sateesh Kumar Payyavula
Reference: Wilson et al. (2016) "The Creation and Analysis of a Website
           Privacy Policy Corpus" -- OPP-115 dataset and methodology
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import GEMINI_MODEL
from ingestion.scraper import extract_from_url
from ingestion.text_cleaner import clean_text
from nlp.clause_extractor import extract_clauses

_RESULTS_DIR = _ROOT / "evaluation" / "results"
_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

_ALL_CATEGORIES = [
    "data_collection",
    "purpose_limitation",
    "retention_period",
    "third_party_sharing",
    "user_rights",
    "consent_mechanism",
    "data_security",
    "breach_notification",
    "children_data",
    "cross_border_transfer",
    "cookies_tracking",
    "contact_info",
]


# ── Data models ───────────────────────────────────────────────────────────────

class CategoryMetrics(BaseModel):
    """Precision/Recall/F1 for a single clause category."""
    category: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


class BenchmarkReport(BaseModel):
    """Complete benchmark results across all policies and categories.

    Academic ref: Wilson et al. (2016) -- OPP-115 evaluation methodology
    """
    policies_tested: int
    categories_evaluated: int
    per_category: list[CategoryMetrics]
    macro_f1: float
    macro_precision: float
    macro_recall: float
    best_category: str
    worst_category: str
    above_threshold: int        # categories with F1 >= 0.75
    timestamp: str
    model_used: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_div(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


# ── Core benchmark ────────────────────────────────────────────────────────────

def run_benchmark(
    ground_truth_path: str = "data/opp115_sample/ground_truth.json",
    use_cache: bool = True,
) -> BenchmarkReport:
    """
    Run clause extraction benchmark against OPP-115 ground truth.

    For each policy:
      1. Scrape URL (cached)
      2. Extract clauses with clause_extractor (cached)
      3. Build binary prediction: category present if >= 1 clause found
      4. Compare to ground truth annotations
      5. Accumulate TP/FP/FN per category

    Precision = TP / (TP + FP)
    Recall    = TP / (TP + FN)
    F1        = 2 * P * R / (P + R)

    Academic ref:
        Wilson et al. (2016) -- OPP-115 dataset methodology
    """
    gt_path = _ROOT / ground_truth_path
    with open(gt_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    policies = ground_truth["policies"]

    # Accumulators: category -> {tp, fp, fn}
    accum: dict[str, dict[str, int]] = {
        cat: {"tp": 0, "fp": 0, "fn": 0} for cat in _ALL_CATEGORIES
    }

    policies_tested = 0
    for policy in policies:
        name        = policy["name"]
        url         = policy["url"]
        annotations: dict[str, bool] = policy["annotations"]

        print(f"  Benchmarking: {name}...")

        res = extract_from_url(url)
        if res.error:
            print(f"    SKIP (scrape error): {res.error}")
            continue

        cleaned = clean_text(res.text)
        clauses = extract_clauses(cleaned.text)

        # A category is "predicted present" if >= 1 clause extracted for it
        predicted: set[str] = {c.category for c in clauses}

        for cat in _ALL_CATEGORIES:
            ground_positive = annotations.get(cat, False)
            pred_positive   = cat in predicted

            if ground_positive and pred_positive:
                accum[cat]["tp"] += 1
            elif not ground_positive and pred_positive:
                accum[cat]["fp"] += 1
            elif ground_positive and not pred_positive:
                accum[cat]["fn"] += 1

        policies_tested += 1

    # Per-category metrics
    per_category: list[CategoryMetrics] = []
    for cat in _ALL_CATEGORIES:
        tp = accum[cat]["tp"]
        fp = accum[cat]["fp"]
        fn = accum[cat]["fn"]

        precision = _safe_div(tp, tp + fp)
        recall    = _safe_div(tp, tp + fn)
        f1        = _safe_div(2 * precision * recall, precision + recall)

        per_category.append(CategoryMetrics(
            category=cat,
            true_positives=tp, false_positives=fp, false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
        ))

    macro_precision = round(sum(m.precision for m in per_category) / len(per_category), 4)
    macro_recall    = round(sum(m.recall    for m in per_category) / len(per_category), 4)
    macro_f1        = round(sum(m.f1        for m in per_category) / len(per_category), 4)

    sorted_f1 = sorted(per_category, key=lambda m: m.f1)
    worst_cat = sorted_f1[0].category
    best_cat  = sorted_f1[-1].category
    above_thr = sum(1 for m in per_category if m.f1 >= 0.75)

    report = BenchmarkReport(
        policies_tested=policies_tested,
        categories_evaluated=len(_ALL_CATEGORIES),
        per_category=per_category,
        macro_f1=macro_f1,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        best_category=best_cat,
        worst_category=worst_cat,
        above_threshold=above_thr,
        timestamp=datetime.utcnow().isoformat(),
        model_used=GEMINI_MODEL,
    )

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = _RESULTS_DIR / f"benchmark_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    print(f"\n  Benchmark saved: {out_path}")

    return report


# ── Display ───────────────────────────────────────────────────────────────────

def print_benchmark_table(report: BenchmarkReport) -> None:
    """
    Print formatted OPP-115 benchmark results table.

    Threshold for pass: F1 >= 0.75 (dissertation requirement)
    """
    W = 26
    N = 11
    sep = "+" + "-" * W + "+" + "-" * N + "+" + "-" * N + "+" + "-" * N + "+" + "-" * 8 + "+"
    dbl = sep.replace("-", "=")

    print("\n" + sep)
    print(
        f"| {'Category':<{W-2}} | {'Precision':^{N-2}} |"
        f" {'Recall':^{N-2}} | {'F1':^{N-2}} | {'Status':^6} |"
    )
    print(dbl)

    for m in report.per_category:
        flag = "[+]" if m.f1 >= 0.75 else "[-]"
        print(
            f"| {m.category:<{W-2}} |"
            f" {m.precision:^{N-2}.3f} |"
            f" {m.recall:^{N-2}.3f} |"
            f" {m.f1:^{N-2}.3f} |"
            f" {flag:^6} |"
        )

    print(dbl)
    print(
        f"| {'MACRO AVERAGE':<{W-2}} |"
        f" {report.macro_precision:^{N-2}.3f} |"
        f" {report.macro_recall:^{N-2}.3f} |"
        f" {report.macro_f1:^{N-2}.3f} |"
        f" {'':^6} |"
    )
    print(sep)

    print(f"\nPolicies tested      : {report.policies_tested}")
    print(f"Target F1 threshold  : 0.750")
    print(f"Categories passing   : {report.above_threshold}/{report.categories_evaluated}")
    print(f"Best category        : {report.best_category}  (F1={max(m.f1 for m in report.per_category):.3f})")
    print(f"Worst category       : {report.worst_category} (F1={min(m.f1 for m in report.per_category):.3f})")
    print(f"Model used           : {report.model_used}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PrivacyLens -- OPP-115 Clause Extraction Benchmark")
    print("Wilson et al. (2016) methodology")
    print("=" * 60)
    print()
    rpt = run_benchmark()
    print_benchmark_table(rpt)
