"""
visualisation/risk_heatmap.py -- Privacy risk heatmap chart.

X: 12 clause categories.  Y: 5 risk dimensions.  Z: risk score 0-100.
Uses DUMMY DATA when clause_risks list is empty (no API key needed).

Author: Sateesh Kumar Payyavula
Reference: Wilson et al. (2016) OPP-115 taxonomy
"""

import plotly.graph_objects as go

CATEGORY_ABBREV: dict[str, str] = {
    "data_collection": "Data Collect.", "purpose_limitation": "Purpose",
    "retention_period": "Retention", "third_party_sharing": "3rd Party",
    "user_rights": "User Rights", "consent_mechanism": "Consent",
    "data_security": "Security", "breach_notification": "Breach",
    "children_data": "Children", "cross_border_transfer": "Cross-Border",
    "cookies_tracking": "Cookies", "contact_info": "Contact",
}
RISK_DIMS = ["Data Sensitivity", "Sharing Scope", "User Control", "Transparency", "Compliance"]

_DUMMY = [
    ("data_collection", 65), ("third_party_sharing", 80), ("cookies_tracking", 55),
    ("user_rights", 20), ("data_security", 40), ("retention_period", 70),
    ("children_data", 30), ("purpose_limitation", 45),
]


def _to_grid(clause_risks: list) -> tuple[list[str], list[list[float]]]:
    """
    Build category list and Z matrix from clause risks.

    Returns:
        (categories, z_matrix) where z_matrix[dim][cat] = score
    """
    cats = list(dict.fromkeys(c.category for c in clause_risks)) if clause_risks else [r[0] for r in _DUMMY]
    score_map = ({c.category: c.final_score for c in clause_risks}
                 if clause_risks else {r[0]: r[1] for r in _DUMMY})

    z = []
    for dim_i, dim in enumerate(RISK_DIMS):
        row = []
        for cat in cats:
            s = score_map.get(cat, 50.0)
            if dim == "User Control":     s = max(0.0, 100.0 - s)
            elif dim == "Sharing Scope":  s = min(100.0, s * (1.2 if "sharing" in cat or "cross" in cat else 0.85))
            elif dim == "Compliance":     s = min(100.0, s * 1.05)
            elif dim == "Transparency":   s = s * 0.9
            row.append(round(min(100.0, max(0.0, s)), 1))
        z.append(row)
    return cats, z


def create_risk_heatmap(clause_risks: list, policy_name: str = "Policy") -> go.Figure:
    """
    Create a colour-coded risk heatmap over 5 dimensions × 12 categories.

    Args:
        clause_risks: list[ClauseRisk] from mad_engine (empty = use dummy data)
        policy_name: displayed in chart title

    Returns:
        plotly Figure (900×450px)

    Academic ref:
        Wilson et al. (2016) OPP-115 -- 12-category taxonomy standard
    """
    cats, z = _to_grid(clause_risks)
    x_labels = [CATEGORY_ABBREV.get(c, c) for c in cats]

    colorscale = [
        [0.00, "#2ECC71"], [0.25, "#2ECC71"],
        [0.26, "#F39C12"], [0.50, "#F39C12"],
        [0.51, "#E67E22"], [0.75, "#E67E22"],
        [0.76, "#E74C3C"], [1.00, "#E74C3C"],
    ]
    demo_note = "" if clause_risks else " (demo data — run Analysis for real scores)"
    fig = go.Figure(go.Heatmap(
        z=z, x=x_labels, y=RISK_DIMS,
        colorscale=colorscale, zmin=0, zmax=100,
        colorbar=dict(title="Risk 0-100"),
        hovertemplate="%{x}<br>%{y}: %{z:.0f}/100<extra></extra>",
    ))
    fig.update_layout(
        title=f"Privacy Risk Heatmap — {policy_name}{demo_note}",
        width=900, height=450,
        xaxis_title="Policy Category", yaxis_title="Risk Dimension",
        font=dict(size=12), margin=dict(l=130, b=80),
    )
    return fig
