"""
nlp/compliance_mapper.py -- Multi-regulation compliance mapping for PrivacyLens.

Maps extracted clauses to GDPR, CCPA, and India DPDP Act 2023 articles.
Identifies required disclosures that are present, partial, or missing.
Scores 0-100 per regulation and per GDPR radar dimension.

Academic ref:
    Xie et al. (USENIX Security 2025) -- comprehensive privacy law compliance
    dataset and clause taxonomy; our mapping tables follow their approach.
    GDPR (2018), CCPA (2018/2020), India DPDP Act (2023)

Author: Sateesh Kumar Payyavula
"""

import logging
import re
from pydantic import BaseModel
from config import GEMINI_API_KEY
from nlp.clause_extractor import ClauseResult

logger = logging.getLogger(__name__)

# ── Legal mapping tables ──────────────────────────────────────────────────────

GDPR_CATEGORY_MAP: dict[str, list[str]] = {
    "data_collection":       ["Art. 5(1)(a)", "Art. 13(1)(c)"],
    "purpose_limitation":    ["Art. 5(1)(b)", "Art. 13(1)(c)"],
    "retention_period":      ["Art. 5(1)(e)", "Art. 13(2)(a)"],
    "third_party_sharing":   ["Art. 13(1)(e)", "Art. 44-49"],
    "user_rights":           ["Art. 15", "Art. 16", "Art. 17",
                              "Art. 18", "Art. 20", "Art. 21"],
    "consent_mechanism":     ["Art. 6(1)(a)", "Art. 7"],
    "data_security":         ["Art. 32"],
    "breach_notification":   ["Art. 33", "Art. 34"],
    "children_data":         ["Art. 8"],
    "cross_border_transfer": ["Art. 44", "Art. 45", "Art. 46"],
    "cookies_tracking":      ["Art. 5(1)(a)", "Art. 6"],
    "contact_info":          ["Art. 13(1)(a)", "Art. 13(1)(b)"],
}

CCPA_CATEGORY_MAP: dict[str, list[str]] = {
    "data_collection":       ["§1798.100", "§1798.110"],
    "third_party_sharing":   ["§1798.115", "§1798.120"],
    "user_rights":           ["§1798.100", "§1798.105",
                              "§1798.106", "§1798.120"],
    "consent_mechanism":     ["§1798.120", "§1798.135"],
    "children_data":         ["§1798.120(c)"],
    "data_security":         ["§1798.150"],
    "contact_info":          ["§1798.130"],
}

DPDP_CATEGORY_MAP: dict[str, list[str]] = {
    "data_collection":       ["§6", "§7"],
    "purpose_limitation":    ["§6(1)"],
    "retention_period":      ["§8(7)"],
    "user_rights":           ["§11", "§12", "§13", "§14"],
    "consent_mechanism":     ["§6", "§9"],
    "data_security":         ["§8"],
    "breach_notification":   ["§8(6)"],
    "children_data":         ["§9"],
    "cross_border_transfer": ["§16"],
    "contact_info":          ["§8(10)"],
}

# ── Required disclosures checklists ───────────────────────────────────────────
# (article, description, category_key, severity)

GDPR_REQUIRED = [
    ("Art. 13(1)(a)", "Identity of data controller",         "contact_info",         "critical"),
    ("Art. 13(1)(c)", "Purposes and legal basis of processing","purpose_limitation",  "critical"),
    ("Art. 13(2)(a)", "Data retention period",               "retention_period",     "high"),
    ("Art. 13(1)(e)", "Recipients of personal data",         "third_party_sharing",  "high"),
    ("Art. 17",       "Right to erasure (right to be forgotten)", "user_rights",     "high"),
    ("Art. 20",       "Right to data portability",           "user_rights",          "medium"),
    ("Art. 33",       "Data breach notification procedure",  "breach_notification",  "medium"),
    ("Art. 8",        "Children's data protection measures", "children_data",        "high"),
    ("Art. 44",       "Cross-border transfer safeguards",    "cross_border_transfer","high"),
    ("Art. 32",       "Technical security measures described","data_security",       "medium"),
]

