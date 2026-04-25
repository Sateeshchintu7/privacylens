"""
ingestion/text_cleaner.py — Text normalisation for PrivacyLens.

Takes raw extracted text (from scraper or PDF parser) and returns a clean,
deduped, boilerplate-stripped version ready for NLP analysis.

Author: Sateesh Kumar Payyavula
Reference: Adhikari, Das & Dewri (2025, arXiv:2501.10319) — preprocessing pipeline
"""

import re
import unicodedata
from typing import Optional

from pydantic import BaseModel


# ── Pydantic model ────────────────────────────────────────────────────────────

class CleanTextResult(BaseModel):
    """Structured result from text cleaning."""
    text: str
    original_char_count: int
    clean_char_count: int
    lines_removed: int


# ── Boilerplate patterns to strip ────────────────────────────────────────────
# Common cookie banner / navigation / footer phrases found on policy pages.
_BOILERPLATE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^(accept all cookies?|manage preferences?|cookie settings?)$"),
    re.compile(r"(?i)^(skip to (main )?content|back to top|jump to)"),
    re.compile(r"(?i)^(copyright\s+©?\s*\d{4})"),
    re.compile(r"(?i)^(all rights reserved)"),
    re.compile(r"(?i)^(follow us on|share this (page|article))"),
    re.compile(r"(?i)^(subscribe|sign up|log in|register now)$"),
    re.compile(r"(?i)^\s*\|\s*$"),           # lone pipe separators
    re.compile(r"(?i)^[\s•·\-–—]+$"),        # bullet-only lines
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _unicode_normalise(text: str) -> str:
    """Replace fancy Unicode punctuation with plain ASCII equivalents."""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes
        "\u201c": '"', "\u201d": '"',   # curly double quotes
        "\u2013": "-", "\u2014": "-",   # en-dash, em-dash
        "\u00a0": " ",                  # non-breaking space
        "\u2022": "-",                  # bullet
        "\u00b7": "-",                  # middle dot
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs to a single space; normalise line endings."""
    text = re.sub(r"[ \t]+", " ", text)        # multiple spaces → one
    text = re.sub(r"\n{3,}", "\n\n", text)     # 3+ blank lines → 2
    return text.strip()


def _is_boilerplate(line: str) -> bool:
    """Return True if this line matches a known boilerplate pattern."""
    stripped = line.strip()
    if len(stripped) < 3:
        return True
    return any(p.match(stripped) for p in _BOILERPLATE_PATTERNS)


def _deduplicate_lines(lines: list[str]) -> tuple[list[str], int]:
    """
    Remove exact duplicate consecutive lines (common in scraped pages).

    Input:  lines (list[str]) — raw line list
    Output: (deduped_lines, count_removed)
    """
    seen: set[str] = set()
    result: list[str] = []
    removed = 0
    for line in lines:
        key = line.strip().lower()
        if key in seen and len(key) > 20:   # only dedup non-trivial repeats
            removed += 1
            continue
        seen.add(key)
        result.append(line)
    return result, removed


# ── Public API ────────────────────────────────────────────────────────────────

def clean_text(raw: str) -> CleanTextResult:
    """
    Clean raw extracted text for NLP processing.

    Steps:
    1. Unicode normalisation (NFKC + curly-quote replacement)
    2. Boilerplate line removal
    3. Exact-duplicate line deduplication
    4. Whitespace collapse

    Input:  raw (str) — text from scraper or PDF parser
    Output: CleanTextResult — .text is the cleaned version

    Reference: Adhikari, Das & Dewri (2025) preprocessing best practices
    """
    original_len = len(raw)

    # Step 1: Unicode normalise
    text = _unicode_normalise(raw)

    # Step 2: Split into lines, strip boilerplate
    lines = text.splitlines()
    filtered = [ln for ln in lines if not _is_boilerplate(ln)]
    lines_removed_boilerplate = len(lines) - len(filtered)

    # Step 3: Deduplicate
    deduped, lines_removed_dup = _deduplicate_lines(filtered)
    total_removed = lines_removed_boilerplate + lines_removed_dup

    # Step 4: Rejoin and collapse whitespace
    text = _collapse_whitespace("\n".join(deduped))

    return CleanTextResult(
        text=text,
        original_char_count=original_len,
        clean_char_count=len(text),
        lines_removed=total_removed,
    )


def extract_sentences(text: str, min_len: int = 20) -> list[str]:
    """
    Split cleaned text into individual sentences for clause-level analysis.

    Input:
        text    (str) — cleaned policy text
        min_len (int) — discard sentences shorter than this (nav fragments etc.)

    Output: list[str] — sentence list
    """
    # Simple sentence splitter — adequate for legal text
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", text)
    return [s.strip() for s in raw_sentences if len(s.strip()) >= min_len]
