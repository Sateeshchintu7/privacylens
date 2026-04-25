"""
pages/01_read.py -- Plain English Read Mode UI for PrivacyLens.

Displays the policy rewritten at the user's reading level,
with readability metrics and a category-by-category breakdown.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- avg policy Grade 14.8; target Grade 6
           Sweller (1988) Cognitive Load -- simplification reduces effort
"""

import streamlit as st
from config import AUDIENCE_LEVELS, RISK_COLOURS, get_audience_level

st.set_page_config(page_title="PrivacyLens · Read", page_icon="📖", layout="wide")
st.markdown("# 📖 Read Mode")
st.markdown("The policy — rewritten in plain English, at your reading level.")
st.divider()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "policy_text" not in st.session_state:
    st.warning("No document loaded. Go to the **Home** page and load a policy first.")
    st.stop()

analysis     = st.session_state.get("analysis", {})
plain_clauses= analysis.get("plain_clauses", [])
readability  = analysis.get("readability")
risk_report  = analysis.get("risk_report")
policy_src   = st.session_state.get("policy_source", "policy")
age          = st.session_state.get("age", 25)
audience_key = get_audience_level(age)
audience     = AUDIENCE_LEVELS[audience_key]

# ── No analysis yet ───────────────────────────────────────────────────────────
if not plain_clauses:
    st.info("Analysis not run yet. Go to the **Home** page → Analysis tab and click **Analyse this document**.")

    with st.expander("📄 Preview raw policy (first 3 000 chars)"):
        st.text(st.session_state["policy_text"][:3000] + "...")
    st.stop()

# ── Readability banner ────────────────────────────────────────────────────────
if readability:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Original FK Grade", f"{readability.flesch_kincaid_grade:.1f}",
                help="Flesch-Kincaid grade level of the original policy (Reidenberg avg = 14.8)")
    avg_plain = sum(p.reading_grade for p in plain_clauses) / len(plain_clauses)
    col2.metric("Plain Version Grade", f"{avg_plain:.1f}",
                delta=f"{avg_plain - readability.flesch_kincaid_grade:+.1f}",
                delta_color="inverse")
    col3.metric("Target Grade", f"≤ {audience['fk_grade']:.0f}",
                help=f"Reading level target for {audience['label']}")
    col4.metric("Read Time", f"{readability.minutes_to_read} min",
                help="Estimated time to read the original policy")

    st.markdown(
        f"<div style='background:#f0f4f8;border-radius:10px;padding:10px;margin-bottom:12px;"
        f"font-size:13px;color:#555'>"
        f"Original policy: <b>{readability.comparison_label}</b> · "
        f"{readability.legal_jargon_count} legal jargon terms · "
        f"{readability.word_count:,} words"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Plain clauses ─────────────────────────────────────────────────────────────
risk_map = {}
if risk_report:
    risk_map = {cr.category: cr for cr in risk_report.clause_risks}

st.subheader(f"Plain English summary — {audience['label']} level")
st.caption(f"Rewritten at Grade {audience['fk_grade']:.0f} reading level")

for p in plain_clauses:
    cr = risk_map.get(p.category)
    risk_score = cr.final_score if cr else 0.0
    colour = RISK_COLOURS.get(
        "F" if risk_score >= 81 else
        "D" if risk_score >= 61 else
        "C" if risk_score >= 41 else
        "B" if risk_score >= 21 else "A",
        "#888",
    )
    grade_badge = (
        f"<span style='background:{colour};color:#fff;padding:2px 9px;"
        f"border-radius:8px;font-size:12px;font-weight:bold'>"
        f"{risk_score:.0f}/100</span>"
        if cr else ""
    )

    with st.expander(f"**{p.category_label}** {grade_badge}", expanded=False):
        st.markdown(p.plain_summary)
        st.info(f"💡 {p.what_it_means}")

        if cr:
            if cr.red_flags:
                st.warning("⚠️ " + " · ".join(cr.red_flags))
            if cr.positive_signals:
                st.success("✅ " + " · ".join(cr.positive_signals))

        meta_cols = st.columns(3)
        meta_cols[0].caption(f"FK Grade: {p.reading_grade:.1f}")
        meta_cols[1].caption(f"Target: ≤ {p.grade_target:.0f}")
        meta_cols[2].caption("✅ PASS" if p.grade_met else "⚠️ Above target")

st.divider()

# ── Original text toggle ──────────────────────────────────────────────────────
with st.expander("📄 View original policy text"):
    st.text(st.session_state["policy_text"][:5000] +
            ("...\n[truncated to 5 000 chars]" if len(st.session_state["policy_text"]) > 5000 else ""))

# ── Copy-all button ───────────────────────────────────────────────────────────
full_plain = "\n\n".join(
    f"{p.category_label}\n{p.plain_summary}\n{p.what_it_means}" for p in plain_clauses
)
st.download_button(
    "⬇️ Download plain text",
    data=full_plain.encode("utf-8"),
    file_name=f"plain_{policy_src[:20].replace(' ', '_')}.txt",
    mime="text/plain",
)

st.caption("PrivacyLens Read Mode · MSc Cyber Security & Human Factors 2025-26")
