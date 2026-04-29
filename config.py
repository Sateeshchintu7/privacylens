"""
config.py — Central settings for PrivacyLens.

Loads all environment variables, defines audience levels, model settings,
risk thresholds, and supported languages.

Author: Sateesh Kumar Payyavula
MSc Cyber Security & Human Factors, 2025–26
Supervisor: Jiankang Zhang
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# ── API Keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
GOOGLE_TRANSLATE_API_KEY: str = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")

# ── Model Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.0"))
GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "8192"))

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_DIR: Path = BASE_DIR / os.getenv("CACHE_DIR", ".cache")
CACHE_DIR.mkdir(exist_ok=True)

# ── Audience Levels ───────────────────────────────────────────────────────────
# Maps an age band to the target Flesch-Kincaid grade level and UI label.
# Reference: Reidenberg et al. (2015) — avg privacy policy = Grade 14.8
AUDIENCE_LEVELS: dict = {
    "adult": {
        "label": "Adult (18+)",
        "fk_grade": 6,
        "description": "Plain English, Grade 6 reading level",
        "prompt_key": "plain_rewrite",
    },
    "teen": {
        "label": "Teen (14–17)",
        "fk_grade": 7,
        "description": "Friendly tone, Grade 7 reading level",
        "prompt_key": "kids_rewrite_grade7",
    },
    "preteen": {
        "label": "Pre-teen (11–13)",
        "fk_grade": 5,
        "description": "Simple language, Grade 5, emoji cues",
        "prompt_key": "kids_rewrite_grade5",
    },
    "child": {
        "label": "Child (8–10)",
        "fk_grade": 3,
        "description": "Story format, Grade 3, lots of emoji",
        "prompt_key": "kids_rewrite_grade3",
    },
}

def get_audience_level(age: int) -> str:
    """Return audience key for a given age integer."""
    if age >= 18:
        return "adult"
    if age >= 14:
        return "teen"
    if age >= 11:
        return "preteen"
    return "child"

# ── Risk Thresholds ───────────────────────────────────────────────────────────
# MAD Engine grade bands (Phase 2)
RISK_GRADES: dict = {
    "A": (0, 20),    # Very low risk — green
    "B": (21, 40),   # Low risk — light green
    "C": (41, 60),   # Moderate risk — amber
    "D": (61, 80),   # High risk — orange
    "F": (81, 100),  # Very high risk — red
}

RISK_COLOURS: dict = {
    "A": "#2ecc71",
    "B": "#a8e6cf",
    "C": "#f39c12",
    "D": "#e67e22",
    "F": "#e74c3c",
}

# ── Supported Languages ───────────────────────────────────────────────────────
# Subset shown in the UI language picker (full list via Google Translate)
SUPPORTED_LANGUAGES: dict = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "pt": "Portuguese",
}

# ── Document Types ────────────────────────────────────────────────────────────
DOCUMENT_TYPES: list = [
    "Privacy Policy",
    "Terms & Conditions",
    "EULA",
    "Cookie Policy",
    "App Permissions",
    "Consent Notice",
    "Other Legal Document",
]

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE: Path = BASE_DIR / "logs" / "analysis_log.jsonl"
LOG_FILE.parent.mkdir(exist_ok=True)

# ── Scraper Settings ──────────────────────────────────────────────────────────
SCRAPER_TIMEOUT: int = 15       # seconds
SCRAPER_MAX_TEXT_LEN: int = 200_000   # characters — safety cap
REQUEST_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PrivacyLens/1.0; "
        "MSc Research Project; +https://github.com/privacylens)"
    )
}
