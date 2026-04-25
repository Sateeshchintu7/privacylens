"""
pages/05_kids.py -- Kids Mode UI for PrivacyLens.

Age-appropriate privacy policy explanations with emoji, colour-coded
verdict cards, and clause-by-clause breakdowns.

Author: Sateesh Kumar Payyavula
Reference: COPPA (1998) / UK Age Appropriate Design Code (2021)
           WCAG 2.2 (2023) -- accessibility (min 16px, high contrast)
"""

import streamlit as st
from config import get_audience_level, GEMINI_API_KEY

st.set_page_config(page_title="PrivacyLens · Kids Mode", page_icon="👧", layout="wide")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .verdict-safe    { background:#2ecc71; color:#fff; padding:18px; border-radius:16px; text-align:center; }
  .verdict-ask     { background:#f39c12; color:#fff; padding:18px; border-radius:16px; text-align:center; }
  .verdict-careful { background:#e74c3c; color:#fff; padding:18px; border-radius:16px; text-align:center; }
  .clause-card     { background:#f8f9fa; border-left:5px solid #3498db; padding:14px; border-radius:8px; margin-bottom:12px; }
  .clause-card.risk-low      { border-color:#2ecc71; }
  .clause-card.risk-medium   { border-color:#f39c12; }
  .clause-card.risk-high     { border-color:#e74c3c; }
  .clause-card.risk-critical { border-color:#8e44ad; }
  .age-pill { display:inline-block; padding:6px 16px; border-radius:20px; margin:4px;
              cursor:pointer; font-weight:bold; font-size:15px; }
  .kids-emoji { font-size:32px; }
</style>
""", unsafe_allow_html=True)

_VERDICT_CSS = {"SAFE": "verdict-safe", "ASK_PARENT": "verdict-ask", "BE_CAREFUL": "verdict-careful"}
_VERDICT_TITLES = {
    "SAFE":       "✅ Looks Safe!",
    "ASK_PARENT": "⚠️ Ask a Grown-Up First",
    "BE_CAREFUL": "🚨 Be Careful!",
}

# ── Guard: document must be loaded ───────────────────────────────────────────
if "policy_text" not in st.session_state:
    st.warning("No document loaded. Go to the **Home** page and load a policy first.")
    st.stop()

policy_text  = st.session_state["policy_text"]
policy_src   = st.session_state.get("policy_source", "this policy")
analysis     = st.session_state.get("analysis", {})
clauses      = analysis.get("clauses", [])
plain_clauses= analysis.get("plain_clauses", [])
risk_report  = analysis.get("risk_report")
clause_risks = risk_report.clause_risks if risk_report else []

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 👧 Kids Mode")
st.markdown(f"**{policy_src[:60]}** — explained just for you!")
st.divider()

# ── Age selector ─────────────────────────────────────────────────────────────
st.markdown("### How old are you?")
age_col1, age_col2, age_col3, age_col4 = st.columns(4)
age_labels = {8: "8-10 🧒", 11: "11-13 👦", 14: "14-17 🧑", 18: "18+ 👤"}

saved_age = st.session_state.get("kids_age", st.session_state.get("age", 10))

selected_age = saved_age
with age_col1:
    if st.button("8–10 🧒", use_container_width=True,
                 type="primary" if 8 <= saved_age <= 10 else "secondary"):
        selected_age = 9
with age_col2:
    if st.button("11–13 👦", use_container_width=True,
                 type="primary" if 11 <= saved_age <= 13 else "secondary"):
        selected_age = 12
with age_col3:
    if st.button("14–17 🧑", use_container_width=True,
                 type="primary" if 14 <= saved_age <= 17 else "secondary"):
        selected_age = 15
with age_col4:
    if st.button("18+ 👤", use_container_width=True,
                 type="primary" if saved_age >= 18 else "secondary"):
        selected_age = 18

if selected_age != saved_age:
    st.session_state["kids_age"] = selected_age
    st.session_state.pop("kids_report", None)
    st.rerun()

age = st.session_state.get("kids_age", saved_age)
audience_key = get_audience_level(age)

# ── Build kids report ─────────────────────────────────────────────────────────
if "kids_report" not in st.session_state:
    if not plain_clauses:
        st.info("Run Analysis first (on the Home page) to unlock Kids Mode explanations.")
        # Show demo verdict without real data
        st.markdown("### Demo preview")
        st.markdown(
            "<div class='verdict-ask'>"
            "<div style='font-size:48px'>⚠️</div>"
            "<div style='font-size:22px;font-weight:bold'>Ask a Grown-Up First</div>"
            "<div style='font-size:15px;margin-top:6px'>Run Analysis to get a real answer for this policy</div>"
            "</div>", unsafe_allow_html=True)
        st.stop()

    from nlp.kids_rewriter import rewrite_for_kids
    with st.spinner("Making it kid-friendly... 🎨"):
        report = rewrite_for_kids(plain_clauses, clause_risks, age=age, use_cache=True)
    st.session_state["kids_report"] = report

report = st.session_state["kids_report"]

# ── Verdict card ─────────────────────────────────────────────────────────────
css_cls = _VERDICT_CSS.get(report.verdict, "verdict-ask")
title   = _VERDICT_TITLES.get(report.verdict, report.verdict_emoji)

st.markdown(
    f"<div class='{css_cls}'>"
    f"<div style='font-size:52px'>{report.verdict_emoji}</div>"
    f"<div style='font-size:24px;font-weight:bold;margin-top:6px'>{title}</div>"
    f"<div style='font-size:15px;margin-top:6px;opacity:.92'>{report.verdict_reason}</div>"
    f"</div>",
    unsafe_allow_html=True,
)
st.markdown("")

# ── Top concerns & positives ──────────────────────────────────────────────────
col_concern, col_positive = st.columns(2)
with col_concern:
    if report.top_concerns:
        st.markdown("#### 🚨 Watch out for:")
        for c in report.top_concerns:
            st.markdown(f"- {c}")
    else:
        st.markdown("#### ✅ No major worries found!")

with col_positive:
    if report.top_positives:
        st.markdown("#### 🌟 Good things:")
        for p in report.top_positives:
            st.markdown(f"- {p}")

if report.overall_emoji_summary:
    st.markdown(
        f"<div style='font-size:28px;text-align:center;padding:10px;"
        f"background:#f0f4f8;border-radius:12px'>{report.overall_emoji_summary}</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Clause-by-clause cards ────────────────────────────────────────────────────
st.subheader("📋 What does this policy actually say?")
api_note = "" if GEMINI_API_KEY else "  *(demo text — add GEMINI_API_KEY for real explanations)*"
if api_note:
    st.caption(api_note.strip("* "))

for clause in report.clauses:
    risk_cls = f"risk-{clause.risk_level}" if clause.risk_level else ""
    flags_html = ""
    for f in clause.feature_flags:
        flags_html += f"<span style='background:#eee;border-radius:10px;padding:2px 8px;font-size:12px;margin-right:4px'>{f}</span>"

    st.markdown(
        f"<div class='clause-card {risk_cls}'>"
        f"<div style='font-size:22px'>{clause.emoji} <b>{clause.category.replace('_', ' ').title()}</b>"
        f"  <span style='font-size:18px'>{clause.risk_emoji}</span></div>"
        f"<div style='font-size:15px;margin:8px 0'>{clause.kids_summary}</div>"
        f"<div style='font-size:13px;color:#555;font-style:italic'>{clause.one_liner}</div>"
        f"<div style='margin-top:6px'>{flags_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Refresh button ────────────────────────────────────────────────────────────
if st.button("🔄 Regenerate Kids Report", key="btn_regen_kids"):
    st.session_state.pop("kids_report", None)
    st.rerun()

st.caption("PrivacyLens Kids Mode · MSc Cyber Security & Human Factors 2025-26")
