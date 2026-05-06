"""
Layer 5 — Scheduling Decision Engine
Issue #9: Implement Scheduling Decision Logic

Decides: POST_NOW vs SCHEDULE based on comparing current-slot score
against optimal-slot score, factoring in time_sensitivity.
"""

import logging

from ..layer2_fusion.context import EngagementContext
from ..layer4_scoring.scorer import compute_score
from ..layer4_scoring.weights import (
    DEFAULT_WEIGHTS, SCHEDULE_THRESHOLDS, NEAR_SLOT_HOURS, ScoringWeights,
)
from .affinity_matrix import get_content_platform_affinity

logger = logging.getLogger(__name__)


def decide_schedule(
    creator_id: str,
    content_type: str,
    submission_hour: int,
    best_platform: str,
    best_slot: int,
    best_score: float,
    time_sensitivity: str,
    context: EngagementContext,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> dict:
    """
    Decide whether to POST_NOW or SCHEDULE.
    
    Rules:
    1. If submission hour == best slot → POST_NOW
    2. If best slot is within NEAR_SLOT_HOURS → POST_NOW
    3. If optimal score < threshold × current score → POST_NOW
    4. Otherwise → SCHEDULE
    
    Returns dict with decision + explanation.
    """
    # Edge case: already at peak
    if submission_hour == best_slot:
        return {
            "decision": "POST_NOW",
            "reason": "Content submitted at optimal time slot",
            "current_slot_score": best_score,
            "optimal_slot_score": best_score,
            "threshold_met": False,
        }

    # Edge case: very close to optimal
    slot_diff = min(
        abs(best_slot - submission_hour),
        24 - abs(best_slot - submission_hour)  # wrap around midnight
    )
    if slot_diff <= NEAR_SLOT_HOURS:
        return {
            "decision": "POST_NOW",
            "reason": f"Optimal slot is only {slot_diff}h away — not worth waiting",
            "current_slot_score": best_score,
            "optimal_slot_score": best_score,
            "threshold_met": False,
        }

    # Compute current-slot score on the best platform
    content_fit = get_content_platform_affinity(content_type, best_platform)
    current_score = compute_score(
        platform_activity=context.get_platform_activity(best_platform, submission_hour),
        creator_history=context.get_creator_history(
            creator_id, best_platform, content_type, submission_hour
        ),
        creator_base=context.get_base_engagement(creator_id),
        content_fit=content_fit,
        weights=weights,
    )

    # Get threshold for this sensitivity level
    threshold = SCHEDULE_THRESHOLDS.get(time_sensitivity, 1.10)

    # Decision
    threshold_met = best_score >= current_score * threshold

    if threshold_met:
        decision = "SCHEDULE"
        reason = (
            f"Optimal score ({best_score:.1f}) exceeds current ({current_score:.1f}) "
            f"by threshold {threshold:.0%} — scheduling for slot {best_slot}"
        )
    else:
        decision = "POST_NOW"
        reason = (
            f"Improvement ({best_score:.1f} vs {current_score:.1f}) below "
            f"threshold {threshold:.0%} — posting immediately"
        )

    return {
        "decision": decision,
        "reason": reason,
        "current_slot_score": round(current_score, 2),
        "optimal_slot_score": round(best_score, 2),
        "threshold_met": threshold_met,
        "threshold": threshold,
        "time_sensitivity": time_sensitivity,
    }
