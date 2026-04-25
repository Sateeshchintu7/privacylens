"""
nlp/readability.py — Readability and legal jargon analysis for PrivacyLens.

Scores text using Flesch-Kincaid grade level and detects legal jargon density.
Used to: (a) measure original policy complexity, (b) verify plain rewrites
hit their target grade, (c) show users how hard the original text is to read.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- average privacy policy = Grade 14.8
           Flesch (1948) -- Reading Ease formula
           Sweller (1988) -- Cognitive Load Theory
"""

from typing import Optional
import textstat
from pydantic import BaseModel

BASELINE_FK: float = 14.8  # Reidenberg et al. (2015) avg privacy policy grade

LEGAL_JARGON: list[str] = [
    "pursuant", "herein", "aforementioned", "notwithstanding",
    "indemnify", "arbitration", "waive", "disclaim", "sublicense",
    "perpetual", "irrevocable", "jurisdiction", "severability",
    "aggregate", "de-identified", "pseudonymous", "fiduciary",
    "controller", "processor", "legitimate interest", "data subject",
    "supervisory authority", "cross-border", "third-party affiliate",
    "opt-out", "opt-in", "cookie", "pixel", "fingerprint", "beacon",
    "inference", "profiling", "automated decision", "lawful basis",
    "rectification", "portability", "erasure", "restriction",
    "objection", "lodge complaint",
]

_LABELS: list[tuple[float, str]] = [
    (6.0,  "Easier than a children's book -- great!"),
    (8.0,  "About as easy as a newspaper article"),
    (10.0, "Similar to a high-school textbook"),
    (12.0, "As complex as a college textbook"),
    (14.0, "Harder than most university essays"),
    (16.0, "As hard as academic journal papers"),
    (1e9,  "Harder than a PhD thesis"),
]


class ReadabilityReport(BaseModel):
    """Full readability analysis of a text sample."""
    flesch_kincaid_grade: float
    flesch_reading_ease: float
    avg_sentence_length: float
    avg_word_length: float
    jargon_density: float           # jargon terms per 100 words
    legal_jargon_count: int
    legal_jargon_found: list[str]
    comparison_label: str
    minutes_to_read: float          # based on 238 wpm adult reading speed
    pct_vs_baseline: float          # % harder/easier vs 14.8 baseline
    word_count: int
    meets_target_grade: Optional[bool] = None
    target_grade: Optional[float] = None


def enforce_readability_improvement(
    original_text: str,
    rewritten_text: str,
) -> str:
    """
    Ensure rewritten text is always easier to read than the original.
    Target: FK Grade <= 6.0. Simplifies by truncating long sentences.
    """
    if not rewritten_text or len(rewritten_text.strip()) < 20:
        return rewritten_text

    orig_grade = textstat.flesch_kincaid_grade(original_text)
    rew_grade  = textstat.flesch_kincaid_grade(rewritten_text)

    if rew_grade <= min(orig_grade, 6.0):
        return rewritten_text  # Already good

    sentences  = rewritten_text.split('.')
    simplified = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        words = s.split()
        if len(words) > 15:
            s = ' '.join(words[:15])
        simplified.append(s)
    return '. '.join(simplified)


def score_readability(text: str, target_grade: Optional[float] = None) -> ReadabilityReport:
    """
    Compute readability metrics for any text sample.

    Args:
        text: Text to analyse (original policy or plain rewrite)
        target_grade: Optional FK grade target; sets meets_target_grade flag

    Returns:
        ReadabilityReport with FK grade, ease score, jargon list, etc.

    Academic ref:
        Reidenberg et al. (2015) -- privacy policy comprehension study
        Wilson et al. (2016) -- OPP-115, policy text analysis
    """
    if not text or not text.strip():
        return ReadabilityReport(
            flesch_kincaid_grade=1.0, flesch_reading_ease=100.0,
            avg_sentence_length=0.0, avg_word_length=0.0,
            jargon_density=0.0, legal_jargon_count=0, legal_jargon_found=[],
            comparison_label="No text provided", minutes_to_read=0.0,
            pct_vs_baseline=0.0, word_count=0,
        )

    fk_grade  = textstat.flesch_kincaid_grade(text)
    fk_ease   = textstat.flesch_reading_ease(text)
    words     = text.split()
    wc        = max(len(words), 1)
    sents     = max(textstat.sentence_count(text), 1)
    avg_sl    = round(wc / sents, 1)
    avg_wl    = round(sum(len(w.strip(".,!?;:'\"")) for w in words) / wc, 2)

    lower        = text.lower()
    jargon_found = [t for t in LEGAL_JARGON if t in lower]
    density      = round(len(jargon_found) / (wc / 100), 2)

    label   = next(lbl for thresh, lbl in _LABELS if fk_grade <= thresh)
    minutes = round(wc / 238, 1)
    pct     = round(((fk_grade - BASELINE_FK) / BASELINE_FK) * 100, 1)

    report = ReadabilityReport(
        flesch_kincaid_grade=round(fk_grade, 1),
        flesch_reading_ease=round(fk_ease, 1),
        avg_sentence_length=avg_sl,
        avg_word_length=avg_wl,
        jargon_density=density,
        legal_jargon_count=len(jargon_found),
        legal_jargon_found=jargon_found,
        comparison_label=label,
        minutes_to_read=minutes,
        pct_vs_baseline=pct,
        word_count=wc,
    )
    if target_grade is not None:
        report.target_grade = target_grade
        report.meets_target_grade = fk_grade <= target_grade + 0.5
    return report
