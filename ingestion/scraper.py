"""
ingestion/scraper.py — URL-based text extraction for PrivacyLens.

Fetches a web page and extracts readable text, stripping navigation,
scripts, styles, and other non-policy content.

Supports standard HTML pages.  JavaScript-heavy pages should use a headless
browser (future enhancement via playwright).

Author: Sateesh Kumar Payyavula
Reference: BeautifulSoup4 docs; Wilson et al. (2016) OPP-115 data collection
"""

import hashlib
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl

from config import CACHE_DIR, SCRAPER_MAX_TEXT_LEN, SCRAPER_TIMEOUT

# Kept for backward-compat imports from other modules
REQUEST_HEADERS: dict = {}

# Rotate between realistic browser user-agent strings to reduce bot-detection
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def _browser_headers() -> dict:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

logger = logging.getLogger(__name__)

# ── Pydantic model ────────────────────────────────────────────────────────────

class ScraperResult(BaseModel):
    """Structured result from URL extraction."""
    url: str
    text: str
    char_count: int
    fetch_ms: int
    cached: bool = False
    error: Optional[str] = None


# ── Internal helpers ──────────────────────────────────────────────────────────

# Tags whose content we always discard
_DISCARD_TAGS = {
    "script", "style", "noscript", "header", "footer",
    "nav", "aside", "form", "button", "svg", "img",
}

def _cache_path(url: str) -> Path:
    """Return the file-system path for the cached result of this URL."""
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"scrape_{key}.json"


def _load_cache(url: str) -> Optional[ScraperResult]:
    """Return cached ScraperResult if it exists, else None."""
    p = _cache_path(url)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            result = ScraperResult(**data)
            result.cached = True
            return result
        except Exception:
            pass
    return None


def _save_cache(result: ScraperResult) -> None:
    """Persist a ScraperResult to the file-system cache."""
    p = _cache_path(result.url)
    p.write_text(result.model_dump_json(), encoding="utf-8")


def _is_prose(text: str) -> bool:
    """
    Return True if a string looks like human-readable prose text.
    Rejects binary garbage, minified JS, CSS, and base64.
    """
    if len(text) < 100:
        return False
    # Must be mostly basic Latin (printable ASCII + common punctuation)
    latin = sum(1 for c in text if "\x20" <= c <= "\x7e")
    if latin / len(text) < 0.85:
        return False
    # Must have enough spaces (words, not tokens)
    words = text.split()
    if len(words) < 10:
        return False
    # Average word length 3–12 chars  (English prose ≈ 4–6)
    avg_wl = sum(len(w) for w in words) / len(words)
    if avg_wl < 3 or avg_wl > 12:
        return False
    # Must not look like minified JS / CSS (too many special chars)
    special = sum(1 for c in text if c in r"{}();=<>\\|&^%$#@!~`")
    if special / len(text) > 0.08:
        return False
    return True


