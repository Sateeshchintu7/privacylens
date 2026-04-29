"""
nlp/clause_extractor.py — Extract, classify, and score privacy policy clauses.

4-layer extraction with guaranteed non-empty output:
  Layer 1: Gemini structured prompt (per-chunk) — now returns clauses + risk + plain summary
  Layer 2: Gemini single-shot simplified prompt
  Layer 3: Keyword-based extraction (no API, 100% reliable)
  Layer 4: Single-clause fallback (absolute safety net)

Combined extraction: each clause now includes risk_score, risk_level, red_flags,
positive_signals, plain_summary, and what_it_means — eliminating separate MAD
and plain rewriter passes for most clauses.

Author: Sateesh Kumar Payyavula
Reference: Xie et al. (2025) LLM-PP2025 -- 18-category taxonomy (extended from OPP-115)
"""

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from config import BASE_DIR, CACHE_DIR
from nlp.llm_client import call_gemini, parse_json_response
from api.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# ── Taxonomy metadata ─────────────────────────────────────────────────────────

GDPR_ARTICLES: dict[str, str] = {
    "data_collection":          "Art. 13, 14",
    "purpose_limitation":       "Art. 5(1)(b)",
    "retention_period":         "Art. 5(1)(e)",
    "third_party_sharing":      "Art. 13(1)(e), 28",
    "user_rights":              "Art. 15-22",
    "consent_mechanism":        "Art. 7",
    "data_security":            "Art. 32",
    "breach_notification":      "Art. 33, 34",
    "children_data":            "Art. 8; COPPA",
    "cross_border_transfer":    "Art. 44-49",
    "cookies_tracking":         "ePrivacy Directive",
    "contact_info":             "Art. 13(1)(a)",
    "automated_decision_making":"Art. 22; EU AI Act",
    "data_sale_vs_sharing":     "CCPA",
    "biometric_data":           "GDPR; BIPA",
    "gpc_signal_honoring":      "12 US States (2026)",
    "ai_system_disclosure":     "EU AI Act Art.50",
    "sensitive_data_categories":"Art. 9",
}

RISK_WEIGHTS: dict[str, float] = {
    "data_collection": 1.2, "purpose_limitation": 1.0,
    "retention_period": 1.3, "third_party_sharing": 1.8,
    "user_rights": 0.9, "consent_mechanism": 1.0,
    "data_security": 1.4, "breach_notification": 1.2,
    "children_data": 2.0, "cross_border_transfer": 1.5,
    "cookies_tracking": 1.1, "contact_info": 1.2,
    "automated_decision_making": 1.6, "data_sale_vs_sharing": 1.7,
    "biometric_data": 2.2, "gpc_signal_honoring": 0.8,
    "ai_system_disclosure": 1.0, "sensitive_data_categories": 1.9,
}

VALID_CATEGORIES = set(GDPR_ARTICLES.keys())

# Maximum clauses to process downstream — prevents runaway LLM calls
MAX_CLAUSES = 20

# Maximum chunks to send to Gemini — prevents hundreds of API calls on large policies
MAX_CHUNKS_TO_PROCESS = 8

# Priority order for clause cap: keep these categories first
PRIORITY_CATEGORIES = [
    "children_data", "third_party_sharing", "data_collection",
    "user_rights", "data_security", "consent_mechanism",
    "cross_border_transfer", "retention_period", "breach_notification",
    "cookies_tracking", "purpose_limitation", "contact_info",
]


def _prioritize_clauses(clauses: list, max_clauses: int = MAX_CLAUSES) -> list:
    """Keep at most `max_clauses`, prioritised by category importance."""
    if len(clauses) <= max_clauses:
        return clauses
    logger.info("Capping %d clauses to %d (priority order)", len(clauses), max_clauses)
    priority_map = {cat: i for i, cat in enumerate(PRIORITY_CATEGORIES)}
    clauses.sort(key=lambda c: (priority_map.get(c.category, 99), -c.confidence))
    return clauses[:max_clauses]

