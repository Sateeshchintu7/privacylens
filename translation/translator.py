"""
translation/translator.py -- Multi-language translation for PrivacyLens.

Translates plain-English policy summaries into 35 languages.
Primary: googletrans (free). Fallback: deep_translator.
Never crashes -- returns original text on failure.

Author: Sateesh Kumar Payyavula
Reference: WCAG 2.2 (2023) -- language accessibility
"""

import hashlib
import logging
from pathlib import Path
from config import BASE_DIR

logger = logging.getLogger(__name__)
_TRANS_CACHE = BASE_DIR / ".cache" / "translations"
_TRANS_CACHE.mkdir(parents=True, exist_ok=True)

LANGUAGES: dict[str, str] = {
    "en": "English",    "hi": "Hindi",      "te": "Telugu",
    "ta": "Tamil",      "kn": "Kannada",    "ml": "Malayalam",
    "bn": "Bengali",    "mr": "Marathi",    "gu": "Gujarati",
    "pa": "Punjabi",    "ur": "Urdu",       "fr": "French",
    "de": "German",     "es": "Spanish",    "it": "Italian",
    "pt": "Portuguese", "nl": "Dutch",      "pl": "Polish",
    "ru": "Russian",    "ar": "Arabic",     "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",       "ja": "Japanese",
    "ko": "Korean",     "th": "Thai",       "vi": "Vietnamese",
    "id": "Indonesian", "ms": "Malay",      "tr": "Turkish",
    "fa": "Persian",    "sw": "Swahili",    "yo": "Yoruba",
    "ha": "Hausa",      "am": "Amharic",    "zu": "Zulu",
}

LANGUAGE_FLAGS: dict[str, str] = {
    "en": "\U0001f1ec\U0001f1e7", "hi": "\U0001f1ee\U0001f1f3",
    "te": "\U0001f1ee\U0001f1f3", "ta": "\U0001f1ee\U0001f1f3",
    "kn": "\U0001f1ee\U0001f1f3", "ml": "\U0001f1ee\U0001f1f3",
    "bn": "\U0001f1e7\U0001f1e9", "mr": "\U0001f1ee\U0001f1f3",
    "gu": "\U0001f1ee\U0001f1f3", "pa": "\U0001f1ee\U0001f1f3",
    "ur": "\U0001f1f5\U0001f1f0", "fr": "\U0001f1eb\U0001f1f7",
    "de": "\U0001f1e9\U0001f1ea", "es": "\U0001f1ea\U0001f1f8",
    "it": "\U0001f1ee\U0001f1f9", "pt": "\U0001f1f5\U0001f1f9",
    "nl": "\U0001f1f3\U0001f1f1", "pl": "\U0001f1f5\U0001f1f1",
    "ru": "\U0001f1f7\U0001f1fa", "ar": "\U0001f1f8\U0001f1e6",
    "zh-cn": "\U0001f1e8\U0001f1f3", "zh-tw": "\U0001f1f9\U0001f1fc",
    "ja": "\U0001f1ef\U0001f1f5", "ko": "\U0001f1f0\U0001f1f7",
    "th": "\U0001f1f9\U0001f1ed", "vi": "\U0001f1fb\U0001f1f3",
    "id": "\U0001f1ee\U0001f1e9", "ms": "\U0001f1f2\U0001f1fe",
    "tr": "\U0001f1f9\U0001f1f7", "fa": "\U0001f1ee\U0001f1f7",
    "sw": "\U0001f1f0\U0001f1ea", "yo": "\U0001f1f3\U0001f1ec",
    "ha": "\U0001f1f3\U0001f1ec", "am": "\U0001f1ea\U0001f1f9",
    "zu": "\U0001f1ff\U0001f1e6",
}


def get_display_name(lang_code: str) -> str:
    """Return a formatted display string e.g. 'English' or 'Hindi'."""
    flag = LANGUAGE_FLAGS.get(lang_code, "\U0001f310")
    name = LANGUAGES.get(lang_code, lang_code)
    return f"{flag} {name}"


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Translate text to the target language.

    Uses googletrans as primary, deep_translator as fallback.
    Caches results to .cache/translations/.
    Never crashes -- returns original text on failure.

    Args:
        text: Text to translate (max 5000 chars)
        target_lang: ISO 639-1 target language code
        source_lang: Source language or "auto"

    Returns:
        Translated string, or original text on failure

    Academic ref: WCAG 2.2 (2023) -- language accessibility
    """
    if not text.strip():
        return text
    if target_lang == "en" or target_lang == source_lang:
        return text

    cache_key = hashlib.md5(f"{text[:200]}{target_lang}".encode()).hexdigest()
    cache_file = _TRANS_CACHE / f"{cache_key}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    chunk = text[:5000]
    result = None

    # Primary: googletrans
    try:
        from googletrans import Translator
        translator = Translator()
        translated = translator.translate(chunk, dest=target_lang)
        result = translated.text
    except Exception as exc:
        logger.info("googletrans failed (%s), trying deep_translator", exc)

    # Fallback: deep_translator
    if not result:
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source="auto", target=target_lang).translate(chunk)
        except Exception as exc:
            logger.warning("Both translation engines failed: %s", exc)
            return text

    if result:
        cache_file.write_text(result, encoding="utf-8")
        return result
    return text


def translate_kids_report(report, target_lang: str):
    """
    Translate all human-readable text in a KidsReport.

    Keeps emojis and category IDs unchanged.
    Returns a new KidsReport with translated text.

    Args:
        report: KidsReport from nlp.kids_rewriter
        target_lang: ISO 639-1 target language code

    Returns:
        KidsReport with translated text fields
    """
    if target_lang == "en":
        return report

    from nlp.kids_rewriter import KidsReport, KidsClause

    translated_clauses = []
    for clause in report.clauses:
        translated_clauses.append(KidsClause(
            category=clause.category, emoji=clause.emoji,
            risk_emoji=clause.risk_emoji, risk_level=clause.risk_level,
            feature_flags=clause.feature_flags,
            kids_summary=translate_text(clause.kids_summary, target_lang),
            one_liner=translate_text(clause.one_liner, target_lang),
        ))

    return KidsReport(
        age_group=report.age_group, target_grade=report.target_grade,
        verdict=report.verdict, verdict_emoji=report.verdict_emoji,
        overall_emoji_summary=report.overall_emoji_summary,
        clauses=translated_clauses,
        verdict_reason=translate_text(report.verdict_reason, target_lang),
        top_concerns=[translate_text(c, target_lang) for c in report.top_concerns],
        top_positives=[translate_text(p, target_lang) for p in report.top_positives],
    )
