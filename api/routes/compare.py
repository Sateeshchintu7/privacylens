"""api/routes/compare.py -- Policy version comparison endpoint."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.schemas import CompareRequest, CompareResponse

router = APIRouter(tags=["compare"])


@router.post("/compare", response_model=CompareResponse)
async def compare_policies_endpoint(request: CompareRequest) -> CompareResponse:
    """Compare two policy versions and return a structured diff."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from ingestion.text_cleaner import clean_text
    from ingestion.change_tracker import compare_policies

    try:
        old_text = clean_text(request.old_content).text
        new_text = clean_text(request.new_content).text
        diff = compare_policies(
            old_text=old_text,
            new_text=new_text,
            policy_name=request.policy_name,
            old_date=request.old_date,
            new_date=request.new_date,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison error: {exc}")

    return CompareResponse(diff=diff.model_dump())
