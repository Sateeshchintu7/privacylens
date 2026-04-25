"""
nlp/rag_qa.py -- Retrieval-Augmented Generation (RAG) chatbot for PrivacyLens.

Build: FAISS vector index over policy chunks (sentence-transformers, local, free).
Query: embed question → retrieve top-k chunks → Gemini answers from context only.
STUB mode: returns demo answer when GEMINI_API_KEY not set.

Author: Sateesh Kumar Payyavula
Reference: Adhikari, Das & Dewri (2025, arXiv:2501.10319) -- RAG for privacy
           Rodriguez et al. (2024, Springer Computing) -- LLM Q&A on legal docs
"""

import hashlib
import logging
import os
import pickle
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel

# Prevent HuggingFace Hub from checking for model updates — use local cache only.
# Same pattern as contradiction_detector.py; avoids 20-30s retry loops on Render.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from config import BASE_DIR, CACHE_DIR, GEMINI_API_KEY
from nlp.clause_extractor import ClauseResult
from nlp.llm_client import call_gemini, parse_json_response
from api.prompt_loader import load_prompt

logger = logging.getLogger(__name__)
PROMPT_PATH = BASE_DIR / "prompts" / "rag_answer.txt"
FAISS_CACHE = CACHE_DIR / "faiss"
FAISS_CACHE.mkdir(parents=True, exist_ok=True)

SUGGESTED_QUESTIONS_GENERAL: list[str] = [
    "Can they sell my personal data?",
    "How long do they keep my data?",
    "Can I delete my account and all my data?",
    "Do they share my data with advertisers?",
    "What happens to my data if the company is sold?",
    "Do they track my location?",
    "Can I opt out of data collection?",
    "What data do they collect about children?",
]
SUGGESTED_QUESTIONS_KIDS: list[str] = [
    "Is my information safe with this app? \U0001f512",
    "Can they see where I live? \U0001f4cd",
    "Do they share my info with strangers? \U0001f517",
    "Can I make them delete my info? \U0001f5d1\ufe0f",
    "Will they send me ads? \U0001f4e2",
]


class QAResult(BaseModel):
    """Answer to a user question about the policy."""
    question: str
    answer: str
    confidence: float
    source_clauses: list[str]
    source_categories: list[str]
    plain_answer: str
    could_not_find: bool


class PolicyIndex:
    """FAISS semantic search index over policy text chunks."""
    def __init__(self, chunks: list[str], embeddings: Any, faiss_index: Any, clause_map: dict):
        self.chunks = chunks
        self.embeddings = embeddings
        self.index = faiss_index
        self.clause_map = clause_map


def _chunk_for_index(text: str, chunk_words: int = 200, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        end = min(i + chunk_words, len(words))
        chunks.append(" ".join(words[i:end]))
        if end >= len(words): break
        i += chunk_words - overlap
    return chunks or [text[:1000]]


def build_index(policy_text: str, clauses: list[ClauseResult]) -> PolicyIndex:
    """
    Build a FAISS semantic search index from policy text.

    Downloads sentence-transformers model once (~80MB), then runs locally.
    Caches the index to .cache/faiss/{hash}.pkl.

    Args:
        policy_text: Full cleaned policy text
        clauses: list[ClauseResult] for clause-level mapping

    Returns:
        PolicyIndex ready for retrieve()

    Academic ref:
        Adhikari et al. (2025, arXiv:2501.10319) -- vector retrieval for privacy
    """
    ph = hashlib.md5(policy_text.encode()).hexdigest()[:12]
    cache_file = FAISS_CACHE / f"{ph}.pkl"

    if cache_file.exists():
        with open(cache_file, "rb") as f:
            data = pickle.load(f)
        return PolicyIndex(**data)

    chunks = _chunk_for_index(policy_text)
    clause_map: dict[int, Optional[ClauseResult]] = {}
    for i, chunk in enumerate(chunks):
        best = min(clauses, key=lambda c: abs(policy_text.find(chunk[:40]) - c.char_start), default=None) if clauses else None
        clause_map[i] = best

    try:
        from sentence_transformers import SentenceTransformer
        import faiss, numpy as np
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(chunks, show_progress_bar=False)
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings.astype("float32"))
        data = dict(chunks=chunks, embeddings=embeddings, faiss_index=index, clause_map=clause_map)
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        return PolicyIndex(chunks, embeddings, index, clause_map)
    except Exception as exc:
        logger.warning("FAISS index build failed: %s — using keyword fallback", exc)
        return PolicyIndex(chunks, None, None, clause_map)


