"""
pages/06_compare.py -- Policy Version Comparison UI for PrivacyLens.

Compare two versions of a privacy policy using ingestion/change_tracker.
Shows verdict banner, WORSENED/IMPROVED/ADDED/REMOVED change cards,
and a timeline chart.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- privacy policy change analysis
"""

import streamlit as st
from ingestion.text_cleaner import clean_text

st.set_page_config(page_title="PrivacyLens · Compare", page_icon="🔄", layout="wide")

st.markdown("""
<style>
  .verdict-improved { background:#2ecc71; color:#fff; padding:16px; border-radius:12px; text-align:center; }
  .verdict-worsened { background:#e74c3c; color:#fff; padding:16px; border-radius:12px; text-align:center; }
  .verdict-mixed    { background:#f39c12; color:#fff; padding:16px; border-radius:12px; text-align:center; }
  .verdict-unchanged{ background:#bdc3c7; color:#555; padding:16px; border-radius:12px; text-align:center; }
  .change-worsened  { background:#fde8e8; border-left:5px solid #e74c3c; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .change-improved  { background:#e8f8ee; border-left:5px solid #2ecc71; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .change-added     { background:#e8f0fe; border-left:5px solid #3498db; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .change-removed   { background:#fef3e8; border-left:5px solid #e67e22; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🔄 Compare Mode")
st.markdown("Compare two versions of a privacy policy — see exactly what changed and whether it got better or worse.")
st.divider()

_VERDICT_CSS = {
    "IMPROVED": "verdict-improved", "WORSENED": "verdict-worsened",
    "MIXED": "verdict-mixed", "UNCHANGED": "verdict-unchanged",
}
_CHANGE_CSS = {
    "WORSENED": "change-worsened", "IMPROVED": "change-improved",
    "ADDED": "change-added", "REMOVED": "change-removed",
}
_ICONS = {"WORSENED": "🔴", "IMPROVED": "🟢", "ADDED": "🔵", "REMOVED": "🟠"}

# ── Input section ─────────────────────────────────────────────────────────────
demo_mode = st.checkbox("Load demo comparison (Google Privacy Policy — simulated older vs current)", value=False)

if not demo_mode:
    # Pre-fill V1 from loaded policy
    if "policy_text" in st.session_state:
        use_loaded = st.checkbox(
            f"Use loaded policy as Version 1 ({st.session_state.get('policy_source','current')[:50]})",
            value=True,
        )
    else:
        use_loaded = False

    col_old, col_new = st.columns(2)
    with col_old:
        st.markdown("### Version 1 (older)")
        if use_loaded and "policy_text" in st.session_state:
            old_raw = st.session_state["policy_text"]
            st.info(f"Using: **{st.session_state.get('policy_source','loaded')[:50]}**")
            st.text_area("Preview", value=old_raw[:300] + "...", height=100, disabled=True, label_visibility="collapsed")
        else:
            old_raw = st.text_area("Paste OLD policy text", height=220, key="old_text",
                                   placeholder="Paste the earlier / previous version...")

    with col_new:
        st.markdown("### Version 2 (newer)")
        new_raw = st.text_area("Paste NEW policy text", height=220, key="new_text",
                               placeholder="Paste the updated / new version...")

    policy_name = st.text_input("Policy name", value=st.session_state.get("policy_source", "Policy")[:50])
    old_date    = st.text_input("Old version label", value="Previous version", key="old_date")
    new_date    = st.text_input("New version label", value="Current version", key="new_date")

    run_compare = st.button("🔍 Compare Versions", type="primary", key="btn_compare_main")

    if run_compare:
        if not old_raw or not new_raw:
            st.warning("Provide both policy versions to compare.")
            st.stop()
        if old_raw.strip() == new_raw.strip():
            st.info("The two versions appear identical.")
            st.stop()
        with st.spinner("Extracting clauses and comparing... (may take ~30s)"):
            from ingestion.change_tracker import compare_policies
            diff = compare_policies(
                old_text=clean_text(old_raw).text,
                new_text=clean_text(new_raw).text,
                policy_name=policy_name,
                old_date=old_date,
                new_date=new_date,
            )
        st.session_state["compare_diff"] = diff
        st.rerun()

else:
    # Demo mode
    if "compare_diff" not in st.session_state or not st.session_state.get("_compare_is_demo"):
        with st.spinner("Running demo comparison on Google Privacy Policy (~45s)..."):
            from ingestion.change_tracker import create_demo_diff
            diff = create_demo_diff()
        st.session_state["compare_diff"] = diff
        st.session_state["_compare_is_demo"] = True
        st.rerun()

# ── Show results ──────────────────────────────────────────────────────────────
if "compare_diff" in st.session_state:
    diff = st.session_state["compare_diff"]
    st.divider()

    # Verdict banner
    css_cls = _VERDICT_CSS.get(diff.verdict, "verdict-mixed")
    st.markdown(
        f"<div class='{css_cls}'>"
        f"<div style='font-size:36px'>{diff.verdict_emoji}</div>"
        f"<div style='font-size:20px;font-weight:bold;margin-top:4px'>{diff.verdict}</div>"
        f"<div style='font-size:14px;margin-top:4px;opacity:.92'>{diff.plain_summary}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Worsened", len(diff.worsened))
    m2.metric("Improved", len(diff.improved))
    m3.metric("Added",    len(diff.added))
    m4.metric("Removed",  len(diff.removed))
    delta_str = f"{diff.overall_risk_delta:+.1f}"
    m5.metric("Risk delta", delta_str, delta=delta_str, delta_color="inverse")

    # Timeline chart
    from visualisation.version_diff_view import create_diff_timeline, policy_diff_to_chart_diffs
    chart_diffs = policy_diff_to_chart_diffs(diff)
    if chart_diffs:
        st.plotly_chart(
            create_diff_timeline(chart_diffs, policy_name=diff.policy_name),
            use_container_width=True,
        )

    st.divider()

    # Change cards — worsened first
    def _render_changes(changes, title):
        if not changes:
            return
        st.markdown(f"#### {title}")
        for ch in changes:
            css = _CHANGE_CSS.get(ch.change_type, "")
            icon = _ICONS.get(ch.change_type, "⚪")
            cat  = ch.category.replace("_", " ").title()
            old_snip = (ch.old_text[:120] + "...") if len(ch.old_text) > 120 else ch.old_text
            new_snip = (ch.new_text[:120] + "...") if len(ch.new_text) > 120 else ch.new_text
            delta_html = f" · risk change: {ch.risk_delta:+.0f}" if ch.risk_delta else ""
            st.markdown(
                f"<div class='{css}'>"
                f"<b>{icon} {ch.change_type} — {cat}</b>{delta_html}<br>"
                f"<small>{ch.plain_summary}</small><br>"
                f"<table style='width:100%;margin-top:6px;font-size:12px'>"
                f"<tr><td style='width:50%;vertical-align:top;color:#777'><b>Before:</b> {old_snip}</td>"
                f"<td style='vertical-align:top;color:#555'><b>After:</b> {new_snip}</td></tr>"
                f"</table></div>",
                unsafe_allow_html=True,
            )

    _render_changes(diff.worsened, "🔴 Worsened sections")
    _render_changes(diff.improved, "🟢 Improved sections")
    _render_changes(diff.added,    "🔵 Added sections")
    _render_changes(diff.removed,  "🟠 Removed sections")

    if st.button("🗑️ Clear comparison", key="btn_clear_cmp"):
        st.session_state.pop("compare_diff", None)
        st.session_state.pop("_compare_is_demo", None)
        st.rerun()

st.divider()
st.caption("PrivacyLens Compare Mode · MSc Cyber Security & Human Factors 2025-26")
