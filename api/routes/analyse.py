"""
api/routes/analyse.py -- Main policy analysis endpoint.

Background-job pattern to bypass Render free tier 30-second HTTP timeout:

  POST /api/analyse                    → returns {job_id} in < 1 second
  GET  /api/analyse/status/{job_id}    → returns running | complete | error

The heavy NLP pipeline runs as a FastAPI BackgroundTask (thread pool),
so the HTTP response is sent BEFORE the work starts — Render's 30-second
timeout never fires because the response is already delivered.

Author: Sateesh Kumar Payyavula
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import AnalyseRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analyse"])

# ── In-memory stores ──────────────────────────────────────────────────────────
# Survive across HTTP requests; reset only on redeploy.

_JOBS: dict[str, dict] = {}   # job_id → {status, result, error}
_CACHE: dict[str, dict] = {}  # md5(content[:3000]) → result dict
_MAX_CACHE = 50
_MAX_JOBS  = 200              # evict oldest jobs after this many


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ck(content: str) -> str:
    return hashlib.md5(content[:3000].encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    return _CACHE.get(key)


def _cache_set(key: str, data: dict) -> None:
    if len(_CACHE) >= _MAX_CACHE:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = data


def _job_set(job_id: str, payload: dict) -> None:
    if len(_JOBS) >= _MAX_JOBS:
        _JOBS.pop(next(iter(_JOBS)))
    _JOBS[job_id] = payload


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyse")
async def start_analysis(
    request: AnalyseRequest,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Starts analysis and returns job_id in < 1 second.
    Cached results return cached=True; frontend can fetch immediately.
    New documents: analysis runs in background; poll /analyse/status/{job_id}.
    """
    ck = _ck(request.content)

    # Cache hit → mark job complete instantly
    cached = _cache_get(ck)
    job_id = str(uuid.uuid4())
    if cached:
        _job_set(job_id, {"status": "complete", "result": cached, "error": None})
        return JSONResponse({"job_id": job_id, "cached": True})

    # Cache miss → start background job
    _job_set(job_id, {"status": "running", "result": None, "error": None})
    background_tasks.add_task(_run_job, job_id, request.model_dump(), ck)
    return JSONResponse({"job_id": job_id, "cached": False})


@router.get("/analyse/status/{job_id}")
async def get_job_status(job_id: str) -> JSONResponse:
    """
    Frontend polls this every 3 seconds.
    Returns {status: running|complete|error, result: {...}|null, error: str|null}.
    """
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return JSONResponse(job)


# ── Background worker ─────────────────────────────────────────────────────────

def _run_job(job_id: str, req: dict, cache_key: str) -> None:
    """
    Synchronous background task — FastAPI runs this in a thread pool.
    NOT subject to HTTP request timeout because the response was already sent.
    """
    try:
        result = _do_analysis(req)
        # Only cache if we got meaningful clause extraction results
        if len(result.get("clauses", [])) > 0:
            _cache_set(cache_key, result)
        _job_set(job_id, {"status": "complete", "result": result, "error": None})
    except Exception as exc:
        import traceback
        print(f"[job {job_id}] FAILED:\n{traceback.format_exc()}")
        _job_set(job_id, {"status": "error", "result": None, "error": str(exc)})


