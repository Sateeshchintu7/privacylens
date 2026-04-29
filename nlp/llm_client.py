"""
nlp/llm_client.py — Shared Gemini LLM client for PrivacyLens.

Provides a single call_gemini() entry point with:
  - File-based caching (keyed on MD5 of prompt text)
  - 3-tier fallback: Gemini Pro → Gemini Flash → OpenRouter (llama-3.3-70b)
  - Structured JSONL logging of every API call
  - Robust JSON response parsing (handles markdown blocks)

Author: Sateesh Kumar Payyavula
MSc Cyber Security & Human Factors, 2025-26
"""

import hashlib
import json
import logging
import re
import time
from pathlib import Path

from config import (
    CACHE_DIR, GEMINI_API_KEY, GEMINI_MAX_TOKENS,
    GEMINI_MODEL, GEMINI_TEMPERATURE, LOG_FILE,
)

logger = logging.getLogger(__name__)
_LLM_CACHE = CACHE_DIR / "llm"
_LLM_CACHE.mkdir(exist_ok=True)


# ── Internal logging ──────────────────────────────────────────────────────────

def _log(fn: str, ti: int, to: int, ms: int, cached: bool) -> None:
    """Append one JSON record to logs/analysis_log.jsonl."""
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": GEMINI_MODEL, "function": fn,
        "tokens_in": ti, "tokens_out": to, "ms": ms, "cached": cached,
    }
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # Non-fatal — logging failure must never break the pipeline


# ── OpenRouter fallback ───────────────────────────────────────────────────────

