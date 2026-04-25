"""
audio/tts_engine.py -- Text-to-speech engine for PrivacyLens.

gTTS (free, always available). ElevenLabs (premium, optional API key).
Caches generated audio by MD5 of (text + language + audience_level).

Author: Sateesh Kumar Payyavula
Reference: WCAG 2.2 (2023) -- audio accessibility requirement
"""

import hashlib
import logging
import re
from pathlib import Path
from pydantic import BaseModel
from config import BASE_DIR, ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)
OUTPUT_DIR = BASE_DIR / "audio" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Maps our ISO codes to gTTS-accepted language codes
_LANG_MAP: dict[str, str] = {
    "hi": "hi", "te": "te", "ta": "ta", "kn": "kn", "ml": "ml",
    "bn": "bn", "mr": "mr", "gu": "gu", "pa": "pa", "ur": "ur",
    "or": "or", "as": "as",
    "en": "en", "en-gb": "en-uk", "en-us": "en", "en-uk": "en-uk",
    "fr": "fr", "de": "de", "es": "es", "it": "it", "pt": "pt",
    "nl": "nl", "pl": "pl", "ru": "ru", "uk": "uk", "cs": "cs",
    "sk": "sk", "ro": "ro", "hu": "hu", "el": "el", "sv": "sv",
    "da": "da", "fi": "fi", "no": "no", "hr": "hr", "bg": "bg",
    "af": "af",
    "zh-cn": "zh-CN", "zh-tw": "zh-TW", "zh": "zh-CN",
    "ja": "ja", "ko": "ko", "th": "th", "vi": "vi", "id": "id",
    "ms": "ms", "tl": "tl",
    "ar": "ar", "fa": "fa", "tr": "tr", "he": "iw", "sw": "sw",
}

_ELEVENLABS_VOICES = {
    # ElevenLabs stable premade voice IDs (v1+ API)
    "adult":   "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "teen":    "EXAVITQu4vr4xnSDxMaL",   # Bella
    "junior":  "MF3mGyEYCl7XYWbV9V6O",   # Elli
    "child":   "MF3mGyEYCl7XYWbV9V6O",   # Elli
    "preteen": "MF3mGyEYCl7XYWbV9V6O",   # Elli
}


class AudioResult(BaseModel):
    """Result of a text-to-speech generation call."""
    audio_path: str
    duration_seconds: float
    language: str
    voice_engine: str          # "gtts" | "elevenlabs"
    text_length: int
    audience_level: str


def _strip_emojis(text: str) -> str:
    """
    Remove emoji/pictograph characters that don't speak well via TTS.

    IMPORTANT: uses a BLACKLIST (only emoji blocks), not a whitelist.
    The previous whitelist stripped Indic scripts (Telugu U+0C00-0C7F,
    Devanagari U+0900-097F, etc.) which are needed for TTS in those languages.
    This version preserves all language scripts while removing only emoji.
    """
    return re.sub(
        "["
        "\U0001F600-\U0001F64F"   # emoticons
        "\U0001F300-\U0001F5FF"   # misc symbols and pictographs
        "\U0001F680-\U0001F6FF"   # transport and map symbols
        "\U0001F700-\U0001F77F"   # alchemical symbols
        "\U0001F780-\U0001F7FF"   # geometric shapes extended
        "\U0001F800-\U0001F8FF"   # supplemental arrows
        "\U0001F900-\U0001F9FF"   # supplemental symbols and pictographs
        "\U0001FA00-\U0001FA6F"   # chess symbols
        "\U0001FA70-\U0001FAFF"   # symbols and pictographs extended-A
        "\U00002702-\U000027B0"   # dingbats
        "\U000024C2-\U0001F251"   # enclosed characters
        "]+",
        " ", text
    ).strip()


