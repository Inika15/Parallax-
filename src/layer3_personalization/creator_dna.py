"""
Layer 3 — Creator DNA Profile Builder
Issues: #4, #10 (Creator-Specific Adaptation)

Builds a compact "DNA" representation of each creator's engagement personality:
- Platform affinities (which platform works best for them)
- Content type affinities (what type of content they excel at)
- Peak posting slots per platform
- Data richness score (for cold-start detection)
"""

import logging
from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CreatorDNA:
    """
    Compact, derived representation of a creator's engagement personality.
    Built from historical data — used by the scorer for personalization.
    """
    creator_id: str
    base_multiplier: float                        # Raw base engagement
    platform_affinity: Dict[str, float]           # platform → affinity multiplier
    type_affinity: Dict[str, float]               # content_type → affinity multiplier
    peak_slots: Dict[str, List[int]]              # platform → top time slots
    data_richness: float                          # 0.0 (no data) → 1.0 (full data)
    cooldown_hours: int = 4                       # Min hours between posts
    trajectory: Dict[str, float] = field(default_factory=dict)  # platform → trend multiplier


def build_creator_dna(
    creator_id: str,
    base_engagement: float,
    cooldown_hours: int,
    creator_history: Dict[Tuple[str, str, str, int], float],
    all_platforms: Set[str],
    all_content_types: Set[str],
    system_average: float,
) -> CreatorDNA:
    """
    Build a CreatorDNA profile from historical engagement data.
    
    Args:
        creator_id: The creator's ID
        base_engagement: Base engagement multiplier from creator profile
        cooldown_hours: Minimum hours between posts
        creator_history: Full historical engagement map
        all_platforms: Set of all platforms in the system
        all_content_types: Set of all content types
        system_average: System-wide average engagement
        
    Returns:
        CreatorDNA profile
    """
    # ── Extract this creator's records ────────────────────────────────
    creator_records: Dict[Tuple[str, str, int], float] = {}
    for (cid, platform, ctype, slot), score in creator_history.items():
        if cid == creator_id:
            creator_records[(platform, ctype, slot)] = score

    total_possible = len(all_platforms) * len(all_content_types) * 24
    data_richness = len(creator_records) / total_possible if total_possible > 0 else 0.0

    # ── Platform affinity ─────────────────────────────────────────────
    platform_affinity = _compute_platform_affinity(
        creator_records, all_platforms, system_average
    )

    # ── Content type affinity ─────────────────────────────────────────
    type_affinity = _compute_type_affinity(
        creator_records, all_content_types, system_average
    )

    # ── Peak slots per platform ───────────────────────────────────────
    peak_slots = _compute_peak_slots(creator_records, all_platforms)

    return CreatorDNA(
        creator_id=creator_id,
        base_multiplier=base_engagement,
        platform_affinity=platform_affinity,
        type_affinity=type_affinity,
        peak_slots=peak_slots,
        data_richness=data_richness,
        cooldown_hours=cooldown_hours,
    )


def _compute_platform_affinity(
    records: Dict[Tuple[str, str, int], float],
    all_platforms: Set[str],
    system_average: float,
) -> Dict[str, float]:
    """
    Compute how well a creator performs on each platform relative to system average.
    
    Returns dict: platform → affinity_multiplier
    - > 1.0 means creator performs above average on this platform
    - < 1.0 means below average
    - = 1.0 means neutral (no data or exactly average)
    """
    platform_scores: Dict[str, List[float]] = {}
    for (platform, _, _), score in records.items():
        platform_scores.setdefault(platform, []).append(score)

    result = {}
    for platform in all_platforms:
        if platform in platform_scores and platform_scores[platform]:
            creator_avg = mean(platform_scores[platform])
            # Affinity = creator's platform avg / system avg
            if system_average > 0:
                result[platform] = creator_avg / system_average
            else:
                result[platform] = 1.0
        else:
            result[platform] = 1.0  # Neutral fallback

    return result


def _compute_type_affinity(
    records: Dict[Tuple[str, str, int], float],
    all_content_types: Set[str],
    system_average: float,
) -> Dict[str, float]:
    """
    Compute how well a creator performs with each content type.
    """
    type_scores: Dict[str, List[float]] = {}
    for (_, ctype, _), score in records.items():
        type_scores.setdefault(ctype, []).append(score)

    result = {}
    for ctype in all_content_types:
        if ctype in type_scores and type_scores[ctype]:
            creator_avg = mean(type_scores[ctype])
            if system_average > 0:
                result[ctype] = creator_avg / system_average
            else:
                result[ctype] = 1.0
        else:
            result[ctype] = 1.0

    return result


def _compute_peak_slots(
    records: Dict[Tuple[str, str, int], float],
    all_platforms: Set[str],
) -> Dict[str, List[int]]:
    """
    Find the top 3 performing time slots per platform for this creator.
    Deterministic: ties broken by earlier slot.
    """
    platform_slot_scores: Dict[str, Dict[int, List[float]]] = {}
    for (platform, _, slot), score in records.items():
        platform_slot_scores.setdefault(platform, {}).setdefault(slot, []).append(score)

    result = {}
    for platform in all_platforms:
        if platform in platform_slot_scores:
            slot_avgs = {
                slot: mean(scores)
                for slot, scores in platform_slot_scores[platform].items()
            }
            # Sort: highest score first, then earliest slot for ties
            sorted_slots = sorted(
                slot_avgs.keys(), key=lambda s: (-slot_avgs[s], s)
            )
            result[platform] = sorted_slots[:3]
        else:
            result[platform] = []

    return result
