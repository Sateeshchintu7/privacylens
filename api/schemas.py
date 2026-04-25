"""
api/schemas.py -- Pydantic v2 request/response models for PrivacyLens API.

All API boundary types defined here.
Internal NLP types imported from nlp/ and serialised via .model_dump().

Author: Sateesh Kumar Payyavula
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    input_type: str = Field(..., description="'url' | 'text' | 'pdf_base64'")
    content: str    = Field(..., description="URL, raw text, or base64-encoded PDF")
    audience_level: str = Field("adult", description="'adult' | 'teen' | 'child'")
    language: str       = Field("en",    description="ISO 639-1 language code")


class KidsRequest(BaseModel):
    plain_clauses: list[dict]
    risk_report: dict
    age_group: str = Field(..., description="'child' | 'junior' | 'teen'")


class AudioRequest(BaseModel):
    text: str
    language: str        = Field("en")
    audience_level: str  = Field("adult")
    engine: str          = Field("auto", description="'gtts' | 'elevenlabs' | 'auto'")


class AskRequest(BaseModel):
    question: str
    clauses: list[dict]
    policy_text: str
    audience_level: str = Field("adult")
    compliance_report: Optional[dict] = None


class CompareRequest(BaseModel):
    old_content: str
    new_content: str
    policy_name: str = Field("Policy")
    old_date: str    = Field("Previous version")
    new_date: str    = Field("Current version")


# ── Responses ────────────────────────────────────────────────────────────────

class AnalyseResponse(BaseModel):
    policy_name: str
    char_count: int
    clauses: list[dict]
    risk_report: dict
    plain_clauses: list[dict]
    readability: dict
    compliance: dict
    contradictions: dict
    dark_patterns: dict
    processing_ms: int


class KidsResponse(BaseModel):
    report: dict


class AudioResponse(BaseModel):
    audio_base64: str
    duration_seconds: float
    engine_used: str


class AskResponse(BaseModel):
    answer: str
    plain_answer: str
    source_quote: str
    confidence: float
    could_not_find: bool


class CompareResponse(BaseModel):
    diff: dict


class HealthResponse(BaseModel):
    status: str
    gemini: bool
    elevenlabs: bool
    version: str
