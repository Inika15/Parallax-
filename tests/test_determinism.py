"""
Test Determinism — Issue #11
============================
Run the full optimizer pipeline twice on identical input.
Assert byte-identical output. This proves the system has zero
non-deterministic behavior (no random, uuid, or time-based logic).
"""

import json
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
from src.layer5_intelligence.optimizer import joint_optimize
from src.layer5_intelligence.scheduler import decide_schedule
from src.layer6_output.output_formatter import format_recommendation


DATA_DIR = os.path.join(ROOT, "data", "raw")


def _run_full_pipeline():
    """Run the complete pipeline and return sorted recommendation list."""
    content = load_content_submissions(os.path.join(DATA_DIR, "content.csv"))
    activity = load_platform_activity(os.path.join(DATA_DIR, "platform_activity.csv"))
    history = load_historical_engagement(os.path.join(DATA_DIR, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(DATA_DIR, "creators.csv"))
    fallback = FallbackRegistry()

    context = EngagementContext(
        content=content, platform_activity=activity,
        creator_history=history, creators=creators, fallback=fallback,
    )

    global_type_avg = compute_global_type_averages(history, context.all_content_types)
    global_peak_slots = compute_global_peak_slots(history, context.all_platforms)

    dna_profiles = {}
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
        dna_profiles[cid] = dna

    recommendations = []
    for item_id in sorted(content.keys(), key=lambda x: int(x)):
        item = content[item_id]
        dna = dna_profiles.get(item.creator_id)
        if not dna:
            dna = build_cold_start_profile(
                item.creator_id, 1.0, 4,
                context.all_platforms, context.all_content_types,
                global_type_avg, global_peak_slots,
            )

        best = joint_optimize(
            item.content_id, item.creator_id, item.content_type, dna, context,
        )
        sched = decide_schedule(
            item.creator_id, item.content_type, item.created_timestamp,
            best.platform, best.recommended_slot, best.score,
            item.time_sensitivity, context,
        )

        rec = format_recommendation(
            content_id=item.content_id,
            platform=best.platform,
            recommended_slot=best.recommended_slot,
            decision=sched["decision"],
            score=best.score,
            confidence=best.confidence,
            explanation={
                "platform_activity": best.breakdown["platform_activity_raw"],
                "creator_history_score": best.breakdown["creator_history_raw"],
                "creator_base": best.breakdown["creator_base_raw"],
                "content_fit": best.breakdown["content_fit_raw"],
                "current_slot_score": sched["current_slot_score"],
                "optimal_slot_score": sched["optimal_slot_score"],
                "schedule_threshold_met": sched["threshold_met"],
            },
        )
        recommendations.append(rec)

    return recommendations


def test_determinism():
    """Run the pipeline twice — output must be byte-identical."""
    run1 = _run_full_pipeline()
    run2 = _run_full_pipeline()

    json1 = json.dumps(run1, sort_keys=True)
    json2 = json.dumps(run2, sort_keys=True)

    assert json1 == json2, "Pipeline is NOT deterministic — outputs differ between runs!"


def test_recommendation_count():
    """Every content item must produce exactly one recommendation."""
    recs = _run_full_pipeline()
    content = load_content_submissions(os.path.join(DATA_DIR, "content.csv"))
    assert len(recs) == len(content), f"Expected {len(content)} recs, got {len(recs)}"


def test_valid_platforms():
    """All recommendations must use valid platform names."""
    recs = _run_full_pipeline()
    for r in recs:
        assert r["platform"] in {"Instagram", "YouTube"}, f"Invalid platform: {r['platform']}"


def test_valid_decisions():
    """All decisions must be POST_NOW or SCHEDULE."""
    recs = _run_full_pipeline()
    for r in recs:
        assert r["decision"] in {"POST_NOW", "SCHEDULE"}, f"Invalid decision: {r['decision']}"


def test_valid_slots():
    """All recommended slots must be in [0, 23]."""
    recs = _run_full_pipeline()
    for r in recs:
        assert 0 <= r["recommended_slot"] <= 23, f"Invalid slot: {r['recommended_slot']}"