CCPA_REQUIRED = [
    ("§1798.100", "Right to know what personal data is collected","data_collection",  "critical"),
    ("§1798.105", "Right to delete personal information",     "user_rights",         "critical"),
    ("§1798.120", "Right to opt-out of sale of personal info","user_rights",         "critical"),
    ("§1798.130", "Designated contact method for requests",   "contact_info",        "high"),
    ("§1798.135", "Opt-out link / Do Not Sell My Info",       "consent_mechanism",   "high"),
]

DPDP_REQUIRED = [
    ("§6",   "Consent notice provided before data collection","consent_mechanism",   "critical"),
    ("§8(7)","Retention limited to purpose-necessary period", "retention_period",    "high"),
    ("§11",  "Right to access personal data",                 "user_rights",         "critical"),
    ("§12",  "Right to correction and erasure",               "user_rights",         "critical"),
    ("§9",   "Children's data — verifiable parental consent", "children_data",       "critical"),
    ("§16",  "Cross-border data transfer conditions stated",  "cross_border_transfer","high"),
]


# ── Pydantic models ───────────────────────────────────────────────────────────

class LegalMapping(BaseModel):
    """Compliance mapping for a single clause."""
    clause_id: str
    category: str
    gdpr_articles: list[str]
    ccpa_sections: list[str]
    dpdp_sections: list[str]
    compliance_score: float
    gaps: list[str]


class ComplianceGap(BaseModel):
    """A single required legal disclosure that is missing or partial."""
    regulation: str
    article: str
    requirement: str
    status: str       # "PRESENT" | "PARTIAL" | "MISSING"
    evidence: str
    severity: str


class ComplianceReport(BaseModel):
    """Full multi-regulation compliance report."""
    gdpr_score: float
    ccpa_score: float
    dpdp_score: float
    eu_ai_act_score: float = 0.0
    overall_score: float
    mappings: list[LegalMapping]
    gaps: list[ComplianceGap]
    critical_gaps: list[ComplianceGap]
    radar_scores: dict[str, float]  # 8 GDPR radar dimensions
    eu_ai_act_gaps: list[ComplianceGap] = []


# ── Helper functions ──────────────────────────────────────────────────────────

def _categories_present(clauses: list[ClauseResult]) -> dict[str, list[ClauseResult]]:
    """Group clauses by category."""
    result: dict[str, list[ClauseResult]] = {}
    for c in clauses:
        result.setdefault(c.category, []).append(c)
    return result


def _check_status(cat: str, cat_map: dict[str, list[ClauseResult]]) -> str:
    """Return PRESENT, PARTIAL, or MISSING based on whether category has clauses."""
    if cat not in cat_map:
        return "MISSING"
    clauses = cat_map[cat]
    if not clauses:
        return "MISSING"
    # PARTIAL if only one short clause; PRESENT if substantive
    total_len = sum(len(c.original_text) for c in clauses)
    return "PRESENT" if total_len > 200 else "PARTIAL"


def _status_score(status: str) -> float:
    return {"PRESENT": 1.0, "PARTIAL": 0.5, "MISSING": 0.0}.get(status, 0.0)


def _evidence(cat: str, cat_map: dict[str, list[ClauseResult]]) -> str:
    if cat not in cat_map or not cat_map[cat]:
        return "Not found in policy"
    return cat_map[cat][0].original_text[:120] + "..."


def _build_gaps(
    required: list[tuple],
    reg: str,
    cat_map: dict[str, list[ClauseResult]],
) -> list[ComplianceGap]:
    gaps = []
    for article, requirement, category, severity in required:
        status = _check_status(category, cat_map)
        if status != "PRESENT":
            gaps.append(ComplianceGap(
                regulation=reg,
                article=article,
                requirement=requirement,
                status=status,
                evidence=_evidence(category, cat_map),
                severity=severity,
            ))
    return gaps


def _score(required: list[tuple], cat_map: dict[str, list[ClauseResult]]) -> float:
    if not required:
        return 100.0
    total = sum(_status_score(_check_status(cat, cat_map)) for _, _, cat, _ in required)
    return round(total / len(required) * 100, 1)


def _normalise_radar(scores: dict[str, float]) -> dict[str, float]:
    """
    Prevent extreme spikes: floor 10, ceiling 95.
    Ensures all 8 dimensions have visible presence on the radar chart.
    """
    return {k: max(10.0, min(95.0, float(v))) for k, v in scores.items()}


