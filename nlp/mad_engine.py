"""
nlp/mad_engine.py — Model-Augmented Detection (MAD) risk scoring engine.

Two-pass scoring strategy:
  Pass 1 (keyword): Fast rule-based scan of every clause.
  Pass 2 (LLM):     Gemini reasoning on any clause scoring >= 50 in Pass 1.
Final score = 0.4 * keyword + 0.6 * LLM  (or 100% keyword if no LLM pass).
Overall policy grade A-F = weighted average across all clauses.

Author: Sateesh Kumar Payyavula
Reference: Rodriguez et al. (2024, Springer Computing) -- LLMs for policy analysis
"""

import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import BaseModel

from config import BASE_DIR, RISK_GRADES
from nlp.clause_extractor import ClauseResult
from nlp.llm_client import call_gemini, parse_json_response
from api.prompt_loader import load_prompt

logger = logging.getLogger(__name__)
PROMPT_PATH = BASE_DIR / "prompts" / "risk_scoring.txt"


# ── Pydantic models ───────────────────────────────────────────────────────────

class ClauseRisk(BaseModel):
    """Risk assessment for a single clause."""
    clause_id: str
    category: str
    keyword_score: float         # 0-100 from keyword pass
    llm_score: float             # 0-100 from LLM pass (= keyword_score if not triggered)
    final_score: float           # weighted blend
    risk_level: str              # low | medium | high | critical
    red_flags: list[str]
    positive_signals: list[str]


class PolicyRiskReport(BaseModel):
    """Full risk assessment for a privacy policy."""
    overall_score: float
    grade: str                   # A-F
    clause_risks: list[ClauseRisk]
    top_red_flags: list[str]     # top 5 by frequency
    positive_signals: list[str]
    grade_explanation: str       # 1-sentence plain English
    llm_passes: int              # number of clauses that triggered LLM pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_rules() -> tuple[list, list]:
    path = BASE_DIR / "data" / "risk_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["red_flags"], data["positive_signals"]


def _keyword_pass(
    text: str, red_flags: list, pos_signals: list
) -> tuple[float, list[str], list[str]]:
    """
    Fast keyword-based risk scan.

    Args:
        text: Clause text
        red_flags: List of risk rule dicts from risk_rules.json
        pos_signals: List of positive signal dicts

    Returns:
        (score_0_100, red_flag_labels, positive_labels)
    """
    lower = text.lower()
    risk_total, pos_total = 0.0, 0.0
    flags, positives = [], []

    for flag in red_flags:
        if any(kw.lower() in lower for kw in flag["keywords"]):
            risk_total += flag["risk_score"]
            flags.append(flag["label"])
    for sig in pos_signals:
        if any(kw.lower() in lower for kw in sig["keywords"]):
            pos_total += sig["risk_reduction"]
            positives.append(sig["label"])

    return max(0.0, min(100.0, risk_total - pos_total)), flags, positives


_DEFINITE_HIGH: list[str] = [
    r"sell.*personal.*data", r"sell.*user.*data", r"third.party.*advertising",
    r"share.*without.*consent", r"retain.*indefinitely", r"no.*right.*delete",
    r"children.*data.*advertising", r"biometric.*data", r"precise.*location.*third",
]
_DEFINITE_LOW: list[str] = [
    r"never.*sell.*data", r"opt.out.*available", r"delete.*account.*any.*time",
    r"encrypt.*transit.*rest", r"not.*share.*personal", r"gdpr.*compliant",
]


def _validate_score(text: str, llm_score: float) -> float:
    """
    Rule-based score override to prevent LLM hallucination.
    If a definite high-risk phrase is found: floor the score at 65.
    If a definite low-risk phrase is found: cap the score at 35.
    """
    import re
    lower = text.lower()
    for pattern in _DEFINITE_HIGH:
        if re.search(pattern, lower):
            return max(llm_score, 65.0)
    for pattern in _DEFINITE_LOW:
        if re.search(pattern, lower):
            return min(llm_score, 35.0)
    return llm_score


def _risk_level(score: float) -> str:
    if score >= 75: return "critical"
    if score >= 50: return "high"
    if score >= 25: return "medium"
    return "low"


def _grade(score: float) -> str:
    for g, (lo, hi) in RISK_GRADES.items():
        if lo <= score <= hi:
            return g
    return "F"


_EXPLANATIONS = {
    "A": "This policy is transparent and user-friendly.",
    "B": "This policy is mostly fair with minor concerns.",
    "C": "This policy has some concerning practices worth knowing about.",
    "D": "This policy has significant privacy risks -- read carefully.",
    "F": "This policy has aggressive data practices -- use caution.",
}


# ── Public API ────────────────────────────────────────────────────────────────