def call_openrouter(
    messages: list[dict],
    function_name: str = "unknown",
) -> tuple[str, bool]:
    """
    Call OpenRouter API (llama-3.3-70b-instruct:free) as final LLM fallback.

    Args:
        messages: List of {"role": ..., "content": ...} dicts (OpenAI format)
        function_name: Label for the log entry

    Returns:
        tuple: (response_text, was_cached=False)
    """
    import os as _os
    import urllib.request as _urllib

    api_key = _os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set — cannot use OpenRouter fallback. "
            "Add OPENROUTER_API_KEY=your_key to your .env file."
        )

    payload = json.dumps({
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": messages,
    }).encode()

    req = _urllib.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    t0 = time.monotonic()
    with _urllib.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    text = data["choices"][0]["message"]["content"]
    ms = int((time.monotonic() - t0) * 1000)
    _log(function_name, 0, len(text) // 4, ms, cached=False)
    return text, False


# ── Public API call ───────────────────────────────────────────────────────────

def call_gemini(
    prompt: str,
    function_name: str = "unknown",
    use_cache: bool = True,
) -> tuple[str, bool]:
    """
    Call the Gemini API with caching, retry, and a 3-tier fallback chain.

    Fallback order:
        1. gemini-2.5-pro   (primary)
        2. gemini-2.5-flash (immediate switch on quota/model errors, no sleep)
        3. OpenRouter llama-3.3-70b (final fallback if all Gemini attempts fail)

    Args:
        prompt: Full prompt string to send to the model
        function_name: Label for the log entry (e.g. "clause_extractor")
        use_cache: If True, check file cache before calling API

    Returns:
        tuple: (response_text, was_cached)

    Academic ref:
        Rodriguez et al. (2024, Springer Computing) -- LLM API methodology
    """
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not set. "
            "Create a .env file and add: GEMINI_API_KEY=your_key_here"
        )

    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    cache_file = _LLM_CACHE / f"{cache_key}.json"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if use_cache and cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        _log(function_name, data.get("ti", 0), data.get("to", 0), 0, cached=True)
        return data["r"], True

    # ── API call (google-genai SDK) ───────────────────────────────────────────
    import os as _os
    from google import genai
    from google.genai import types

    # Remove any system GOOGLE_API_KEY so SDK uses our explicit key only
    _os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=GEMINI_API_KEY)

    _FALLBACK_MODEL = "gemini-2.5-flash"
    active_model = GEMINI_MODEL

    def _make_config(model: str) -> types.GenerateContentConfig:
        # 2.5-pro requires thinking_budget > 0 (thinking-only model).
        # 2.5-flash and older models accept budget=0 (thinking optional).
        budget = 8192 if "2.5-pro" in model else 0
        return types.GenerateContentConfig(
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_budget=budget),
        )

    logger.info("Using Gemini Pro (%s)", active_model)
    t0 = time.monotonic()
    last_err = None
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=active_model,
                contents=prompt,
                config=_make_config(active_model),
            )
            text = resp.text
            if not text:
                raise RuntimeError("Gemini returned empty response (resp.text is None/empty)")
            ms = int((time.monotonic() - t0) * 1000)
            meta = getattr(resp, "usage_metadata", None)
            ti = getattr(meta, "prompt_token_count", len(prompt) // 4)
            to = getattr(meta, "candidates_token_count", len(text) // 4)
            _log(function_name, ti, to, ms, cached=False)
            if use_cache:
                cache_file.write_text(
                    json.dumps({"r": text, "ti": ti, "to": to}), encoding="utf-8"
                )
            return text, False
        except Exception as exc:
            last_err = exc
            logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
            err_str = str(exc).lower()
            # Switch to fallback immediately on quota exhaustion OR model unavailability
            if active_model != _FALLBACK_MODEL and any(
                k in err_str for k in (
                    "not found", "invalid", "unsupported", "does not exist",
                    "resource_exhausted", "429",
                )
            ):
                logger.warning("Falling back to Gemini Flash (%s)", _FALLBACK_MODEL)
                active_model = _FALLBACK_MODEL
                continue  # retry immediately with fallback, no sleep
            if attempt < 2:
                # Extract retry delay from 429 errors when available
                err_str = str(exc)
                wait = [5, 15][attempt]  # default backoff
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    import re as _re
                    m = _re.search(r"retryDelay.*?(\d+)s", err_str)
                    if m:
                        wait = min(int(m.group(1)) + 2, 60)  # respect API hint + 2s buffer
                    else:
                        wait = [25, 35][attempt]  # longer waits for rate limits
                logger.info("Retrying in %ds...", wait)
                time.sleep(wait)

    # ── Gemini exhausted — try OpenRouter ─────────────────────────────────────
    if not _os.getenv("OPENROUTER_API_KEY", ""):
        logger.warning("OPENROUTER_API_KEY not set — no OpenRouter fallback available")
        raise RuntimeError(
            f"Gemini API failed after 3 attempts: {last_err}. "
            "Check your API key and internet connection."
        )

    logger.warning("Falling back to OpenRouter (llama-3.3-70b)")
    try:
        text, _ = call_openrouter(
            [{"role": "user", "content": prompt}],
            function_name=function_name,
        )
    except Exception as or_err:
        raise RuntimeError(
            f"All LLM backends failed. Gemini: {last_err}. OpenRouter: {or_err}"
        ) from or_err

    if use_cache:
        ti, to = len(prompt) // 4, len(text) // 4
        cache_file.write_text(
            json.dumps({"r": text, "ti": ti, "to": to}), encoding="utf-8"
        )
    return text, False


# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_json_response(text: str) -> dict | list:
    """
    Robustly parse a JSON response from an LLM.

    Handles plain JSON, markdown ```json ... ``` blocks, and embedded JSON.

    Args:
        text: Raw LLM response string

    Returns:
        Parsed dict or list, or {} on complete failure
    """
    if not text:
        return {}
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Find first { or [ in the raw text
    for sc, ec in [("{", "}"), ("[", "]")]:
        s, e = text.find(sc), text.rfind(ec)
        if s != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except json.JSONDecodeError:
                pass

    logger.error("JSON parse failed for response (first 200 chars): %.200s", text)
    return {}
