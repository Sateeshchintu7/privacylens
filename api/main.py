"""
api/main.py -- PrivacyLens FastAPI application.

Mounts all route modules and configures CORS.
Run with: uvicorn api.main:app --host 0.0.0.0 --port $PORT

Author: Sateesh Kumar Payyavula
MSc Cyber Security & Human Factors, 2025-26
"""

import os
import sys
from pathlib import Path

# Ensure project root is on path so nlp/, ingestion/ etc. are importable.
# This runs before any other import so all sub-modules resolve correctly.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env for local development (no-op on Render — env vars injected natively)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PrivacyLens API",
    description=(
        "Privacy policy analysis engine. "
        "Clause extraction, risk scoring, plain-English rewriting, "
        "compliance mapping, contradiction detection, and more."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# IMPORTANT: allow_credentials=True is incompatible with allow_origins=["*"].
# List allowed origins explicitly instead.
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "https://privacylens-5yhe.vercel.app",
    "https://privacylens.vercel.app",
    "https://privacylens-api-610974231553.europe-west2.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Inline health check ───────────────────────────────────────────────────────
# Registered directly so it works even if a route module fails to import.

@app.get("/health")
def health_check() -> dict:
    """Returns API health status."""
    gemini_key     = os.getenv("GEMINI_API_KEY", "")
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    return {
        "status": "ok",
        "gemini": bool(gemini_key),
        "elevenlabs": bool(elevenlabs_key),
        "version": "1.0.0",
    }


@app.get("/warm")
def warm() -> dict:
    """
    Pre-warm endpoint — trigger module imports so first analysis is fast.
    Also used by navbar to show server status dot.
    """
    import time
    t0 = time.time()
    imported = []
    failed = []
    for mod in [
        "nlp.clause_extractor",
        "nlp.mad_engine",
        "nlp.plain_rewriter",
        "audio.tts_engine",
    ]:
        try:
            __import__(mod)
            imported.append(mod.split(".")[-1])
        except Exception as exc:
            failed.append(f"{mod}: {exc}")
    return {
        "status": "warm",
        "imports_ok": imported,
        "imports_failed": failed,
        "warm_time_ms": round((time.time() - t0) * 1000),
    }


# ── Route modules ─────────────────────────────────────────────────────────────
# Wrapped in try/except so a broken route doesn't prevent the rest from loading.

def _load_routes() -> None:
    try:
        from api.routes import analyse
        app.include_router(analyse.router, prefix="/api")
        print("[routes] analyse OK")
    except Exception as exc:
        print(f"[routes] analyse FAILED: {exc}")

    try:
        from api.routes import kids
        app.include_router(kids.router, prefix="/api")
        print("[routes] kids OK")
    except Exception as exc:
        print(f"[routes] kids FAILED: {exc}")

    try:
        from api.routes import audio
        app.include_router(audio.router, prefix="/api")
        print("[routes] audio OK")
    except Exception as exc:
        print(f"[routes] audio FAILED: {exc}")

    try:
        from api.routes import ask
        app.include_router(ask.router, prefix="/api")
        print("[routes] ask OK")
    except Exception as exc:
        print(f"[routes] ask FAILED: {exc}")

    try:
        from api.routes import compare
        app.include_router(compare.router, prefix="/api")
        print("[routes] compare OK")
    except Exception as exc:
        print(f"[routes] compare FAILED: {exc}")

    try:
        from api.routes import contradictions
        app.include_router(contradictions.router, prefix="/api")
        print("[routes] contradictions OK")
    except Exception as exc:
        print(f"[routes] contradictions FAILED: {exc}")

    try:
        from api.routes import analyse_report
        app.include_router(analyse_report.router, prefix="/api")
        print("[routes] analyse_report OK")
    except Exception as exc:
        print(f"[routes] analyse_report FAILED: {exc}")

    try:
        from api.routes import translate
        app.include_router(translate.router, prefix="/api")
        print("[routes] translate OK")
    except Exception as exc:
        print(f"[routes] translate FAILED: {exc}")


_load_routes()
