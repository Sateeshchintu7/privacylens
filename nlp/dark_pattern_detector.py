"""
nlp/dark_pattern_detector.py -- Dark pattern detection for PrivacyLens.

Keyword/regex approach based on DarkBench (ICLR 2025):
  Kyi et al. "DarkBench: Benchmarking Dark Patterns in LLM Applications"
  ICLR 2025 -- six-category dark pattern taxonomy

Six categories:
  1. sneaking          -- hidden/buried data collection via vague language
  2. asymmetric_effort -- easy opt-in, hard opt-out
  3. obstruction       -- deliberately complex processes for exercising rights
  4. ambiguity         -- vague/contradictory language obscuring obligations
  5. false_urgency     -- passive consent / pressure to accept without reading
  6. sycophancy        -- emotional reassurance that contradicts actual practices

Author: Sateesh Kumar Payyavula
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel

from nlp.clause_extractor import ClauseResult

logger = logging.getLogger(__name__)

# ── Pattern definitions (DarkBench taxonomy) ─────────────────────────────────

_PATTERNS: list[dict] = [
    {
        "category": "sneaking",
        "label": "Hidden Data Collection",
        "severity": "high",
        "description": (
            "Vague or non-exhaustive language used to hide the true scope of data collection"
        ),
        "patterns": [
            r"including\s+but\s+not\s+limited\s+to",
            r"such\s+as\s+.{0,50}\s+and\s+other",
            r"various\s+(types\s+of\s+)?(information|data)",
            r"infer(?:red|ring|s)?\s+(?:information|data|interests|preferences)",
            r"among\s+other\s+(things|information|data)",
            r"may\s+also\s+collect\s+(?:other|additional)",
        ],
    },
    {
        "category": "asymmetric_effort",
        "label": "Hard to Opt Out",
        "severity": "high",
        "description": (
            "Opting out requires disproportionate effort compared to opting in"
        ),
        "patterns": [
            r"to\s+opt.?out.{0,80}(contact\s+us|write\s+to|send\s+a\s+(written\s+)?request|postal)",
            r"opt.?out\s+(by\s+)?(calling|phone|mailing|postal\s+mail)",
            r"cannot\s+opt.?out\s+of",
            r"no\s+opt.?out\s+(is\s+)?(available|provided|offered)",
            r"required\s+for\s+(the\s+)?service\s+to\s+function",
        ],
    },
    {
        "category": "obstruction",
        "label": "Complex Rights Process",
        "severity": "medium",
        "description": (
            "Exercising privacy rights requires navigating unnecessarily complex procedures"
        ),
        "patterns": [
            r"may\s+take\s+up\s+to\s+\d+\s+(business\s+)?days?\s+to\s+(process|respond|complete|fulfill)",
            r"(30|60|90)\s+days?\s+(to\s+(process|respond)|response\s+period)",
            r"contact\s+each\s+(partner|vendor|advertiser|third.party)\s+individually",
            r"we\s+may\s+(deny|reject|refuse)\s+(your\s+)?(deletion\s+)?request",
        ],
    },
    {
        "category": "ambiguity",
        "label": "Deliberately Vague Language",
        "severity": "medium",
        "description": (
            "Vague or open-ended language that obscures the company's actual obligations"
        ),
        "patterns": [
            r"legitimate\s+(business\s+)?interests?",
            r"at\s+our\s+(sole\s+)?discretion",
            r"we\s+reserve\s+the\s+right\s+to",
            r"without\s+(prior\s+)?notice",
            r"as\s+permitted\s+by\s+(applicable\s+)?law",
            r"reasonable\s+(period|time|advance\s+notice)",
        ],
    },
    {
        "category": "false_urgency",
        "label": "Passive Consent Trap",
        "severity": "low",
        "description": (
            "Implied consent obtained through continued use, bypassing explicit choice"
        ),
        "patterns": [
            r"by\s+continuing\s+to\s+use.{0,60}you\s+(agree|consent|accept)",
            r"your\s+continued\s+use.{0,60}(constitutes|means|indicates)\s+(acceptance|consent|agreement)",
            r"by\s+(accessing|using)\s+(our|this)\s+(service|site|app|platform).{0,50}you\s+(agree|consent)",
        ],
    },
    {
        "category": "sycophancy",
        "label": "Misleading Reassurance",
        "severity": "low",
        "description": (
            "Emotional reassurance language that may contradict the company's actual data practices"
        ),
        "patterns": [
            r"your\s+(privacy|security|trust)\s+is\s+(?:our\s+)?(?:top\s+)?priority",
            r"we\s+(never|do\s+not)\s+sell.{0,60}(but|however|except|unless)",
            r"we\s+take\s+(your\s+)?(privacy|security)\s+very\s+seriously",
            r"we\s+care\s+(deeply|greatly)\s+about\s+your\s+privacy",
        ],
    },
]

# ── Pydantic models ───────────────────────────────────────────────────────────


class DarkPattern(BaseModel):
    category: str
    label: str
    severity: str        # "high" | "medium" | "low"
    description: str
    evidence: str        # short surrounding snippet from the policy


class DarkPatternReport(BaseModel):
    total_found: int
    patterns: list[DarkPattern]
    has_high: bool
    categories_found: list[str]
    summary: str


# ── Public API ────────────────────────────────────────────────────────────────


def detect_dark_patterns(clauses: list[ClauseResult], policy_text: str | None = None) -> DarkPatternReport:
    """
    Scan a privacy policy for manipulation tactics using the DarkBench taxonomy.

    Academic ref:
        Kyi et al. "DarkBench: Benchmarking Dark Patterns in LLM Applications"
        ICLR 2025 -- keyword/regex detection across six dark pattern categories

    Args:
        clauses: extracted ClauseResult list from clause_extractor
        policy_text: optional full cleaned policy text for broader detection
    Returns:
        DarkPatternReport with findings and plain-English summary
    """
    full_text = policy_text.strip() if isinstance(policy_text, str) and policy_text.strip() else " ".join(c.original_text for c in clauses)
    full_lower = full_text.lower()

    found: list[DarkPattern] = []
    seen: set[str] = set()   # one finding per category to avoid duplicate noise

    for defn in _PATTERNS:
        cat = defn["category"]
        if cat in seen:
            continue
        for pat in defn["patterns"]:
            m = re.search(pat, full_lower, re.IGNORECASE)
            if m:
                start = max(0, m.start() - 25)
                end   = min(len(full_lower), m.end() + 60)
                snippet = full_text[start:end].strip()
                if snippet:
                    snippet = snippet[0].upper() + snippet[1:]
                found.append(DarkPattern(
                    category=cat,
                    label=defn["label"],
                    severity=defn["severity"],
                    description=defn["description"],
                    evidence=f"...{snippet}...",
                ))
                seen.add(cat)
                break

    has_high = any(p.severity == "high" for p in found)
    categories = sorted({p.category for p in found})

    if not found:
        summary = "No manipulation tactics detected"
    else:
        high = sum(1 for p in found if p.severity == "high")
        labels = ", ".join(p.label for p in found[:3])
        suffix = "..." if len(found) > 3 else ""
        summary = f"{len(found)} dark pattern{'s' if len(found) != 1 else ''} detected ({labels}{suffix})"
        if high:
            summary += f" — {high} high severity"

    return DarkPatternReport(
        total_found=len(found),
        patterns=found,
        has_high=has_high,
        categories_found=categories,
        summary=summary,
    )
