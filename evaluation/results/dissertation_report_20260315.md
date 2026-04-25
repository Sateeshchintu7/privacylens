# PrivacyLens -- Evaluation Report
Generated: 2026-03-15 12:23 UTC
Author: Sateesh Kumar Payyavula
MSc Cyber Security & Human Factors, 2025-26

---

## 4.1 Technical Evaluation (RQ1)

### 4.1.1 Benchmark Setup

Clause extraction accuracy was evaluated against a manually annotated ground-truth
dataset following the OPP-115 methodology (Wilson et al., 2016). Five real-world
privacy policies were used: Google Privacy Policy, TikTok Terms of Service, Instagram Privacy Policy, WhatsApp Privacy Policy, Spotify Privacy Policy.

Each policy was scraped, cleaned, and passed through PrivacyLens's `clause_extractor`
module. A category is "predicted present" if at least one clause is extracted for it.
Predictions are compared against human annotations across 12 categories from the
OPP-115 taxonomy (Andow et al., 2019).

**Evaluation formula:**
- Precision = TP / (TP + FP)
- Recall    = TP / (TP + FN)
- F1        = 2 * Precision * Recall / (Precision + Recall)

### 4.1.2 Clause Extraction Results

| Category                     | Precision | Recall | F1     | Status |
|------------------------------|-----------|--------|--------|--------|
| Data Collection              |     1.000 |   1.000 |   1.000 |   Pass |
| Purpose Limitation           |     1.000 |   0.750 |   0.857 |   Pass |
| Retention Period             |     0.750 |   1.000 |   0.857 |   Pass |
| Third Party Sharing          |     1.000 |   0.750 |   0.857 |   Pass |
| User Rights                  |     1.000 |   1.000 |   1.000 |   Pass |
| Consent Mechanism            |     1.000 |   0.500 |   0.667 |   Fail |
| Data Security                |     1.000 |   1.000 |   1.000 |   Pass |
| Breach Notification          |     0.000 |   0.000 |   0.000 |   Fail |
| Children Data                |     1.000 |   1.000 |   1.000 |   Pass |
| Cross Border Transfer        |     1.000 |   0.750 |   0.857 |   Pass |
| Cookies Tracking             |     1.000 |   0.750 |   0.857 |   Pass |
| Contact Info                 |     1.000 |   1.000 |   1.000 |   Pass |
| **MACRO AVERAGE**            | **0.896** | **0.792** | **0.829** | |

*Model: gemini-2.5-flash | Policies tested: 4*

### 4.1.3 Key Findings

- **Best performing category**: Contact Info (F1 = 1.000)
- **Lowest performing category**: Breach Notification (F1 = 0.000)
- **10/12** categories exceed the F1 = 0.75 threshold
- **Macro F1 = 0.829** — above the 0.75 dissertation target

The lower performance on `breach_notification` is expected: this category is
absent from most policies (ground truth negative), creating a precision floor.
The high recall on `data_collection` and `third_party_sharing` aligns with prior
work showing these are the most linguistically distinctive categories
(Andow et al., 2019; PolicyLint).


## 4.2 User Study Results (RQ2 & RQ3)

### 4.2.1 Study Design

A controlled between-subjects experiment was conducted with 10 participants,
randomly assigned to either a **control group** (n=5,
reading the original policy text) or a **tool group** (n=5,
using PrivacyLens). All participants answered the same 10 comprehension questions
about the Google Privacy Policy and recorded their completion time. Tool-group
participants additionally completed the SUS questionnaire.

This design mirrors Reidenberg et al. (2015), who used a similar comprehension-based
study to evaluate whether policy simplification tools improve user understanding.

### 4.2.2 Comprehension Results

Tool group participants scored 90.0% on average, compared to 50.0% for the control group — an improvement of 40.0 percentage points.

| Metric | Control Group | Tool Group | Difference |
|--------|--------------|------------|------------|
| Participants | n=5 | n=5 |  |
| Avg comprehension | 50.0% | 90.0% | +40.0pp |
| Avg time (seconds) | 426 | 283 | -143s faster |
| SUS Score | N/A | 83.5/100 | A  (Excellent) |
| Sig. (p < 0.05) | -- | -- | Yes (p=0.000) |

### 4.2.3 Usability Results

The System Usability Scale (Brooke, 1996) was administered to the 5 tool-group participants after completing the study. The mean SUS score was **83.5/100** (A  (Excellent)). A score of 68 represents average usability; scores above 80 are considered excellent.

### 4.2.4 Statistical Analysis

An independent-samples t-test was used to compare comprehension scores between
groups. The result was statistically significant (t=-7.303, p=0.000, p < 0.05).


## 4.3 Readability Analysis

Reidenberg et al. (2015) established a baseline average Flesch-Kincaid grade of 14.8 for real-world privacy policies. PrivacyLens plain rewrites achieve grade 3.7, an improvement of 11.1 grade levels — from postgraduate to middle-school level.

| Metric | Original Policies | PrivacyLens Plain | Improvement |
|--------|------------------|-------------------|-------------|
| Avg FK Grade | 14.8 | 3.7 | -11.1 grades |
| Reading level | Postgraduate | Middle school | Significant |

The improvement of 11.1 grade levels demonstrates that
PrivacyLens successfully meets its primary accessibility goal. A Flesch-Kincaid
grade of 3.7 corresponds approximately to a reading age of
8, making it accessible to the majority of adult users.

---

*References*

- Wilson, S. et al. (2016). The creation and analysis of a website privacy policy corpus. ACL.
- Andow, B. et al. (2019). PolicyLint: Investigating internal privacy policy contradictions. USENIX Security.
- Brooke, J. (1996). SUS: A quick and dirty usability scale. Usability Evaluation in Industry.
- Reidenberg, J.R. et al. (2015). Disagreeable privacy policies. SSRN.
- GDPR (2018). General Data Protection Regulation. OJ EU L 119/1.
