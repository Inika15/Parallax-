"""
Layer 4 — Configurable Weights
Issue #5: Design Recommendation Scoring Function

All scoring weights and thresholds live here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    """Weights for the multi-variable engagement scoring function."""
    w_platform_activity: float = 0.30
    w_creator_history: float = 0.40
    w_creator_base: float = 0.15
    w_content_fit: float = 0.15

    def validate(self) -> bool:
        total = (self.w_platform_activity + self.w_creator_history
                 + self.w_creator_base + self.w_content_fit)
        return abs(total - 1.0) < 1e-6


MAX_SCORE = 100.0
SCALE_FACTOR = 88.0  # Tuned so top items score ~95, not all 100

SCHEDULE_THRESHOLDS = {
    "High": 1.05,
    "Medium": 1.10,
    "Low": 1.20,
}

NEAR_SLOT_HOURS = 1

DEFAULT_WEIGHTS = ScoringWeights()
assert DEFAULT_WEIGHTS.validate(), "Scoring weights must sum to 1.0"
