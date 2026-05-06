"""
Layer 5 — Creator Momentum Score (perfect.md Layer 17)
Postiz pattern: streakSince engagement consistency tracking.

Momentum = how consistently strong a creator's engagement is.
High momentum (low CoV) = reliable predictions.
Low momentum (high CoV) = volatile, spiky engagement.
"""

import logging
from typing import Dict

from ..layer2_fusion.context import EngagementContext

logger = logging.getLogger(__name__)


def compute_momentum_score(
    creator_id: str,
    context: EngagementContext,
) -> float:
    """
    Compute engagement consistency score (0.0–1.0).
    1.0 = perfectly consistent, lower = more volatile.
    """
    all_scores = []
    for platform in sorted(context.all_platforms):
        for content_type in sorted(context.all_content_types):
            for slot in range(24):
                score = context.get_creator_history(
                    creator_id, platform, content_type, slot
                )
                if score > 0:
                    all_scores.append(score)

    if len(all_scores) < 2:
        return 0.5  # insufficient data

    mean_score = sum(all_scores) / len(all_scores)
    if mean_score <= 0:
        return 0.0

    variance = sum((s - mean_score) ** 2 for s in all_scores) / len(all_scores)
    std_dev = variance ** 0.5
    cov = std_dev / mean_score  # coefficient of variation

    momentum = max(0.0, min(1.0, 1.0 - cov))
    return round(momentum, 3)


def compute_all_momentum_scores(
    context: EngagementContext,
) -> Dict[str, float]:
    """Compute momentum for all creators at startup."""
    scores = {}
    for creator_id in context.creators:
        scores[creator_id] = compute_momentum_score(creator_id, context)

    avg = sum(scores.values()) / max(len(scores), 1)
    logger.info(
        f"Momentum scores: avg={avg:.3f}, "
        f"min={min(scores.values()):.3f}, "
        f"max={max(scores.values()):.3f}"
    )
    return scores


def compute_engagement_trajectory(
    creator_id: str,
    platform: str,
    context: EngagementContext,
) -> Dict:
    """
    Engagement trajectory (perfect.md Layer 12).
    Early day (0-11) vs late day (12-23) — detect evening/morning peaks.
    """
    early_scores = []
    late_scores = []

    for ct in sorted(context.all_content_types):
        for slot in range(12):
            s = context.get_creator_history(creator_id, platform, ct, slot)
            if s > 0:
                early_scores.append(s)
        for slot in range(12, 24):
            s = context.get_creator_history(creator_id, platform, ct, slot)
            if s > 0:
                late_scores.append(s)

    early_avg = sum(early_scores) / max(len(early_scores), 1)
    late_avg = sum(late_scores) / max(len(late_scores), 1)

    trajectory_factor = late_avg / early_avg if early_avg > 0 else 1.0

    return {
        "early_day_avg": round(early_avg, 3),
        "late_day_avg": round(late_avg, 3),
        "trajectory_factor": round(trajectory_factor, 3),
        "trend": (
            "EVENING_PEAK" if trajectory_factor > 1.1
            else "MORNING_PEAK" if trajectory_factor < 0.9
            else "FLAT"
        ),
    }