# ── Keyword lists for Layer 3 fallback ───────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "data_collection": [
        "collect", "gather", "obtain", "receive", "record", "personal data",
        "name", "email", "location", "device", "ip address", "browsing history",
        "information we", "data we", "we may collect", "we collect", "we process",
        "we receive", "types of information", "categories of data",
        "account information", "usage information", "technical data",
        "contact details", "profile", "identifier", "infer",
    ],
    "third_party_sharing": [
        "share", "disclose", "transfer", "sell", "partner",
        "third party", "third-party", "advertis", "vendor", "affiliate",
        "we may share", "shared with", "disclosed to", "pass on", "provide to",
        "business partner", "service provider", "trusted partner", "other compan",
        "subprocessor", "resell", "sublicense",
    ],
    "user_rights": [
        "right to", "you can", "you may", "access your", "delete", "erasure",
        "opt out", "opt-out", "withdraw", "request", "portab", "correct",
        "your choices", "your options", "manage your", "control your",
        "preferences", "settings", "unsubscribe", "cancel", "contact us to",
        "subject access", "data subject", "exercise your", "submit a request",
    ],
    "retention_period": [
        "retain", "retention", "keep", "store for", "years", "months",
        "days", "period", "duration", "as long as",
        "delete after", "how long", "length of time", "no longer than",
        "until", "expir", "purge", "archive",
    ],
    "data_security": [
        "encrypt", "secure", "security", "protect", "ssl", "tls", "aes",
        "safeguard", "firewall", "access control",
        "industry standard", "reasonable measure", "technical measure",
        "organisational measure", "administrative safeguard", "audit",
        "penetration", "vulnerability", "two-factor", "authentication",
    ],
    "consent_mechanism": [
        "consent", "agree", "agreement", "by using", "opt-in",
        "permission", "accept", "terms", "continuing",
        "you agree", "indicates your", "constitutes acceptance",
        "legal basis", "legitimate interest", "by clicking",
    ],
    "cookies_tracking": [
        "cookie", "track", "pixel", "beacon", "fingerprint",
        "analytics", "behavioural", "cross-site",
        "web beacon", "clear gif", "local storage", "session storage",
        "google analytics", "advertising id", "interest-based",
    ],
    "children_data": [
        "child", "children", "minor", "under 13", "under 18",
        "coppa", "parental",
        "age", "underage", "not intended for", "do not knowingly",
        "guardian", "verifiable parental consent",
    ],
    "cross_border_transfer": [
        "transfer", "international", "country", "countries",
        "united states", "europe", "adequacy", "standard contractual",
        "outside your", "cross-border", "overseas", "eu-u.s.", "privacy shield",
        "binding corporate", "sccs", "derogation",
    ],
    "purpose_limitation": [
        "purpose", "use your", "used for", "process", "improve",
        "provide", "service", "research",
        "how we use", "we use your", "why we collect", "in order to",
        "to provide", "to improve", "to send", "to personalise",
        "to detect", "to prevent", "to comply",
    ],
    "breach_notification": [
        "breach", "incident", "notify", "notification",
        "inform you", "security event", "unauthorised access",
        "data breach", "without undue delay", "72 hours", "promptly notify",
    ],
    "contact_info": [
        "contact", "email us", "write to", "dpo", "data officer",
        "reach us", "privacy@", "grievance",
        "data protection officer", "privacy team", "questions about",
        "complaints", "how to contact", "contact details",
    ],
    "automated_decision_making": [
        "automated decision", "algorithm", "profiling", "ai", "machine learning",
        "decision making", "based on automated", "solely automated",
        "human intervention", "right to human", "explain decision",
        "art. 22", "eu ai act",
    ],
    "data_sale_vs_sharing": [
        "sell", "sale", "selling", "share for advertising", "cross-context",
        "behavioral advertising", "interest-based", "targeted advertising",
        "ccpa", "do not sell", "opt-out of sale", "opt-out of sharing",
    ],
    "biometric_data": [
        "biometric", "facial recognition", "fingerprint", "voiceprint",
        "iris scan", "retina", "dna", "physiological", "behavioral biometric",
        "bipa", "california biometric",
    ],
    "gpc_signal_honoring": [
        "global privacy control", "gpc", "opt-out preference signal",
        "universal opt-out", "do not sell", "do not share", "12 states",
    ],
    "ai_system_disclosure": [
        "ai system", "artificial intelligence", "chatbot", "virtual assistant",
        "emotion recognition", "biometric categorization", "deepfake",
        "synthetic content", "eu ai act art. 50",
    ],
    "sensitive_data_categories": [
        "sensitive data", "special categories", "racial origin", "ethnic origin",
        "political opinions", "religious beliefs", "philosophical beliefs",
        "trade union membership", "genetic data", "biometric data",
        "health data", "sex life", "sexual orientation", "criminal convictions",
        "art. 9",
    ],
}


