"""
api/routes/stats.py -- Performance monitoring endpoint.

Returns in-memory stats: total analyses, cache hit rate, timing metrics,
language distribution, and uptime. Resets on server restart.

Author: Sateesh Kumar Payyavula
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def get_stats() -> JSONResponse:
    """Return performance statistics for monitoring dashboard."""
    from api.routes.analyse import get_stats
    return JSONResponse(get_stats())
