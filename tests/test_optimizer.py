"""
Test Joint Optimizer — Issues #6, #7, #8, #11
===============================================
Tests the joint platform × time optimizer for correctness,
tie-breaking, and platform selection quality.
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
from src.layer3_personalization.creator_dna import build_creator_dna
from src.layer3_personalization.cold_start import (
    build_cold_start_profile, compute_global_type_averages,
    compute_global_peak_slots, is_cold_start,
)
from src.layer5_intelligence.optimizer import joint_optimize, get_top_k_recommendations


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


@pytest.fixture
def dna_profiles(context):
    content = load_content_submissions(os.path.join(DATA_DIR, "content.csv"))
    history = load_historical_engagement(os.path.join(DATA_DIR, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(DATA_DIR, "creators.csv"))
    global_type_avg = compute_global_type_averages(history, context.all_content_types)
    global_peak_slots = compute_global_peak_slots(history, context.all_platforms)

    profiles = {}
    for cid, profile in creators.items():
        dna = build_creator_dna(
            cid, profile.base_engagement, profile.cooldown_hours,
            history, context.all_platforms, context.all_content_types,
            context.system_average,
        )
        if is_cold_start(dna):
            dna = build_cold_start_profile(
                cid, profile.base_engagement, profile.cooldown_hours,
                context.all_platforms, context.all_content_types,
                global_type_avg, global_peak_slots,
            )
        profiles[cid] = dna
    return profiles


class TestJointOptimizer:
    """Test the joint platform × time optimizer."""

    def test_returns_valid_recommendation(self, context, dna_profiles):
        """Optimizer must return a valid Recommendation object."""
        dna = dna_profiles["1"]
        rec = joint_optimize("1", "1", "SHORT", dna, context)
        assert rec.platform in {"Instagram", "YouTube"}
        assert 0 <= rec.recommended_slot <= 23
        assert rec.score > 0
        assert rec.confidence in {"HIGH", "MEDIUM", "LOW"}

    def test_short_content_prefers_instagram(self, context, dna_profiles):
        """SHORT content should generally prefer Instagram (higher affinity)."""
        ig_count = 0
        yt_count = 0
        for cid in list(dna_profiles.keys())[:10]:
            dna = dna_profiles[cid]
            rec = joint_optimize(f"test_{cid}", cid, "SHORT", dna, context)
            if rec.platform == "Instagram":
                ig_count += 1
            else:
                yt_count += 1
        # SHORT → Instagram should be the majority
        assert ig_count > yt_count, f"Expected Instagram majority for SHORT, got IG={ig_count} YT={yt_count}"

    def test_long_content_prefers_youtube(self, context, dna_profiles):
        """LONG content should generally prefer YouTube (higher affinity)."""
        ig_count = 0
        yt_count = 0
        for cid in list(dna_profiles.keys())[:10]:
            dna = dna_profiles[cid]
            rec = joint_optimize(f"test_{cid}", cid, "LONG", dna, context)
            if rec.platform == "YouTube":
                yt_count += 1
            else:
                ig_count += 1
        assert yt_count > ig_count, f"Expected YouTube majority for LONG, got IG={ig_count} YT={yt_count}"

    def test_deterministic_same_inputs(self, context, dna_profiles):
        """Same inputs must produce identical output (Issue #11)."""
        dna = dna_profiles["1"]
        rec1 = joint_optimize("1", "1", "SHORT", dna, context)
        rec2 = joint_optimize("1", "1", "SHORT", dna, context)
        assert rec1.platform == rec2.platform
        assert rec1.recommended_slot == rec2.recommended_slot
        assert rec1.score == rec2.score

    def test_optimal_score_is_best(self, context, dna_profiles):
        """The optimizer's chosen score must be >= all other candidates."""
        dna = dna_profiles["1"]
        top_all = get_top_k_recommendations("1", "1", "SHORT", dna, context, k=48)
        best = top_all[0]
        for rec in top_all[1:]:
            assert best.score >= rec.score


class TestTopKRecommendations:
    """Test the top-K recommendation retrieval."""

    def test_returns_correct_count(self, context, dna_profiles):
        """top_k must return exactly k results (or all 48 if k > 48)."""
        dna = dna_profiles["1"]
        top5 = get_top_k_recommendations("1", "1", "SHORT", dna, context, k=5)
        assert len(top5) == 5

    def test_sorted_descending(self, context, dna_profiles):
        """Results must be sorted by score descending."""
        dna = dna_profiles["1"]
        top10 = get_top_k_recommendations("1", "1", "SHORT", dna, context, k=10)
        for i in range(len(top10) - 1):
            assert top10[i].score >= top10[i + 1].score

    def test_all_48_candidates(self, context, dna_profiles):
        """Requesting 48 should return all platform × slot combinations."""
        dna = dna_profiles["1"]
        all48 = get_top_k_recommendations("1", "1", "SHORT", dna, context, k=48)
        assert len(all48) == 48