# ── Pydantic model ────────────────────────────────────────────────────────────

class ClauseResult(BaseModel):
    """A single classified clause from a privacy policy."""
    clause_id: str           # UUID
    category: str            # one of the 18 LLM-PP2025 categories
    original_text: str       # exact text from the policy
    confidence: float        # 0.0 – 1.0
    gdpr_article: str        # e.g. "Art. 13"
    risk_weight: float       # from RISK_WEIGHTS
    char_start: int          # position in the full document
    char_end: int
    # ── Combined extraction fields (populated from Gemini combined prompt) ──
    plain_summary: Optional[str] = None
    what_it_means: Optional[str] = None
    risk_level: Optional[str] = None       # low|medium|high|critical
    risk_score: Optional[float] = None     # 0-100
    red_flags: Optional[list[str]] = None
    positive_signals: Optional[list[str]] = None


# ── Chunking ──────────────────────────────────────────────────────────────────

def _sample_chunks(chunks: list) -> list:
    """Select at most MAX_CHUNKS_TO_PROCESS chunks: first 4 + 2 mid + last 2."""
    if len(chunks) <= MAX_CHUNKS_TO_PROCESS:
        return chunks
    n = len(chunks)
    mid = n // 2
    selected = chunks[:4] + chunks[mid - 1 : mid + 1] + chunks[-2:]
    # Deduplicate (edge case: tiny policy)
    seen, result = set(), []
    for c in selected:
        key = id(c)
        if key not in seen:
            seen.add(key)
            result.append(c)
    logger.info("Strategic sampling: %d -> %d chunks", n, len(result))
    return result


def _chunk_text(text: str, chunk_words: int = 400, overlap: int = 40) -> list[tuple[str, int]]:
    """Split text into overlapping word chunks, tracking char offsets."""
    words = text.split()
    if not words:
        return []
    pos, positions = 0, []
    for w in words:
        idx = text.find(w, pos)
        positions.append(idx)
        pos = idx + len(w)

    chunks, i = [], 0
    while i < len(words):
        end = min(i + chunk_words, len(words))
        chunks.append((" ".join(words[i:end]), positions[i]))
        if end >= len(words):
            break
        i += chunk_words - overlap
    return chunks


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_llm_response(raw: dict | list, full_text: str, chunk_offset: int) -> list[ClauseResult]:
    """Convert raw LLM JSON into ClauseResult objects. Handles both dict and list."""
    # Normalise: accept {"clauses": [...]} OR a bare list
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("clauses") or raw.get("results") or raw.get("data") or []
    else:
        return []

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cat = item.get("category", "").strip().lower().replace(" ", "_")
        if cat not in VALID_CATEGORIES:
            continue
        clause_text = str(item.get("text", "") or item.get("original_text", "")).strip()
        if len(clause_text) < 30:
            continue
        conf = float(max(0.0, min(1.0, item.get("confidence", 0.7))))

        cs = full_text.find(clause_text[:80])
        if cs == -1:
            cs = chunk_offset

        # Extract combined fields if present
        risk_score_raw = item.get("risk_score")
        risk_score = float(max(0.0, min(100.0, risk_score_raw))) if risk_score_raw is not None else None

        results.append(ClauseResult(
            clause_id=str(uuid.uuid4()),
            category=cat,
            original_text=clause_text,
            confidence=conf,
            gdpr_article=item.get("gdpr_article", GDPR_ARTICLES.get(cat, "")),
            risk_weight=RISK_WEIGHTS.get(cat, 1.0),
            char_start=cs,
            char_end=cs + len(clause_text),
            # Combined extraction fields
            plain_summary=item.get("plain_summary") or None,
            what_it_means=item.get("what_it_means") or None,
            risk_level=item.get("risk_level") or None,
            risk_score=risk_score,
            red_flags=item.get("red_flags") if isinstance(item.get("red_flags"), list) else None,
            positive_signals=item.get("positive_signals") if isinstance(item.get("positive_signals"), list) else None,
        ))
    return results


