"""
audio/tts_engine.py -- Text-to-speech engine for PrivacyLens.

Fallback chain: Google Cloud TTS → gTTS → error.
Caches generated audio by MD5 of (text + language + audience_level).

Author: Sateesh Kumar Payyavula
Reference: WCAG 2.2 (2023) -- audio accessibility requirement
"""

import base64
import hashlib
import logging
import os
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

# Google Cloud TTS voice map
_CLOUD_TTS_VOICES: dict[str, tuple[str, str]] = {
    "en": ("en-GB", "en-GB-Neural2-A"),
    "hi": ("hi-IN", "hi-IN-Neural2-A"),
    "te": ("te-IN", "te-IN-Standard-A"),
    "ta": ("ta-IN", "ta-IN-Neural2-A"),
    "fr": ("fr-FR", "fr-FR-Neural2-A"),
    "de": ("de-DE", "de-DE-Neural2-A"),
    "es": ("es-ES", "es-ES-Neural2-A"),
    "ar": ("ar-XA", "ar-XA-Neural2-A"),
}


class AudioResult(BaseModel):
    """Result of a text-to-speech generation call."""
    audio_path: str
    duration_seconds: float
    language: str
    voice_engine: str          # "gtts" | "elevenlabs" | "google_cloud_tts"
    text_length: int
    audience_level: str


def _strip_emojis(text: str) -> str:
    """
    Remove emoji/pictograph characters that don't speak well via TTS.

    IMPORTANT: uses a BLACKLIST of specific emoji Unicode blocks only.
    Preserves ALL language scripts including:
      - Telugu (U+0C00-0C7F)
      - Devanagari/Hindi (U+0900-097F)
      - Tamil (U+0B80-0BFF)
      - Kannada (U+0C80-0CFF)
      - Malayalam (U+0D00-0D7F)
      - Bengali (U+0980-09FF)
      - Arabic (U+0600-06FF)
      - All other writing systems
    """
    return re.sub(
        "["
        "\U0001F600-\U0001F64F"   # emoticons
        "\U0001F300-\U0001F5FF"   # misc symbols and pictographs
        "\U0001F680-\U0001F6FF"   # transport and map symbols
        "\U0001F900-\U0001F9FF"   # supplemental symbols and pictographs
        "\U0001FA00-\U0001FAFF"   # symbols and pictographs extended-A
        "\u2600-\u26FF"           # misc symbols (sun, stars, etc.)
        "\u2700-\u27BF"           # dingbats
        "\uFE00-\uFE0F"          # variation selectors
        "\u200D"                  # zero-width joiner (emoji combiner)
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


def _has_cloud_tts_credentials() -> bool:
    """Check if Google Cloud TTS credentials are available."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_path and os.path.exists(creds_path):
        return True
    # Also check for default app credentials
    try:
        from google.auth import default
        default()
        return True
    except Exception:
        return False


def _google_cloud_tts(text: str, language: str, audience_level: str, out_path: Path) -> float:
    """
    Generate audio using Google Cloud TTS (free tier: 1M chars/month).

    Args:
        text: Text to speak
        language: ISO 639-1 code
        audience_level: affects speaking speed
        out_path: output MP3 file path

    Returns:
        Estimated duration in seconds
    """
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()

    clean = _strip_emojis(text)[:5000]
    synthesis_input = texttospeech.SynthesisInput(text=clean)

    lang_code, voice_name = _CLOUD_TTS_VOICES.get(language, ("en-GB", "en-GB-Neural2-A"))

    voice = texttospeech.VoiceSelectionParams(
        language_code=lang_code,
        name=voice_name,
    )

    speaking_rate = 0.9 if audience_level in ["child", "junior"] else 1.0
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(str(out_path), "wb") as f:
        f.write(response.audio_content)

    word_count = len(clean.split())
    wpm = 100 if audience_level in ["child", "junior"] else 150
    return round(word_count / wpm * 60, 1)


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

    Fallback chain: Google Cloud TTS → ElevenLabs → gTTS.

    Args:
        text: Text to speak aloud
        language: ISO 639-1 code (e.g. "en", "hi", "fr")
        audience_level: "adult" | "teen" | "junior" | "child"
        engine: "auto" | "gtts" | "elevenlabs" | "google_cloud_tts"

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

    # Try Google Cloud TTS first (best quality for Indic languages)
    if engine in ["auto", "google_cloud_tts"] and _has_cloud_tts_credentials():
        try:
            duration = _google_cloud_tts(text, language, audience_level, out_path)
            logger.info("Google Cloud TTS succeeded for lang=%s", language)
            return AudioResult(audio_path=str(out_path), duration_seconds=duration,
                               language=language, voice_engine="google_cloud_tts",
                               text_length=len(text), audience_level=audience_level)
        except Exception as exc:
            logger.warning("Google Cloud TTS failed, falling back: %s", exc)

    # Try ElevenLabs (English only, premium)
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

    # gTTS fallback (always available)
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
