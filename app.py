"""
app.py — PrivacyLens main Streamlit entrypoint.

Two main tabs: Load Document | Analysis.
All other modes (Read, Listen, See, Ask, Kids, Compare) live in pages/.

Author: Sateesh Kumar Payyavula
MSc Cyber Security & Human Factors, 2025-26
Supervisor: Jiankang Zhang
"""

import hashlib
import streamlit as st

from config import (
    DOCUMENT_TYPES, AUDIENCE_LEVELS, RISK_COLOURS,
    GEMINI_API_KEY, ELEVENLABS_API_KEY, GOOGLE_TRANSLATE_API_KEY,
    get_audience_level,
)
from ingestion.scraper import extract_from_url
from ingestion.pdf_parser import extract_from_pdf
from ingestion.text_cleaner import clean_text
from nlp.clause_extractor import extract_clauses
from nlp.mad_engine import score_policy
from nlp.plain_rewriter import rewrite_policy
from nlp.readability import score_readability
from nlp.contradiction_detector import detect_contradictions
from nlp.compliance_mapper import map_compliance

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PrivacyLens", page_icon="🔍",
    layout="wide", initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🔍 PrivacyLens")
    st.caption("MSc Cyber Security & Human Factors 2025-26")
    st.divider()

    # Document type
    doc_type = st.selectbox("Document type", DOCUMENT_TYPES)

    # Age / audience
    age_input = st.number_input("Your age", min_value=6, max_value=100, value=25)
    audience_key = get_audience_level(age_input)
    audience = AUDIENCE_LEVELS[audience_key]
    st.info(f"**{audience['label']}** — {audience['description']}")

    st.divider()

    # API status indicator
    st.markdown("**🔑 API Status**")
    if GEMINI_API_KEY and ELEVENLABS_API_KEY:
        st.success("🟢 Gemini + ElevenLabs — all features active")
    elif GEMINI_API_KEY:
        st.warning("🟡 Gemini only — audio uses free voice")
    else:
        st.error("🔴 No API key — demo mode (analysis uses stubs)")
        st.caption("Add GEMINI_API_KEY to .env to activate full analysis")

    st.divider()

    # Loaded policy indicator
    if "policy_text" in st.session_state:
        src = st.session_state.get("policy_source", "unknown")
        st.markdown(f"📄 **Loaded:** {src[:35]}")
    else:
        st.caption("No document loaded")

    # Risk grade badge (once analysis is done)
    if "analysis" in st.session_state and st.session_state["analysis"].get("risk_report"):
        grade = st.session_state["analysis"]["risk_report"].grade
        score = st.session_state["analysis"]["risk_report"].overall_score
        colour = RISK_COLOURS.get(grade, "#888")
        st.markdown(
            f"<div style='background:{colour};padding:10px;border-radius:8px;"
            f"text-align:center;color:#fff;font-weight:bold;font-size:20px'>"
            f"Grade {grade} · {score:.0f}/100</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption("Supervisor: Jiankang Zhang")

# ── Main tabs ─────────────────────────────────────────────────────────────────
st.title("🔍 PrivacyLens")
tab_load, tab_analyse = st.tabs(["📂 Load Document", "🧠 Analysis"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOAD DOCUMENT
# ════════════════════════════════════════════════════════════════════════════
with tab_load:
    st.markdown("**Make any legal document understandable — for anyone, at any age, in any language.**")
    st.divider()

    sub_url, sub_pdf, sub_paste = st.tabs(["🌐 URL", "📄 Upload PDF", "📋 Paste Text"])
    raw_text, source_label = "", ""

    with sub_url:
        url = st.text_input("Policy URL", placeholder="https://policies.google.com/privacy")
        if st.button("Fetch document", key="btn_url", type="primary"):
            if not url.strip():
                st.warning("Please enter a URL first.")
            else:
                with st.spinner("Fetching and extracting text..."):
                    res = extract_from_url(url.strip())
                if res.error:
                    st.error(res.error)
                else:
                    raw_text = res.text
                    source_label = f"URL: {url.strip()}"
                    st.success(f"Fetched {res.char_count:,} characters ({'cached' if res.cached else f'{res.fetch_ms}ms'}).")

    with sub_pdf:
        uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])
        if uploaded:
            with st.spinner("Reading PDF..."):
                res = extract_from_pdf(uploaded.read())
            if res.error:
                st.error(res.error)
            else:
                raw_text = res.text
                source_label = f"PDF: {uploaded.name} ({res.page_count} pages)"
                st.success(f"Read {res.page_count} pages, {res.char_count:,} chars.")

    with sub_paste:
        pasted = st.text_area("Paste policy text", height=200,
                              placeholder="Paste the full policy text here...")
        if pasted.strip():
            raw_text = pasted.strip()
            source_label = "Pasted text"

    if raw_text:
        with st.spinner("Cleaning text..."):
            cleaned = clean_text(raw_text)
        st.session_state.update({
            "policy_text": cleaned.text, "policy_source": source_label,
            "doc_type": doc_type, "audience_key": audience_key,
            "age": age_input, "analysis": {},
        })
        c1, c2, c3 = st.columns(3)
        c1.metric("Characters", f"{cleaned.clean_char_count:,}")
        c2.metric("Words", f"{len(cleaned.text.split()):,}")
        c3.metric("Lines cleaned", f"{cleaned.lines_removed:,}")
        with st.expander("Preview (first 2 000 chars)"):
            st.text(cleaned.text[:2000] + ("..." if len(cleaned.text) > 2000 else ""))
        st.success(f"Loaded from **{source_label}**. Switch to Analysis tab or use sidebar pages.")

    elif "policy_text" in st.session_state:
        st.info(f"Loaded: **{st.session_state.get('policy_source', '?')}** — use Analysis tab or sidebar pages.")
    else:
        st.info("Load a document above to get started.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSIS (Phase 2 pipeline)
# ════════════════════════════════════════════════════════════════════════════
with tab_analyse:
    if "policy_text" not in st.session_state:
        st.info("Load a document first (use the Load Document tab).")
        st.stop()

    policy_text = st.session_state["policy_text"]
    aud_key = st.session_state.get("audience_key", "adult")
    doc_hash = hashlib.md5(policy_text.encode()).hexdigest()[:8]
    analysis = st.session_state.get("analysis", {})

    if not analysis or analysis.get("_hash") != doc_hash:
        if st.button("Analyse this document", type="primary", key="btn_analyse"):
            if not GEMINI_API_KEY:
                st.error("GEMINI_API_KEY required for full analysis. Add it to your .env file.")
            else:
                with st.status("Analysing document...", expanded=True) as status:
                    st.write("Step 1/4 — Extracting clauses...")
                    clauses = extract_clauses(policy_text)
                    st.write(f"Step 2/4 — Scoring risk ({len(clauses)} clauses found)...")
                    risk_report = score_policy(clauses)
                    st.write("Step 3/4 — Rewriting in plain English...")
                    plain_clauses = rewrite_policy(clauses, audience_level=aud_key)
                    st.write("Step 4/4 — Scoring readability...")
                    readability = score_readability(policy_text, target_grade=6.0)
                    st.write("Step 5/6 — Detecting contradictions...")
                    contradictions = detect_contradictions(clauses)
                    st.write("Step 6/6 — Mapping compliance (GDPR / CCPA / DPDP)...")
                    compliance = map_compliance(clauses)
                    status.update(label="Analysis complete!", state="complete")
                st.session_state["analysis"] = {
                    "_hash": doc_hash, "clauses": clauses, "risk_report": risk_report,
                    "plain_clauses": plain_clauses, "readability": readability,
                    "contradictions": contradictions, "compliance_report": compliance,
                }
                st.rerun()
        st.stop()

    # ── Summary card ──────────────────────────────────────────────────────────
    risk = analysis["risk_report"]
    read = analysis["readability"]
    plain = analysis["plain_clauses"]
    contradictions = analysis.get("contradictions")
    compliance = analysis.get("compliance_report")
    colour = RISK_COLOURS.get(risk.grade, "#888")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(
            f"<div style='background:{colour};padding:20px;border-radius:12px;"
            f"text-align:center;color:#fff'>"
            f"<div style='font-size:48px;font-weight:bold'>Grade {risk.grade}</div>"
            f"<div style='font-size:20px'>{risk.overall_score:.0f} / 100</div>"
            f"<div style='font-size:13px;margin-top:8px'>{risk.grade_explanation}</div>"
            f"</div>", unsafe_allow_html=True,
        )
    with c2:
        st.markdown(f"**⚠️ {len(risk.top_red_flags)} red flag(s)** · **✅ {len(risk.positive_signals)} positive signal(s)**")

        # Contradictions badge (Phase 7)
        if contradictions:
            n = contradictions.total_found
            badge_col = "#e74c3c" if n > 0 else "#2ecc71"
            st.markdown(
                f"<span style='background:{badge_col};color:#fff;padding:2px 10px;"
                f"border-radius:10px;font-size:13px'>⚡ {n} contradiction{'s' if n != 1 else ''} found</span>",
                unsafe_allow_html=True,
            )

        # Compliance scores (Phase 7)
        if compliance:
            st.markdown(
                f"**GDPR:** {compliance.gdpr_score:.0f}%  "
                f"**CCPA:** {compliance.ccpa_score:.0f}%  "
                f"**DPDP:** {compliance.dpdp_score:.0f}%"
            )

        st.markdown(f"📖 Original: **Grade {read.flesch_kincaid_grade}** — {read.comparison_label}")
        if plain:
            avg_plain = sum(p.reading_grade for p in plain) / len(plain)
            target = AUDIENCE_LEVELS[aud_key]["fk_grade"]
            st.markdown(f"{'✅' if avg_plain <= target + 1.5 else '⚠️'} Plain version: **Grade {avg_plain:.1f}** (target ≤ {target})")
        breakdown = " | ".join(
            f"**{sum(1 for r in risk.clause_risks if r.risk_level == lvl)} {lvl}**"
            for lvl in ["critical", "high", "medium", "low"]
        )
        st.markdown(f"Clause breakdown: {breakdown}")
        if risk.top_red_flags:
            st.error("🚨 " + " · ".join(risk.top_red_flags[:3]))
        if risk.positive_signals:
            st.success("✅ " + " · ".join(risk.positive_signals[:3]))

    st.divider()
    st.subheader("Category breakdown")
    risk_map = {cr.category: cr for cr in risk.clause_risks}
    for p in plain:
        cr = risk_map.get(p.category)
        score_txt = f" — {cr.final_score:.0f}/100" if cr else ""
        with st.expander(f"**{p.category_label}**{score_txt}"):
            st.markdown(p.plain_summary)
            st.info(p.what_it_means)
            if cr and cr.red_flags:
                st.warning("⚠️ " + " · ".join(cr.red_flags))
            st.caption(f"FK grade: {p.reading_grade} | Target: {p.grade_target} | {'PASS ✅' if p.grade_met else 'Above target ⚠️'}")

    # ── Contradictions section ─────────────────────────────────────────────────
    if contradictions and contradictions.total_found > 0:
        st.divider()
        st.subheader(f"⚡ Internal contradictions ({contradictions.total_found} found)")
        st.caption(contradictions.summary)
        _SEV_COLOUR = {"high": "#e74c3c", "medium": "#f39c12", "low": "#3498db"}
        for c in contradictions.contradictions:
            badge = f"<span style='background:{_SEV_COLOUR.get(c.severity,'#888')};color:#fff;" \
                    f"padding:1px 8px;border-radius:8px;font-size:12px'>{c.severity.upper()}</span>"
            with st.expander(
                f"⚡ {badge} {c.contradiction_type.replace('_',' ').title()} "
                f"({c.clause_a_category} ↔ {c.clause_b_category})",
                expanded=False,
            ):
                st.markdown(f"**Explanation:** {c.plain_explanation}")
                st.markdown(f"**Example:** _{c.example}_")
                col_a, col_b = st.columns(2)
                col_a.markdown(f"**Clause A ({c.clause_a_category})**")
                col_a.text(c.clause_a_text[:300])
                col_b.markdown(f"**Clause B ({c.clause_b_category})**")
                col_b.text(c.clause_b_text[:300])

    # ── Compliance section ─────────────────────────────────────────────────────
    if compliance:
        st.divider()
        st.subheader("📋 Multi-Regulation Compliance")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("GDPR", f"{compliance.gdpr_score:.0f}/100")
        cc2.metric("CCPA", f"{compliance.ccpa_score:.0f}/100")
        cc3.metric("DPDP", f"{compliance.dpdp_score:.0f}/100")
        if compliance.critical_gaps:
            with st.expander(f"🔴 {len(compliance.critical_gaps)} critical gap(s)"):
                for g in compliance.critical_gaps:
                    st.error(f"**[{g.regulation}] {g.article}** — {g.requirement} ({g.status})")

    if st.button("Clear analysis", key="btn_clear"):
        st.session_state.pop("analysis", None)
        st.rerun()
