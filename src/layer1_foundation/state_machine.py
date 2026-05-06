"""
Layer 1 — Content State Machine (perfect.md Layer 1)
Postiz pattern: DRAFT → QUEUE → PUBLISHED | ERROR

Every content item transitions through explicit states.
Errors get fallback recommendations. Coverage stays 100/100.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class ContentState(Enum):
    PENDING   = "PENDING"     # loaded from CSV, not yet optimized
    OPTIMIZED = "OPTIMIZED"   # optimizer ran, recommendation ready
    SCHEDULED = "SCHEDULED"   # decision = SCHEDULE
    COMPLETE  = "COMPLETE"    # decision = POST_NOW
    ERROR     = "ERROR"       # optimizer failed, fallback used


@dataclass
class StatefulContent:
    """Content item with explicit lifecycle tracking."""
    content_id: int
    creator_id: str
    content_type: str
    created_timestamp: int
    time_sensitivity: str
    state: ContentState = ContentState.PENDING
    recommendation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def transition(self, new_state: ContentState):
        """Explicit state transition — mirrors Postiz's changeState()."""
        valid_transitions = {
            ContentState.PENDING:   {ContentState.OPTIMIZED, ContentState.ERROR},
            ContentState.OPTIMIZED: {ContentState.SCHEDULED, ContentState.COMPLETE},
            ContentState.ERROR:     {ContentState.OPTIMIZED},  # retry allowed
        }
        allowed = valid_transitions.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid state transition: {self.state.value} → {new_state.value} "
                f"for content #{self.content_id}"
            )
        self.state = new_state


# Fallback recommendations for ERROR state items (Layer 10)
FALLBACK_RECOMMENDATIONS = {
    "SHORT": ("Instagram", 18),   # Instagram peak for SHORT
    "LONG":  ("YouTube", 20),     # YouTube peak for LONG
}


def generate_fallback_recommendation(item: StatefulContent) -> Dict[str, Any]:
    """Last-resort recommendation — guarantees 100/100 coverage."""
    platform, slot = FALLBACK_RECOMMENDATIONS.get(
        item.content_type, ("Instagram", 18)
    )
    return {
        "content_id":       int(item.content_id),
        "platform":         platform,
        "recommended_slot": slot,
        "decision":         "SCHEDULE",
        "score":            0.0,
        "confidence":       "LOW",
        "explanation":      {"fallback": True, "reason": item.error or "Unknown error"},
    }
