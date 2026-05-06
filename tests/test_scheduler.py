"""
Test Scheduling Decision Engine — Issue #9
============================================
Tests POST_NOW vs SCHEDULE decision logic including
time sensitivity adjustment and edge cases.
"""

import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.layer1_foundation.data_loader import (
    load_content_submissions, load_platform_activity,
    load_historical_engagement, load_creator_profiles,
)
from src.layer1_foundation.fallback_registry import FallbackRegistry
from src.layer2_fusion.context import EngagementContext
from src.layer5_intelligence.scheduler import decide_schedule
from src.layer4_scoring.weights import SCHEDULE_THRESHOLDS, NEAR_SLOT_HOURS


DATA_DIR = os.path.join(ROOT, "data", "raw")


@pytest.fixture
def context():
    content = load_content_submissions(os.path.join(DATA_DIR, "content.csv"))
    activity = load_platform_activity(os.path.join(DATA_DIR, "platform_activity.csv"))
    history = load_historical_engagement(os.path.join(DATA_DIR, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(DATA_DIR, "creators.csv"))
    fallback = FallbackRegistry()
    return EngagementContext(
        content=content, platform_activity=activity,
        creator_history=history, creators=creators, fallback=fallback,
    )


class TestSchedulerEdgeCases:
    """Test edge cases in the scheduling decision."""

    def test_submission_at_optimal_slot_gives_post_now(self, context):
        """Content submitted at the optimal slot → POST_NOW always."""
        result = decide_schedule(
            creator_id="1", content_type="SHORT", submission_hour=18,
            best_platform="Instagram", best_slot=18, best_score=85.0,
            time_sensitivity="Medium", context=context,
        )
        assert result["decision"] == "POST_NOW"
        assert "optimal time" in result["reason"].lower() or result["current_slot_score"] == result["optimal_slot_score"]

    def test_near_slot_gives_post_now(self, context):
        """Optimal slot within 1 hour → POST_NOW (not worth waiting)."""
        result = decide_schedule(
            creator_id="1", content_type="SHORT", submission_hour=17,
            best_platform="Instagram", best_slot=18, best_score=85.0,
            time_sensitivity="Medium", context=context,
        )
        assert result["decision"] == "POST_NOW"

    def test_midnight_wrap_near_slot(self, context):
        """Near-slot check should handle midnight wrapping (23 → 0)."""
        result = decide_schedule(
            creator_id="1", content_type="SHORT", submission_hour=23,
            best_platform="Instagram", best_slot=0, best_score=85.0,
            time_sensitivity="Medium", context=context,
        )
        assert result["decision"] == "POST_NOW"

    def test_schedule_decision_has_required_keys(self, context):
        """Schedule result must contain all required keys."""
        result = decide_schedule(
            creator_id="1", content_type="SHORT", submission_hour=6,
            best_platform="Instagram", best_slot=20, best_score=85.0,
            time_sensitivity="Medium", context=context,
        )
        required = {"decision", "reason", "current_slot_score", "optimal_slot_score", "threshold_met"}
        assert required.issubset(result.keys())

    def test_valid_decisions_only(self, context):
        """Decision must be either POST_NOW or SCHEDULE."""
        result = decide_schedule(
            creator_id="1", content_type="SHORT", submission_hour=6,
            best_platform="Instagram", best_slot=20, best_score=85.0,
            time_sensitivity="Medium", context=context,
        )
        assert result["decision"] in {"POST_NOW", "SCHEDULE"}


class TestTimeSensitivity:
    """Test that time sensitivity adjusts thresholds."""

    def test_high_sensitivity_has_lower_threshold(self):
        """High sensitivity should use a lower threshold (easier to schedule)."""
        assert SCHEDULE_THRESHOLDS["High"] < SCHEDULE_THRESHOLDS["Medium"]

    def test_low_sensitivity_has_higher_threshold(self):
        """Low sensitivity should use a higher threshold (harder to schedule)."""
        assert SCHEDULE_THRESHOLDS["Low"] > SCHEDULE_THRESHOLDS["Medium"]

    def test_threshold_values(self):
        """Verify expected threshold values."""
        assert SCHEDULE_THRESHOLDS["High"] == 1.05
        assert SCHEDULE_THRESHOLDS["Medium"] == 1.10
        assert SCHEDULE_THRESHOLDS["Low"] == 1.20
