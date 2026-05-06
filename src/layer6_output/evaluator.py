"""
Layer 6 — Evaluation Metrics
Issue #18: Implement Evaluation Metrics Calculation

Computes engagement score, timing effectiveness, platform selection quality,
and efficiency score for the recommendation set.
"""

import logging
from typing import Any, Dict, List

from ..layer5_intelligence.affinity_matrix import get_content_platform_affinity

logger = logging.getLogger(__name__)


def compute_eval_metrics(
    recommendations: List[Dict[str, Any]],
    context,
) -> Dict[str, float]:
    """
    Compute all 4 evaluation axes + composite score.
    """
    if not recommendations:
        return {
            "engagement_score": 0.0,
            "timing_effectiveness": 0.0,
            "platform_quality": 0.0,
            "efficiency_score": 0.0,
            "composite_score": 0.0,
        }

    engagement = _compute_engagement(recommendations)
    timing = _compute_timing(recommendations, context)
    platform_q = _compute_platform_quality(recommendations, context)
    efficiency = _compute_efficiency(recommendations)

    # Composite: equal weights across all 4 axes
    composite = (engagement + timing + platform_q + efficiency) / 4.0

    return {
        "engagement_score": round(engagement, 4),
        "timing_effectiveness": round(timing, 4),
        "platform_quality": round(platform_q, 4),
        "efficiency_score": round(efficiency, 4),
        "composite_score": round(composite, 4),
    }


def _compute_engagement(recs: List[Dict]) -> float:
    """Average score across all recommendations, normalized to 0-1."""
    scores = [r["score"] for r in recs if "score" in r]
    if not scores:
        return 0.0
    return sum(scores) / (len(scores) * 100.0)  # Normalize from 0-100 to 0-1


def _compute_timing(recs: List[Dict], context) -> float:
    """
    How well do recommended slots align with platform peak activity?
    Ratio of recommended slot activity vs peak slot activity.
    """
    ratios = []
    for r in recs:
        platform = r.get("platform", "")
        slot = r.get("recommended_slot", 0)
        rec_activity = context.get_platform_activity(platform, slot)

        # Find peak activity for this platform
        peak_activity = max(
            context.get_platform_activity(platform, s)
            for s in range(24)
        )
        if peak_activity > 0:
            ratios.append(rec_activity / peak_activity)
        else:
            ratios.append(0.0)

    return sum(ratios) / len(ratios) if ratios else 0.0


def _compute_platform_quality(recs: List[Dict], context) -> float:
    """
    How well does the chosen platform match the content type?
    Based on the affinity matrix.
    """
    affinities = []
    for r in recs:
        content_item = context.get_content_item(r.get("content_id", ""))
        if content_item:
            affinity = get_content_platform_affinity(
                content_item.content_type, r.get("platform", "")
            )
            # Normalize: 1.4 is max affinity → scale to 0-1
            affinities.append(min(affinity / 1.4, 1.0))
        else:
            affinities.append(0.5)

    return sum(affinities) / len(affinities) if affinities else 0.0


def _compute_efficiency(recs: List[Dict]) -> float:
    """
    Efficiency: how well does the system choose between POST_NOW and SCHEDULE?
    - SCHEDULE is efficient if the gain is meaningful (>5% improvement)
    - POST_NOW is efficient if we're already close to optimal (>=90%)
    """
    if not recs:
        return 0.0

    efficient_count = 0
    for r in recs:
        explanation = r.get("explanation", {})
        decision = r.get("decision", "POST_NOW")
        current = explanation.get("current_slot_score", 0)
        optimal = explanation.get("optimal_slot_score", 0)

        if decision == "SCHEDULE":
            # Efficient if the gain is meaningful (at least 5% real improvement)
            if optimal > current * 1.05:
                efficient_count += 1
        elif decision == "POST_NOW":
            # POST_NOW is efficient if current slot is already near-optimal
            if optimal > 0 and current / optimal >= 0.9:
                efficient_count += 1

    return efficient_count / len(recs)