def retrieve(question: str, policy_index: PolicyIndex, top_k: int = 5) -> list[str]:
    """
    Retrieve top-k relevant chunks for a question.

    Uses FAISS semantic search if available, keyword matching as fallback.

    Args:
        question: Natural language question
        policy_index: PolicyIndex from build_index()
        top_k: Number of chunks to return

    Returns:
        list[str] of most relevant policy text chunks

    Academic ref:
        Adhikari et al. (2025, arXiv:2501.10319) -- retrieval methodology
    """
    if policy_index.index is not None:
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            model = SentenceTransformer("all-MiniLM-L6-v2")
            q_emb = model.encode([question]).astype("float32")
            _, indices = policy_index.index.search(q_emb, top_k)
            return [policy_index.chunks[i] for i in indices[0] if 0 <= i < len(policy_index.chunks)]
        except Exception as exc:
            logger.warning("FAISS retrieval failed (%s) — falling back to keyword", exc)

    q_words = set(question.lower().split())
    scored = [(sum(1 for w in q_words if w in c.lower()), c) for c in policy_index.chunks]
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k] if _]


def answer_question(
    question: str,
    policy_index: PolicyIndex,
    clauses: list[ClauseResult],
    audience_level: str = "adult",
    use_cache: bool = True,
) -> QAResult:
    """
    Answer a natural-language question about the loaded policy using RAG.

    Retrieves top-5 relevant chunks → prompts Gemini to answer from context only.
    STUB: returns demo answer when GEMINI_API_KEY not set.

    Args:
        question: User's question in plain English
        policy_index: PolicyIndex from build_index()
        clauses: list[ClauseResult] for source attribution
        audience_level: affects answer reading level
        use_cache: cache LLM responses

    Returns:
        QAResult with answer, confidence, and source citation

    Academic ref:
        Rodriguez et al. (2024) -- LLM Q&A on legal documents
        Adhikari et al. (2025, arXiv:2501.10319) -- RAG pipeline
    """
    top_chunks = retrieve(question, policy_index, top_k=5)
    context = "\n---\n".join(top_chunks)

    source_cats: list[str] = []
    for chunk in top_chunks:
        for c in clauses:
            if chunk[:40] in c.original_text or c.original_text[:40] in chunk:
                if c.category not in source_cats:
                    source_cats.append(c.category)

    # STUB: requires GEMINI_API_KEY -- will auto-activate when set
    if not GEMINI_API_KEY:
        return QAResult(
            question=question,
            answer=f"[DEMO MODE] I found {len(top_chunks)} relevant sections for '{question}'. Add GEMINI_API_KEY to .env to get a real answer.",
            confidence=0.0,
            source_clauses=[c[:100] for c in top_chunks[:2]],
            source_categories=source_cats,
            plain_answer="[DEMO] Add API key for real answers.",
            could_not_find=False,
        )

    prompt = (load_prompt("prompts/rag_answer.txt")
              .replace("{QUESTION}", question)
              .replace("{CONTEXT_CHUNKS}", context[:4000])
              .replace("{AUDIENCE_LEVEL}", audience_level))

    try:
        resp, _ = call_gemini(prompt, function_name="rag_qa", use_cache=use_cache)
        raw = parse_json_response(resp)
        if not isinstance(raw, dict):
            raise ValueError("Non-dict JSON response")
        return QAResult(
            question=question,
            answer=str(raw.get("answer", "I could not find a clear answer in this policy.")),
            confidence=float(raw.get("confidence", 0.5)),
            source_clauses=[str(raw.get("source_quote", ""))],
            source_categories=source_cats,
            plain_answer=str(raw.get("plain_answer", "")),
            could_not_find=bool(raw.get("could_not_find", False)),
        )
    except Exception as exc:
        logger.warning("RAG answer failed: %s", exc)
        return QAResult(
            question=question,
            answer="We couldn't generate an answer right now. Please try again.",
            confidence=0.0, source_clauses=[], source_categories=[],
            plain_answer="Try again.", could_not_find=True,
        )
