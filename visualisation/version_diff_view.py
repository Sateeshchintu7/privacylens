"""
visualisation/version_diff_view.py -- Policy version comparison for PrivacyLens.

Compares two policy text versions using difflib, classifies changes,
and returns a Plotly horizontal bar chart showing what changed and how.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- policy change tracking study
"""

import difflib
from pydantic import BaseModel
import plotly.graph_objects as go

_CHANGE_COLOURS = {
    "IMPROVED": "#2ecc71", "UNCHANGED": "#bdc3c7",
    "WORSENED": "#e74c3c", "ADDED": "#3498db", "REMOVED": "#e67e22",
}

_DUMMY_DIFFS = [
    ("data_collection",     "WORSENED", "Collect name, email",        "Collect name, email, location, browsing", 30.0, "Data collection expanded to include location and browsing history"),
    ("third_party_sharing", "WORSENED", "Share with partners",         "Share and SELL to advertising networks",   45.0, "Changed from sharing to selling data to advertisers"),
    ("user_rights",         "IMPROVED", "Request deletion in 90 days", "Request deletion within 30 days",         -20.0, "Deletion response time improved from 90 to 30 days"),
    ("retention_period",    "WORSENED", "Keep data 1 year",            "Keep data 3 years or indefinitely",        35.0, "Data retention extended from 1 year to indefinite"),
    ("data_security",       "IMPROVED", "Industry standard encryption", "AES-256 encryption + annual audits",      -15.0, "Security measures strengthened with specifics"),
]


class PolicyDiff(BaseModel):
    """Represents a change in one policy category between two versions."""
    category: str
    change_type: str     # ADDED | REMOVED | WORSENED | IMPROVED | UNCHANGED
    old_text: str
    new_text: str
    risk_change: float   # positive = got worse, negative = improved
    summary: str


def compare_policies(old_text: str, new_text: str) -> list[PolicyDiff]:
    """
    Compare two versions of a policy text using paragraph-level difflib.

    Classifies each section as ADDED, REMOVED, WORSENED, IMPROVED, or UNCHANGED.

    Args:
        old_text: Previous policy text
        new_text: Updated policy text

    Returns:
        list[PolicyDiff] -- one entry per changed section

    Academic ref:
        Reidenberg et al. (2015) -- privacy policy change analysis
    """
    old_paras = [p.strip() for p in old_text.split("\n\n") if p.strip()]
    new_paras = [p.strip() for p in new_text.split("\n\n") if p.strip()]

    if not old_paras or not new_paras:
        return []

    diffs: list[PolicyDiff] = []
    matcher = difflib.SequenceMatcher(None, old_paras, new_paras)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = " ".join(old_paras[i1:i2])[:300]
        new_chunk = " ".join(new_paras[j1:j2])[:300]

        if tag == "equal":
            change_type = "UNCHANGED"
            risk_change = 0.0
            summary = "No change in this section"
        elif tag == "insert":
            change_type = "ADDED"
            risk_change = len(new_chunk) / 200
            summary = f"New section added: {new_chunk[:80]}..."
        elif tag == "delete":
            change_type = "REMOVED"
            risk_change = 0.0
            summary = f"Section removed: {old_chunk[:80]}..."
        else:  # replace
            ratio = difflib.SequenceMatcher(None, old_chunk, new_chunk).ratio()
            risk_change = (len(new_chunk) - len(old_chunk)) / max(len(old_chunk), 1) * 50
            if risk_change > 5:
                change_type = "WORSENED"
                summary = f"Section expanded (may add risk): {new_chunk[:80]}..."
            elif risk_change < -5:
                change_type = "IMPROVED"
                summary = f"Section simplified (reduced risk): {new_chunk[:80]}..."
                risk_change = abs(risk_change)
            else:
                change_type = "UNCHANGED"
                summary = "Minor wording change, no significant risk shift"

        diffs.append(PolicyDiff(
            category=f"Section {i1+1}", change_type=change_type,
            old_text=old_chunk, new_text=new_chunk,
            risk_change=round(abs(risk_change), 1), summary=summary,
        ))

    return [d for d in diffs if d.change_type != "UNCHANGED"][:15]


def policy_diff_to_chart_diffs(tracker_diff) -> list[PolicyDiff]:
    """
    Convert a change_tracker.PolicyDiff into local PolicyDiff list
    for use with create_diff_timeline().

    Args:
        tracker_diff: ingestion.change_tracker.PolicyDiff

    Returns:
        list[PolicyDiff] ready for create_diff_timeline()
    """
    result: list[PolicyDiff] = []
    for change in (
        tracker_diff.worsened +
        tracker_diff.improved +
        tracker_diff.added +
        tracker_diff.removed
    ):
        result.append(PolicyDiff(
            category=change.category.replace("_", " ").title(),
            change_type=change.change_type,
            old_text=change.old_text[:200],
            new_text=change.new_text[:200],
            risk_change=abs(change.risk_delta),
            summary=change.plain_summary,
        ))
    return result


def create_diff_timeline(diffs, policy_name: str = "Policy") -> go.Figure:
    """
    Horizontal bar chart showing what changed between two policy versions.

    Uses demo data if diffs list is empty.

    Args:
        diffs: list[PolicyDiff] from compare_policies
        policy_name: displayed in chart title

    Returns:
        plotly Figure (800×400px)

    Academic ref: Reidenberg et al. (2015) -- policy version tracking
    """
    if not diffs:
        # Demo data
        use_diffs = [
            PolicyDiff(category=cat, change_type=ct, old_text=old, new_text=new,
                       risk_change=rc, summary=sm)
            for cat, ct, old, new, rc, sm in _DUMMY_DIFFS
        ]
        demo_note = " (demo — provide two policies above)"
    else:
        use_diffs = diffs
        demo_note = ""

    categories = [d.category for d in use_diffs]
    values     = [max(d.risk_change, 5) for d in use_diffs]  # min bar width 5
    colours    = [_CHANGE_COLOURS.get(d.change_type, "#888") for d in use_diffs]
    hovers     = [f"<b>{d.change_type}</b><br>{d.summary}" for d in use_diffs]

    fig = go.Figure(go.Bar(
        x=values, y=categories, orientation="h",
        marker_color=colours,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hovers,
    ))

    # Legend items
    for ct, colour in _CHANGE_COLOURS.items():
        fig.add_trace(go.Bar(x=[0], y=[""], name=ct, marker_color=colour,
                             showlegend=True, visible="legendonly"))

    fig.update_layout(
        title=f"Policy Version Changes — {policy_name}{demo_note}",
        xaxis_title="Change magnitude",
        width=800, height=max(300, len(use_diffs) * 40 + 100),
        barmode="overlay", showlegend=True,
    )
    return fig
