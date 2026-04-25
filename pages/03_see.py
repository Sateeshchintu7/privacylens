"""
pages/03_see.py -- Visualisations UI for PrivacyLens.

Five chart tabs: Risk Heatmap | Data Flow | GDPR Radar | Summary Card | Compliance.
All charts show demo data before analysis; real data after.

Author: Sateesh Kumar Payyavula
Reference: Adhikari, Das & Dewri (2025, arXiv:2501.10319) -- data viz for privacy
           Xie et al. (USENIX Security 2025) -- compliance mapping
           Sweller (1988) Cognitive Load -- visual summaries aid comprehension
"""

import io
import streamlit as st
from config import RISK_COLOURS

st.set_page_config(page_title="PrivacyLens · See", page_icon="📊", layout="wide")
st.markdown("# 📊 See Mode")
st.markdown("Visual summaries — understand the policy at a glance.")
st.divider()

# ── Load session state ────────────────────────────────────────────────────────
policy_src      = st.session_state.get("policy_source", "Policy")
analysis        = st.session_state.get("analysis", {})
clause_risks    = []
clauses         = []
risk_report     = None
readability     = None
plain_clauses   = []
compliance_rpt  = None

if analysis:
    rpt = analysis.get("risk_report")
    if rpt:
        risk_report  = rpt
        clause_risks = rpt.clause_risks
    clauses         = analysis.get("clauses", [])
    readability     = analysis.get("readability")
    plain_clauses   = analysis.get("plain_clauses", [])
    compliance_rpt  = analysis.get("compliance_report")

demo_banner = "" if analysis else (
    "> ⚠️ **Demo data** — load a document and run Analysis to see charts for your policy."
)
if demo_banner:
    st.info("Charts below use demo data. Load a document and run Analysis on the Home page for real results.")

# ── Chart tabs ────────────────────────────────────────────────────────────────
tab_heat, tab_sankey, tab_radar, tab_card, tab_comply = st.tabs([
    "🌡️ Risk Heatmap", "🔀 Data Flow", "🎯 GDPR Radar", "🃏 Summary Card", "📋 Compliance"
])

# ── Tab 1: Risk Heatmap ───────────────────────────────────────────────────────
with tab_heat:
    st.markdown("**Risk scores across 12 policy categories and 5 risk dimensions.**")
    from visualisation.risk_heatmap import create_risk_heatmap
    fig = create_risk_heatmap(clause_risks, policy_name=policy_src[:40])
    st.plotly_chart(fig, use_container_width=True)

    if clause_risks:
        st.markdown("**Top risk categories:**")
        sorted_risks = sorted(clause_risks, key=lambda r: r.final_score, reverse=True)
        for cr in sorted_risks[:5]:
            colour = "#e74c3c" if cr.final_score >= 75 else "#f39c12" if cr.final_score >= 50 else "#2ecc71"
            st.markdown(
                f"<span style='background:{colour};color:#fff;padding:3px 10px;"
                f"border-radius:10px;font-size:13px'>{cr.category.replace('_',' ').title()}"
                f" — {cr.final_score:.0f}/100</span>",
                unsafe_allow_html=True,
            )
        st.markdown("")

# ── Tab 2: Data Flow Sankey ───────────────────────────────────────────────────
with tab_sankey:
    st.markdown("**How your data flows from collection to use.**")
    from visualisation.sankey_flow import create_sankey
    fig = create_sankey(clauses, policy_name=policy_src[:40])
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Blue = your data · Orange = who receives it · Green = what it's used for. "
        "Wider bands = more data flows that way."
    )

# ── Tab 3: GDPR Radar ─────────────────────────────────────────────────────────
with tab_radar:
    st.markdown("**How well this policy meets GDPR obligations (8 dimensions).**")
    from visualisation.gdpr_radar import create_gdpr_radar, GDPR_DIMENSIONS
    fig = create_gdpr_radar(risk_report, compliance_rpt, policy_name=policy_src[:40])
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 GDPR dimension guide"):
        gdpr_notes = [
            ("Lawful Basis (Art.6)",       "Policy must state a legal reason for processing."),
            ("Transparency (Art.13)",      "Must clearly disclose what data is collected."),
            ("Data Minimisation (Art.5)",  "Only collect what is strictly necessary."),
            ("Purpose Limitation (Art.5)", "Data used only for stated purposes."),
            ("Retention Limits (Art.5)",   "Data deleted once no longer needed."),
            ("User Rights (Art.15-22)",    "Right to access, delete, and port your data."),
            ("Security (Art.32)",          "Appropriate technical security measures."),
            ("Breach Notification (Art.33)","Must notify users within 72 hours of a breach."),
        ]
        for dim, note in gdpr_notes:
            st.markdown(f"**{dim}** — {note}")

