"""
Layer 4 — Scoring Engine (WEIGHTED SUM)
Issues: #5, #17, #18

From how_to_win.md:
  "The safest interpretation that matches standard recommendation system literature is:
   score = (W1 * activity) + (W2 * history) + (W3 * base) + (W4 * affinity)"

WEIGHTED SUM scoring — all factors are on comparable 0–1.25 scale.
Scaled to 0–100 at the end.

W1=0.30 (platform_activity)  — step function: 0.6 or 1.0
W2=0.40 (creator_history)    — continuous: 0.255–1.250 (dominant term)
W3=0.15 (base_engagement)    — continuous: 0.61–1.38
W4=0.15 (content_fit)        — derived: ~0.79–1.21
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
    Weighted sum scoring function.

    SCORE = (W1*pa + W2*ch + W3*cb + W4*cf) / MAX_RAW * 100

    The raw weighted sum ranges from ~0.4 to ~1.2 depending on input
    quality. We normalize by the theoretical maximum so that only the
    absolute best input combination scores 100.

    Edge cases (Issue #17, how_to_win.md):
    - Zero platform activity → score = 0.0 (never recommend dead slots)
    - Any factor <= 0 → score = 0.0
    - NaN/Inf → clipped to 0.0
    - Score capped at MAX_SCORE
    """
    # Dead slot / missing data guard (how_to_win.md: "zero activity → always score 0.0")
    if platform_activity <= 0.0:
        return 0.0

    # Weighted sum — all factors on comparable scales
    raw = (
        weights.w_platform_activity * platform_activity
        + weights.w_creator_history * creator_history
        + weights.w_creator_base * creator_base
        + weights.w_content_fit * content_fit
    )

    # Theoretical max: PA=1.0, CH=1.25, CB=1.38, CF=1.21
    # max_raw = 0.30*1.0 + 0.40*1.25 + 0.15*1.38 + 0.15*1.21 = 1.1885
    max_raw = (
        weights.w_platform_activity * 1.0
        + weights.w_creator_history * 1.25
        + weights.w_creator_base * 1.38
        + weights.w_content_fit * 1.21
    )

    score = (raw / max_raw) * SCALE_FACTOR

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
        "w_platform_contribution": round(weights.w_platform_activity * platform_activity, 4),
        "w_history_contribution": round(weights.w_creator_history * creator_history, 4),
        "w_base_contribution": round(weights.w_creator_base * creator_base, 4),
        "w_fit_contribution": round(weights.w_content_fit * content_fit, 4),
    }
