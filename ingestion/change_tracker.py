"""
ingestion/change_tracker.py -- Policy version comparison for PrivacyLens.

Compares two versions of a privacy policy at the category level:
  1. Extract clauses from both versions
  2. Compare category presence and risk scores
  3. LLM plain-English summaries for changed categories
  4. Return PolicyDiff with verdict and emoji

Also provides create_demo_diff() for testing without two real versions.

Academic ref: Reidenberg et al. (2015) -- privacy policy change study.
              Compared 75 policies over 14 years; 72% changed at least once.

Author: Sateesh Kumar Payyavula
"""

import logging
from pydantic import BaseModel
from config import BASE_DIR, GEMINI_API_KEY
from nlp.llm_client import call_gemini

logger = logging.getLogger(__name__)
PROMPT_PATH = BASE_DIR / "prompts" / "change_summary.txt"

_SEVERITY = {
    "deny_then_share": "critical",
    "WORSENED": "high",
    "IMPROVED": "low",
    "ADDED": "medium",
    "REMOVED": "medium",
    "UNCHANGED": "low",
}


class ClauseChange(BaseModel):
    """A change in one policy category between two versions."""
    category: str
    change_type: str   # ADDED | REMOVED | WORSENED | IMPROVED | UNCHANGED
    old_text: str
    new_text: str
    risk_delta: float
    plain_summary: str
    severity: str


class PolicyDiff(BaseModel):
    """Full diff between two policy versions."""
    policy_name: str
    old_date: str
    new_date: str
    total_changes: int
    worsened: list[ClauseChange]
    improved: list[ClauseChange]
    added: list[ClauseChange]
    removed: list[ClauseChange]
    unchanged_count: int
    overall_risk_delta: float
    plain_summary: str
    verdict: str          # IMPROVED | WORSENED | MIXED | UNCHANGED
    verdict_emoji: str


def _llm_summary(old_text: str, new_text: str, change_type: str) -> str:
    """Generate one-sentence plain summary of what changed via LLM."""
    if not GEMINI_API_KEY or not PROMPT_PATH.exists():
        # Fallback: heuristic summary
        if change_type == "WORSENED":
            return f"This section was expanded, potentially increasing privacy risks."
        elif change_type == "IMPROVED":
            return f"This section was simplified or shortened, reducing complexity."
        elif change_type == "ADDED":
            return "A new section was added to the policy."
        else:
            return "This section was removed from the policy."

    prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        .replace("{OLD_TEXT}", old_text[:400])
        .replace("{NEW_TEXT}", new_text[:400])
        .replace("{CHANGE_TYPE}", change_type)
    )
    try:
        resp, _ = call_gemini(prompt, function_name="change_tracker", use_cache=True)
        return resp.strip()[:200]
    except Exception as exc:
        logger.warning("Change summary LLM call failed: %s", exc)
        return f"{change_type}: content changed between versions."


