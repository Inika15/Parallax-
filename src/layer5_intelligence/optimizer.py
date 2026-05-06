"""
Layer 5 — Joint Platform × Time Optimizer
Issues: #6, #7, #8, #11

Evaluates ALL (platform × time_slot) combinations simultaneously
and selects the globally optimal recommendation.

Deterministic: identical input → identical output. Always.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..layer2_fusion.context import EngagementContext
from ..layer3_personalization.creator_dna import CreatorDNA
from ..layer4_scoring.scorer import compute_score, compute_score_with_breakdown
from ..layer4_scoring.weights import DEFAULT_WEIGHTS, ScoringWeights
from .affinity_matrix import get_content_platform_affinity

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """A single content posting recommendation."""
    content_id: str
    platform: str
    recommended_slot: int
    score: float
    confidence: str  # HIGH, MEDIUM, LOW
    breakdown: dict


def joint_optimize(
    content_id: str,
    creator_id: str,
    content_type: str,
    creator_dna: CreatorDNA,
    context: EngagementContext,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> Recommendation:
    """
    Joint platform × time optimization (Issue #8).
    
    Evaluates every (platform, slot) combination and returns the best one.
    A video at peak Instagram time might outscore the 'best' YouTube slot
    even if YouTube is the 'natural' fit. We test every combination.
    
    Tie-breaking (Issue #11):
    1. Highest score first
    2. Earlier time slot
    3. Alphabetically first platform name
    """
    candidates: List[Tuple[float, int, str, dict]] = []

    for platform in sorted(context.all_platforms):  # sorted for determinism
        content_fit = get_content_platform_affinity(content_type, platform)

        for slot in range(24):
            platform_activity = context.get_platform_activity(platform, slot)
            creator_history = context.get_creator_history(
                creator_id, platform, content_type, slot
            )
            creator_base = context.get_base_engagement(creator_id)

            breakdown = compute_score_with_breakdown(
                platform_activity=platform_activity,
                creator_history=creator_history,
                creator_base=creator_base,
                content_fit=content_fit,
                weights=weights,
            )
            score = breakdown["total_score"]

            # Tuple: (score, slot, platform, breakdown)
            candidates.append((score, slot, platform, breakdown))

    # Sort: highest score → earliest slot → alphabetical platform
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))

    best_score, best_slot, best_platform, best_breakdown = candidates[0]

    # Confidence based on data richness
    if creator_dna.data_richness >= 0.7:
        confidence = "HIGH"
    elif creator_dna.data_richness >= 0.3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return Recommendation(
        content_id=content_id,
        platform=best_platform,
        recommended_slot=best_slot,
        score=round(best_score, 2),
        confidence=confidence,
        breakdown=best_breakdown,
    )


def get_top_k_recommendations(
    content_id: str,
    creator_id: str,
    content_type: str,
    creator_dna: CreatorDNA,
    context: EngagementContext,
    k: int = 5,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> List[Recommendation]:
    """Get top K recommendations for counterfactual analysis."""
    candidates: List[Tuple[float, int, str, dict]] = []

    for platform in sorted(context.all_platforms):
        content_fit = get_content_platform_affinity(content_type, platform)
        for slot in range(24):
            pa = context.get_platform_activity(platform, slot)
            ch = context.get_creator_history(creator_id, platform, content_type, slot)
            cb = context.get_base_engagement(creator_id)
            bd = compute_score_with_breakdown(pa, ch, cb, content_fit, weights)
            candidates.append((bd["total_score"], slot, platform, bd))

    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))

    if creator_dna.data_richness >= 0.7:
        confidence = "HIGH"
    elif creator_dna.data_richness >= 0.3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    results = []
    for score, slot, platform, bd in candidates[:k]:
        results.append(Recommendation(
            content_id=content_id,
            platform=platform,
            recommended_slot=slot,
            score=round(score, 2),
            confidence=confidence,
            breakdown=bd,
        ))
    return results