def _deduplicate(clauses: list[ClauseResult]) -> list[ClauseResult]:
    """Keep highest-confidence clause per unique text excerpt."""
    seen: dict[str, ClauseResult] = {}
    for c in clauses:
        key = c.original_text[:80].strip().lower()
        if key not in seen or c.confidence > seen[key].confidence:
            seen[key] = c
    return list(seen.values())


# ── Layer 3: Keyword-based extraction ────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in parts if len(s.strip()) > 20]


def _keyword_extract(text: str) -> list[ClauseResult]:
    """
    Layer 3: No-API keyword scan — always produces output.
    One ClauseResult per matched category.
    """
    sentences = _split_sentences(text)
    results: list[ClauseResult] = []

    for category, keywords in _CATEGORY_KEYWORDS.items():
        matched = []
        for sentence in sentences:
            s_lower = sentence.lower()
            if any(kw in s_lower for kw in keywords):
                matched.append(sentence)

        if not matched:
            continue

        excerpt = " ".join(matched[:2])[:400]
        cs = text.find(excerpt[:60]) if excerpt else 0
        if cs == -1:
            cs = 0

        results.append(ClauseResult(
            clause_id=str(uuid.uuid4()),
            category=category,
            original_text=excerpt,
            confidence=0.65,
            gdpr_article=GDPR_ARTICLES.get(category, ""),
            risk_weight=RISK_WEIGHTS.get(category, 1.0),
            char_start=cs,
            char_end=cs + len(excerpt),
        ))

    logger.info("Keyword extraction: %d clauses", len(results))
    return results


# ── Layer 4: Single-clause fallback ──────────────────────────────────────────

def _fallback_clause(text: str) -> list[ClauseResult]:
    """Layer 4: Absolute safety net — guarantees > 0 clauses."""
    sample = (text[:300] if text else "Privacy policy content.").strip()
    return [ClauseResult(
        clause_id=str(uuid.uuid4()),
        category="data_collection",
        original_text=sample,
        confidence=0.4,
        gdpr_article=GDPR_ARTICLES["data_collection"],
        risk_weight=RISK_WEIGHTS["data_collection"],
        char_start=0,
        char_end=len(sample),
    )]


# ── Public API ────────────────────────────────────────────────────────────────

