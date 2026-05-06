"""
Test Scoring Engine — Issues #5, #17
=====================================
Tests the weighted sum scoring function for correct behavior,
edge cases, and boundary conditions.
"""

import math
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.layer4_scoring.scorer import compute_score, compute_score_with_breakdown
from src.layer4_scoring.weights import DEFAULT_WEIGHTS, MAX_SCORE, SCALE_FACTOR, ScoringWeights


class TestComputeScore:
    """Test the core scoring function."""

    def test_all_ones_gives_max_scale(self):
        """All factors = 1.0 should produce SCALE_FACTOR (100.0)."""
        score = compute_score(1.0, 1.0, 1.0, 1.0)
        assert score == SCALE_FACTOR

    def test_zero_platform_activity_gives_zero(self):
        """Zero platform activity → score must be 0.0 (dead slot)."""
        score = compute_score(0.0, 0.8, 1.2, 1.0)
        assert score == 0.0

    def test_score_capped_at_max(self):
        """Even with very high factors, score never exceeds MAX_SCORE."""
        score = compute_score(10.0, 10.0, 10.0, 10.0)
        assert score <= MAX_SCORE

    def test_score_is_positive_for_positive_inputs(self):
        """All positive inputs → score must be > 0."""
        score = compute_score(0.5, 0.3, 0.8, 0.7)
        assert score > 0

    def test_higher_inputs_give_higher_score(self):
        """Increasing any factor should increase the score."""
        base = compute_score(0.6, 0.5, 1.0, 1.0)
        higher_pa = compute_score(1.0, 0.5, 1.0, 1.0)
        higher_ch = compute_score(0.6, 1.0, 1.0, 1.0)
        assert higher_pa > base
        assert higher_ch > base

    def test_score_is_rounded(self):
        """Score should be rounded to 2 decimal places."""
        score = compute_score(0.6, 0.55, 0.99, 0.82)
        assert score == round(score, 2)

    def test_typical_values(self):
        """Typical dataset values should produce a reasonable score."""
        score = compute_score(1.0, 0.83, 1.11, 1.0)
        assert 0 < score <= MAX_SCORE

    def test_nan_inf_clamped(self):
        """NaN/Inf inputs should be handled gracefully."""
        # The scorer should handle edge cases without crashing
        score = compute_score(float('inf'), 1.0, 1.0, 1.0)
        assert score <= MAX_SCORE or score == 0.0


class TestScoreBreakdown:
    """Test the breakdown variant of the scorer."""

    def test_breakdown_has_all_keys(self):
        """Breakdown must contain all required keys."""
        bd = compute_score_with_breakdown(0.8, 0.7, 1.0, 0.9)
        required = {
            "total_score", "platform_activity_raw", "creator_history_raw",
            "creator_base_raw", "content_fit_raw",
            "w_platform_contribution", "w_history_contribution",
            "w_base_contribution", "w_fit_contribution",
        }
        assert required.issubset(bd.keys())

    def test_breakdown_total_matches_compute(self):
        """Breakdown total_score must match compute_score."""
        args = (0.8, 0.7, 1.0, 0.9)
        bd = compute_score_with_breakdown(*args)
        score = compute_score(*args)
        assert bd["total_score"] == score

    def test_breakdown_raw_values_preserved(self):
        """Raw values in breakdown must match inputs."""
        bd = compute_score_with_breakdown(0.6, 0.55, 1.1, 0.82)
        assert bd["platform_activity_raw"] == 0.6
        assert bd["creator_history_raw"] == 0.55
        assert bd["creator_base_raw"] == 1.1
        assert bd["content_fit_raw"] == 0.82


class TestWeights:
    """Test scoring weight configuration."""

    def test_default_weights_sum_to_one(self):
        """Default weights must sum to 1.0."""
        assert DEFAULT_WEIGHTS.validate()

    def test_custom_weights_validation(self):
        """Custom weights that don't sum to 1.0 must fail validation."""
        bad = ScoringWeights(w_platform_activity=0.5, w_creator_history=0.5,
                             w_creator_base=0.5, w_content_fit=0.5)
        assert not bad.validate()

    def test_custom_weights_valid(self):
        """Custom weights that sum to 1.0 must pass validation."""
        good = ScoringWeights(w_platform_activity=0.25, w_creator_history=0.25,
                              w_creator_base=0.25, w_content_fit=0.25)
        assert good.validate()