def score_policy(clauses: list[ClauseResult], use_cache: bool = True) -> PolicyRiskReport:
    """
    Score a full policy using the two-pass MAD methodology.

    If clauses already have risk_score from combined extraction, use those
    directly — no LLM pass needed. Otherwise:
      Pass 1 runs on every clause (fast keyword scan).
      Pass 2 (Gemini) runs only on clauses with keyword_score >= 50.
      Final score = 0.4 * keyword + 0.6 * LLM where LLM pass ran.

    Args:
        clauses: list[ClauseResult] from clause_extractor
        use_cache: Cache LLM responses

    Returns:
        PolicyRiskReport with grade A-F, top red flags, and explanation

    Academic ref:
        Rodriguez et al. (2024) -- LLM-assisted risk analysis methodology
    """
    red_rules, pos_rules = _load_rules()
    prompt_tmpl = load_prompt("prompts/risk_scoring.txt")

    # Pass 1: keyword scan all clauses (fast, no I/O)
    kw_data: list[tuple] = []
    for clause in clauses:
        kw_score, kw_flags, kw_pos = _keyword_pass(
            clause.original_text, red_rules, pos_rules
        )
        kw_data.append((clause, kw_score, kw_flags, kw_pos))

    # Pass 2: LLM on high-risk clauses — run in parallel
    # SKIP clauses that already have risk_score from combined extraction
    def _llm_pass(clause: ClauseResult, kw_score: float, kw_flags: list) -> tuple:
        prompt = (
            prompt_tmpl
            .replace("{CLAUSE_TEXT}", clause.original_text[:1200])
            .replace("{CATEGORY}", clause.category)
            .replace("{GDPR_ARTICLE}", clause.gdpr_article)
        )
        try:
            resp, _ = call_gemini(prompt, function_name="mad_engine", use_cache=use_cache)
            raw = parse_json_response(resp)
            if isinstance(raw, dict) and "llm_score" in raw:
                llm_score = float(max(0.0, min(100.0, raw["llm_score"])))
                return clause.clause_id, llm_score, raw.get("red_flags", kw_flags), True
        except Exception as exc:
            logger.warning("LLM risk pass failed for %s: %s", clause.clause_id, exc)
        return clause.clause_id, kw_score, kw_flags, False

    llm_results: dict[str, tuple] = {}
    # Only run LLM on clauses missing pre-computed risk AND high keyword score
    high_risk = [
        (c, kw_s, kw_f) for c, kw_s, kw_f, _ in kw_data
        if kw_s >= 50 and c.risk_score is None
    ]
    pre_scored = sum(1 for c in clauses if c.risk_score is not None)
    if pre_scored:
        logger.info("MAD: %d/%d clauses pre-scored from extraction — skipping LLM for those", pre_scored, len(clauses))

    if high_risk:
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(_llm_pass, c, kw_s, kw_f): c.clause_id
                       for c, kw_s, kw_f in high_risk}
            for fut in as_completed(futures):
                cid, llm_score, llm_flags, did_llm = fut.result()
                llm_results[cid] = (llm_score, llm_flags, did_llm)

    clause_risks: list[ClauseRisk] = []
    all_flags: list[str] = []
    all_positives: list[str] = []
    llm_passes = 0

    for clause, kw_score, kw_flags, kw_pos in kw_data:
        # Use pre-computed risk from combined extraction if available
        if clause.risk_score is not None:
            pre_score = clause.risk_score
            pre_flags = clause.red_flags or kw_flags
            pre_pos = clause.positive_signals or kw_pos
            final = round(_validate_score(clause.original_text, pre_score), 1)
            all_flags.extend(pre_flags)
            all_positives.extend(pre_pos)
            clause_risks.append(ClauseRisk(
                clause_id=clause.clause_id, category=clause.category,
                keyword_score=round(kw_score, 1), llm_score=round(pre_score, 1),
                final_score=final, risk_level=clause.risk_level or _risk_level(final),
                red_flags=list(set(pre_flags)),
                positive_signals=list(set(pre_pos)),
            ))
            continue

        if clause.clause_id in llm_results:
            llm_score, llm_flags, did_llm = llm_results[clause.clause_id]
            if did_llm:
                llm_passes += 1
        else:
            llm_score, llm_flags = kw_score, kw_flags

        blend = 0.4 * kw_score + 0.6 * llm_score if llm_score != kw_score else kw_score
        blend = _validate_score(clause.original_text, blend)
        final = round(max(0.0, min(100.0, blend)), 1)

        all_flags.extend(llm_flags)
        all_positives.extend(kw_pos)

        clause_risks.append(ClauseRisk(
            clause_id=clause.clause_id, category=clause.category,
            keyword_score=round(kw_score, 1), llm_score=round(llm_score, 1),
            final_score=final, risk_level=_risk_level(final),
            red_flags=list(set(llm_flags)),
            positive_signals=list(set(kw_pos)),
        ))

    # Weighted overall score
    id_to_weight = {c.clause_id: c.risk_weight for c in clauses}
    total_w = sum(id_to_weight.get(cr.clause_id, 1.0) for cr in clause_risks)
    if total_w > 0:
        overall = sum(
            cr.final_score * id_to_weight.get(cr.clause_id, 1.0)
            for cr in clause_risks
        ) / total_w
    else:
        overall = sum(cr.final_score for cr in clause_risks) / max(len(clause_risks), 1)

    overall = round(overall, 1)
    grade = _grade(overall)
    top_flags = [f for f, _ in Counter(all_flags).most_common(5)]

    return PolicyRiskReport(
        overall_score=overall,
        grade=grade,
        clause_risks=clause_risks,
        top_red_flags=top_flags,
        positive_signals=list(set(all_positives)),
        grade_explanation=_EXPLANATIONS.get(grade, f"Risk score: {overall}/100."),
        llm_passes=llm_passes,
    )