def _split_sentences(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks at sentence boundaries for gTTS."""
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:500]]


def _gtts_generate(text: str, language: str, audience_level: str, out_path: Path) -> float:
    """
    Generate audio using gTTS (free, no API key needed).

    Args:
        text: Text to speak
        language: ISO 639-1 language code
        audience_level: affects speaking speed
        out_path: output MP3 file path

    Returns:
        Estimated duration in seconds

    Academic ref: WCAG 2.2 (2023) success criterion 1.2.1
    """
    from gtts import gTTS
    import io

    clean = _strip_emojis(text)
    slow = audience_level in ["child", "junior"]
    # Normalise to gTTS-accepted code via map; fall back to prefix, then 'en'
    lang_lower = language.lower()
    lang = _LANG_MAP.get(lang_lower) or _LANG_MAP.get(lang_lower.split('-')[0], 'en')
    logger.info("TTS language: requested=%s resolved=%s", language, lang)

    chunks = _split_sentences(clean, max_chars=400)
    if len(chunks) == 1:
        try:
            tts = gTTS(text=chunks[0], lang=lang, slow=slow)
        except Exception:
            tts = gTTS(text=chunks[0], lang="en", slow=slow)
        tts.save(str(out_path))
    else:
        # Multiple chunks: save each as MP3 then concatenate raw bytes.
        # MP3 frames are self-contained, so byte concatenation is safe for
        # playback. This avoids pydub / ffprobe entirely.
        import tempfile
        all_bytes = b""
        for i, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                tmp_path = tf.name
            try:
                try:
                    gTTS(text=chunk, lang=lang, slow=slow).save(tmp_path)
                except Exception:
                    gTTS(text=chunk, lang="en", slow=slow).save(tmp_path)
                all_bytes += open(tmp_path, "rb").read()
            finally:
                try:
                    import os as _os
                    _os.unlink(tmp_path)
                except OSError:
                    pass
        with open(str(out_path), "wb") as f:
            f.write(all_bytes)

    word_count = len(clean.split())
    wpm = 100 if slow else 150
    return round(word_count / wpm * 60, 1)


def _elevenlabs_generate(text: str, audience_level: str, out_path: Path) -> float:
    """
    Generate audio using ElevenLabs API (premium quality).
    Falls back to gTTS silently if API key is missing or call fails.
    """
    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    voice = _ELEVENLABS_VOICES.get(audience_level, "Rachel")
    clean = _strip_emojis(text)[:5000]
    audio_iter = client.text_to_speech.convert(
        text=clean, voice_id=voice, model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )
    with open(str(out_path), "wb") as f:
        for chunk in audio_iter:
            f.write(chunk)
    return round(len(clean.split()) / 150 * 60, 1)


def generate_audio(
    text: str,
    language: str = "en",
    audience_level: str = "adult",
    engine: str = "auto",
) -> AudioResult:
    """
    Convert text to an MP3 audio file, with caching.

    Args:
        text: Text to speak aloud
        language: ISO 639-1 code (e.g. "en", "hi", "fr")
        audience_level: "adult" | "teen" | "junior" | "child"
        engine: "auto" | "gtts" | "elevenlabs"

    Returns:
        AudioResult with path, duration, engine used

    Academic ref: WCAG 2.2 (2023) -- audio content accessibility
    """
    cache_key = hashlib.md5(f"{text}{language}{audience_level}".encode()).hexdigest()
    out_path = OUTPUT_DIR / f"{cache_key}.mp3"

    if out_path.exists():
        wc = len(text.split())
        return AudioResult(
            audio_path=str(out_path), duration_seconds=round(wc / 150 * 60, 1),
            language=language, voice_engine="cached", text_length=len(text),
            audience_level=audience_level,
        )

    use_elevenlabs = (
        engine in ["auto", "elevenlabs"]
        and bool(ELEVENLABS_API_KEY)
        and language == "en"
    )

    if use_elevenlabs:
        try:
            duration = _elevenlabs_generate(text, audience_level, out_path)
            return AudioResult(audio_path=str(out_path), duration_seconds=duration,
                               language=language, voice_engine="elevenlabs",
                               text_length=len(text), audience_level=audience_level)
        except Exception as exc:
            logger.warning("ElevenLabs failed, falling back to gTTS: %s", exc)

    try:
        duration = _gtts_generate(text, language, audience_level, out_path)
        return AudioResult(audio_path=str(out_path), duration_seconds=duration,
                           language=language, voice_engine="gtts",
                           text_length=len(text), audience_level=audience_level)
    except Exception as exc:
        raise RuntimeError(
            f"We couldn't generate audio. Check that gTTS is installed and you have internet access. ({exc})"
        ) from exc


def build_kids_audio_text(kids_report) -> str:
    """
    Build a narration script from a KidsReport for TTS.

    Removes emojis (they don't speak well) and structures a friendly script.

    Args:
        kids_report: KidsReport from nlp.kids_rewriter

    Returns:
        Plain string ready for generate_audio()

    Academic ref: WCAG 2.2 (2023) success criterion 1.2.1
    """
    def clean(t: str) -> str:
        return _strip_emojis(t).replace("[DEMO]", "").strip()

    lines = [
        "Let me tell you about this app's privacy policy.",
        clean(kids_report.verdict_reason),
        "Here are the most important things to know:",
    ]
    for concern in kids_report.top_concerns:
        lines.append(f"- {clean(concern)}")
    for positive in kids_report.top_positives:
        lines.append(f"- Good news: {clean(positive)}")
    for clause in kids_report.clauses[:5]:
        one = clean(clause.one_liner)
        if one and not one.startswith("About"):
            lines.append(one)
    lines.append("Remember to talk to a trusted adult before agreeing to any app's terms.")
    return "\n".join(lines)
