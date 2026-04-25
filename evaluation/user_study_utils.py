"""
evaluation/user_study_utils.py -- User study materials and analysis for PrivacyLens.

Provides:
  - SUS (System Usability Scale) scoring and interpretation
  - Comprehension question bank for Google Privacy Policy (10 questions)
  - StudyParticipant recording and results analysis
  - CSV export for SPSS/R analysis
  - Markdown results table for dissertation

Author: Sateesh Kumar Payyavula
Reference: Brooke (1996) "SUS: A 'Quick and Dirty' Usability Scale"
           Reidenberg et al. (2015) -- comprehension study methodology
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_STUDY_DIR  = _ROOT / "evaluation" / "study_data"
_RESULTS_DIR = _ROOT / "evaluation" / "results"
_STUDY_DIR.mkdir(parents=True, exist_ok=True)
_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

_PARTICIPANTS_FILE = _STUDY_DIR / "participants.jsonl"


# ── SUS ───────────────────────────────────────────────────────────────────────

SUS_QUESTIONS = [
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
]


def calculate_sus(responses: list[int]) -> float:
    """
    Calculate SUS score from 10 Likert responses (1-5).

    Odd questions (1,3,5,7,9)  : contribution = score - 1
    Even questions (2,4,6,8,10): contribution = 5 - score
    SUS score = sum of contributions * 2.5   (range 0–100)

    Score >= 68 = above average usability.

    Academic ref: Brooke (1996) -- SUS methodology
    """
    if len(responses) != 10:
        raise ValueError(f"SUS requires exactly 10 responses, got {len(responses)}")
    if any(r < 1 or r > 5 for r in responses):
        raise ValueError("Each SUS response must be in range 1-5")

    total = 0
    for i, r in enumerate(responses):
        # 0-indexed: positions 0,2,4,6,8 are odd questions
        if i % 2 == 0:
            total += r - 1
        else:
            total += 5 - r

    return round(total * 2.5, 1)


def interpret_sus(score: float) -> str:
    """
    Return letter grade and adjective for a SUS score.

    Thresholds from Bangor et al. (2008) adjective ratings.
    """
    if score >= 85.5:
        return "A+ (Best Imaginable)"
    if score >= 80.3:
        return "A  (Excellent)"
    if score >= 68.0:
        return "B  (Good) -- Above average"
    if score >= 51.0:
        return "C  (OK)"
    if score >= 25.0:
        return "D  (Poor)"
    return "F  (Worst Imaginable)"


# ── Comprehension questions ───────────────────────────────────────────────────

class ComprehensionQuestion(BaseModel):
    """Single multiple-choice comprehension question for a privacy policy.

    Academic ref: Reidenberg et al. (2015) -- comprehension test design
    """
    question_id: str
    policy_name: str
    question: str
    options: list[str]           # 4 answer options
    correct_answer: int          # 0-indexed
    correct_answer_text: str
    category: str
    difficulty: str              # "easy" | "medium" | "hard"
    original_text_excerpt: str


GOOGLE_COMPREHENSION_QUESTIONS: list[ComprehensionQuestion] = [
    ComprehensionQuestion(
        question_id="G001",
        policy_name="Google Privacy Policy",
        question="According to Google's privacy policy, what happens to your search history?",
        options=[
            "A) Google never stores search history",
            "B) Google stores your searches to improve recommendations and show ads",
            "C) Search history is only kept for 24 hours",
            "D) Your searches are never linked to your account",
        ],
        correct_answer=1,
        correct_answer_text="B) Google stores your searches to improve recommendations and show ads",
        category="data_collection",
        difficulty="medium",
        original_text_excerpt=(
            "We collect information about your activity in our services, which we use to do "
            "things like recommend a YouTube video you might like."
        ),
    ),
    ComprehensionQuestion(
        question_id="G002",
        policy_name="Google Privacy Policy",
        question="Can you ask Google to delete all your personal data?",
        options=[
            "A) No, once collected data cannot be deleted",
            "B) Yes, but only for data collected in the last 30 days",
            "C) Yes, you can request deletion through your Google Account",
            "D) Only if you are in the European Union",
        ],
        correct_answer=2,
        correct_answer_text="C) Yes, you can request deletion through your Google Account",
        category="user_rights",
        difficulty="easy",
        original_text_excerpt=(
            "You can export a copy of content in your Google Account if you want to back it up "
            "or use it with a service outside of Google."
        ),
    ),
    ComprehensionQuestion(
        question_id="G003",
        policy_name="Google Privacy Policy",
        question="Does Google share your personal data with advertisers?",
        options=[
            "A) Yes, Google sells your personal data directly to advertisers",
            "B) No, Google never shares data with advertisers",
            "C) Google shares insights with advertisers but not your personal identifying information",
            "D) Google only shares data with advertisers if you opt in",
        ],
        correct_answer=2,
        correct_answer_text=(
            "C) Google shares insights with advertisers but not your personal identifying information"
        ),
        category="third_party_sharing",
        difficulty="hard",
        original_text_excerpt=(
            "We do not share your personal information with companies, organizations, or individuals "
            "outside of Google except in the following cases..."
        ),
    ),
    ComprehensionQuestion(
        question_id="G004",
        policy_name="Google Privacy Policy",
        question="Does Google's privacy policy have special protections for children?",
        options=[
            "A) No, the policy applies the same to all ages",
            "B) Yes, children under 13 need parental consent",
            "C) Yes, Google services require users to be 18+",
            "D) Children's data is automatically deleted after 30 days",
        ],
        correct_answer=1,
        correct_answer_text="B) Yes, children under 13 need parental consent",
        category="children_data",
        difficulty="medium",
        original_text_excerpt="We provide age-appropriate experiences for children with Family Link.",
    ),
    ComprehensionQuestion(
        question_id="G005",
        policy_name="Google Privacy Policy",
        question="If Google experiences a data breach, what will they do?",
        options=[
            "A) Notify all users within 24 hours by email",
            "B) The policy does not clearly specify breach notification procedures",
            "C) Post a notice on their website only",
            "D) Notify only users whose data was definitely compromised",
        ],
        correct_answer=1,
        correct_answer_text="B) The policy does not clearly specify breach notification procedures",
        category="breach_notification",
        difficulty="hard",
        original_text_excerpt="",
    ),
    ComprehensionQuestion(
        question_id="G006",
        policy_name="Google Privacy Policy",
        question="Does Google track your location?",
        options=[
            "A) Only when you use Google Maps",
            "B) Never -- location tracking requires explicit opt-in",
            "C) Yes, through GPS, WiFi, device sensors and IP address",
            "D) Only on Android devices",
        ],
        correct_answer=2,
        correct_answer_text="C) Yes, through GPS, WiFi, device sensors and IP address",
        category="cookies_tracking",
        difficulty="easy",
        original_text_excerpt=(
            "When you use Google services, we may collect and process information about your actual location."
        ),
    ),
    ComprehensionQuestion(
        question_id="G007",
        policy_name="Google Privacy Policy",
        question="How long does Google keep your data?",
        options=[
            "A) Forever unless you delete it",
            "B) Maximum 3 years",
            "C) It varies -- some data is deleted quickly, other data kept longer",
            "D) 90 days after you stop using Google services",
        ],
        correct_answer=2,
        correct_answer_text=(
            "C) It varies -- some data is deleted quickly, other data kept longer"
        ),
        category="retention_period",
        difficulty="hard",
        original_text_excerpt=(
            "We maintain different retention periods depending on the type of data."
        ),
    ),
    ComprehensionQuestion(
        question_id="G008",
        policy_name="Google Privacy Policy",
        question="Can your Google data be transferred to other countries?",
        options=[
            "A) No, data stays in your home country",
            "B) Only within the European Union",
            "C) Yes, Google operates globally and data may be processed anywhere",
            "D) Only with explicit consent per transfer",
        ],
        correct_answer=2,
        correct_answer_text=(
            "C) Yes, Google operates globally and data may be processed anywhere"
        ),
        category="cross_border_transfer",
        difficulty="medium",
        original_text_excerpt=(
            "Google LLC is headquartered in the United States, and we process and store "
            "information in the US and other countries."
        ),
    ),
    ComprehensionQuestion(
        question_id="G009",
        policy_name="Google Privacy Policy",
        question="How does Google protect your personal data?",
        options=[
            "A) There are no specific security measures mentioned",
            "B) Physical security only -- no digital encryption",
            "C) Encryption in transit and at rest, plus access controls",
            "D) Data is anonymised so no protection is needed",
        ],
        correct_answer=2,
        correct_answer_text="C) Encryption in transit and at rest, plus access controls",
        category="data_security",
        difficulty="easy",
        original_text_excerpt=(
            "We protect our users by implementing safety features like Safe Browsing, "
            "Security Checkup, and 2-Step Verification."
        ),
    ),
    ComprehensionQuestion(
        question_id="G010",
        policy_name="Google Privacy Policy",
        question="What is the main purpose Google collects your data for?",
        options=[
            "A) To sell to data brokers",
            "B) Only to make their services work",
            "C) To improve services, personalise experience, and show relevant ads",
            "D) Legal compliance only",
        ],
        correct_answer=2,
        correct_answer_text=(
            "C) To improve services, personalise experience, and show relevant ads"
        ),
        category="purpose_limitation",
        difficulty="medium",
        original_text_excerpt=(
            "We use the information we collect from all our services for the following purposes: "
            "Provide, maintain, and improve our services."
        ),
    ),
]


# ── Participant / results models ──────────────────────────────────────────────

class StudyParticipant(BaseModel):
    """Single user study participant record."""
    participant_id: str
    age_group: str               # "18-24" | "25-34" | "35-44" | "45+"
    education: str               # "secondary" | "undergrad" | "postgrad"
    condition: str               # "control" | "tool"
    policy_tested: str
    comprehension_scores: list[bool]
    time_seconds: int
    sus_responses: list[int]     # empty for control group
    sus_score: float
    notes: str = ""


class StudyResults(BaseModel):
    """Aggregated results from all study participants."""
    participants: list[StudyParticipant]
    control_group_size: int
    tool_group_size: int
    control_avg_comprehension: float
    tool_avg_comprehension: float
    comprehension_improvement: float
    control_avg_time: float
    tool_avg_time: float
    time_difference: float
    avg_sus_score: float
    sus_interpretation: str
    statistical_significance: bool
    t_statistic: float
    p_value: float


# ── Recording ─────────────────────────────────────────────────────────────────

def record_participant(
    participant: StudyParticipant,
    output_dir: str = "evaluation/study_data",
) -> None:
    """
    Append a participant record to participants.jsonl.

    One JSON object per line (append mode) for easy streaming reads.
    """
    out_path = _ROOT / output_dir / "participants.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(participant.model_dump_json() + "\n")


def load_participants(
    data_path: str = "evaluation/study_data/participants.jsonl",
) -> list[StudyParticipant]:
    """Load all participant records from JSONL file."""
    path = _ROOT / data_path
    if not path.exists():
        return []
    participants = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                participants.append(StudyParticipant.model_validate_json(line))
    return participants


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyse_results(
    data_path: str = "evaluation/study_data/participants.jsonl",
) -> Optional[StudyResults]:
    """
    Analyse all recorded participants.

    Splits into control/tool groups, calculates comprehension and time metrics,
    runs independent-samples t-test (scipy) on comprehension scores.

    Academic ref:
        Reidenberg et al. (2015) -- controlled comprehension study analysis
    """
    participants = load_participants(data_path)
    if not participants:
        return None

    control = [p for p in participants if p.condition == "control"]
    tool    = [p for p in participants if p.condition == "tool"]

    def avg_comp(group: list[StudyParticipant]) -> float:
        if not group:
            return 0.0
        scores = [sum(p.comprehension_scores) / len(p.comprehension_scores) * 100
                  for p in group]
        return round(sum(scores) / len(scores), 1)

    def avg_time(group: list[StudyParticipant]) -> float:
        if not group:
            return 0.0
        return round(sum(p.time_seconds for p in group) / len(group), 1)

    ctrl_comp = avg_comp(control)
    tool_comp = avg_comp(tool)
    ctrl_time = avg_time(control)
    tool_time = avg_time(tool)

    sus_scores = [p.sus_score for p in tool if p.sus_score > 0]
    avg_sus = round(sum(sus_scores) / len(sus_scores), 1) if sus_scores else 0.0

    # T-test
    t_stat = 0.0
    p_val  = 1.0
    sig    = False
    if len(control) >= 2 and len(tool) >= 2:
        try:
            from scipy import stats  # type: ignore
            ctrl_raw = [sum(p.comprehension_scores) / len(p.comprehension_scores)
                        for p in control]
            tool_raw = [sum(p.comprehension_scores) / len(p.comprehension_scores)
                        for p in tool]
            t_stat, p_val = stats.ttest_ind(ctrl_raw, tool_raw)
            t_stat = round(float(t_stat), 4)
            p_val  = round(float(p_val),  4)
            sig    = p_val < 0.05
        except ImportError:
            pass  # scipy not available

    return StudyResults(
        participants=participants,
        control_group_size=len(control),
        tool_group_size=len(tool),
        control_avg_comprehension=ctrl_comp,
        tool_avg_comprehension=tool_comp,
        comprehension_improvement=round(tool_comp - ctrl_comp, 1),
        control_avg_time=ctrl_time,
        tool_avg_time=tool_time,
        time_difference=round(ctrl_time - tool_time, 1),
        avg_sus_score=avg_sus,
        sus_interpretation=interpret_sus(avg_sus),
        statistical_significance=sig,
        t_statistic=t_stat,
        p_value=p_val,
    )


# ── Output ────────────────────────────────────────────────────────────────────

def generate_results_table(results: StudyResults) -> str:
    """
    Return a markdown table of study results for dissertation insertion.

    Academic ref: APA-style results table format
    """
    sig_str = f"Yes (p={results.p_value:.3f})" if results.statistical_significance \
              else f"No  (p={results.p_value:.3f})"

    time_diff_str = (
        f"-{results.time_difference:.0f}s faster" if results.time_difference > 0
        else f"+{abs(results.time_difference):.0f}s slower"
    )

    rows = [
        ("Participants",         f"n={results.control_group_size}", f"n={results.tool_group_size}", ""),
        ("Avg comprehension",    f"{results.control_avg_comprehension:.1f}%",
         f"{results.tool_avg_comprehension:.1f}%",
         f"+{results.comprehension_improvement:.1f}pp"),
        ("Avg time (seconds)",   f"{results.control_avg_time:.0f}",
         f"{results.tool_avg_time:.0f}", time_diff_str),
        ("SUS Score",            "N/A",
         f"{results.avg_sus_score:.1f}/100", results.sus_interpretation.strip()),
        ("Sig. (p < 0.05)",      "--", "--", sig_str),
    ]

    header = "| Metric | Control Group | Tool Group | Difference |\n"
    sep    = "|--------|--------------|------------|------------|\n"
    body   = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows)
    return header + sep + body


def export_for_spss(
    data_path: str = "evaluation/study_data/participants.jsonl",
    output_path: str = "evaluation/results/study_data.csv",
) -> None:
    """
    Export participant data to CSV for SPSS / R analysis.

    Columns: participant_id, condition, age_group, education,
             comprehension_score, time_seconds, sus_score, q1..q10
    """
    participants = load_participants(data_path)
    if not participants:
        print("No participant data to export.")
        return

    out = _ROOT / output_path
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        q_headers = [f"q{i+1}" for i in range(10)]
        writer.writerow([
            "participant_id", "condition", "age_group", "education",
            "comprehension_score", "time_seconds", "sus_score",
        ] + q_headers)

        for p in participants:
            comp_score = round(
                sum(p.comprehension_scores) / len(p.comprehension_scores) * 100, 1
            )
            q_vals = [int(b) for b in p.comprehension_scores[:10]]
            while len(q_vals) < 10:
                q_vals.append("")  # type: ignore
            writer.writerow([
                p.participant_id, p.condition, p.age_group, p.education,
                comp_score, p.time_seconds, p.sus_score,
            ] + q_vals)

    print(f"SPSS/R export saved: {out}")


# ── Demo data seed ────────────────────────────────────────────────────────────

def seed_demo_participants() -> None:
    """
    Seed 10 demo participants (5 control, 5 tool) for testing.

    These simulate plausible study results; replace with real data.
    """
    demo = [
        # control group (reads original text)
        StudyParticipant(participant_id="P001", age_group="18-24", education="undergrad",
            condition="control", policy_tested="Google",
            comprehension_scores=[True, False, False, True, False, True, False, True, True, False],
            time_seconds=420, sus_responses=[], sus_score=0.0),
        StudyParticipant(participant_id="P002", age_group="25-34", education="postgrad",
            condition="control", policy_tested="Google",
            comprehension_scores=[True, True, False, True, False, True, False, False, True, False],
            time_seconds=390, sus_responses=[], sus_score=0.0),
        StudyParticipant(participant_id="P003", age_group="18-24", education="secondary",
            condition="control", policy_tested="Google",
            comprehension_scores=[True, False, False, False, False, True, False, True, True, False],
            time_seconds=510, sus_responses=[], sus_score=0.0),
        StudyParticipant(participant_id="P004", age_group="35-44", education="undergrad",
            condition="control", policy_tested="Google",
            comprehension_scores=[True, True, False, True, False, True, True, True, True, False],
            time_seconds=350, sus_responses=[], sus_score=0.0),
        StudyParticipant(participant_id="P005", age_group="25-34", education="undergrad",
            condition="control", policy_tested="Google",
            comprehension_scores=[True, False, False, True, False, False, False, True, True, False],
            time_seconds=460, sus_responses=[], sus_score=0.0),
        # tool group (uses PrivacyLens)
        StudyParticipant(participant_id="P006", age_group="18-24", education="undergrad",
            condition="tool", policy_tested="Google",
            comprehension_scores=[True, True, True, True, True, True, True, True, True, False],
            time_seconds=280, sus_responses=[4, 2, 4, 2, 4, 2, 4, 2, 4, 2], sus_score=0.0),
        StudyParticipant(participant_id="P007", age_group="25-34", education="postgrad",
            condition="tool", policy_tested="Google",
            comprehension_scores=[True, True, False, True, True, True, True, True, True, True],
            time_seconds=260, sus_responses=[5, 1, 5, 1, 5, 1, 5, 1, 5, 1], sus_score=0.0),
        StudyParticipant(participant_id="P008", age_group="18-24", education="secondary",
            condition="tool", policy_tested="Google",
            comprehension_scores=[True, True, True, True, False, True, True, True, True, True],
            time_seconds=310, sus_responses=[4, 2, 4, 1, 4, 2, 4, 2, 4, 2], sus_score=0.0),
        StudyParticipant(participant_id="P009", age_group="35-44", education="undergrad",
            condition="tool", policy_tested="Google",
            comprehension_scores=[True, True, True, True, True, True, True, True, True, False],
            time_seconds=295, sus_responses=[4, 2, 5, 2, 4, 1, 5, 2, 4, 2], sus_score=0.0),
        StudyParticipant(participant_id="P010", age_group="25-34", education="undergrad",
            condition="tool", policy_tested="Google",
            comprehension_scores=[True, True, True, True, True, True, False, True, True, True],
            time_seconds=270, sus_responses=[5, 2, 4, 2, 4, 2, 4, 1, 5, 2], sus_score=0.0),
    ]

    # Calculate SUS for tool group
    for p in demo:
        if p.sus_responses:
            p.sus_score = calculate_sus(p.sus_responses)

    # Write all
    out = _STUDY_DIR / "participants.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for p in demo:
            f.write(p.model_dump_json() + "\n")
    print(f"Demo participants seeded: {out}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SUS self-test:")
    # Perfect score: all 5s on odd, all 1s on even
    perfect = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]
    score = calculate_sus(perfect)
    print(f"  Perfect SUS: {score} -- {interpret_sus(score)}")

    # Worst score: all 1s on odd, all 5s on even
    worst = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]
    score = calculate_sus(worst)
    print(f"  Worst SUS  : {score} -- {interpret_sus(score)}")

    print(f"\n{len(GOOGLE_COMPREHENSION_QUESTIONS)} comprehension questions loaded for Google policy.")

    print("\nSeeding demo participants...")
    seed_demo_participants()

    print("\nAnalysing results...")
    results = analyse_results()
    if results:
        print(generate_results_table(results))
        export_for_spss()
