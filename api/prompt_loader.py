"""
api/prompt_loader.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Resilient prompt file loader.

PROBLEM:
  NLP modules use open("prompts/foo.txt") which is
  relative to the process working directory (CWD).
  Locally CWD = project root → works.
  On Cloud Run CWD = /app → works IF prompts/ was COPY'd.
  If prompts/ was not COPY'd (deployment error): crash.

SOLUTION:
  Try 5 different path strategies before giving up.
  As last resort, return a hardcoded minimal prompt that
  keeps the app functional (degraded, not dead).

USAGE:
  Replace all open("prompts/x.txt") calls with:
    from api.prompt_loader import load_prompt
    text = load_prompt("prompts/x.txt")
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Hardcoded fallback prompts ────────────────────────────
# Used only when all file paths fail.
# Minimal but functional — keeps app alive.
_FALLBACKS: dict[str, str] = {
    "clause_extraction": (
        "You are a privacy policy analyst.\n"
        "Extract all privacy clauses from the text below.\n"
        "For each clause identify the category from this list:\n"
        "data_collection, purpose_limitation, retention_period,\n"
        "third_party_sharing, user_rights, consent_mechanism,\n"
        "data_security, breach_notification, children_data,\n"
        "cross_border_transfer, cookies_tracking, contact_info,\n"
        "automated_decision_making, data_sale_vs_sharing, biometric_data,\n"
        "gpc_signal_honoring, ai_system_disclosure, sensitive_data_categories.\n\n"
        "For each clause also provide a short Grade 6 plain-English summary, a one-sentence 'This means...' explanation, a risk level, a risk score, red flags, and positive signals.\n\n"
        "Return ONLY valid JSON with no markdown:\n"
        '{"clauses": [{'
        '"category": "data_collection", '
        '"text": "exact quote from policy", '
        '"confidence": 0.85, '
        '"gdpr_article": "Art. 13(1)(c)", '
        '"plain_summary": "short rewrite", '
        '"what_it_means": "This means...", '
        '"risk_level": "medium", '
        '"risk_score": 45, '
        '"red_flags": [], '
        '"positive_signals": []'
        "}]}"
    ),
    "risk_scoring": (
        "Score this privacy clause for risk level (0-100).\n"
        "0 = no risk to user. 100 = severe risk to user.\n"
        "Base score ONLY on what is explicitly written.\n\n"
        "Return ONLY valid JSON:\n"
        '{"llm_score": 50, "reasoning": "brief explanation", '
        '"red_flags": [], "positive_signals": []}'
    ),
    "plain_rewrite": (
        "Rewrite this privacy clause in plain English.\n"
        "Target: Grade 6 reading level (Flesch-Kincaid).\n"
        "Rules: max 15 words per sentence, active voice.\n\n"
        "Return ONLY valid JSON:\n"
        '{"plain_summary": "2-3 sentence rewrite", '
        '"what_it_means": "This means [one sentence]."}'
    ),
    "kids_rewrite_grade3": (
        "Rewrite for a child aged 8-10 years.\n"
        "Max 8 words per sentence. Use toy/game analogies.\n\n"
        "Return ONLY valid JSON:\n"
        '{"kids_summary": "2 sentence rewrite", '
        '"one_liner": "max 10 words"}'
    ),
    "kids_rewrite_grade5": (
        "Rewrite for a child aged 11-13 years.\n"
        "Max 12 words per sentence.\n\n"
        "Return ONLY valid JSON:\n"
        '{"kids_summary": "2-3 sentence rewrite", '
        '"one_liner": "max 12 words"}'
    ),
    "kids_rewrite_grade7": (
        "Rewrite for a teenager aged 14-17 years.\n"
        "Max 16 words per sentence. Be direct and honest.\n\n"
        "Return ONLY valid JSON:\n"
        '{"kids_summary": "2-3 sentence rewrite", '
        '"one_liner": "max 15 words"}'
    ),
    "contradiction_detection": (
        "Do these two privacy policy clauses contradict each other?\n\n"
        "Return ONLY valid JSON:\n"
        '{"is_contradiction": false, '
        '"contradiction_type": "", '
        '"severity": "low", '
        '"explanation": "", '
        '"user_impact": ""}'
    ),
    "rag_answer": (
        "Answer the user question using ONLY the context below.\n"
        "If the answer is not in the context, say so clearly.\n\n"
        "Return ONLY valid JSON:\n"
        '{"answer": "plain English answer", '
        '"confidence": 0.8, '
        '"source_quote": "exact quote supporting answer", '
        '"could_not_find": false}'
    ),
    "change_summary": (
        "Summarise what changed between these two privacy policy\n"
        "versions in one plain sentence of maximum 20 words."
    ),
    "compliance_mapping": (
        "Check this privacy policy clause for compliance with GDPR, CCPA, and DPDP.\n\n"
        "Return ONLY valid JSON:\n"
        '{"gdpr_compliant": true, "ccpa_compliant": true, "dpdp_compliant": true, "gaps": []}'
    ),
}


def load_prompt(relative_path: str) -> str:
    """
    Load a prompt file with multi-path fallback strategy.

    Args:
        relative_path: Relative path from project root.
                       Example: "prompts/clause_extraction.txt"

    Returns:
        File contents as a string.

    Raises:
        FileNotFoundError: Only if no fallback is registered
                           for this prompt type.
    """
    filename = Path(relative_path).name    # clause_extraction.txt
    stem = Path(filename).stem             # clause_extraction

    # 5-path search strategy — first non-empty match wins
    candidates = [
        Path(relative_path),                            # 1. CWD-relative
        Path("/app") / relative_path,                   # 2. Cloud Run /app
        Path(__file__).parent.parent / relative_path,  # 3. Repo root via this file
        Path("/app/prompts") / filename,                # 4. Cloud Run flat
        Path("prompts") / filename,                     # 5. CWD/prompts flat
    ]

    for candidate in candidates:
        try:
            content = candidate.read_text(encoding="utf-8").strip()
            if content:
                logger.debug("Loaded prompt: %s → %s", relative_path, candidate)
                return content
        except (FileNotFoundError, PermissionError, OSError):
            continue

    # Fallback: match on stem
    for key, fallback_text in _FALLBACKS.items():
        if stem == key or stem.startswith(key) or key in stem:
            logger.warning(
                "PROMPT FILE NOT FOUND: %s — using built-in fallback for '%s'. "
                "Results may be degraded. Restore prompts/ folder for best results.",
                relative_path,
                key,
            )
            return fallback_text

    raise FileNotFoundError(
        f"Prompt '{relative_path}' not found in any location:\n"
        + "\n".join(f"  {c}" for c in candidates)
        + f"\nNo built-in fallback registered for stem '{stem}'."
    )