def extract_clauses(policy_text: str, use_cache: bool = True) -> list[ClauseResult]:
    """
    Extract and classify all clauses from a privacy policy.

    4-layer fallback guarantees at least 1 clause is always returned.

    Args:
        policy_text: Cleaned text from ingestion.text_cleaner
        use_cache: Cache results keyed on MD5 of policy text

    Returns:
        list[ClauseResult] — never empty

    Academic ref:
        Wilson et al. (2016) OPP-115 -- 12-category taxonomy standard
    """
    if not policy_text or len(policy_text.strip()) < 50:
        logger.warning("Policy text too short (%d chars), using fallback", len(policy_text or ""))
        return _fallback_clause(policy_text or "")

    text_hash = hashlib.md5(policy_text.encode()).hexdigest()[:12]
    cache_file = CACHE_DIR / f"clauses_{text_hash}.json"

    if use_cache and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if data:  # don't use cached empty list
                logger.info("Clause cache hit: %s (%d clauses)", cache_file.name, len(data))
                return [ClauseResult.model_validate(c) for c in data]
        except Exception as exc:
            logger.warning("Clause cache read failed: %s", exc)

    # ── Layer 1: Gemini structured extraction ─────────────────────────────────
    final = _gemini_extract(policy_text)

    # ── Layer 2: Gemini simplified (if Layer 1 got nothing) ──────────────────
    if not final:
        logger.warning("Layer 1 returned 0 clauses — trying simplified Gemini prompt")
        final = _gemini_simple(policy_text)

    # ── Layer 3: Keyword extraction (if Gemini fails entirely) ───────────────
    if not final:
        logger.warning("Gemini returned 0 clauses — falling back to keyword extraction")
        final = _keyword_extract(policy_text)

    # ── Layer 4: Single-clause guarantee ─────────────────────────────────────
    if not final:
        logger.error("All extraction layers failed — using single-clause fallback")
        final = _fallback_clause(policy_text)

    final.sort(key=lambda c: c.char_start)

    # ── Cap at MAX_CLAUSES to prevent runaway downstream LLM calls ────────
    final = _prioritize_clauses(final, max_clauses=MAX_CLAUSES)

    if use_cache and final:
        try:
            cache_file.write_text(
                json.dumps([c.model_dump() for c in final]), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Clause cache write failed: %s", exc)

    logger.info("extract_clauses: %d clauses from %d chars", len(final), len(policy_text))
    return final


def _gemini_extract(policy_text: str) -> list[ClauseResult]:
    """Layer 1: Structured per-chunk Gemini extraction — parallel."""
    try:
        prompt_template = load_prompt("prompts/clause_extraction.txt")
    except Exception:
        prompt_template = _DEFAULT_EXTRACTION_PROMPT

    chunks = _sample_chunks(_chunk_text(policy_text))
    if not chunks:
        return []

    def _extract_chunk(i: int, chunk_text: str, char_offset: int) -> list[ClauseResult]:
        prompt = prompt_template.replace("{POLICY_CHUNK}", chunk_text)
        try:
            response, _ = call_gemini(prompt, function_name="clause_extractor")
            raw = parse_json_response(response)
            parsed = _parse_llm_response(raw, policy_text, char_offset)
            logger.info("Chunk %d/%d: %d clauses", i + 1, len(chunks), len(parsed))
            return parsed
        except Exception as exc:
            logger.warning("Chunk %d/%d extraction failed: %s", i + 1, len(chunks), exc)
            return []

    all_clauses: list[ClauseResult] = []
    with ThreadPoolExecutor(max_workers=min(len(chunks), 15)) as ex:
        futures = {
            ex.submit(_extract_chunk, i, ct, co): i
            for i, (ct, co) in enumerate(chunks)
        }
        for fut in as_completed(futures):
            all_clauses.extend(fut.result())

    logger.info("Parallel extraction complete: %d raw clauses from %d chunks", len(all_clauses), len(chunks))
    return _deduplicate(all_clauses)


def _gemini_simple(policy_text: str) -> list[ClauseResult]:
    """Layer 2: Single-shot Gemini call with a simpler prompt."""
    sample = policy_text[:4000]
    prompt = (
        "Extract privacy practices from this policy. "
        "Return ONLY a JSON array, no markdown, no explanation:\n"
        '[{"category":"data_collection","text":"exact quote","confidence":0.8}]\n\n'
        f"Valid categories: {', '.join(VALID_CATEGORIES)}\n\n"
        f"Policy:\n{sample}\n\nJSON array:"
    )
    try:
        response, _ = call_gemini(prompt, function_name="clause_extractor_simple")
        raw = parse_json_response(response)
        return _parse_llm_response(raw, policy_text, 0)
    except Exception as exc:
        logger.warning("Layer 2 simplified Gemini failed: %s", exc)
        return []


_DEFAULT_EXTRACTION_PROMPT = """You are a privacy policy analyst. Extract and classify relevant clauses from the provided policy text chunk into one of 18 standardised categories, based on the LLM-PP2025 taxonomy (Xie et al., 2025).

CATEGORIES (use EXACTLY these snake_case IDs):
1.  data_collection          - Personal data collected: name, email, location, device info, browsing history, etc.
2.  purpose_limitation       - Why data is collected; stated purposes and legal basis for processing
3.  retention_period         - How long data is stored; deletion schedules; retention criteria
4.  third_party_sharing      - Whether and how data is shared with third parties, partners, advertisers, or affiliates
5.  user_rights              - Rights to access, correct, delete, restrict, or port personal data (GDPR Art. 15-22)
6.  consent_mechanism        - How user consent is obtained, withdrawn, or managed (opt-in, opt-out, continued use)
7.  data_security            - Technical and organisational measures to protect personal data (encryption, access controls)
8.  breach_notification      - How and when users are notified of data breaches or security incidents
9.  children_data            - Special rules or restrictions for users under 13 or under 18 (COPPA / GDPR Art. 8)
10. cross_border_transfer    - Transfer of personal data to other countries or international servers
11. cookies_tracking         - Use of cookies, pixels, web beacons, device fingerprinting, or tracking technologies
12. contact_info             - How to contact the company with privacy questions, rights requests, or complaints
13. automated_decision_making- AI profiling and automated decisions (GDPR Art. 22, EU AI Act)
14. data_sale_vs_sharing     - Legal distinction between selling and sharing data for advertising (CCPA)
15. biometric_data           - Facial recognition, fingerprints, voiceprints, biometric identifiers (GDPR, BIPA)
16. gpc_signal_honoring      - Whether Global Privacy Control signals are honoured (12 US States 2026)
17. ai_system_disclosure     - Disclosure of AI system usage (EU AI Act Article 50)
18. sensitive_data_categories- Special categories: race, health, political views, sexual orientation (GDPR Art. 9)

INSTRUCTIONS:
- Extract ONLY sentences or paragraphs that clearly belong to one of the 18 categories above.
- Copy the EXACT text from the document - do NOT paraphrase or summarise.
- Assign a confidence score (0.0-1.0):
    0.9-1.0 = clearly and unambiguously fits the category
    0.7-0.8 = likely fits, minor ambiguity present
    0.5-0.6 = possible fit, significant ambiguity
    Below 0.5 = do NOT include
- Assign the most relevant GDPR article or regulation.
- A single text segment may only be assigned ONE category -- choose the best fit.
- For EACH clause, also provide:
  - plain_summary: a Grade 6 plain English rewrite (max 80 words, active voice, short sentences)
  - what_it_means: one sentence starting with "This means..." explaining the real-world impact
  - risk_level: one of "low", "medium", "high", "critical"
  - risk_score: integer 0-100 (0=harmless, 100=extremely harmful)
  - red_flags: array of short plain-English concerns (empty array if low risk)
  - positive_signals: array of good practices found (empty array if none)
- Skip text that does not fit any category (navigation, headings, footers).
- Return ONLY valid JSON. No markdown fences, no explanations, no preamble.

RISK SCORING GUIDE:
0-25   (low): Transparent, fair, user-friendly. Example: "We only collect your email to send receipts." -> 8
26-50  (medium): Some concern but common practice. Example: "We use analytics to track page views." -> 35
51-75  (high): Significant concern users would object to. Example: "We share browsing history with advertisers." -> 68
76-100 (critical): Aggressive, harmful, or legally questionable. Example: "We sell personal data to brokers." -> 95

OUTPUT FORMAT - return ONLY this JSON:
{"clauses": [{"category": "<category_id>", "text": "<exact text from document>", "confidence": <0.0-1.0>, "gdpr_article": "<article>", "plain_summary": "<Grade 6 rewrite>", "what_it_means": "This means...", "risk_level": "<low|medium|high|critical>", "risk_score": <0-100>, "red_flags": ["<flag>"], "positive_signals": ["<signal>"]}]}

If no relevant clauses are found, return: {"clauses": []}

POLICY TEXT CHUNK:
{POLICY_CHUNK}"""
