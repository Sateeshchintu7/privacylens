"""
nlp/plain_rewriter.py — Plain English rewriter for privacy policy clauses.

Groups clauses by category, merges their text, then calls Gemini to rewrite
each group at the target Flesch-Kincaid grade for the chosen audience level.
Verifies output grade with readability.py; retries once if grade too high.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- avg policy Grade 14.8, justifies need
           Sweller (1988) -- Cognitive Load Theory, justifies simplification
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import BaseModel

from config import BASE_DIR
from nlp.clause_extractor import ClauseResult
from nlp.llm_client import call_gemini, parse_json_response
from nlp.readability import score_readability
from api.prompt_loader import load_prompt

logger = logging.getLogger(__name__)
PROMPT_PATH = BASE_DIR / "prompts" / "plain_rewrite.txt"

CATEGORY_LABELS: dict[str, str] = {
    "data_collection":      "What data they collect",
    "purpose_limitation":   "Why they collect it",
    "retention_period":     "How long they keep your data",
    "third_party_sharing":  "Who else gets your data",
    "user_rights":          "Your rights",
    "consent_mechanism":    "How you give consent",
    "data_security":        "How they protect your data",
    "breach_notification":  "What happens if there's a data breach",
    "children_data":        "Rules about children's data",
    "cross_border_transfer":"Sending data to other countries",
    "cookies_tracking":     "Cookies and tracking",
    "contact_info":         "How to contact them",
}

# Target FK grade per audience level
GRADE_TARGETS: dict[str, float] = {
    "adult":   6.0,
    "teen":    4.0,
    "preteen": 3.0,
    "child":   2.0,
}


# ── Pydantic model ────────────────────────────────────────────────────────────

class PlainClause(BaseModel):
    """Plain English rewrite for one policy category."""
    clause_id: str
    category: str
    category_label: str
    plain_summary: str
    what_it_means: str
    original_length: int       # chars of merged source text
    summary_length: int        # chars of rewritten text
    reading_grade: float       # FK grade achieved
    audience_level: str
    grade_target: float
    grade_met: bool


# ── Internal helpers ──────────────────────────────────────────────────────────

def _call_rewrite(
    category: str,
    merged_text: str,
    grade_target: float,
    prompt_tmpl: str,
    use_cache: bool,
    strict: bool = False,
) -> tuple[str, str]:
    """
    Single Gemini call to rewrite a category's text.

    Args:
        strict: If True, adds an extra instruction to simplify further.

    Returns:
        (plain_summary, what_it_means)
    """
    extra = "\nIMPORTANT: The previous attempt was too complex. Use even shorter sentences." if strict else ""
    prompt = (
        prompt_tmpl
        .replace("{GRADE_LEVEL}", str(int(round(grade_target))))
        .replace("{GRADE_NUMBER}", f"{grade_target:.1f}")
        .replace("{CATEGORY_LABEL}", CATEGORY_LABELS.get(category, category))
        .replace("{CLAUSES_TEXT}", merged_text[:3000] + extra)
    )
    resp, _ = call_gemini(prompt, function_name="plain_rewriter", use_cache=use_cache)
    raw = parse_json_response(resp)
    if not isinstance(raw, dict):
        return "", ""
    return str(raw.get("plain_summary", "")).strip(), str(raw.get("what_it_means", "")).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def rewrite_policy(
    clauses: list[ClauseResult],
    audience_level: str = "adult",
    use_cache: bool = True,
) -> list[PlainClause]:
    """
    Rewrite all policy clauses in plain language for the target audience.

    Groups by category, merges clause texts, rewrites with Gemini,
    verifies FK grade, and retries with stricter prompt if grade too high.

    Args:
        clauses: list[ClauseResult] from clause_extractor
        audience_level: "adult" | "teen" | "preteen" | "child"
        use_cache: Cache LLM responses

    Returns:
        list[PlainClause] -- one entry per category found in the policy

    Academic ref:
        Reidenberg et al. (2015) -- policy readability baseline
        Sweller (1988) -- Cognitive Load Theory
    """
    grade_target = GRADE_TARGETS.get(audience_level, 6.0)
    prompt_tmpl = load_prompt("prompts/plain_rewrite.txt")

    # Group clauses by category
    grouped: dict[str, list[str]] = {}
    for c in clauses:
        grouped.setdefault(c.category, []).append(c.original_text)

    def _rewrite_one(category: str, texts: list[str]) -> PlainClause:
        merged = " ".join(texts)
        plain_summary, what_it_means = "", ""
        try:
            plain_summary, what_it_means = _call_rewrite(
                category, merged, grade_target, prompt_tmpl, use_cache
            )
            if plain_summary:
                achieved = score_readability(plain_summary).flesch_kincaid_grade
                if achieved > grade_target + 1.5:
                    logger.info("Grade %.1f too high for %s, retrying...", achieved, category)
                    plain_summary, what_it_means = _call_rewrite(
                        category, merged, grade_target, prompt_tmpl,
                        use_cache=False, strict=True
                    )
        except Exception as exc:
            logger.warning("Rewrite failed for %s: %s", category, exc)

        if not plain_summary:
            plain_summary = merged[:300] + "..."
            what_it_means = "This section describes how the company handles your data."

        grade_achieved = score_readability(plain_summary).flesch_kincaid_grade
        return PlainClause(
            clause_id=f"{category}_plain",
            category=category,
            category_label=CATEGORY_LABELS.get(category, category),
            plain_summary=plain_summary,
            what_it_means=what_it_means,
            original_length=len(merged),
            summary_length=len(plain_summary),
            reading_grade=round(grade_achieved, 1),
            audience_level=audience_level,
            grade_target=grade_target,
            grade_met=grade_achieved <= grade_target + 1.5,
        )

    results: list[PlainClause] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_rewrite_one, cat, texts): cat
                   for cat, texts in grouped.items()}
        for fut in as_completed(futures):
            results.append(fut.result())

    return results