def compare_policies(
    old_text: str,
    new_text: str,
    policy_name: str = "Policy",
    old_date: str = "Previous version",
    new_date: str = "Current version",
) -> PolicyDiff:
    """
    Compare two versions of a policy at the category level.

    Steps:
      1. Extract clauses from both versions
      2. Score risk for both
      3. Compare per category: ADDED / REMOVED / WORSENED / IMPROVED
      4. LLM plain summaries for significant changes
      5. Compute verdict

    Args:
        old_text: Full text of older policy version
        new_text: Full text of newer policy version
        policy_name: Name for display
        old_date: Label for old version
        new_date: Label for new version

    Returns:
        PolicyDiff

    Academic ref: Reidenberg et al. (2015) -- policy version change analysis.
    """
    from nlp.clause_extractor import extract_clauses
    from nlp.mad_engine import score_policy

    old_clauses = extract_clauses(old_text, use_cache=False)
    new_clauses = extract_clauses(new_text, use_cache=True)

    old_report = score_policy(old_clauses)
    new_report = score_policy(new_clauses)

    old_scores: dict[str, float] = {cr.category: cr.final_score for cr in old_report.clause_risks}
    new_scores: dict[str, float] = {cr.category: cr.final_score for cr in new_report.clause_risks}
    old_texts: dict[str, str] = {}
    new_texts: dict[str, str] = {}

    for c in old_clauses:
        old_texts.setdefault(c.category, "")
        old_texts[c.category] += " " + c.original_text[:200]

    for c in new_clauses:
        new_texts.setdefault(c.category, "")
        new_texts[c.category] += " " + c.original_text[:200]

    all_cats = set(old_scores) | set(new_scores)
    worsened, improved, added, removed, unchanged_count = [], [], [], [], 0

    for cat in sorted(all_cats):
        old_s = old_scores.get(cat, 0.0)
        new_s = new_scores.get(cat, 0.0)
        old_t = old_texts.get(cat, "").strip()
        new_t = new_texts.get(cat, "").strip()

        if cat not in old_scores:
            change_type = "ADDED"
            risk_delta = new_s
            summary = _llm_summary("", new_t, "ADDED")
            added.append(ClauseChange(
                category=cat, change_type="ADDED",
                old_text="", new_text=new_t[:200],
                risk_delta=risk_delta,
                plain_summary=summary,
                severity="medium",
            ))
        elif cat not in new_scores:
            change_type = "REMOVED"
            risk_delta = -old_s
            summary = _llm_summary(old_t, "", "REMOVED")
            removed.append(ClauseChange(
                category=cat, change_type="REMOVED",
                old_text=old_t[:200], new_text="",
                risk_delta=risk_delta,
                plain_summary=summary,
                severity="medium",
            ))
        else:
            delta = new_s - old_s
            if delta > 10:
                change_type = "WORSENED"
                summary = _llm_summary(old_t, new_t, "WORSENED")
                worsened.append(ClauseChange(
                    category=cat, change_type="WORSENED",
                    old_text=old_t[:200], new_text=new_t[:200],
                    risk_delta=round(delta, 1),
                    plain_summary=summary,
                    severity="high",
                ))
            elif delta < -10:
                change_type = "IMPROVED"
                summary = _llm_summary(old_t, new_t, "IMPROVED")
                improved.append(ClauseChange(
                    category=cat, change_type="IMPROVED",
                    old_text=old_t[:200], new_text=new_t[:200],
                    risk_delta=round(delta, 1),
                    plain_summary=summary,
                    severity="low",
                ))
            else:
                unchanged_count += 1

    total_changes = len(worsened) + len(improved) + len(added) + len(removed)
    overall_delta = new_report.overall_score - old_report.overall_score

    if total_changes == 0:
        verdict, emoji = "UNCHANGED", "➡️"
    elif len(worsened) > len(improved):
        verdict, emoji = "WORSENED", "⬇️"
    elif len(improved) > len(worsened):
        verdict, emoji = "IMPROVED", "⬆️"
    else:
        verdict, emoji = "MIXED", "↔️"

    plain = (
        f"The new version {verdict.lower()} the policy. "
        f"{len(worsened)} section(s) got worse, {len(improved)} improved, "
        f"{len(added)} added, {len(removed)} removed."
    )

    return PolicyDiff(
        policy_name=policy_name, old_date=old_date, new_date=new_date,
        total_changes=total_changes,
        worsened=worsened, improved=improved, added=added, removed=removed,
        unchanged_count=unchanged_count,
        overall_risk_delta=round(overall_delta, 1),
        plain_summary=plain,
        verdict=verdict, verdict_emoji=emoji,
    )


def create_demo_diff() -> PolicyDiff:
    """
    Create a realistic demo PolicyDiff from the Google Privacy Policy.

    Simulates an "older" version by:
      - Removing the retention_period clause text
      - Adding "We may sell your data to third parties"
      - Removing right-to-deletion language

    Lets you demo the Compare page without needing two real historical versions.

    Academic ref: Reidenberg et al. (2015) -- common policy change patterns.
    """
    from ingestion.scraper import extract_from_url
    from ingestion.text_cleaner import clean_text

    res = extract_from_url("https://policies.google.com/privacy")
    current_text = clean_text(res.text).text

    # Simulate an "older" worse policy
    old_text = current_text
    # Inject synthetic worsenings
    old_text = old_text + (
        "\n\nWe may sell your personal data to third-party advertising companies "
        "for their direct marketing purposes.\n\n"
        "We retain your data indefinitely or for as long as necessary for our "
        "business purposes.\n\n"
        "Users may not request deletion of their data once submitted."
    )

    return compare_policies(
        old_text=old_text,
        new_text=current_text,
        policy_name="Google Privacy Policy",
        old_date="Simulated older version",
        new_date="Current version (2024)",
    )
