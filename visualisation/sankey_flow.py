"""
visualisation/sankey_flow.py -- Data flow Sankey diagram for PrivacyLens.

Shows: Your Data types --> Recipients --> Purposes.
Hardcoded links for demo; enriched by real clause data when available.

Author: Sateesh Kumar Payyavula
Reference: Adhikari, Das & Dewri (2025, arXiv:2501.10319) -- data flow viz
"""

import plotly.graph_objects as go

_DATA_SOURCES = ["Your Name", "Email", "Location", "Device Info", "Usage Data", "Payment Info"]
_RECIPIENTS   = ["The Company", "Advertisers", "Analytics Partners", "Government/Legal", "Subsidiaries"]
_PURPOSES     = ["Service Operation", "Personalisation", "Advertising", "Legal Compliance", "Research"]

_ALL_NODES = _DATA_SOURCES + _RECIPIENTS + _PURPOSES

_DS  = len(_DATA_SOURCES)
_REC = len(_RECIPIENTS)

def _node_idx(name: str) -> int:
    return _ALL_NODES.index(name)

_C_LOW  = "rgba(46,204,113,0.4)"
_C_MED  = "rgba(243,156,18,0.4)"
_C_HIGH = "rgba(231,76,60,0.4)"

_BASE_LINKS = [
    # (source_name, target_name, value, colour)
    ("Your Name",    "The Company",        4, _C_LOW),
    ("Email",        "The Company",        4, _C_LOW),
    ("Email",        "Analytics Partners", 2, _C_MED),
    ("Usage Data",   "Advertisers",        5, _C_HIGH),
    ("Usage Data",   "Analytics Partners", 3, _C_MED),
    ("Location",     "Advertisers",        4, _C_HIGH),
    ("Location",     "The Company",        2, _C_MED),
    ("Device Info",  "The Company",        3, _C_LOW),
    ("Device Info",  "Analytics Partners", 2, _C_MED),
    ("Payment Info", "The Company",        3, _C_LOW),
    ("The Company",  "Service Operation",  5, _C_LOW),
    ("The Company",  "Legal Compliance",   3, _C_LOW),
    ("Advertisers",  "Advertising",        6, _C_HIGH),
    ("Advertisers",  "Personalisation",    4, _C_MED),
    ("Analytics Partners", "Research",     3, _C_MED),
    ("Analytics Partners", "Personalisation", 3, _C_MED),
    ("Government/Legal", "Legal Compliance", 2, _C_LOW),
    ("Subsidiaries", "Service Operation",  2, _C_LOW),
]

# Recipient → Purpose second-hop links
_HOP2_LINKS = [
    ("The Company", "Service Operation", 3, _C_LOW),
    ("Advertisers", "Advertising", 4, _C_HIGH),
]

_NODE_COLOURS = (
    ["#3498db"] * len(_DATA_SOURCES) +
    ["#e67e22"] * len(_RECIPIENTS) +
    ["#2ecc71"] * len(_PURPOSES)
)


def create_sankey(clauses: list, policy_name: str = "Policy") -> go.Figure:
    """
    Create a data-flow Sankey: Data → Recipients → Purposes.

    Uses hardcoded demo flows by default.
    Attempts to enrich from third_party_sharing clauses if provided.

    Args:
        clauses: list[ClauseResult] from clause_extractor (can be empty)
        policy_name: displayed in chart title

    Returns:
        plotly Figure (1000×550px)

    Academic ref:
        Adhikari, Das & Dewri (2025, arXiv:2501.10319) -- data flow analysis
    """
    links = list(_BASE_LINKS)

    # Enrich from real clauses where possible
    if clauses:
        for clause in clauses:
            if clause.category not in ("third_party_sharing", "purpose_limitation"):
                continue
            lower = clause.original_text.lower()
            if "advertis" in lower:
                links.append(("Usage Data", "Advertisers", 2, _C_HIGH))
            if "government" in lower or "law enforcement" in lower:
                links.append(("Your Name", "Government/Legal", 2, _C_MED))
            if "research" in lower or "analytic" in lower:
                links.append(("Usage Data", "Analytics Partners", 1, _C_MED))

    sources = [_node_idx(s) for s, _, _, _ in links]
    targets = [_node_idx(t) for _, t, _, _ in links]
    values  = [v for _, _, v, _ in links]
    colours = [c for _, _, _, c in links]

    demo_note = "" if clauses else " (demo flow — run Analysis for real data)"
    fig = go.Figure(go.Sankey(
        node=dict(
            label=_ALL_NODES,
            color=_NODE_COLOURS,
            pad=15, thickness=20,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(source=sources, target=targets, value=values, color=colours),
    ))
    fig.update_layout(
        title=f"Your Data Flow — {policy_name}{demo_note}",
        width=1000, height=550,
        font=dict(size=11), margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
