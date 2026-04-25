"""
api/routes/ask.py -- RAG question-answering with keyword fallback.

Two-path architecture:
  1. RAG (primary):      FAISS index + Gemini generation.
  2. Keyword (fallback): Deterministic clause lookup.
                         Always returns a real answer — never a generic error.
"""

from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from api.schemas import AskRequest, AskResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ask"])

# In-memory FAISS index cache keyed by policy_text hash
_INDEX_CACHE: dict = {}

# Question → clause category mapping (most specific first)
_Q_CATEGORY_MAP = [
    ({"sell", "selling", "sold", "sale"},                    "third_party_sharing"),
    ({"advertis", "marketing", "target"},                    "third_party_sharing"),
    ({"share", "sharing", "third party", "partner", "vendor"}, "third_party_sharing"),
    ({"location", "gps", "geolocation", "whereabouts"},      "cookies_tracking"),
    ({"track", "tracking", "cookie", "cookies", "pixel"},    "cookies_tracking"),
    ({"delete", "deletion", "erase", "erasure", "remove",
      "right to be forgotten"},                              "user_rights"),
    ({"right", "rights", "access", "portab", "correct"},     "user_rights"),
    ({"children", "child", "minor", "kid", "coppa",
      "under 13"},                                           "children_data"),
    ({"how long", "keep", "store", "storing", "retention",
      "retain", "period", "years"},                          "retention_period"),
    ({"secure", "security", "encrypt", "protect"},           "data_security"),
    ({"breach", "incident", "notif", "inform"},              "breach_notification"),
    ({"collect", "collection", "gather", "what data"},       "data_collection"),
    ({"consent", "agree", "opt-in", "opt-out", "permission"}, "consent_mechanism"),
    ({"purpose", "why", "reason", "how do you use"},         "purpose_limitation"),
    ({"country", "countries", "border", "transfer",
      "international"},                                      "cross_border_transfer"),
    ({"contact", "reach", "report", "complain", "email"},    "contact_info"),
    ({"ai", "algorithm", "automat", "profil", "decision"},   "automated_decision_making"),
]


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Answer a user question about the policy using RAG with keyword fallback."""
    import hashlib
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from nlp.clause_extractor import ClauseResult

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="No question provided.")

    clauses_raw = request.clauses or []
    policy_text = (request.policy_text or "").strip()

    # Reconstruct policy_text from clause original_text if it looks like a URL
    if (not policy_text or policy_text.startswith("http")) and clauses_raw:
        policy_text = " ".join(
            (c.get("original_text") or c.get("text") or "")
            for c in clauses_raw[:80]
        ).strip()
        logger.info("Reconstructed policy_text from %d clauses (%d chars)",
                    len(clauses_raw), len(policy_text))

    # ── Compliance question shortcut ─────────────────────────────────────────
    # Answer compliance questions directly from scores (no LLM needed)
    compliance_report = request.compliance_report or {}
    if compliance_report:
        q_lower = request.question.lower()
        compliance_kw = {"gdpr", "ccpa", "dpdp", "compliant", "compliance",
                         "comply", "regulation", "data protection", "eu ai act"}
        if any(kw in q_lower for kw in compliance_kw):
            return _compliance_answer(request.question, compliance_report)

    # ── Primary path: RAG ────────────────────────────────────────────────────
    if len(policy_text) >= 200:
        try:
            from nlp.rag_qa import build_index, answer_question

            typed_clauses = [ClauseResult.model_validate(c) for c in clauses_raw]

            cache_key = hashlib.md5(policy_text[:500].encode()).hexdigest()
            if cache_key not in _INDEX_CACHE:
                _INDEX_CACHE[cache_key] = build_index(policy_text, typed_clauses)
            index = _INDEX_CACHE[cache_key]

            result = answer_question(
                question=request.question,
                policy_index=index,
                clauses=typed_clauses,
                audience_level=request.audience_level,
            )

            source_quote = result.source_clauses[0] if result.source_clauses else ""

            # Only use RAG if it produced a real answer
            if result.answer and len(result.answer) > 20 and not result.could_not_find:
                logger.info("RAG answer: confidence=%.2f", result.confidence)
                return AskResponse(
                    answer=result.answer,
                    plain_answer=result.plain_answer,
                    source_quote=source_quote,
                    confidence=result.confidence,
                    could_not_find=result.could_not_find,
                )
        except Exception as exc:
            logger.warning("RAG failed (%s) — using keyword fallback", exc)

    # ── Fallback path: keyword search ────────────────────────────────────────
    logger.info("Keyword fallback for: %s", request.question[:80])
    return _keyword_answer(request.question, clauses_raw, policy_text)


def _compliance_answer(question: str, compliance: dict) -> AskResponse:
    """Answer compliance questions directly from scored data — no LLM needed."""
    q = question.lower()
    gdpr = int(compliance.get("gdpr_score", 0))
    ccpa = int(compliance.get("ccpa_score", 0))
    dpdp = int(compliance.get("dpdp_score", 0))

    def grade(s: int) -> str:
        return "strong" if s >= 75 else "moderate" if s >= 50 else "weak"

    if "gdpr" in q:
        detail = "It meets most GDPR requirements." if gdpr >= 75 else "It has significant gaps under EU privacy law."
        answer = f"This policy scores {gdpr}% for GDPR (EU) compliance — {grade(gdpr)}. {detail}"
    elif "ccpa" in q:
        detail = "California residents' rights appear well covered." if ccpa >= 75 else "California residents may have limited rights under this policy."
        answer = f"This policy scores {ccpa}% for CCPA (California) compliance — {grade(ccpa)}. {detail}"
    elif "dpdp" in q:
        detail = "It aligns well with India's Digital Personal Data Protection Act." if dpdp >= 75 else "It has gaps under India's DPDP Act."
        answer = f"This policy scores {dpdp}% for DPDP (India) compliance — {grade(dpdp)}. {detail}"
    elif "eu ai act" in q or "ai act" in q:
        eu_ai = int(compliance.get("eu_ai_act_score", 0))
        answer = (f"This policy scores {eu_ai}% for EU AI Act Art.50 transparency. "
                  f"EU AI Act disclosure requirements take effect August 2, 2026.")
    else:
        overall = int((gdpr + ccpa + dpdp) / 3)
        answer = (
            f"Overall compliance: {overall}% average across GDPR ({gdpr}%), "
            f"CCPA ({ccpa}%), and DPDP ({dpdp}%). "
            f"{'This policy has generally strong privacy protections.' if overall >= 70 else 'This policy has significant compliance gaps.' if overall < 50 else 'This policy has moderate compliance — some areas need improvement.'}"
        )
        gaps = compliance.get("critical_gaps", [])
        if gaps:
            answer += f" There are {len(gaps)} critical gap(s) that need attention."

    return AskResponse(
        answer=answer, plain_answer=answer,
        source_quote="", confidence=0.95, could_not_find=False,
    )


_DELETION_KEYWORDS = {
    "delete", "deletion", "deactivate", "deactivation",
    "remove account", "close account", "cancel account",
    "right to be forgotten", "erasure", "opt out", "opt-out",
}

_DELETION_SIGNALS = [
    "to delete", "to deactivate", "to close",
    "email us", "contact us", "submit a request",
    "privacy@", "settings", "account settings",
    "privacy settings", "visit", "click",
    "request deletion", "data deletion",
]


def _deletion_answer(policy_text: str) -> AskResponse | None:
    """
    Search the policy text for actual deletion procedure sentences.
    Returns an AskResponse if found, else None (caller tries next path).
    """
    if not policy_text:
        return None

    sentences = [s.strip() for s in policy_text.replace("\n", ". ").split(".")
                 if len(s.strip()) > 20]
    hits = [s for s in sentences if any(sig in s.lower() for sig in _DELETION_SIGNALS)]

    if hits:
        excerpt = ". ".join(hits[:2]) + "."
        return AskResponse(
            answer=(
                f"According to this policy: {excerpt} "
                "If no direct link is given, go to Account Settings "
                "and look for a 'Delete Account' or 'Privacy' option."
            ),
            plain_answer=excerpt,
            source_quote=hits[0][:200],
            confidence=0.75,
            could_not_find=False,
        )

    # Policy has no deletion instructions — tell the user what to do anyway
    return AskResponse(
        answer=(
            "This policy does not clearly describe how to delete your account. "
            "You can: (1) check Account Settings for a Delete or Deactivate option, "
            "(2) email the privacy contact listed in this policy, or "
            "(3) submit a Data Subject Request citing your right to erasure "
            "under GDPR Article 17. The absence of clear deletion instructions "
            "may itself be a compliance concern."
        ),
        plain_answer="The policy does not clearly explain how to delete your account.",
        source_quote="",
        confidence=0.4,
        could_not_find=True,
    )


def _keyword_answer(question: str, clauses: list, policy_text: str) -> AskResponse:
    """
    Deterministic keyword-based answer. Never raises. Always returns something real.
    """
    q = question.lower()

    # Special handler: deletion / account removal questions
    if any(kw in q for kw in _DELETION_KEYWORDS):
        result = _deletion_answer(policy_text)
        if result is not None:
            return result

    # Match question to clause category
    target_category: str | None = None
    for keywords, category in _Q_CATEGORY_MAP:
        if any(kw in q for kw in keywords):
            target_category = category
            break

    # Find best clause in that category
    best_clause: dict | None = None
    best_score: float = 0.0

    if target_category and clauses:
        for clause in clauses:
            if clause.get("category") == target_category:
                score = float(clause.get("confidence", 0.5))
                if score > best_score:
                    best_score = score
                    best_clause = clause

    if best_clause:
        original = (
            best_clause.get("original_text")
            or best_clause.get("text")
            or ""
        )[:300]
        plain = (
            best_clause.get("plain_summary")
            or best_clause.get("what_it_means")
            or original
        )
        return AskResponse(
            answer=plain,
            plain_answer=plain,
            source_quote=original[:200],
            confidence=round(min(best_score * 0.85, 0.85), 2),
            could_not_find=False,
        )

    # Sentence-level last resort
    if policy_text:
        stop = {"the", "a", "an", "is", "are", "do", "does", "did", "can",
                "will", "they", "you", "my", "i", "we"}
        q_words = set(q.split()) - stop
        sentences = [s.strip() for s in policy_text.replace(".", ". ").split(". ")
                     if len(s.strip()) > 25]
        if sentences and q_words:
            scored = sorted(sentences,
                            key=lambda s: len(q_words & set(s.lower().split())),
                            reverse=True)
            best = scored[0]
            overlap = len(q_words & set(best.lower().split()))
            if overlap >= 1:
                return AskResponse(
                    answer=best, plain_answer=best,
                    source_quote=best[:200],
                    confidence=min(overlap * 0.15, 0.5),
                    could_not_find=False,
                )

    return AskResponse(
        answer=(
            "This policy does not clearly address your question. "
            "The absence of a clear answer may itself be a concern — "
            "a well-written privacy policy should be explicit."
        ),
        plain_answer="The policy doesn't clearly answer this. That may be worth noting.",
        source_quote="",
        confidence=0.1,
        could_not_find=True,
    )
