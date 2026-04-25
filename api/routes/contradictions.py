"""
api/routes/contradictions.py -- Lazy contradiction detection endpoint.

Separated from /analyse so the main pipeline stays fast (~5s).
The frontend calls this after showing initial results.

Author: Sateesh Kumar Payyavula
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["contradictions"])


class ContradictionsRequest(BaseModel):
    clauses: list[dict]


@router.post("/contradictions")
async def detect_contradictions_endpoint(request: ContradictionsRequest) -> dict:
    """
    Run contradiction detection on already-extracted clauses.
    Call this after /analyse returns — it takes 10-30s.
    Results are cached so repeat calls are instant.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from nlp.clause_extractor import ClauseResult
    from nlp.contradiction_detector import detect_contradictions

    try:
        clauses = [ClauseResult.model_validate(c) for c in request.clauses]
        report  = detect_contradictions(clauses, use_cache=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Contradiction detection error: {exc}")

    return report.model_dump()
