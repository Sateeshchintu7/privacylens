"""
api/routes/analyse_report.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Comprehensive single-shot analysis using one Gemini prompt.

Why single-shot beats the fragmented pipeline:
  - One Gemini call reasons across the WHOLE policy
  - Output is coherent, not 7 fragments stitched together
  - Supports multilingual output via language parameter

Job lifecycle:
  POST /api/analyse/report            → {job_id}   <1s
  GET  /api/analyse/report/status/id  → running | complete | error
"""

import hashlib
import json
import logging
import os
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_REPORT_JOBS:  dict[str, dict] = {}
_REPORT_CACHE: dict[str, dict] = {}
_CACHE_MAX = 30

_LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",      "te": "Telugu",     "ta": "Tamil",
    "kn": "Kannada",    "ml": "Malayalam",  "bn": "Bengali",
    "mr": "Marathi",    "gu": "Gujarati",   "pa": "Punjabi",
    "ur": "Urdu",       "fr": "French",     "de": "German",
    "es": "Spanish",    "it": "Italian",    "pt": "Portuguese",
    "nl": "Dutch",      "pl": "Polish",     "ru": "Russian",
    "ar": "Arabic",     "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",         "ja": "Japanese",
    "ko": "Korean",     "tr": "Turkish",    "vi": "Vietnamese",
    "id": "Indonesian", "ms": "Malay",      "th": "Thai",
    "sw": "Swahili",    "fa": "Persian",
}

_ENGLISH_CODES = {"en", "en-gb", "en-us", "en-uk"}


@router.post("/analyse/report")
async def start_report(
    request: dict,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Start comprehensive analysis. Returns job_id instantly."""
    content  = request.get("content", "")
    language = request.get("language", "en")

    cache_key = hashlib.md5(
        f"{content[:3000]}{language}".encode()
    ).hexdigest()

    if cache_key in _REPORT_CACHE:
        job_id = f"cached-{cache_key[:8]}"
        _REPORT_JOBS[job_id] = {
            "status": "complete",
            "result": _REPORT_CACHE[cache_key],
            "from_cache": True,
        }
        return JSONResponse({"job_id": job_id, "cached": True})

    job_id = str(uuid.uuid4())
    _REPORT_JOBS[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_report, job_id, request, cache_key)
    return JSONResponse({"job_id": job_id, "cached": False})


@router.get("/analyse/report/status/{job_id}")
async def report_status(job_id: str) -> JSONResponse:
    """Poll for report result."""
    job = _REPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found")
    return JSONResponse(job)


def _run_report(job_id: str, request: dict, cache_key: str) -> None:
    """Synchronous background task — runs in FastAPI thread pool."""
    try:
        result = _generate_report(request)
        if len(_REPORT_CACHE) >= _CACHE_MAX:
            del _REPORT_CACHE[next(iter(_REPORT_CACHE))]
        _REPORT_CACHE[cache_key] = result
        _REPORT_JOBS[job_id] = {"status": "complete", "result": result, "error": None}
    except Exception as exc:
        logger.error("Report job %s failed: %s", job_id[:8], exc)
        _REPORT_JOBS[job_id] = {"status": "error", "result": None, "error": str(exc)}


def _generate_report(request: dict) -> dict:
    """Single-shot Gemini analysis."""
    input_type = request.get("input_type", "text")
    content    = request.get("content", "")
    language   = request.get("language", "en")

    # Get policy text
    if input_type == "url":
        from ingestion.scraper import extract_from_url
        res = extract_from_url(content.strip())
        if res.error:
            if "403" in res.error or "blocked" in res.error.lower():
                raise Exception(
                    "BLOCKED_403: This website blocks automated access. "
                    "Please paste the policy text directly."
                )
            raise Exception(f"Could not fetch URL: {res.error}")
        raw_text = res.text
        policy_name = content.strip()[:60]
    else:
        raw_text = content
        policy_name = "Pasted text"

    from ingestion.text_cleaner import clean_text
    cleaned = clean_text(raw_text)
    text = cleaned.text if hasattr(cleaned, 'text') else str(cleaned)

    if len(text.strip()) < 100:
        raise Exception("Text too short to analyse.")

    # Load master prompt
    from api.prompt_loader import load_prompt
    prompt_template = load_prompt("prompts/master_analysis.txt")

    # Language instruction
    lang_instruction = ""
    if language.lower() not in _ENGLISH_CODES:
        lang_name = _LANG_NAMES.get(language.lower(), language)
        lang_instruction = (
            f"\nCRITICAL LANGUAGE REQUIREMENT: "
            f"Write your ENTIRE response in {lang_name} language using the native {lang_name} script. "
            f"ALL text fields must be in {lang_name}. "
            f"DO NOT use English or romanised letters. "
            f"Only keep in English: GDPR, CCPA, DPDP, EU AI Act, "
            f"JSON field names, and numeric scores.\n"
        )

    text_sample = text[:8000]
    if len(text) > 8000:
        text_sample += "\n\n[Policy truncated for analysis]"

    full_prompt = prompt_template.replace("{POLICY_TEXT}", text_sample)
    if lang_instruction:
        full_prompt = lang_instruction + full_prompt

    # Call Gemini using existing llm_client infrastructure
    from config import GEMINI_API_KEY, GEMINI_MODEL
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set")

    client = genai.Client(api_key=GEMINI_API_KEY)
    gen_config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=8192,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt,
        config=gen_config,
    )

    raw = resp.text
    if not raw:
        raise Exception("Gemini returned empty response")

    report = _parse_report(raw)
    report["policy_name"] = policy_name
    report["policy_text"] = text[:5000]
    report["language"]    = language
    logger.info(
        "Report generated: %s, lang=%s, clauses=%d",
        policy_name, language, len(report.get("clause_analysis", []))
    )
    return report


def _parse_report(raw: str) -> dict:
    """Parse Gemini JSON response. Never raises."""
    if not raw:
        return _fallback_report()

    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return _fallback_report()


def _fallback_report() -> dict:
    return {
        "plain_summary": {
            "overview": "Analysis could not be completed.",
            "analogy": "", "for_children": "", "for_elderly": "",
            "the_catch": "Please try again.",
        },
        "data_collected": [], "how_data_is_used": [],
        "third_party_sharing": {"does_share": False, "parties": [], "summary": ""},
        "user_rights": {
            "gdpr": {"rights": [], "how_to_exercise": "", "strength": "weak"},
            "ccpa": {"rights": [], "how_to_exercise": "", "strength": "weak"},
            "dpdp": {"rights": [], "how_to_exercise": "", "strength": "weak"},
        },
        "compliance": {
            "gdpr":     {"score": 0, "grade": "?", "explanation": "", "strengths": [], "gaps": []},
            "ccpa":     {"score": 0, "grade": "?", "explanation": "", "strengths": [], "gaps": []},
            "dpdp":     {"score": 0, "grade": "?", "explanation": "", "strengths": [], "gaps": []},
            "eu_ai_act":{"score": 0, "explanation": "", "gaps": [], "enforcement_date": "August 2, 2026"},
            "overall_grade": "?", "overall_explanation": "Analysis failed.",
        },
        "clause_analysis": [], "red_flags": [],
        "positive_signals": [], "dark_patterns": [],
        "final_verdict": {
            "is_safe": False, "verdict": "Use with caution",
            "who_should_be_cautious": ["All users"],
            "recommendation": "Analysis failed. Please try again.",
            "action_steps": [],
        },
        "readability": {
            "original_grade": 0, "assessment": "Unknown",
            "plain_version_available": False,
        },
    }
