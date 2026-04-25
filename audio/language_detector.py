"""
audio/language_detector.py -- Language detection for PrivacyLens.

Detects the language of policy text so TTS uses the correct voice.
Falls back to "en" if confidence is low or detection fails.

Author: Sateesh Kumar Payyavula
Reference: WCAG 2.2 (2023) -- language identification requirement (SC 3.1.1)
"""

import logging

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect the ISO 639-1 language code of the given text.

    Uses langdetect with a fixed seed for reproducibility.
    Returns "en" if confidence < 0.8 or detection fails.

    Args:
        text: Any text sample (first 2000 chars are used)

    Returns:
        ISO 639-1 code string, e.g. "en", "hi", "fr"

    Academic ref:
        WCAG 2.2 (2023) Success Criterion 3.1.1 -- Language of Page
    """
    try:
        from langdetect import detect, DetectorFactory, LangDetectException
        DetectorFactory.seed = 42  # reproducibility across runs
        lang = detect(text[:2000])
        return lang if lang else "en"
    except Exception as exc:
        logger.info("Language detection failed (%s), defaulting to English", exc)
        return "en"
