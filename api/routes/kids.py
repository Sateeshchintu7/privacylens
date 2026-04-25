"""
api/routes/kids.py -- Kids Mode with background-job pattern.

POST /api/kids              → {job_id: "..."}   returns in < 1s
GET  /api/kids/status/{id}  → {status, result, error}

Same pattern as /api/analyse. Critical because rewriting 5+ clauses
via Gemini takes 30-90s — well beyond any HTTP timeout.
"""

from __future__ import annotations
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["kids"])

# In-memory job store (single worker process)
_KIDS_JOBS: dict[str, dict] = {}
_MAX_JOBS = 300


def _prune() -> None:
    """Keep job store bounded — remove oldest entries."""
    if len(_KIDS_JOBS) >= _MAX_JOBS:
        oldest = list(_KIDS_JOBS.keys())[:60]
        for k in oldest:
            _KIDS_JOBS.pop(k, None)


@router.post("/kids")
async def start_kids_analysis(
    request: dict,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Start a Kids Mode analysis job. Returns job_id immediately.
    Frontend polls /api/kids/status/{job_id} every 3s.
    """
    job_id = str(uuid.uuid4())
    _prune()
    _KIDS_JOBS[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_kids_job, job_id, request)
    return JSONResponse({"job_id": job_id})


@router.get("/kids/status/{job_id}")
async def get_kids_status(job_id: str) -> JSONResponse:
    """Poll for Kids Mode job result."""
    job = _KIDS_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Kids job not found or expired.")
    return JSONResponse(job)


def _run_kids_job(job_id: str, req: dict) -> None:
    """Synchronous background worker — runs in FastAPI thread pool."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

        from nlp.kids_rewriter import rewrite_for_kids
        from nlp.plain_rewriter import PlainClause
        from nlp.mad_engine import PolicyRiskReport

        plain_clauses = [PlainClause.model_validate(c) for c in (req.get("plain_clauses") or [])]
        risk_report   = PolicyRiskReport.model_validate(req.get("risk_report") or {})

        age_map = {"child": 9, "junior": 12, "teen": 16, "8-10": 9, "11-13": 12, "14-17": 16}
        age_group = req.get("age_group", "teen")
        age = age_map.get(str(age_group), 16)

        clause_risks = risk_report.clause_risks
        report = rewrite_for_kids(plain_clauses, clause_risks, age)

        _KIDS_JOBS[job_id] = {
            "status": "complete",
            "result": {"report": report.model_dump()},
            "error": None,
        }
        logger.info("[kids job %s] complete — age=%d", job_id, age)

    except Exception as exc:
        import traceback
        logger.error("[kids job %s] FAILED:\n%s", job_id, traceback.format_exc())
        _KIDS_JOBS[job_id] = {"status": "error", "result": None, "error": str(exc)}
