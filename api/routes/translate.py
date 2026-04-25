"""
api/routes/translate.py
Batch translation endpoint for frontend display text.
Translates clause summaries, red flags, etc. into the user's selected language.
Uses the shared call_gemini helper (new google-genai SDK, gemini-2.5-flash,
thinking_budget=0) — identical model path as the rest of the NLP pipeline.

Author: Sateesh Kumar Payyavula
"""
from __future__ import annotations
import logging
import re
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["translate"])

_ENGLISH_CODES = {"en", "en-gb", "en-us", "en-uk"}

_LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",    "te": "Telugu",   "ta": "Tamil",    "kn": "Kannada",
    "ml": "Malayalam","bn": "Bengali",  "mr": "Marathi",  "gu": "Gujarati",
    "pa": "Punjabi",  "ur": "Urdu",     "fr": "French",   "de": "German",
    "es": "Spanish",  "it": "Italian",  "pt": "Portuguese","nl": "Dutch",
    "pl": "Polish",   "ru": "Russian",  "ar": "Arabic",
    "zh-cn": "Chinese (Simplified)", "ja": "Japanese", "ko": "Korean",
    "tr": "Turkish",  "vi": "Vietnamese","id": "Indonesian","th": "Thai",
}


@router.post("/translate")
async def translate_batch(request: dict) -> JSONResponse:
    """
    Translate a batch of English strings to target language.

    Request:  { "texts": ["str1", "str2", ...], "language": "te" }
    Response: { "translated": ["...", "..."], "language": "te", "skipped": bool }
    """
    texts    = request.get("texts", [])
    language = (request.get("language") or "en").strip().lower()

    if language in _ENGLISH_CODES or not texts:
        return JSONResponse({"translated": texts, "language": language, "skipped": True})

    lang_name = _LANG_NAMES.get(language, language)
    texts = [str(t) for t in texts[:20]]  # cap at 20 items

    try:
        from nlp.llm_client import call_gemini

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        prompt = (
            f"Translate each numbered item to {lang_name}.\n"
            f"Write in the native {lang_name} script (NOT romanised/Latin letters).\n"
            f"Keep numbers, percentages, and regulation names (GDPR, CCPA, DPDP) in English.\n"
            f"Return ONLY the numbered translations in the exact same format.\n\n"
            f"{numbered}"
        )

        raw, _ = call_gemini(prompt, function_name="translate_batch", use_cache=False)
        raw = (raw or "").strip()

        # Parse "1. text", "2. text" ... lines
        translated: list[str] = []
        for line in raw.split("\n"):
            clean = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if clean:
                translated.append(clean)

        # Pad with originals if Gemini returned fewer items than expected
        while len(translated) < len(texts):
            translated.append(texts[len(translated)])

        logger.info("Batch translated %d strings to %s", len(texts), lang_name)
        return JSONResponse({
            "translated": translated[:len(texts)],
            "language":   language,
            "skipped":    False,
        })

    except Exception as exc:
        logger.error("Batch translation failed: %s", exc)
        return JSONResponse({"translated": texts, "language": language,
                             "skipped": True, "error": str(exc)})