def _radar_scores(cat_map: dict[str, list[ClauseResult]]) -> dict[str, float]:
    """
    Compute 8 GDPR radar dimension scores (0-100, higher = better compliance).

    Academic ref: GDPR (2018) Art. 5, 6, 7, 13, 32, 33 -- data protection principles.
    """
    def inv(cat: str) -> float:
        status = _check_status(cat, cat_map)
        return {"PRESENT": 85.0, "PARTIAL": 50.0, "MISSING": 15.0}.get(status, 15.0)

    return {
        "Lawful Basis (Art.6)":       inv("consent_mechanism"),
        "Transparency (Art.13)":       inv("contact_info"),
        "Data Minimisation (Art.5)":   inv("data_collection"),
        "Purpose Limitation (Art.5)":  inv("purpose_limitation"),
        "Retention Limits (Art.5)":    inv("retention_period"),
        "User Rights (Art.15-22)":     inv("user_rights"),
        "Security (Art.32)":           inv("data_security"),
        "Breach Notification (Art.33)":inv("breach_notification"),
    }


# ── EU AI Act Art.50 ─────────────────────────────────────────────────────────

_EU_AI_ACT_CHECKS: list[tuple] = [
    # (article, requirement, keywords, severity)
    (
        "Art.50(1)",
        "Discloses use of AI systems or automated processing in services",
        ["artificial intelligence", "automated system", "ai-powered", "machine learning",
         "chatbot", "virtual assistant", "automated decision", "automated processing"],
        "high",
    ),
    (
        "Art.50(2)",
        "Discloses emotion recognition or biometric categorization AI use",
        ["emotion recognition", "biometric categorization", "sentiment analysis",
         "facial recognition", "emotional state", "biometric data"],
        "high",
    ),
    (
        "Art.50(3)",
        "Labels or discloses AI-generated or synthetic content",
        ["ai-generated", "ai generated", "generated by ai", "synthetic content",
         "deepfake", "generated by artificial intelligence", "computer-generated"],
        "medium",
    ),
    (
        "Art.50(4)",
        "Provides right to human oversight for automated decisions",
        ["human review", "right to explanation", "not solely automated",
         "human oversight", "contest automated", "human involvement"],
        "high",
    ),
]


def _check_eu_ai_act(
    clauses: list[ClauseResult],
) -> tuple[float, list[ComplianceGap]]:
    """
    Score EU AI Act Art.50 transparency requirements against policy text.

    Academic ref:
        EU AI Act (Regulation 2024/1689), Art.50 -- Transparency obligations
        for providers and deployers of certain AI systems.
        Enforcement begins August 2, 2026.
    """
    full_lower = " ".join(c.original_text for c in clauses).lower()

    def _status(keywords: list[str]) -> str:
        return "PRESENT" if any(re.search(kw, full_lower) for kw in keywords) else "MISSING"

    def _evidence(keywords: list[str]) -> str:
        for c in clauses:
            t = c.original_text.lower()
            if any(kw in t for kw in keywords[:3]):
                return c.original_text[:120] + "..."
        return "Not found in policy"

    gaps: list[ComplianceGap] = []
    score_sum = 0.0
    for article, requirement, keywords, severity in _EU_AI_ACT_CHECKS:
        status = _status(keywords)
        score_sum += _status_score(status)
        if status != "PRESENT":
            gaps.append(ComplianceGap(
                regulation="EU AI Act",
                article=article,
                requirement=requirement,
                status=status,
                evidence=_evidence(keywords),
                severity=severity,
            ))

    score = round(score_sum / len(_EU_AI_ACT_CHECKS) * 100, 1)
    return score, gaps


# ── Public API ────────────────────────────────────────────────────────────────

