"""
pages/04_ask.py -- Ask Mode (RAG Chatbot) UI for PrivacyLens.

FAISS semantic search over policy chunks → Gemini answers from context only.
Suggested question chips, confidence indicator, source citation.

Author: Sateesh Kumar Payyavula
Reference: Adhikari, Das & Dewri (2025, arXiv:2501.10319) -- RAG for privacy Q&A
           Rodriguez et al. (2024, Springer Computing) -- LLM Q&A on legal docs
"""

import streamlit as st
from config import GEMINI_API_KEY, get_audience_level

st.set_page_config(page_title="PrivacyLens · Ask", page_icon="💬", layout="wide")

st.markdown("""
<style>
  .chat-bubble-user { background:#3498db; color:#fff; padding:10px 14px;
      border-radius:16px 16px 4px 16px; margin:4px 0; display:inline-block; max-width:80%; }
  .chat-bubble-bot  { background:#f0f4f8; color:#222; padding:10px 14px;
      border-radius:16px 16px 16px 4px; margin:4px 0; display:inline-block; max-width:80%; }
  .conf-high   { color:#2ecc71; font-weight:bold; }
  .conf-medium { color:#f39c12; font-weight:bold; }
  .conf-low    { color:#e74c3c; font-weight:bold; }
  .chip { display:inline-block; background:#eef2f7; border:1px solid #c8d6e5;
          padding:5px 12px; border-radius:14px; margin:3px; cursor:pointer; font-size:13px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 💬 Ask Mode")
st.markdown("Ask anything about this policy — I'll search it and answer from the text only.")
st.divider()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "policy_text" not in st.session_state:
    st.warning("No document loaded. Go to the **Home** page and load a policy first.")
    st.stop()

policy_text  = st.session_state["policy_text"]
policy_src   = st.session_state.get("policy_source", "policy")
age          = st.session_state.get("age", 25)
audience_key = get_audience_level(age)
analysis     = st.session_state.get("analysis", {})
clauses      = analysis.get("clauses", [])

# ── Build / load FAISS index ──────────────────────────────────────────────────
if "policy_index" not in st.session_state:
    with st.spinner("Building search index... (first load ~10s)"):
        from nlp.rag_qa import build_index
        idx = build_index(policy_text, clauses)
    st.session_state["policy_index"] = idx

policy_index = st.session_state["policy_index"]

# ── Suggested questions ───────────────────────────────────────────────────────
from nlp.rag_qa import SUGGESTED_QUESTIONS_GENERAL, SUGGESTED_QUESTIONS_KIDS

is_kids = age < 18
suggested = SUGGESTED_QUESTIONS_KIDS if is_kids else SUGGESTED_QUESTIONS_GENERAL

st.markdown("**💡 Suggested questions — click to ask:**")
chip_cols = st.columns(4)
for i, q in enumerate(suggested):
    if chip_cols[i % 4].button(q, key=f"chip_{i}", use_container_width=True):
        st.session_state["ask_input"] = q

# ── Chat history ──────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if st.session_state["chat_history"]:
    st.markdown("---")
    for entry in st.session_state["chat_history"]:
        q_html = entry["question"].replace("<", "&lt;").replace(">", "&gt;")
        a_html = entry["answer"].replace("<", "&lt;").replace(">", "&gt;")
        conf   = entry.get("confidence", 0.0)
        conf_cls = "conf-high" if conf >= 0.75 else "conf-medium" if conf >= 0.4 else "conf-low"
        conf_label = f"{conf*100:.0f}% confident"

        st.markdown(
            f"<div style='text-align:right'><span class='chat-bubble-user'>🧑 {q_html}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div><span class='chat-bubble-bot'>🔍 {a_html}<br>"
            f"<small><span class='{conf_cls}'>{conf_label}</span></small></span></div>",
            unsafe_allow_html=True,
        )
        if entry.get("source_quote"):
            with st.expander("📄 Source quote"):
                st.markdown(f'> *"{entry["source_quote"]}"*')
        if entry.get("could_not_find"):
            st.caption("⚠️ The answer wasn't clearly stated in this policy.")

# ── Question input ────────────────────────────────────────────────────────────
st.markdown("---")
default_q = st.session_state.pop("ask_input", "")

with st.form(key="ask_form", clear_on_submit=True):
    question = st.text_input(
        "Your question",
        value=default_q,
        placeholder="e.g. Can they sell my data?",
        label_visibility="collapsed",
    )
    col_ask, col_clear = st.columns([5, 1])
    submitted = col_ask.form_submit_button("🔍 Ask", type="primary", use_container_width=True)
    cleared   = col_clear.form_submit_button("🗑️ Clear", use_container_width=True)

if cleared:
    st.session_state["chat_history"] = []
    st.rerun()

if submitted and question.strip():
    with st.spinner("Searching the policy..."):
        from nlp.rag_qa import answer_question
        result = answer_question(
            question=question.strip(),
            policy_index=policy_index,
            clauses=clauses,
            audience_level=audience_key,
            use_cache=True,
        )

    st.session_state["chat_history"].append({
        "question":     result.question,
        "answer":       result.answer,
        "plain_answer": result.plain_answer,
        "confidence":   result.confidence,
        "source_quote": result.source_clauses[0] if result.source_clauses else "",
        "could_not_find": result.could_not_find,
    })
    st.rerun()

# ── API status note ───────────────────────────────────────────────────────────
if not GEMINI_API_KEY:
    st.info(
        "🔴 **Demo mode** — FAISS search is live but answers are stubs. "
        "Add `GEMINI_API_KEY` to `.env` for real Gemini-powered answers."
    )

st.divider()
st.caption("PrivacyLens Ask Mode · MSc Cyber Security & Human Factors 2025-26")
