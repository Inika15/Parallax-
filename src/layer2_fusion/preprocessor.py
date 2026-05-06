"""
Layer 2 — Preprocessor
Issue #14: Optimize Recommendation Latency

Pre-computes platform-level statistics during data load
so they don't need to be recalculated per recommendation.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..layer1_foundation.data_loader import PlatformActivityMap

logger = logging.getLogger(__name__)


@dataclass
class PlatformStats:
    """Pre-computed statistics for a single platform."""
    platform: str
    peak_slot: int                    # Hour with highest activity
    avg_activity: float               # Mean activity across all 24 slots
    top_3_slots: List[int]            # Top 3 slots by activity (descending)
    min_activity: float               # Lowest activity score
    max_activity: float               # Highest activity score
    slot_scores: Dict[int, float] = field(default_factory=dict)  # All slot scores


def compute_platform_stats(
    activity_map: PlatformActivityMap,
) -> Dict[str, PlatformStats]:
    """
    Pre-compute per-platform statistics from activity data.
    
    This is called ONCE at startup and cached in the context.
    Reduces per-recommendation latency by avoiding repeated aggregations.
    
    Args:
        activity_map: Dict[(platform, time_slot) → activity_score]
        
    Returns:
        Dict[platform → PlatformStats]
    """
    # Group by platform
    platform_slots: Dict[str, Dict[int, float]] = {}
    for (platform, slot), score in activity_map.items():
        platform_slots.setdefault(platform, {})[slot] = score

    stats: Dict[str, PlatformStats] = {}

    for platform, slot_scores in platform_slots.items():
        if not slot_scores:
            continue

        scores_list = list(slot_scores.items())
        scores_list.sort(key=lambda x: (-x[1], x[0]))  # Deterministic tie-breaking

        peak_slot = scores_list[0][0]
        top_3 = [s[0] for s in scores_list[:3]]
        all_scores = list(slot_scores.values())
        avg = sum(all_scores) / len(all_scores)

        stats[platform] = PlatformStats(
            platform=platform,
            peak_slot=peak_slot,
            avg_activity=avg,
            top_3_slots=top_3,
            min_activity=min(all_scores),
            max_activity=max(all_scores),
            slot_scores=dict(slot_scores),
        )

        logger.info(
            f"Platform '{platform}': peak_slot={peak_slot}, "
            f"avg_activity={avg:.3f}, top_3={top_3}"
        )

    return stats


def compute_creator_slot_stats(
    creator_history: Dict[Tuple[str, str, str, int], float],
) -> Dict[str, Dict[str, List[int]]]:
    """
    Pre-compute per-creator peak time slots per platform.
    
    Returns:
        Dict[creator_id → Dict[platform → List[top_3_slots]]]
    """
    # Aggregate: (creator, platform) → {slot: avg_score}
    creator_platform_slots: Dict[Tuple[str, str], Dict[int, List[float]]] = {}

    for (creator, platform, _, slot), score in creator_history.items():
        key = (creator, platform)
        creator_platform_slots.setdefault(key, {}).setdefault(slot, []).append(score)

    result: Dict[str, Dict[str, List[int]]] = {}

    for (creator, platform), slot_scores in creator_platform_slots.items():
        # Average across content types for each slot
        avg_by_slot = {
            slot: sum(scores) / len(scores)
            for slot, scores in slot_scores.items()
        }
        # Sort by score descending, then slot ascending for determinism
        sorted_slots = sorted(avg_by_slot.keys(), key=lambda s: (-avg_by_slot[s], s))
        result.setdefault(creator, {})[platform] = sorted_slots[:3]

    return result
