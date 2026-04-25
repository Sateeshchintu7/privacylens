"""api/routes/health.py -- Health check endpoint."""

from fastapi import APIRouter
from api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Returns API health status and feature flags."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from config import GEMINI_API_KEY, ELEVENLABS_API_KEY

    gemini_ok      = bool(GEMINI_API_KEY)
    elevenlabs_ok  = bool(ELEVENLABS_API_KEY)

    return HealthResponse(
        status="ok",
        gemini=gemini_ok,
        elevenlabs=elevenlabs_ok,
        version="1.0.0",
    )
