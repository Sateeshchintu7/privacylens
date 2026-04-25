"""
nlp/kids_rewriter.py -- Age-adaptive kids mode rewriter for PrivacyLens.

Author: Sateesh Kumar Payyavula
Reference: COPPA (1998); UK Age Appropriate Design Code (2021)
           Sweller (1988) Cognitive Load Theory
"""

import re
import logging
from pydantic import BaseModel
from config import BASE_DIR, GEMINI_API_KEY
from nlp.llm_client import call_gemini, parse_json_response

logger = logging.getLogger(__name__)

DATA_SIGNALS: dict[str, str] = {
    "data_collection": "\U0001f440", "third_party_sharing": "\U0001f517",
    "cookies_tracking": "\U0001f36a", "cross_border_transfer": "\u2708\ufe0f",
    "children_data": "\U0001f467", "retention_period": "\U0001f5c4\ufe0f",
    "user_rights": "\u2705", "consent_mechanism": "\U0001f58a\ufe0f",
    "data_security": "\U0001f512", "breach_notification": "\U0001f6a8",
    "purpose_limitation": "\U0001f3af", "contact_info": "\U0001f4ec",
}
RISK_EMOJIS: dict[str, str] = {
    "low": "\u2705", "medium": "\u26a0\ufe0f",
    "high": "\U0001f6a8", "critical": "\U0001f6d1",
}
FEATURE_EMOJIS: dict[str, str] = {
    "uses_location": "\U0001f4cd", "uses_camera": "\U0001f4f8",
    "uses_microphone": "\U0001f3a4", "in_app_purchases": "\U0001f4b0",
    "sells_data": "\U0001f4b8", "deletes_on_request": "\U0001f5d1\ufe0f",
    "encryption": "\U0001f510", "shares_with_police": "\U0001f46e",
}
_GRADE_MAP: dict[str, int] = {"child": 3, "junior": 5, "teen": 7}
_VERDICT_MSGS: dict[str, dict[str, str]] = {
    "child": {
        "SAFE":        "This app seems okay! But always ask a grown-up before signing up.",
        "ASK_PARENT":  "Some things here are a bit tricky. Show this to a parent first!",
        "BE_CAREFUL":  "This app wants a LOT of your information. Talk to a grown-up!",
    },
    "junior": {
        "SAFE":        "This looks mostly fine, but read the important bits with a parent.",
        "ASK_PARENT":  "There are some things you should check with a parent before agreeing.",
        "BE_CAREFUL":  "This app collects a lot of data. You and a parent should read this carefully.",
    },
    "teen": {
        "SAFE":        "This policy looks reasonably fair. A few things worth knowing below.",
        "ASK_PARENT":  "Some clauses here are worth discussing, especially around data sharing.",
        "BE_CAREFUL":  "This policy has significant privacy concerns. Read the red flags below.",
    },
}


class KidsClause(BaseModel):
    """Single policy category rewritten for a child/teen audience."""
    category: str
    emoji: str
    risk_emoji: str
    kids_summary: str
    one_liner: str
    risk_level: str
    feature_flags: list[str]


class KidsReport(BaseModel):
    """Full kids-mode report: verdict, clause cards, emoji summary."""
    age_group: str
    target_grade: int
    clauses: list[KidsClause]
    verdict: str
    verdict_emoji: str
    verdict_reason: str
    top_concerns: list[str]
    top_positives: list[str]
    overall_emoji_summary: str


def _age_group(age: int) -> str:
    if age <= 10: return "child"
    if age <= 13: return "junior"
    return "teen"


def detect_features(text: str) -> list[str]:
    """
    Keyword-based feature flag detection — no LLM required.

    Args:
        text: Plain text of a policy clause

    Returns:
        list[str]: detected feature keys from FEATURE_EMOJIS

    Academic ref: COPPA (1998) — data type disclosure requirements
    """
    lower = text.lower()
    flags: list[str] = []
    if any(k in lower for k in ["location", "gps", "geolocation"]): flags.append("uses_location")
    if any(k in lower for k in ["camera", "photo", "webcam"]): flags.append("uses_camera")
    if any(k in lower for k in ["microphone", "voice", "audio recording"]): flags.append("uses_microphone")
    if any(k in lower for k in ["purchase", "subscription", "in-app", "payment"]): flags.append("in_app_purchases")
    if re.search(r"\bsell\b.{0,30}\b(data|information)\b", lower): flags.append("sells_data")
    if re.search(r"\bdelete\b.{0,30}\b(account|data)\b", lower): flags.append("deletes_on_request")
    if "encrypt" in lower: flags.append("encryption")
    if any(k in lower for k in ["law enforcement", "police", "government request"]): flags.append("shares_with_police")
    return flags


