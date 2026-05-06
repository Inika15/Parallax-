"""
Layer 4 — Scoring Engine (MULTIPLICATIVE)
Issues: #5, #17, #18

Multiplicative scoring: a zero on ANY factor tanks the score.
This is correct because e.g. zero platform activity = don't post there.

Formula:
    SCORE = platform_activity^W1 × creator_history^W2 × base_engagement^W3 × content_affinity^W4 × SCALE

Why multiplicative (not additive):
    - Zero on any factor → zero score (correct: dead slot = no post)
    - Additive would let a strong creator compensate for a dead time slot — wrong
    - Weights act as elasticities (exponents), not linear coefficients
    - Product is scale-independent before SCALE_FACTOR

Scaled to 0–100.
"""

import logging
import math
from typing import Dict

from .weights import DEFAULT_WEIGHTS, MAX_SCORE, SCALE_FACTOR, ScoringWeights

logger = logging.getLogger(__name__)


def compute_score(
    platform_activity: float,
    creator_history: float,
    creator_base: float,
    content_fit: float,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Multiplicative scoring function.
    
    SCORE = (pa^w1 * ch^w2 * cb^w3 * cf^w4) * SCALE
    
    Edge cases (Issue #17):
    - Zero platform activity → score = 0.0 (never recommend dead slots)
    - Any factor <= 0 → score = 0.0
    - NaN/Inf → clipped to 0.0
    - Score capped at MAX_SCORE
    """
    # Dead slot / missing data guard
    if platform_activity <= 0.0 or creator_history <= 0.0 or creator_base <= 0.0 or content_fit <= 0.0:
        return 0.0

    # Multiplicative geometric scoring:
    # Each factor is raised to its weight power, then multiplied.
    # This ensures:
    # - Zero on any factor → zero score (correct: dead slot = no post)
    # - Weights act as elasticities, not linear coefficients
    # - e.g. PA=1.0^0.30 = 1.0, PA=0.6^0.30 ≈ 0.85 → modest penalty for off-peak
    # - e.g. CH=0.3^0.40 ≈ 0.60 → heavy penalty for poor creator history
    raw = (
        (platform_activity ** weights.w_platform_activity)
        * (creator_history ** weights.w_creator_history)
        * (creator_base ** weights.w_creator_base)
        * (content_fit ** weights.w_content_fit)
    )

    score = raw * SCALE_FACTOR

    # Sanity guards
    if math.isnan(score) or math.isinf(score):
        logger.warning(f"Invalid score detected: {score}. Clamping to 0.0")
        return 0.0

    return round(min(max(score, 0.0), MAX_SCORE), 2)


def compute_score_with_breakdown(
    platform_activity: float,
    creator_history: float,
    creator_base: float,
    content_fit: float,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> Dict:
    """
    Same as compute_score but returns a full breakdown for explainability.
    """
    score = compute_score(platform_activity, creator_history, creator_base, content_fit, weights)

    return {
        "total_score": score,
        "platform_activity_raw": platform_activity,
        "creator_history_raw": creator_history,
        "creator_base_raw": creator_base,
        "content_fit_raw": content_fit,
        "w_platform_contribution": round(platform_activity ** weights.w_platform_activity, 4),
        "w_history_contribution": round(creator_history ** weights.w_creator_history, 4),
        "w_base_contribution": round(creator_base ** weights.w_creator_base, 4),
        "w_fit_contribution": round(content_fit ** weights.w_content_fit, 4),
    }