def _text_compliance_estimate(text: str) -> ComplianceReport:
    """Keyword-based compliance estimate when clauses list is empty."""
    t = text.lower()
    gdpr_hits = sum(1 for kw in [
        "right to erasure", "right to access", "data portability", "lawful basis",
        "consent", "legitimate interest", "data controller", "dpo",
        "breach notification", "privacy by design",
    ] if kw in t)
    ccpa_hits = sum(1 for kw in [
        "california", "ccpa", "do not sell", "opt-out",
        "right to know", "right to delete",
    ] if kw in t)
    dpdp_hits = sum(1 for kw in [
        "india", "dpdp", "data fiduciary", "data principal", "grievance",
    ] if kw in t)

    gdpr = min(round(gdpr_hits / 10 * 100), 80)
    ccpa = min(round(ccpa_hits / 6 * 100), 80)
    dpdp = min(round(dpdp_hits / 5 * 100), 80)
    overall = round((gdpr + ccpa + dpdp) / 3, 1)
    return ComplianceReport(
        gdpr_score=float(gdpr), ccpa_score=float(ccpa), dpdp_score=float(dpdp),
        eu_ai_act_score=0.0, overall_score=overall,
        mappings=[], gaps=[], critical_gaps=[], eu_ai_act_gaps=[],
        radar_scores={
            "Lawful Basis (Art.6)": float(gdpr),
            "Transparency (Art.13)": float(gdpr),
            "Data Minimisation (Art.5)": 15.0,
            "Purpose Limitation (Art.5)": 15.0,
            "Retention Limits (Art.5)": 15.0,
            "User Rights (Art.15-22)": float(gdpr),
            "Security (Art.32)": 15.0,
            "Breach Notification (Art.33)": 15.0,
        },
    )


def map_compliance(
    clauses: list[ClauseResult],
    use_cache: bool = True,
    policy_text: str = "",
) -> ComplianceReport:
    """
    Map policy clauses to GDPR, CCPA, and DPDP Act requirements.

    Identifies present, partial, and missing required disclosures.
    Most scoring is rule-based; LLM only used for disambiguation.

    Args:
        clauses: list[ClauseResult] from clause_extractor
        use_cache: passed through to LLM calls if any

    Returns:
        ComplianceReport with scores, gaps, and radar dimensions

    Academic ref:
        Xie et al. (USENIX Security 2025) -- privacy law compliance taxonomy
        GDPR (2018), CCPA (2018/2020 amended), India DPDP Act (2023)
    """
    if not clauses:
        logger.warning("map_compliance called with 0 clauses — using text-based estimate")
        return _text_compliance_estimate(policy_text)

    cat_map = _categories_present(clauses)

    # Build per-clause mappings
    mappings: list[LegalMapping] = []
    for cat, clause_list in cat_map.items():
        gdpr = GDPR_CATEGORY_MAP.get(cat, [])
        ccpa = CCPA_CATEGORY_MAP.get(cat, [])
        dpdp = DPDP_CATEGORY_MAP.get(cat, [])
        # Simple scoring: presence of at least one clause = reasonable compliance
        total_regs = len(gdpr) + len(ccpa) + len(dpdp)
        comp_score = min(100.0, 50.0 + (total_regs * 5.0)) if clause_list else 0.0
        mappings.append(LegalMapping(
            clause_id=clause_list[0].clause_id if clause_list else "",
            category=cat,
            gdpr_articles=gdpr,
            ccpa_sections=ccpa,
            dpdp_sections=dpdp,
            compliance_score=round(comp_score, 1),
            gaps=[],
        ))

    # Build gaps
    gdpr_gaps = _build_gaps(GDPR_REQUIRED, "GDPR", cat_map)
    ccpa_gaps = _build_gaps(CCPA_REQUIRED, "CCPA", cat_map)
    dpdp_gaps = _build_gaps(DPDP_REQUIRED, "DPDP", cat_map)
    all_gaps = gdpr_gaps + ccpa_gaps + dpdp_gaps
    critical_gaps = [g for g in all_gaps if g.severity == "critical"]

    gdpr_score = _score(GDPR_REQUIRED, cat_map)
    ccpa_score = _score(CCPA_REQUIRED, cat_map)
    dpdp_score = _score(DPDP_REQUIRED, cat_map)
    eu_ai_score, eu_ai_gaps = _check_eu_ai_act(clauses)
    overall = round((gdpr_score + ccpa_score + dpdp_score + eu_ai_score) / 4, 1)

    all_eu_critical = [g for g in eu_ai_gaps if g.severity == "critical"]
    all_critical = critical_gaps + all_eu_critical

    return ComplianceReport(
        gdpr_score=gdpr_score,
        ccpa_score=ccpa_score,
        dpdp_score=dpdp_score,
        eu_ai_act_score=eu_ai_score,
        overall_score=overall,
        mappings=mappings,
        gaps=all_gaps + eu_ai_gaps,
        critical_gaps=all_critical,
        radar_scores=_normalise_radar(_radar_scores(cat_map)),
        eu_ai_act_gaps=eu_ai_gaps,
    )
