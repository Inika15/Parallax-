"""
Layer 3 — Cold Start Fallback
Issue #15: Handle Missing or Incomplete Data

When a creator has limited or no historical data (data_richness < 0.3),
we build a "cold start" profile using system-wide averages.
"""

import logging
from statistics import mean
from typing import Dict, List, Set, Tuple

from .creator_dna import CreatorDNA

logger = logging.getLogger(__name__)

# Threshold: below this data_richness, we blend with cold-start profile
COLD_START_THRESHOLD = 0.3


def build_cold_start_profile(
    creator_id: str,
    base_engagement: float,
    cooldown_hours: int,
    all_platforms: Set[str],
    all_content_types: Set[str],
    global_type_averages: Dict[str, float],
    global_peak_slots: Dict[str, List[int]],
) -> CreatorDNA:
    """
    Build a cold-start CreatorDNA profile using system-wide averages.
    
    Used when a creator has insufficient historical data.
    All affinities default to 1.0 (neutral), peak slots come from global data.
    """
    logger.info(f"Building cold-start profile for creator {creator_id}")

    return CreatorDNA(
        creator_id=creator_id,
        base_multiplier=base_engagement,
        platform_affinity={p: 1.0 for p in all_platforms},
        type_affinity=global_type_averages if global_type_averages else {t: 1.0 for t in all_content_types},
        peak_slots=global_peak_slots if global_peak_slots else {p: list(range(8, 23)) for p in all_platforms},
        data_richness=0.0,
        cooldown_hours=cooldown_hours,
    )


def compute_global_type_averages(
    creator_history: Dict[Tuple[str, str, str, int], float],
    all_content_types: Set[str],
) -> Dict[str, float]:
    """
    Compute system-wide average engagement per content type.
    Used as fallback affinity for cold-start creators.
    """
    type_scores: Dict[str, List[float]] = {}
    for (_, _, ctype, _), score in creator_history.items():
        type_scores.setdefault(ctype, []).append(score)

    system_avg = mean(creator_history.values()) if creator_history else 1.0

    result = {}
    for ctype in all_content_types:
        if ctype in type_scores and type_scores[ctype]:
            result[ctype] = mean(type_scores[ctype]) / system_avg if system_avg > 0 else 1.0
        else:
            result[ctype] = 1.0

    return result


def compute_global_peak_slots(
    creator_history: Dict[Tuple[str, str, str, int], float],
    all_platforms: Set[str],
) -> Dict[str, List[int]]:
    """
    Compute system-wide best performing time slots per platform.
    Used as peak slots for cold-start creators.
    """
    platform_slot_scores: Dict[str, Dict[int, List[float]]] = {}
    for (_, platform, _, slot), score in creator_history.items():
        platform_slot_scores.setdefault(platform, {}).setdefault(slot, []).append(score)

    result = {}
    for platform in all_platforms:
        if platform in platform_slot_scores:
            slot_avgs = {
                slot: mean(scores)
                for slot, scores in platform_slot_scores[platform].items()
            }
            sorted_slots = sorted(slot_avgs.keys(), key=lambda s: (-slot_avgs[s], s))
            result[platform] = sorted_slots[:5]
        else:
            result[platform] = list(range(9, 21))  # Default: business hours

    return result


def is_cold_start(dna: CreatorDNA) -> bool:
    """Check if a creator profile qualifies as cold-start."""
    return dna.data_richness < COLD_START_THRESHOLD
