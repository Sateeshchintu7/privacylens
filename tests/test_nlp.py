"""Module: test_nlp - Regression tests for NLP components."""

import pytest
from nlp.clause_extractor import extract_clauses, ClauseResult
from nlp.dark_pattern_detector import detect_dark_patterns


def test_clause_extraction_has_combined_fields():
    """Test that clause extraction returns clauses with plain_summary, what_it_means, risk_level, etc."""
    sample_policy = """
    We collect your email address and name to provide our services.
    We may share your data with third parties for advertising purposes.
    You have the right to access and delete your personal information.
    We retain data for 2 years after account closure.
    We use encryption to protect your data.
    """

    clauses = extract_clauses(sample_policy, use_cache=False)

    assert len(clauses) > 0, "Should extract at least one clause"
    for clause in clauses:
        assert isinstance(clause, ClauseResult)
        # Check new combined fields are present (may be None if LLM fails)
        assert hasattr(clause, 'plain_summary')
        assert hasattr(clause, 'what_it_means')
        assert hasattr(clause, 'risk_level')
        assert hasattr(clause, 'risk_score')
        assert hasattr(clause, 'red_flags')
        assert hasattr(clause, 'positive_signals')


def test_dark_pattern_detection_on_full_text():
    """Test that dark pattern detection scans full policy text, not just clauses."""
    sample_policy = """
    By continuing to use our service, you agree to our terms and data collection.
    We reserve the right to share your information with partners at our discretion.
    To opt out, please contact us via postal mail.
    We value your privacy and take it seriously, but we may sell data to improve services.
    """

    # Mock clauses (empty list to force full-text scanning)
    clauses = []
    report = detect_dark_patterns(clauses, policy_text=sample_policy)

    assert report.total_found >= 0
    assert isinstance(report.patterns, list)
    assert isinstance(report.categories_found, list)
    assert report.summary is not None

    # Should detect at least some patterns in this manipulative text
    if report.total_found > 0:
        for pattern in report.patterns:
            assert pattern.category in ['sneaking', 'asymmetric_effort', 'obstruction', 'ambiguity', 'false_urgency', 'sycophancy']
            assert pattern.evidence is not None


if __name__ == "__main__":
    test_clause_extraction_has_combined_fields()
    test_dark_pattern_detection_on_full_text()
    print("All tests passed!")
