"""
Layer 5 — Cooldown-Aware Batch Scheduler (perfect.md Layers 2, 4, 5)
Postiz pattern: TERMINATE_EXISTING conflict policy — no double-scheduling.

CreatorScheduleLock prevents cooldown violations.
Batch processing groups items by creator, processes HIGH sensitivity first.
Algorithm-aware sensitivity routing (from PS4 research doc).
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from ..layer2_fusion.context import EngagementContext
from ..layer3_personalization.creator_dna import CreatorDNA
from ..layer4_scoring.scorer import compute_score
from ..layer4_scoring.weights import DEFAULT_WEIGHTS, ScoringWeights
from ..layer4_scoring.sensitivity_risk import (
    compute_sensitivity_risk,
    compute_first_hour_velocity_bonus,
    get_sensitivity_routing_label,
)
from .affinity_matrix import get_content_platform_affinity

logger = logging.getLogger(__name__)

SENSITIVITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


@dataclass
class CreatorScheduleLock:
    """Per-creator slot reservation — prevents cooldown violations."""
    creator_id: str
    cooldown_hours: int
    reserved_slots: List[int] = field(default_factory=list)

    def is_slot_available(self, slot: int) -> bool:
        for reserved in self.reserved_slots:
            if abs(slot - reserved) < self.cooldown_hours:
                return False
        return True

    def reserve(self, slot: int):
        self.reserved_slots.append(slot)

    def available_count(self) -> int:
        return sum(1 for s in range(24) if self.is_slot_available(s))


def group_by_creator(content_items: list) -> Dict[str, list]:
    """
    Group content by creator for batch processing.
    Within each group: HIGH sensitivity first, then by submission hour.
    """
    groups = defaultdict(list)
    for item in content_items:
        groups[item.creator_id].append(item)

    # Sort within each group
    for creator_id in groups:
        groups[creator_id].sort(key=lambda x: (
            SENSITIVITY_ORDER.get(x.time_sensitivity, 1),
            x.created_timestamp,
        ))

    return dict(groups)


def joint_optimize_with_cooldown(
    content_id: str,
    creator_id: str,
    content_type: str,
    context: EngagementContext,
    lock: CreatorScheduleLock,
    time_sensitivity: str = "Medium",
    submission_hour: int = 12,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> Tuple[str, int, float, dict]:
    """
    Joint optimization respecting cooldown + sensitivity risk.
    Returns (platform, slot, score, breakdown).
    
    Algorithm-aware routing (from PS4 research doc):
      HIGH sensitivity content gets penalized at peak hours
      to route it toward loyal-audience off-peak slots.
    """
    candidates = []

    for platform in sorted(context.all_platforms):
        content_fit = get_content_platform_affinity(content_type, platform)

        for slot in range(24):
            # Skip cooldown-locked slots
            if not lock.is_slot_available(slot):
                continue

            pa = context.get_platform_activity(platform, slot)
            ch = context.get_creator_history(creator_id, platform, content_type, slot)
            cb = context.get_base_engagement(creator_id)

            base_score = compute_score(pa, ch, cb, content_fit, weights)

            # Algorithm-aware sensitivity risk (penalize sensitive content at peak)
            risk_penalty = compute_sensitivity_risk(time_sensitivity, pa)
            velocity_bonus = compute_first_hour_velocity_bonus(submission_hour, slot)
            routing_label = get_sensitivity_routing_label(time_sensitivity, pa)

            # Adjust score: subtract risk, add velocity bonus, cap at 100
            adjusted_score = round(
                min(100.0, max(0.0, base_score * (1.0 - risk_penalty) + velocity_bonus * 100)),
                2,
            )

            candidates.append((adjusted_score, slot, platform, {
                "platform_activity_raw": pa,
                "creator_history_raw": ch,
                "creator_base_raw": cb,
                "content_fit_raw": content_fit,
                "sensitivity_risk": risk_penalty,
                "velocity_bonus": velocity_bonus,
                "sensitivity_routing": routing_label,
            }))

    if not candidates:
        # All slots locked — use best regardless (extreme cooldown edge case)
        logger.warning(f"All slots locked for creator {creator_id}, ignoring cooldown")
        return joint_optimize_with_cooldown(
            content_id, creator_id, content_type, context,
            CreatorScheduleLock(creator_id, 0),  # no cooldown
            time_sensitivity, submission_hour, weights,
        )

    # Deterministic sort: highest score → earliest slot → alphabetical platform
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))

    best_score, best_slot, best_platform, best_breakdown = candidates[0]
    lock.reserve(best_slot)

    return best_platform, best_slot, best_score, best_breakdown