def _do_analysis(req: dict) -> dict:
    """Full NLP pipeline. Runs in a thread pool worker."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from ingestion.scraper          import extract_from_url
    from ingestion.pdf_parser       import extract_from_pdf
    from ingestion.text_cleaner     import clean_text
    from nlp.clause_extractor       import extract_clauses
    from nlp.mad_engine             import score_policy
    from nlp.plain_rewriter         import rewrite_policy
    from nlp.readability            import score_readability
    from nlp.compliance_mapper      import map_compliance
    from nlp.dark_pattern_detector  import detect_dark_patterns

    t0 = time.perf_counter()

    input_type     = req.get("input_type", "text")
    content        = req.get("content", "")
    audience_level = req.get("audience_level", "adult")
    policy_name    = "Policy"

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    if input_type == "url":
        res = extract_from_url(content.strip())
        if res.error:
            err_lower = res.error.lower()
            if any(k in err_lower for k in ("403", "block", "access denied", "automated", "forbidden")):
                raise ValueError(
                    "BLOCKED_403: This website prevents automated access to its privacy policy. "
                    "Open it in your browser, copy the text, then use the Paste Text tab."
                )
            raise ValueError(f"Could not fetch URL: {res.error}")
        raw_text    = res.text
        policy_name = content.strip()[:60]

        # Quality gate: make sure we actually got privacy policy content.
        # Google Cache / CDN fallbacks can return page-shell HTML (nav, meta,
        # cookie banners) that passes the 200-char length check but has no
        # policy substance.  If the text is ≥ 500 chars but contains none of
        # the expected privacy keywords we almost certainly got the wrong page.
        _POLICY_KW = {"privacy", "personal", "information", "collect", "data", "consent"}
        text_lower  = raw_text.lower()
        kw_hits     = sum(1 for kw in _POLICY_KW if kw in text_lower)
        if len(raw_text) >= 500 and kw_hits < 2:
            raise ValueError(
                "BLOCKED_403: We fetched the page but it doesn't appear to contain "
                "a privacy policy (likely a bot-detection or JavaScript-rendered page). "
                "Open the policy in your browser, copy the text, then use the Paste Text tab."
            )

    elif input_type == "text":
        raw_text    = content
        policy_name = "Pasted text"

    elif input_type == "pdf_base64":
        try:
            pdf_bytes = base64.b64decode(content)
        except Exception:
            raise ValueError("Invalid base64 PDF content")
        res = extract_from_pdf(pdf_bytes)
        if res.error:
            raise ValueError(f"PDF parse error: {res.error}")
        raw_text    = res.text
        policy_name = "Uploaded PDF"

    else:
        raise ValueError(f"Unknown input_type: {input_type}")

    if not raw_text.strip():
        raise ValueError("No text could be extracted from the input")

    # ── Step 2–7: NLP pipeline ────────────────────────────────────────────────
    logger.info("Ingested %d raw chars from input_type=%s", len(raw_text), input_type)
    cleaned       = clean_text(raw_text)
    policy_text   = cleaned.text
    logger.info("Cleaned text: %d chars (was %d raw)", len(policy_text), len(raw_text))

    clauses       = extract_clauses(policy_text)
    clause_count  = len(clauses)
    logger.info("extract_clauses: %d clauses from %d chars of text", clause_count, len(policy_text))
    if clause_count == 0:
        logger.error("CRITICAL: 0 clauses extracted. Text sample: %.200s", policy_text)

    # Run independent pipeline stages in parallel — major speedup vs sequential
    with ThreadPoolExecutor(max_workers=5) as ex:
        f_risk       = ex.submit(score_policy, clauses)
        f_plain      = ex.submit(rewrite_policy, clauses, audience_level)
        f_readability = ex.submit(score_readability, policy_text)
        f_compliance = ex.submit(map_compliance, clauses, True, policy_text)
        f_dark       = ex.submit(detect_dark_patterns, clauses)
        risk_report   = f_risk.result()
        plain_clauses = f_plain.result()
        readability   = f_readability.result()
        compliance    = f_compliance.result()
        dark_patterns = f_dark.result()

    # Contradictions served lazily via /api/contradictions
    contradictions = {
        "total_found": 0, "contradictions": [], "has_critical": False,
        "summary": "pending", "candidates_screened": 0, "llm_calls_made": 0,
    }

    processing_ms = int((time.perf_counter() - t0) * 1000)
    print(f"[analyse] {policy_name!r} — {len(clauses)} clauses — {processing_ms}ms")

    return {
        "policy_name":   policy_name,
        "policy_text":   policy_text[:5000],
        "char_count":    cleaned.clean_char_count,
        "clauses":       [c.model_dump() for c in clauses],
        "risk_report":   risk_report.model_dump(),
        "plain_clauses": [p.model_dump() for p in plain_clauses],
        "readability":   readability.model_dump(),
        "compliance":    compliance.model_dump(),
        "contradictions": contradictions,
        "dark_patterns": dark_patterns.model_dump(),
        "processing_ms": processing_ms,
    }


def _log_analysis(policy_name: str, clause_count: int, ms: int) -> None:
    print(f"[analyse] {policy_name!r} — {clause_count} clauses — {ms}ms")
