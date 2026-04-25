"""
visualisation/gdpr_radar.py -- GDPR compliance radar chart for PrivacyLens.

8-dimension spider chart comparing 'This Policy' vs 'GDPR Ideal' (100).
Uses demo scores when no risk_report is provided.

Author: Sateesh Kumar Payyavula
Reference: GDPR (2018) Art. 5, 6, 7, 13, 32, 33
"""

import plotly.graph_objects as go

GDPR_DIMENSIONS = [
    "Lawful Basis (Art.6)",
    "Transparency (Art.13)",
    "Data Minimisation (Art.5)",
    "Purpose Limitation (Art.5)",
    "Retention Limits (Art.5)",
    "User Rights (Art.15-22)",
    "Security (Art.32)",
    "Breach Notification (Art.33)",
]

_DEMO_SCORES = [65, 45, 70, 55, 40, 80, 60, 50]

_CAT_DIM_MAP = {
    "consent_mechanism":    0,  # Lawful Basis
    "purpose_limitation":   0,
    "data_collection":      1,  # Transparency (inverted)
    "data_collection_min":  2,  # Data Minimisation (inverted)
    "purpose_limitation_2": 3,  # Purpose Limitation (inverted)
    "retention_period":     4,  # Retention Limits (inverted)
    "user_rights":          5,  # User Rights (inverted)
    "data_security":        6,  # Security (inverted)
    "breach_notification":  7,  # Breach Notification (inverted)
}


def _scores_from_report(risk_report) -> list[float]:
    """
    Derive 8 GDPR compliance scores from a PolicyRiskReport.

    Higher score = better compliance (inverts risk scores).

    Academic ref: GDPR (2018) Art. 5 -- data protection principles
    """
    cat_scores: dict[str, float] = {cr.category: cr.final_score for cr in risk_report.clause_risks}

    def inv(cat: str, default: float = 50.0) -> float:
        """Invert risk score to compliance score."""
        return round(max(0.0, 100.0 - cat_scores.get(cat, default)), 1)

    return [
        inv("consent_mechanism"),     # Lawful Basis
        inv("data_collection"),        # Transparency
        inv("data_collection"),        # Data Minimisation
        inv("purpose_limitation"),     # Purpose Limitation
        inv("retention_period"),       # Retention Limits
        inv("user_rights"),            # User Rights
        inv("data_security"),          # Security
        inv("breach_notification"),    # Breach Notification
    ]


def create_gdpr_radar(
    risk_report=None,
    compliance_report=None,
    policy_name: str = "Policy",
) -> go.Figure:
    """
    Create a GDPR compliance radar chart (8 dimensions).

    Shows 'This Policy' vs the GDPR ideal (100 on all dimensions).
    Prefers radar_scores from ComplianceReport if provided (Phase 7+),
    falls back to risk_report-derived scores, then demo scores.

    Args:
        risk_report: PolicyRiskReport from mad_engine (None = use demo)
        compliance_report: ComplianceReport from compliance_mapper (preferred)
        policy_name: displayed in chart title

    Returns:
        plotly Figure (600×600px)

    Academic ref:
        GDPR (2018) Art. 5, 6, 7, 13, 32, 33 -- compliance dimensions
    """
    if compliance_report is not None and compliance_report.radar_scores:
        # Use real compliance scores ordered by GDPR_DIMENSIONS
        scores = [compliance_report.radar_scores.get(d, 50.0) for d in GDPR_DIMENSIONS]
    elif risk_report is not None:
        scores = _scores_from_report(risk_report)
    else:
        scores = list(_DEMO_SCORES)
    ideal  = [100] * 8

    # Close the polygon
    dims_c   = GDPR_DIMENSIONS + [GDPR_DIMENSIONS[0]]
    scores_c = scores + [scores[0]]
    ideal_c  = ideal  + [ideal[0]]

    demo_note = "" if risk_report else " (demo — run Analysis for real data)"
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=ideal_c, theta=dims_c, fill="toself",
        name="GDPR Ideal",
        fillcolor="rgba(46,204,113,0.15)",
        line=dict(color="#2ecc71", dash="dot", width=2),
    ))
    fig.add_trace(go.Scatterpolar(
        r=scores_c, theta=dims_c, fill="toself",
        name="This Policy",
        fillcolor="rgba(231,76,60,0.25)",
        line=dict(color="#e74c3c", width=2),
    ))

    fig.update_layout(
        title=f"GDPR Compliance Radar — {policy_name}{demo_note}",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10))),
        width=600, height=600,
        showlegend=True,
        legend=dict(x=0.8, y=1.1),
    )
    return fig
