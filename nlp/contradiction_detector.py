"""
nlp/contradiction_detector.py -- Internal contradiction detection for PrivacyLens.

Two-pass pipeline:
  Pass 1: Cosine similarity screening (sentence-transformers, no LLM)
  Pass 2: LLM reasoning on candidate pairs (Gemini)

Academic ref: Andow et al. (2019, PolicyLint) -- semantic contradiction
              detection in privacy policies using SRL; we use embedding
              similarity + LLM as a more accessible alternative.

Author: Sateesh Kumar Payyavula
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

# Prevent HuggingFace Hub from checking for model updates on every load.
# The sentence-transformer model is already cached locally; without this flag
# the library does HEAD requests to hf.co with exponential-backoff retries
# (~23 s) when the network blocks the connection.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from config import BASE_DIR, GEMINI_API_KEY
from nlp.clause_extractor import ClauseResult
from nlp.llm_client import call_gemini, parse_json_response
from api.prompt_loader import load_prompt

logger = logging.getLogger(__name__)
PROMPT_PATH = BASE_DIR / "prompts" / "contradiction_detection.txt"

_PRIORITY_PAIRS: set[frozenset] = {
    frozenset({"data_collection",     "third_party_sharing"}),
    frozenset({"user_rights",         "consent_mechanism"}),
    frozenset({"retention_period",    "data_collection"}),
    frozenset({"data_security",       "cross_border_transfer"}),
    frozenset({"cookies_tracking",    "consent_mechanism"}),
    frozenset({"purpose_limitation",  "third_party_sharing"}),
}

_MAX_LLM_PAIRS = 5   # keep fast: priority pairs only


class Contradiction(BaseModel):
    """A detected contradiction between two clauses in the same policy."""
    contradiction_id: str
    clause_a_id: str
    clause_b_id: str
    clause_a_text: str
    clause_b_text: str
    clause_a_category: str
    clause_b_category: str
    contradiction_type: str
    severity: str
    plain_explanation: str
    example: str


class ContradictionReport(BaseModel):
    """Full report of contradictions detected in a policy."""
    total_found: int
    contradictions: list[Contradiction]
    has_critical: bool
    summary: str
    candidates_screened: int
    llm_calls_made: int


def _embed_clauses(clauses: list[ClauseResult]):
    """Return numpy normalised embeddings for all clauses."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [c.original_text[:500] for c in clauses]
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def _cosine(a, b) -> float:
    import numpy as np
    return float(np.dot(a, b))


def _candidate_pairs(
    clauses: list[ClauseResult],
) -> list[tuple[ClauseResult, ClauseResult, float, bool]]:
    """
    Screen clause pairs for contradiction candidates.

    Similarity window 0.3–0.75 for non-priority pairs.
    Priority category pairs always included.

    Academic ref: Andow et al. (2019, PolicyLint) -- candidate selection.
    """
    try:
        embeddings = _embed_clauses(clauses)
    except ImportError:
        logger.warning("sentence-transformers not available — using priority pairs only")
        embeddings = None

    candidates: list[tuple[ClauseResult, ClauseResult, float, bool]] = []
    seen: set[frozenset] = set()

    for i, a in enumerate(clauses):
        for j, b in enumerate(clauses):
            if j <= i or a.category == b.category:
                continue
            key = frozenset({a.clause_id, b.clause_id})
            if key in seen:
                continue
            seen.add(key)

            is_priority = frozenset({a.category, b.category}) in _PRIORITY_PAIRS
            sim = _cosine(embeddings[i], embeddings[j]) if embeddings is not None else (0.5 if is_priority else 0.0)

            if is_priority or (0.3 < sim < 0.75):
                candidates.append((a, b, sim, is_priority))

    candidates.sort(key=lambda x: (not x[3], -x[2]))
    return candidates[:_MAX_LLM_PAIRS]


def _llm_check(a: ClauseResult, b: ClauseResult, use_cache: bool) -> Optional[dict]:
    """Ask Gemini whether two clauses contradict each other."""
    prompt = (
        load_prompt("prompts/contradiction_detection.txt")
        .replace("{CATEGORY_A}", a.category)
        .replace("{CLAUSE_A}", a.original_text[:600])
        .replace("{CATEGORY_B}", b.category)
        .replace("{CLAUSE_B}", b.original_text[:600])
    )
    try:
        resp, _ = call_gemini(prompt, function_name="contradiction_detector", use_cache=use_cache)
        data = parse_json_response(resp)
        if isinstance(data, dict) and data.get("is_contradiction"):
            return data
    except Exception as exc:
        logger.warning("LLM contradiction check failed: %s", exc)
    return None


def detect_contradictions(
    clauses: list[ClauseResult],
    use_cache: bool = True,
) -> ContradictionReport:
    """
    Detect internal contradictions within a privacy policy.

    Two-pass pipeline:
      Pass 1 — cosine similarity screening (no LLM)
      Pass 2 — LLM reasoning on up to 20 candidate pairs

    Args:
        clauses: list[ClauseResult] from clause_extractor
        use_cache: use LLM response cache

    Returns:
        ContradictionReport

    Academic ref:
        Andow et al. (2019, PolicyLint) -- contradiction detection methodology
    """
    if len(clauses) < 2:
        return ContradictionReport(
            total_found=0, contradictions=[], has_critical=False,
            summary="Not enough clauses to check for contradictions.",
            candidates_screened=0, llm_calls_made=0,
        )

    # STUB: requires GEMINI_API_KEY -- will auto-activate when set
    if not GEMINI_API_KEY:
        return ContradictionReport(
            total_found=1,
            contradictions=[Contradiction(
                contradiction_id=str(uuid.uuid4()),
                clause_a_id="demo_a", clause_b_id="demo_b",
                clause_a_text="[DEMO] We do not sell personal data.",
                clause_b_text="[DEMO] We share data with advertising partners.",
                clause_a_category="data_collection",
                clause_b_category="third_party_sharing",
                contradiction_type="deny_then_share",
                severity="high",
                plain_explanation="[DEMO] Add GEMINI_API_KEY for real contradiction detection.",
                example="[DEMO] Example scenario would appear here.",
            )],
            has_critical=False,
            summary="[DEMO MODE] Add GEMINI_API_KEY for real contradiction detection.",
            candidates_screened=0, llm_calls_made=0,
        )

    candidates = _candidate_pairs(clauses)
    found: list[Contradiction] = []
    llm_calls = 0

    for a, b, sim, is_priority in candidates:
        result = _llm_check(a, b, use_cache=use_cache)
        llm_calls += 1
        if result:
            found.append(Contradiction(
                contradiction_id=str(uuid.uuid4()),
                clause_a_id=a.clause_id,
                clause_b_id=b.clause_id,
                clause_a_text=a.original_text[:300],
                clause_b_text=b.original_text[:300],
                clause_a_category=a.category,
                clause_b_category=b.category,
                contradiction_type=str(result.get("type", "scope_conflict")),
                severity=str(result.get("severity", "medium")),
                plain_explanation=str(result.get("explanation", "")),
                example=str(result.get("example", "")),
            ))

    has_critical = any(c.severity == "high" for c in found)
    summary = (
        f"Found {len(found)} internal contradiction(s). "
        + (f"Most serious: {found[0].plain_explanation}" if found else "")
        if found else "No internal contradictions detected in this policy."
    )

    return ContradictionReport(
        total_found=len(found), contradictions=found,
        has_critical=has_critical, summary=summary,
        candidates_screened=len(candidates), llm_calls_made=llm_calls,
    )
