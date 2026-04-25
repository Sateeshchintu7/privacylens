"""api/routes/audio.py -- TTS audio generation endpoint with language support."""

from __future__ import annotations
import base64
import logging
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from api.schemas import AudioRequest, AudioResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["audio"])

_ENGLISH_CODES = {"en", "en-gb", "en-us", "en-uk"}

_LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",    "te": "Telugu",   "ta": "Tamil",    "kn": "Kannada",
    "ml": "Malayalam","bn": "Bengali",  "mr": "Marathi",  "gu": "Gujarati",
    "pa": "Punjabi",  "ur": "Urdu",     "fr": "French",   "de": "German",
    "es": "Spanish",  "it": "Italian",  "pt": "Portuguese","nl": "Dutch",
    "pl": "Polish",   "ru": "Russian",  "ar": "Arabic",
    "zh-cn": "Simplified Chinese", "zh-tw": "Traditional Chinese",
    "ja": "Japanese", "ko": "Korean",   "tr": "Turkish",  "vi": "Vietnamese",
    "id": "Indonesian","ms": "Malay",   "th": "Thai",     "sw": "Swahili",
    "fa": "Persian",
}

# Unicode ranges for Indic scripts — used to validate translation output
_INDIC_RANGES: dict[str, tuple[int, int]] = {
    "hi": (0x0900, 0x097F),  # Devanagari
    "mr": (0x0900, 0x097F),  # Devanagari (Marathi)
    "te": (0x0C00, 0x0C7F),  # Telugu
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "bn": (0x0980, 0x09FF),  # Bengali
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "pa": (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
}


def _is_garbage(text: str) -> bool:
    """Detect suspiciously repetitive text (e.g. 'google google google')."""
    words = text.lower().split()
    if len(words) <= 3:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio < 0.2  # >80% same word = garbage


def _is_same_as_original(original: str, translated: str) -> bool:
    """Return True if translation looks unchanged from the English original."""
    orig_words  = set(re.sub(r'\s+', ' ', original.lower()).split())
    trans_words = set(re.sub(r'\s+', ' ', translated.lower()).split())
    if not orig_words:
        return True
    overlap = len(orig_words & trans_words) / len(orig_words)
    return overlap > 0.65


def _translate_text(text: str, target_lang: str) -> str:
    """
    Translate English text to target language using Gemini.

    Validates that Indic-language translations contain actual native script
    characters (not romanised/English output) and retries once with a
    stricter prompt if the first attempt fails the check.

    Falls back to English on any error. Never raises.
    """
    if not text or len(text.strip()) < 5:
        return text

    lang_name = _LANG_NAMES.get(target_lang.lower(), target_lang)

    def _call_gemini(prompt: str) -> str:
        from nlp.llm_client import call_gemini
        result, _ = call_gemini(prompt, function_name="translate_audio", use_cache=False)
        return (result or "").strip()

    def _count_script_chars(t: str, lang: str) -> int:
        rng = _INDIC_RANGES.get(lang)
        if not rng:
            return 9999  # non-Indic — skip check
        lo, hi = rng
        return sum(1 for c in t if lo <= ord(c) <= hi)

    try:
        prompt = (
            f"Translate the following English text to {lang_name}.\n"
            f"CRITICAL: Write in the native {lang_name} script — NOT in English "
            f"letters or romanisation.\n"
            f"Return ONLY the translated text. No labels, no explanation.\n\n"
            f"{text}"
        )
        translated = _call_gemini(prompt)

        if not translated or len(translated) < 3:
            logger.warning("Empty Gemini translation for lang=%s", target_lang)
            return text

        if _is_garbage(translated):
            logger.warning("Garbage translation for %s: '%s...'", target_lang, translated[:40])
            return text

        if _is_same_as_original(text, translated):
            logger.warning("Translation looks identical to original for %s", target_lang)
            return text

        # Validate Indic script presence
        script_chars = _count_script_chars(translated, target_lang)
        if script_chars < 3 and target_lang in _INDIC_RANGES:
            logger.warning(
                "Translation for %s has only %d native script chars — retrying",
                target_lang, script_chars
            )
            # One retry with an even more explicit prompt
            retry_prompt = (
                f"Write in {lang_name} language using {lang_name} alphabet characters.\n"
                f"Do NOT use English or Roman letters. Use the actual {lang_name} script.\n"
                f"Translate: {text[:300]}"
            )
            retry = _call_gemini(retry_prompt)
            if _count_script_chars(retry, target_lang) >= 3:
                logger.info("Retry translation OK for %s: %d script chars", target_lang, _count_script_chars(retry, target_lang))
                return retry
            logger.error("Both translation attempts failed for %s — using English", target_lang)
            return text

        logger.info("Translated %d chars → %s (%d chars, %d script chars)",
                    len(text), lang_name, len(translated), script_chars)
        return translated

    except Exception as exc:
        logger.warning("Gemini translation to '%s' failed: %s — using English", target_lang, exc)
        return text


@router.post("/audio", response_model=AudioResponse)
async def generate_audio_endpoint(request: AudioRequest) -> AudioResponse:
    """Generate speech audio in requested language and return as base64 MP3."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from audio.tts_engine import generate_audio

    text     = request.text
    language = request.language

    # Translate to target language before TTS if non-English
    if language.lower() not in _ENGLISH_CODES:
        text = _translate_text(text, language)
        # Second-pass garbage check after translation
        if _is_garbage(text):
            logger.error("Post-translation garbage detected — falling back to English TTS")
            text     = request.text
            language = "en"

    try:
        result = generate_audio(
            text=text,
            language=language,
            audience_level=request.audience_level,
            engine=request.engine,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio generation error: {exc}")

    audio_path = Path(str(result.audio_path))
    if not audio_path.exists():
        raise HTTPException(status_code=500, detail="Audio file not created")

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    return AudioResponse(
        audio_base64=audio_b64,
        duration_seconds=result.duration_seconds or 0.0,
        engine_used=result.voice_engine or "gtts",
    )