# ── Tab 4: Summary Card ────────────────────────────────────────────────────────
with tab_card:
    st.markdown("**Shareable summary card — copy or screenshot to share.**")
    from visualisation.traffic_light_card import create_traffic_light_card
    card_html = create_traffic_light_card(
        risk_report=risk_report,
        readability=readability,
        plain_clauses=plain_clauses,
        policy_name=policy_src[:45],
    )
    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("")
    # Offer HTML download
    html_bytes = card_html.encode("utf-8")
    st.download_button(
        "⬇️ Download card as HTML",
        data=html_bytes,
        file_name="privacylens_card.html",
        mime="text/html",
    )

# ── Tab 5: Compliance ────────────────────────────────────────────────────────
with tab_comply:
    st.markdown("**Multi-regulation compliance scores — GDPR · CCPA · India DPDP Act 2023.**")

    if compliance_rpt is None:
        if clauses:
            with st.spinner("Running compliance mapping..."):
                from nlp.compliance_mapper import map_compliance
                compliance_rpt = map_compliance(clauses)
                if analysis:
                    analysis["compliance_report"] = compliance_rpt
                    st.session_state["analysis"] = analysis
        else:
            st.info("Run Analysis on the Home page to see compliance scores.")
            st.stop()

    if compliance_rpt:
        c1, c2, c3 = st.columns(3)
        c1.metric("GDPR Score", f"{compliance_rpt.gdpr_score:.0f}/100")
        c2.metric("CCPA Score", f"{compliance_rpt.ccpa_score:.0f}/100")
        c3.metric("DPDP Score", f"{compliance_rpt.dpdp_score:.0f}/100")

        st.markdown("#### Compliance bars")
        for reg, score in [
            ("GDPR (EU)", compliance_rpt.gdpr_score),
            ("CCPA (California)", compliance_rpt.ccpa_score),
            ("DPDP (India)", compliance_rpt.dpdp_score),
        ]:
            colour = "#2ecc71" if score >= 75 else "#f39c12" if score >= 50 else "#e74c3c"
            st.markdown(
                f"<div style='margin-bottom:10px'>"
                f"<div style='font-size:13px;font-weight:600'>{reg} — {score:.0f}/100</div>"
                f"<div style='background:#eee;border-radius:8px;height:14px;width:100%'>"
                f"<div style='background:{colour};border-radius:8px;height:14px;width:{score:.0f}%'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        if compliance_rpt.critical_gaps:
            st.markdown("#### Critical gaps")
            for gap in compliance_rpt.critical_gaps:
                st.error(
                    f"**[{gap.regulation}] {gap.article}** — {gap.requirement}  \n"
                    f"Status: **{gap.status}** · Evidence: _{gap.evidence[:80]}_"
                )

        if compliance_rpt.gaps:
            with st.expander(f"All {len(compliance_rpt.gaps)} gaps (non-critical)"):
                for gap in compliance_rpt.gaps:
                    icon = "🔴" if gap.severity == "critical" else "🟠" if gap.severity == "high" else "🟡"
                    st.markdown(
                        f"{icon} **[{gap.regulation}] {gap.article}** — {gap.requirement}  \n"
                        f"Status: `{gap.status}`"
                    )

        st.markdown("#### What you should do")
        _actions = {
            "MISSING": "This required disclosure is absent — add it to comply.",
            "PARTIAL": "This disclosure exists but is incomplete — expand it.",
        }
        action_items = [g for g in compliance_rpt.gaps if g.status in _actions][:6]
        for g in action_items:
            st.markdown(f"- **{g.article}**: {_actions[g.status]}")

st.divider()
st.caption("PrivacyLens See Mode · MSc Cyber Security & Human Factors 2025-26")
