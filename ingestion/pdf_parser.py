"""
ingestion/pdf_parser.py — PDF text extraction for PrivacyLens.

Uses pdfplumber as the primary extractor (handles tables and layout well).
Falls back to PyPDF2 if pdfplumber fails (e.g., encrypted or malformed PDFs).

Author: Sateesh Kumar Payyavula
Reference: pdfplumber docs; PyPDF2 docs
"""

import io
import logging
from typing import Optional, Union

import pdfplumber
import PyPDF2
from pydantic import BaseModel

from config import SCRAPER_MAX_TEXT_LEN

logger = logging.getLogger(__name__)


# ── Pydantic model ────────────────────────────────────────────────────────────

class PDFResult(BaseModel):
    """Structured result from PDF extraction."""
    text: str
    page_count: int
    char_count: int
    extractor_used: str          # "pdfplumber" or "pypdf2"
    error: Optional[str] = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_with_pdfplumber(data: bytes) -> tuple[str, int]:
    """
    Extract text from PDF bytes using pdfplumber.

    Input:  data (bytes) — raw PDF file content
    Output: (text, page_count)
    """
    pages_text = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                pages_text.append(txt.strip())
    return "\n\n".join(pages_text), page_count


def _extract_with_pypdf2(data: bytes) -> tuple[str, int]:
    """
    Fallback: extract text from PDF bytes using PyPDF2.

    Input:  data (bytes) — raw PDF file content
    Output: (text, page_count)
    """
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    page_count = len(reader.pages)
    pages_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            pages_text.append(txt.strip())
    return "\n\n".join(pages_text), page_count


# ── Public API ────────────────────────────────────────────────────────────────

def extract_from_pdf(source: Union[bytes, str]) -> PDFResult:
    """
    Extract readable text from a PDF file.

    Accepts either raw bytes (e.g., from st.file_uploader) or a file path string.

    Strategy:
    1. Try pdfplumber — best quality for text-based PDFs.
    2. Fall back to PyPDF2 if pdfplumber raises any exception.
    3. Return a friendly error if both fail.

    Input:
        source (bytes | str) — PDF bytes or path to a local PDF file

    Output:
        PDFResult — .text contains extracted text, .error set on failure
    """
    # Load bytes from path if a string was passed
    if isinstance(source, str):
        try:
            with open(source, "rb") as f:
                data = f.read()
        except OSError as exc:
            return PDFResult(
                text="", page_count=0, char_count=0,
                extractor_used="none",
                error=f"Could not open that file: {exc}",
            )
    else:
        data = source

    if not data:
        return PDFResult(
            text="", page_count=0, char_count=0,
            extractor_used="none",
            error="The uploaded file appears to be empty.",
        )

    # 1. Try pdfplumber
    try:
        text, page_count = _extract_with_pdfplumber(data)
        extractor = "pdfplumber"
        logger.info("pdfplumber extracted %d chars from %d pages", len(text), page_count)
    except Exception as plumber_err:
        logger.warning("pdfplumber failed (%s), trying PyPDF2", plumber_err)
        # 2. Fallback: PyPDF2
        try:
            text, page_count = _extract_with_pypdf2(data)
            extractor = "pypdf2"
            logger.info("PyPDF2 extracted %d chars from %d pages", len(text), page_count)
        except Exception as pypdf_err:
            logger.error("Both extractors failed: %s", pypdf_err)
            return PDFResult(
                text="", page_count=0, char_count=0,
                extractor_used="none",
                error=(
                    "We couldn't read that PDF. "
                    "It may be scanned or password-protected. "
                    "Try pasting the text directly."
                ),
            )

    text = text[:SCRAPER_MAX_TEXT_LEN]

    if len(text.strip()) < 100:
        return PDFResult(
            text="", page_count=page_count, char_count=0,
            extractor_used=extractor,
            error=(
                "The PDF didn't contain selectable text. "
                "It may be a scanned image — try pasting the text directly."
            ),
        )

    return PDFResult(
        text=text,
        page_count=page_count,
        char_count=len(text),
        extractor_used=extractor,
    )
