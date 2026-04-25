"""
pages/02_listen.py -- Listen Mode UI for PrivacyLens.

Generates audio from plain-English policy summaries via gTTS (free)
or ElevenLabs (premium). Supports 35 languages via Google Translate.

Author: Sateesh Kumar Payyavula
Reference: Sweller (1988) Cognitive Load -- audio reduces reading burden
           WCAG 2.2 (2023) -- audio alternatives for text content
"""

import streamlit as st
from config import ELEVENLABS_API_KEY, get_audience_level
from translation.translator import LANGUAGES, LANGUAGE_FLAGS, get_display_name

st.set_page_config(page_title="PrivacyLens · Listen", page_icon="🔊", layout="wide")
st.markdown("# 🔊 Listen Mode")
st.markdown("Hear the policy explained in plain language — in your language.")
st.divider()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "policy_text" not in st.session_state:
    st.warning("No document loaded. Go to the **Home** page and load a policy first.")
    st.stop()

analysis     = st.session_state.get("analysis", {})
plain_clauses= analysis.get("plain_clauses", [])
kids_report  = st.session_state.get("kids_report")
policy_src   = st.session_state.get("policy_source", "policy")
age          = st.session_state.get("age", 25)
audience_key = get_audience_level(age)

# ── Language selector ─────────────────────────────────────────────────────────
st.markdown("### 🌐 Choose language")
lang_options = ["en"] + [k for k in LANGUAGES if k != "en"]
lang_display = [get_display_name(k) for k in lang_options]
sel_idx = st.selectbox("Language", range(len(lang_display)),
                       format_func=lambda i: lang_display[i], label_visibility="collapsed")
target_lang = lang_options[sel_idx]

# ── Content selector ──────────────────────────────────────────────────────────
st.markdown("### 📄 What to listen to")
content_options = ["Plain English summary"]
if kids_report:
    content_options.append("Kids Mode summary")
content_options.append("Full policy text (long)")

content_choice = st.radio("Content", content_options, horizontal=True, label_visibility="collapsed")

# ── Build text to speak ───────────────────────────────────────────────────────
def _build_summary_text() -> str:
    if not plain_clauses:
        return (
            "This policy has not been analysed yet. "
            "Please run the Analysis on the Home page first, then come back here."
        )
    lines = []
    for p in plain_clauses:
        lines.append(f"{p.category_label}. {p.plain_summary} {p.what_it_means}")
    return "  ".join(lines)


def _build_full_text() -> str:
    return st.session_state.get("policy_text", "No policy loaded.")[:3000]


if content_choice == "Kids Mode summary" and kids_report:
    from audio.tts_engine import build_kids_audio_text
    speak_text = build_kids_audio_text(kids_report)
elif content_choice == "Full policy text (long)":
    speak_text = _build_full_text()
else:
    speak_text = _build_summary_text()

# ── Translate if needed ───────────────────────────────────────────────────────
display_text = speak_text
if target_lang != "en" and speak_text:
    with st.spinner(f"Translating to {get_display_name(target_lang)}..."):
        from translation.translator import translate_text
        translated = translate_text(speak_text, target_lang=target_lang)
    display_text = translated
    st.success(f"Translated to {get_display_name(target_lang)}")

# ── Text preview ──────────────────────────────────────────────────────────────
with st.expander("📝 Text preview"):
    st.markdown(display_text[:1500] + ("..." if len(display_text) > 1500 else ""))

st.markdown(f"**Word count:** {len(display_text.split())} | "
            f"**Est. audio length:** ~{max(1, len(display_text.split()) // 130)} min")

# ── Generate audio ────────────────────────────────────────────────────────────
engine_choice = "elevenlabs" if ELEVENLABS_API_KEY else "gtts"
engine_label  = "ElevenLabs (premium)" if ELEVENLABS_API_KEY else "gTTS (free)"

st.markdown(f"**Voice engine:** {engine_label}")

if st.button("🎙️ Generate Audio", type="primary", key="btn_gen_audio"):
    if not display_text.strip():
        st.warning("Nothing to speak — run Analysis first.")
    else:
        with st.spinner("Generating audio... 🎵"):
            try:
                from audio.tts_engine import generate_audio
                result = generate_audio(
                    text=display_text[:4000],
                    language=target_lang,
                    audience_level=audience_key,
                    engine=engine_choice,
                )
                st.session_state["audio_result"] = result
            except Exception as exc:
                st.error(f"Audio generation failed: {exc}")
                st.session_state.pop("audio_result", None)

# ── Audio player ──────────────────────────────────────────────────────────────
if "audio_result" in st.session_state:
    result = st.session_state["audio_result"]
    from pathlib import Path as _Path
    audio_path = _Path(str(result.audio_path)) if result.audio_path else None

    if audio_path and audio_path.exists():
        st.success(f"Audio ready! ({result.duration_seconds:.0f}s · {result.voice_engine})")
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/mp3")
        st.download_button(
            "⬇️ Download MP3", data=audio_bytes,
            file_name=f"privacylens_{policy_src[:20].replace(' ', '_')}.mp3",
            mime="audio/mpeg",
        )
    else:
        st.error("Audio file not found — try regenerating.")

st.divider()

# ── Language info table ───────────────────────────────────────────────────────
with st.expander("🌍 All supported languages"):
    cols = st.columns(4)
    for i, (code, name) in enumerate(LANGUAGES.items()):
        flag = LANGUAGE_FLAGS.get(code, "🏳️")
        cols[i % 4].markdown(f"{flag} {name}")

st.caption("PrivacyLens Listen Mode · MSc Cyber Security & Human Factors 2025-26")
