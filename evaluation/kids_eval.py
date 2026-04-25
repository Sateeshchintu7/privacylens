"""
evaluation/kids_eval.py -- Age-appropriate comprehension evaluation for Kids Mode.

Tests whether under-18 users understand Kids Mode rewrites better than the
original policy text. Questions are tiered by age group.

Author: Sateesh Kumar Payyavula
Reference: Reidenberg et al. (2015) -- comprehension study design
           Lorenz-Spreen et al. (2021) -- adolescent digital literacy
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Data models ───────────────────────────────────────────────────────────────

class KidsQuestion(BaseModel):
    """A single age-appropriate comprehension question.

    Uses 3 options for 'child', 4 options for 'junior' and 'teen'.
    """
    question_id: str
    age_group: str               # "child" | "junior" | "teen"
    question: str
    emoji_hint: str
    options: list[str]
    correct_answer: int          # 0-indexed
    simple_explanation: str      # plain-language explanation of correct answer


class KidsStudyResult(BaseModel):
    """Result of a single kids study session."""
    participant_id: str
    age_group: str
    condition: str               # "original_text" | "kids_mode"
    policy: str
    responses: list[int]
    correct: int
    total: int
    percentage: float
    passed: bool                 # percentage >= 60%


# ── TikTok question bank ──────────────────────────────────────────────────────

KIDS_QUESTIONS_TIKTOK: list[KidsQuestion] = [
    # ── Child (age 8-10) — 3 options ─────────────────────────────────────────
    KidsQuestion(
        question_id="K001",
        age_group="child",
        question="Does TikTok know where you are?",
        emoji_hint="📍",
        options=["Yes", "No", "Only sometimes"],
        correct_answer=0,
        simple_explanation=(
            "TikTok can find out where you are using your phone's GPS and WiFi."
        ),
    ),
    KidsQuestion(
        question_id="K002",
        age_group="child",
        question="If you post a video on TikTok, can TikTok keep it?",
        emoji_hint="🎥",
        options=["Yes, they might keep it", "No, it is always yours", "Only if you say yes"],
        correct_answer=0,
        simple_explanation=(
            "Once you share a video on TikTok, they may keep a copy of it."
        ),
    ),
    KidsQuestion(
        question_id="K003",
        age_group="child",
        question="Should you put your real name on TikTok?",
        emoji_hint="🙈",
        options=["Yes, always", "No, it is safer not to", "Only your first name is fine"],
        correct_answer=1,
        simple_explanation=(
            "Using your real name online can be risky. It is safer to use a nickname."
        ),
    ),

    # ── Junior (age 11-13) — 4 options ───────────────────────────────────────
    KidsQuestion(
        question_id="K004",
        age_group="junior",
        question="Does TikTok share your information with other companies?",
        emoji_hint="🔗",
        options=[
            "No, TikTok keeps everything private",
            "Yes, they share with advertisers and partners",
            "Only your username is shared",
            "Only if you give permission",
        ],
        correct_answer=1,
        simple_explanation=(
            "TikTok shares your information with advertising companies to show you adverts."
        ),
    ),
    KidsQuestion(
        question_id="K005",
        age_group="junior",
        question="Can you ask TikTok to delete all your data?",
        emoji_hint="🗑️",
        options=[
            "No, once TikTok has your data they keep it forever",
            "Yes, you can request deletion in the app settings",
            "Only if you are over 18",
            "You can delete videos but not your personal information",
        ],
        correct_answer=1,
        simple_explanation=(
            "You can ask TikTok to delete your data. Look in Privacy settings in the app."
        ),
    ),
    KidsQuestion(
        question_id="K006",
        age_group="junior",
        question="How old do you have to be to use TikTok?",
        emoji_hint="🎂",
        options=[
            "Any age is fine",
            "You must be at least 13 years old",
            "You must be at least 16 years old",
            "You must be at least 18 years old",
        ],
        correct_answer=1,
        simple_explanation=(
            "TikTok's minimum age is 13. If you are under 13 you should not have an account."
        ),
    ),

    # ── Teen (age 14-17) — 4 options ─────────────────────────────────────────
    KidsQuestion(
        question_id="K007",
        age_group="teen",
        question=(
            "Under TikTok's terms, what happens to your content if you delete your account?"
        ),
        emoji_hint="⚠️",
        options=[
            "All content is immediately and permanently deleted",
            "Content may be retained if required by law or if others have shared it",
            "Content is anonymised but kept for analytics",
            "TikTok must delete everything within 30 days",
        ],
        correct_answer=1,
        simple_explanation=(
            "Deleting your account does not guarantee all your content disappears -- "
            "especially if others have shared it or there are legal reasons to keep it."
        ),
    ),
    KidsQuestion(
        question_id="K008",
        age_group="teen",
        question="What data does TikTok collect when you watch videos?",
        emoji_hint="👁️",
        options=[
            "Nothing -- watching is fully private",
            "Only the video titles you watched",
            "Watch time, interactions, and device information",
            "Only data if you comment or like",
        ],
        correct_answer=2,
        simple_explanation=(
            "TikTok tracks how long you watch videos, what you interact with, "
            "and information about your device to personalise your feed."
        ),
    ),
    KidsQuestion(
        question_id="K009",
        age_group="teen",
        question="Can advertisers target you based on your TikTok activity?",
        emoji_hint="🎯",
        options=[
            "No -- TikTok does not allow targeted advertising",
            "Only if you have a business account",
            "Yes -- TikTok uses your behaviour to show targeted adverts",
            "Only with explicit opt-in consent",
        ],
        correct_answer=2,
        simple_explanation=(
            "TikTok uses your viewing habits and interactions to serve targeted "
            "adverts. You can limit this in your privacy settings."
        ),
    ),
    KidsQuestion(
        question_id="K010",
        age_group="teen",
        question=(
            "If you share your location in a video or bio, who can potentially see it?"
        ),
        emoji_hint="🌍",
        options=[
            "Only your followers",
            "Only TikTok employees",
            "Anyone with access to the video, potentially globally",
            "Nobody -- location data is always stripped",
        ],
        correct_answer=2,
        simple_explanation=(
            "Sharing location in content makes it visible to whoever can see that "
            "content. Public videos are visible globally."
        ),
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

_AGE_GROUPS = ("child", "junior", "teen")


def get_questions_for_age(age_group: str) -> list[KidsQuestion]:
    """Return questions appropriate for the given age group."""
    if age_group not in _AGE_GROUPS:
        raise ValueError(f"age_group must be one of {_AGE_GROUPS}, got '{age_group}'")
    return [q for q in KIDS_QUESTIONS_TIKTOK if q.age_group == age_group]


# ── Study runner ──────────────────────────────────────────────────────────────

def run_kids_study(
    participant_id: str,
    age_group: str,
    condition: str,
    responses: list[int],
    policy: str = "TikTok",
) -> KidsStudyResult:
    """
    Score a kids study session.

    Args:
        participant_id: Anonymous participant ID
        age_group: "child" | "junior" | "teen"
        condition: "original_text" | "kids_mode"
        responses: Selected option index (0-based) per question

    Returns:
        KidsStudyResult with score and pass/fail
    """
    questions = get_questions_for_age(age_group)
    if len(responses) != len(questions):
        raise ValueError(
            f"Expected {len(questions)} responses for age_group '{age_group}', "
            f"got {len(responses)}"
        )

    correct = sum(
        1 for q, r in zip(questions, responses) if r == q.correct_answer
    )
    total      = len(questions)
    percentage = round(correct / total * 100, 1)

    return KidsStudyResult(
        participant_id=participant_id,
        age_group=age_group,
        condition=condition,
        policy=policy,
        responses=responses,
        correct=correct,
        total=total,
        percentage=percentage,
        passed=percentage >= 60.0,
    )


def print_kids_quiz(age_group: str) -> None:
    """Print questions and answers for a given age group (for study facilitators)."""
    questions = get_questions_for_age(age_group)
    print(f"\n=== TikTok Comprehension Quiz -- {age_group.upper()} ({len(questions)} questions) ===\n")
    for i, q in enumerate(questions, 1):
        print(f"Q{i} {q.emoji_hint}  {q.question}")
        for j, opt in enumerate(q.options):
            mark = " <-- CORRECT" if j == q.correct_answer else ""
            print(f"     {j+1}. {opt}{mark}")
        print(f"     Explanation: {q.simple_explanation}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Kids comprehension questions loaded:")
    for group in _AGE_GROUPS:
        qs = get_questions_for_age(group)
        print(f"  {group:8s}: {len(qs)} questions")

    # Demo: simulate perfect score in kids_mode
    for group in _AGE_GROUPS:
        qs = get_questions_for_age(group)
        perfect = [q.correct_answer for q in qs]
        result = run_kids_study("DEMO", group, "kids_mode", perfect)
        print(f"  {group:8s} perfect score: {result.correct}/{result.total} "
              f"({result.percentage}%) -- {'PASS' if result.passed else 'FAIL'}")

    print()
    print_kids_quiz("junior")