def _walk_json(obj: object, results: list, depth: int = 0) -> None:
    """Recursively collect prose strings from a JSON object."""
    if depth > 25:
        return
    if isinstance(obj, str):
        if len(obj) >= 150 and _is_prose(obj):
            results.append(obj.strip())
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_json(v, results, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _walk_json(item, results, depth + 1)


def _collect_text_from_json(json_str: str) -> Optional[str]:
    """Parse a JSON string and return all prose text found within it."""
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None
    texts: list[str] = []
    _walk_json(data, texts)
    if not texts:
        return None
    seen: set[str] = set()
    unique = [t for t in texts if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
    return "\n\n".join(unique) if unique else None


def _extract_spa_content(html: str) -> Optional[str]:
    """
    Extract text from JavaScript-rendered pages (Next.js, React, etc.).

    Tries three sources in order:
      1. <script id="__NEXT_DATA__"> — Next.js server-side props JSON.
      2. <script type="application/json"> — generic SSR data blobs.
      3. Inline scripts containing window.__DATA__ = {...} or similar patterns.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 1. __NEXT_DATA__ (Next.js)
        next_script = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_script and next_script.string:
            text = _collect_text_from_json(next_script.string)
            if text and len(text) > 500:
                logger.info("SPA: extracted %d chars from __NEXT_DATA__", len(text))
                return text

        # 2. application/json script tags
        for script in soup.find_all("script", {"type": "application/json"}):
            if script.string and len(script.string) > 1000:
                text = _collect_text_from_json(script.string)
                if text and len(text) > 500:
                    logger.info("SPA: extracted %d chars from application/json", len(text))
                    return text

        # 3. Inline scripts with embedded JSON assignment patterns
        #    Only try on very large scripts (< 5 KB is usually minified fragments)
        #    and only match patterns that look like data assignments, not bundle code.
        for script in soup.find_all("script"):
            src = script.string or ""
            if len(src) < 5000:
                continue
            # Look for known data-carrier variable patterns only
            m = re.search(
                r'(?:__(?:DATA|SSR|APP)__|self\.__next_f)\s*=\s*(\{.+?\}|\[.+?\])\s*;',
                src, re.DOTALL
            )
            if m:
                text = _collect_text_from_json(m.group(1))
                if text and len(text) > 500:
                    logger.info("SPA: extracted %d chars from inline script JSON", len(text))
                    return text

    except Exception as exc:
        logger.debug("SPA extraction failed: %s", exc)
    return None


def _parse_html_to_text(html: str) -> str:
    """
    Convert raw HTML to clean readable text.

    Strategy:
    1. Parse with lxml (fast) or html.parser as fallback.
    2. Remove all discard-tag subtrees.
    3. Extract visible text with whitespace normalisation.

    Input:  html (str) — raw HTML source
    Output: text (str) — stripped readable text
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tag trees
    for tag in soup.find_all(_DISCARD_TAGS):
        tag.decompose()

    # Try to find the main content block first (improves quality)
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main-content")
        or soup.find("body")
        or soup
    )

    lines = []
    for element in main.descendants:
        if element.name in ("p", "li", "h1", "h2", "h3", "h4", "td", "th"):
            txt = element.get_text(separator=" ", strip=True)
            if txt:
                lines.append(txt)

    # Fallback: get all text if structured extraction found nothing
    if not lines:
        lines = [main.get_text(separator="\n", strip=True)]

    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def _fetch_with_session(url: str) -> requests.Response:
    """
    Fetch a URL using a browser-like session that first visits the domain
    root to pick up cookies, then requests the target page.

    Reference: Wilson et al. (2016) OPP-115 — web collection methodology
    """
    session = requests.Session()
    headers = _browser_headers()

    # Visit homepage to pick up anti-bot cookies before the policy page
    parsed = urlparse(url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    try:
        session.get(domain_root, headers=headers, timeout=10, allow_redirects=True)
        time.sleep(random.uniform(0.3, 0.8))
    except Exception:
        pass  # homepage visit is best-effort

    return session.get(url, headers=headers, timeout=SCRAPER_TIMEOUT, allow_redirects=True)


def _fetch_google_cache(url: str) -> Optional[str]:
    """
    Try Google's cache of the URL as a 403 fallback.
    Returns extracted text or None if cache is unavailable.
    """
    cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
    try:
        r = requests.get(cache_url, headers=_browser_headers(), timeout=20)
        if r.status_code == 200 and len(r.content) > 1000:
            soup = BeautifulSoup(r.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            joined = "\n".join(lines)
            if len(joined) > 500:
                return joined
    except Exception:
        pass
    return None


def _fetch_www_variant(url: str) -> Optional[requests.Response]:
    """Try adding/removing www. as a 403 fallback."""
    parsed = urlparse(url)
    if parsed.netloc.startswith("www."):
        alt = url.replace("://www.", "://", 1)
    else:
        alt = url.replace("://", "://www.", 1)
    try:
        r = requests.get(alt, headers=_browser_headers(), timeout=SCRAPER_TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


def extract_from_url(url: str, use_cache: bool = True) -> ScraperResult:
    """
    Fetch a URL and return its readable text content.

    Uses three fallback methods when a site returns 403:
      1. Browser-like session with domain cookie pre-load
      2. Google Cache
      3. www / non-www URL variant

    Checks the file-system cache first to avoid repeat fetches.

    Reference: Wilson et al. (2016) OPP-115 — web scraping methodology
    """
    url = url.strip()

    # 1. Check cache
    if use_cache:
        cached = _load_cache(url)
        if cached:
            logger.info("Cache hit for %s", url)
            return cached

    t0 = time.monotonic()

    # 2. Primary fetch (browser-like session)
    response: Optional[requests.Response] = None
    try:
        response = _fetch_with_session(url)
        if response.status_code == 403:
            response = None  # fall through to fallbacks
        elif response.status_code != 200:
            response.raise_for_status()
    except requests.exceptions.Timeout:
        return ScraperResult(url=url, text="", char_count=0, fetch_ms=0,
                             error="The website took too long to respond. Try pasting the text directly.")
    except requests.exceptions.ConnectionError:
        return ScraperResult(url=url, text="", char_count=0, fetch_ms=0,
                             error="Could not connect to that website. Check the URL or paste the text directly.")
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        if code != 403:
            return ScraperResult(url=url, text="", char_count=0, fetch_ms=0,
                                 error=f"The website returned HTTP {code}. Try pasting the text directly.")
        response = None  # 403 — try fallbacks
    except Exception as exc:
        return ScraperResult(url=url, text="", char_count=0, fetch_ms=0,
                             error=f"Something went wrong fetching that page: {exc}")

    html_source: Optional[str] = response.text if response is not None else None

    # 3. Fallback 1 — Google Cache
    if html_source is None:
        logger.info("Primary fetch blocked (403) for %s — trying Google Cache", url)
        cached_text = _fetch_google_cache(url)
        if cached_text:
            text = cached_text[:SCRAPER_MAX_TEXT_LEN]
            fetch_ms = int((time.monotonic() - t0) * 1000)
            result = ScraperResult(url=url, text=text, char_count=len(text), fetch_ms=fetch_ms)
            if use_cache:
                _save_cache(result)
            logger.info("Google Cache served %s — %d chars", url, len(text))
            return result

    # 4. Fallback 2 — www/non-www variant
    if html_source is None:
        alt_resp = _fetch_www_variant(url)
        if alt_resp is not None:
            html_source = alt_resp.text

    # 5. Give up — show user-friendly error
    if html_source is None:
        return ScraperResult(
            url=url, text="", char_count=0, fetch_ms=int((time.monotonic() - t0) * 1000),
            error=(
                "This website blocks automated access. "
                "Please copy the privacy policy text and paste it using the 'Paste Text' tab instead. "
                "Most policies are at /privacy or /legal on the website."
            ),
        )

    fetch_ms = int((time.monotonic() - t0) * 1000)

    # 6. Parse HTML → text
    text = _parse_html_to_text(html_source)

    # 6b. For JS-rendered pages (Next.js / React SPAs) the normal parser
    #     finds almost nothing.  Try mining __NEXT_DATA__ and JSON blobs.
    if len(text) < 500:
        spa_text = _extract_spa_content(html_source)
        if spa_text and len(spa_text) > len(text):
            logger.info(
                "SPA extraction improved text: %d → %d chars", len(text), len(spa_text)
            )
            text = spa_text

    text = text[:SCRAPER_MAX_TEXT_LEN]

    if len(text) < 200:
        return ScraperResult(url=url, text="", char_count=0, fetch_ms=fetch_ms,
                             error="We couldn't find enough text on that page. "
                                   "The site may require JavaScript — try pasting the policy text directly.")

    result = ScraperResult(url=url, text=text, char_count=len(text), fetch_ms=fetch_ms)
    if use_cache:
        _save_cache(result)

    logger.info("Scraped %s — %d chars in %dms", url, len(text), fetch_ms)
    return result