def _llm_rewrite_batch(
    clauses_data: list[dict[str, str]],
    group: str,
    grade: int,
    use_cache: bool,
) -> dict[str, tuple[str, str]]:
    """
    Rewrite all clauses in a SINGLE Gemini call instead of one call per clause.
    Reduces N LLM calls → 1 LLM call, cutting Kids Mode from 30-60s to ~5s.

    Returns: {category: (kids_summary, one_liner)}
    """
    age_desc = {"child": "8-10 year old child", "junior": "11-13 year old pre-teen", "teen": "14-17 year old teenager"}
    desc = age_desc.get(group, "teenager")
    grade_desc = f"Grade {grade} reading level"

    summaries_json = [
        {"category": c["category"], "label": c["label"], "text": c["text"][:300]}
        for c in clauses_data
    ]

    prompt = f"""Rewrite these privacy policy sections for a {desc} ({grade_desc}).
Use simple, friendly language. Be honest about risks. Max 2 sentences each.

Sections:
{summaries_json}

Return ONLY valid JSON in this exact format:
{{"rewrites": [{{"category": "category_name", "kids_summary": "friendly explanation", "one_liner": "one short sentence"}}]}}

Rules:
- kids_summary: 1-2 sentences, plain words, honest about data risks
- one_liner: max 10 words, the single most important thing
- No markdown, no extra text, ONLY the JSON"""

    try:
        resp, _ = call_gemini(prompt, function_name="kids_rewriter_batch", use_cache=use_cache)
        raw = parse_json_response(resp)
        if isinstance(raw, dict) and "rewrites" in raw:
            return {
                r["category"]: (str(r.get("kids_summary", "")), str(r.get("one_liner", "")))
                for r in raw["rewrites"]
                if isinstance(r, dict) and "category" in r
            }
    except Exception as exc:
        logger.warning("Kids batch rewrite failed: %s", exc)
    return {}


def _verdict(clauses: list[KidsClause]) -> tuple[str, str]:
    """
    Rule-based safety verdict — no LLM required.

    Returns: (verdict_str, verdict_emoji)

    Academic ref: UK Age Appropriate Design Code (2021) — risk assessment
    """
    critical = sum(1 for c in clauses if c.risk_level == "critical")
    high     = sum(1 for c in clauses if c.risk_level == "high")
    sells    = any("sells_data" in c.feature_flags for c in clauses)
    kids_bad = any(c.category == "children_data" and c.risk_level in ["high", "critical"] for c in clauses)
    if critical >= 1 or high >= 4 or sells or kids_bad:
        return "BE_CAREFUL", "\U0001f6d1"
    if high >= 2:
        return "ASK_PARENT", "\u26a0\ufe0f"
    return "SAFE", "\u2705"


def rewrite_for_kids(plain_clauses, clause_risks, age: int, use_cache: bool = True) -> KidsReport:
    """
    Produce a KidsReport from PlainClause + ClauseRisk lists for a given age.

    Args:
        plain_clauses: list[PlainClause] from nlp.plain_rewriter
        clause_risks:  list[ClauseRisk] from nlp.mad_engine
        age: user age integer (determines grade level and vocabulary)
        use_cache: cache LLM responses to avoid repeated API calls

    Returns:
        KidsReport with verdict, clause cards, emoji summary

    Academic ref:
        COPPA (1998); UK Age Appropriate Design Code (2021)
        Sweller (1988) Cognitive Load Theory
    """
    group = _age_group(age)
    grade = _GRADE_MAP[group]
    risk_map = {r.category: r for r in clause_risks}
    kids_clauses: list[KidsClause] = []

    # Sort by risk (high-risk first) and cap at 6 categories to keep response fast
    def _risk_order(pc) -> int:
        cr = risk_map.get(pc.category)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return order.get(cr.risk_level if cr else "low", 3)

    sorted_clauses = sorted(plain_clauses, key=_risk_order)[:6]

    # Single batch LLM call for all clauses (1 call vs N calls)
    llm_results: dict[str, tuple[str, str]] = {}
    if GEMINI_API_KEY and sorted_clauses:
        try:
            from nlp.plain_rewriter import CATEGORY_LABELS
        except Exception:
            CATEGORY_LABELS = {}
        clauses_data = [
            {
                "category": pc.category,
                "label": CATEGORY_LABELS.get(pc.category, pc.category.replace("_", " ")),
                "text": pc.plain_summary,
            }
            for pc in sorted_clauses
        ]
        llm_results = _llm_rewrite_batch(clauses_data, group, grade, use_cache)

    for pc in sorted_clauses:
        cr = risk_map.get(pc.category)
        risk_level = cr.risk_level if cr else "low"
        features = detect_features(pc.plain_summary)

        summary, one_liner = llm_results.get(pc.category, ("", ""))

        if not summary:
            label = getattr(pc, "category_label", pc.category.replace("_", " "))
            summary = f"[DEMO] {label}: {pc.plain_summary[:120]}..."
            one_liner = f"About {pc.category.replace('_', ' ')}"

        kids_clauses.append(KidsClause(
            category=pc.category,
            emoji=DATA_SIGNALS.get(pc.category, "\U0001f4cb"),
            risk_emoji=RISK_EMOJIS.get(risk_level, "\u26a0\ufe0f"),
            kids_summary=summary,
            one_liner=one_liner[:80],
            risk_level=risk_level,
            feature_flags=features,
        ))

    verdict, v_emoji = _verdict(kids_clauses)
    reason = _VERDICT_MSGS.get(group, _VERDICT_MSGS["teen"])[verdict]
    high_risk = [c for c in kids_clauses if c.risk_level in ["high", "critical"]]
    low_risk  = [c for c in kids_clauses if c.risk_level == "low"]
    concerns  = [c.one_liner.replace("[DEMO] ", "") for c in high_risk[:3]]
    positives = [c.one_liner.replace("[DEMO] ", "") for c in low_risk[:3]]
    top5      = "".join(DATA_SIGNALS.get(c.category, "\U0001f4cb") for c in kids_clauses[:5])

    return KidsReport(
        age_group=group, target_grade=grade, clauses=kids_clauses,
        verdict=verdict, verdict_emoji=v_emoji, verdict_reason=reason,
        top_concerns=concerns, top_positives=positives, overall_emoji_summary=top5,
    )
