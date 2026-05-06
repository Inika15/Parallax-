"""
Layer 2 — EngagementContext (Unified Data View)
Issues: #2, #3, #13, #14

Single immutable object that fuses all 4 datasets for O(1) queries.
Constructed ONCE at startup → enables true parallelism for burst workloads.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..layer1_foundation.data_loader import (
    ContentMap, PlatformActivityMap, HistoricalEngagementMap, CreatorMap,
    ContentItem, CreatorProfile,
)
from ..layer1_foundation.fallback_registry import FallbackRegistry

logger = logging.getLogger(__name__)


@dataclass
class EngagementContext:
    """
    Unified, immutable view of all engagement data.
    
    This is the SINGLE source of truth that every layer queries.
    Built once at startup — all reads are lock-free and stateless.
    """
    content: ContentMap
    platform_activity: PlatformActivityMap
    creator_history: HistoricalEngagementMap
    creators: CreatorMap
    fallback: FallbackRegistry

    # Pre-computed during build
    _all_platforms: Set[str] = field(default_factory=set)
    _all_content_types: Set[str] = field(default_factory=set)
    _system_average: float = 0.5

    def __post_init__(self):
        """Pre-compute frequently accessed metadata."""
        # Extract unique platforms
        self._all_platforms = set()
        for (platform, _) in self.platform_activity:
            self._all_platforms.add(platform)
        
        # Extract unique content types  
        self._all_content_types = set()
        for (_, _, ctype, _) in self.creator_history:
            self._all_content_types.add(ctype)

        # System-wide average engagement
        if self.creator_history:
            self._system_average = sum(self.creator_history.values()) / len(self.creator_history)
        else:
            self._system_average = 0.5

        # Populate fallback registry with computed averages
        self._populate_fallbacks()

    def _populate_fallbacks(self):
        """Pre-compute fallback averages at various granularities."""
        from statistics import mean

        # Platform average activity
        platform_scores: Dict[str, List[float]] = {}
        for (platform, _), score in self.platform_activity.items():
            platform_scores.setdefault(platform, []).append(score)
        for platform, scores in platform_scores.items():
            self.fallback.set_platform_avg_activity(platform, mean(scores))

        # Creator average engagement
        creator_scores: Dict[str, List[float]] = {}
        for (creator, _, _, _), score in self.creator_history.items():
            creator_scores.setdefault(creator, []).append(score)
        for creator, scores in creator_scores.items():
            self.fallback.set_creator_avg_engagement(creator, mean(scores))

        # Platform × content_type averages
        plat_type_scores: Dict[Tuple[str, str], List[float]] = {}
        for (_, platform, ctype, _), score in self.creator_history.items():
            plat_type_scores.setdefault((platform, ctype), []).append(score)
        for (platform, ctype), scores in plat_type_scores.items():
            self.fallback.set_platform_type_avg(platform, ctype, mean(scores))

        # System-wide averages
        self.fallback.set_system_avg_engagement(self._system_average)
        if self.platform_activity:
            self.fallback.set_system_avg_activity(
                mean(self.platform_activity.values())
            )

    # ─── Query Methods (O(1) lookups) ────────────────────────────────

    def get_platform_activity(self, platform: str, slot: int) -> float:
        """Get activity score for a platform at a time slot, with fallback."""
        key = (platform, slot)
        if key in self.platform_activity:
            return self.platform_activity[key]
        return self.fallback.get_platform_activity_fallback(platform)

    def get_creator_history(
        self, creator_id: str, platform: str, content_type: str, slot: int
    ) -> float:
        """Get historical engagement for a specific combo, with tiered fallback."""
        key = (creator_id, platform, content_type, slot)
        if key in self.creator_history:
            return self.creator_history[key]
        return self.fallback.get_engagement_fallback(creator_id, platform, content_type)

    def has_history(
        self, creator_id: str, platform: str, content_type: str, slot: int
    ) -> bool:
        """Check if exact historical data exists for this combo."""
        return (creator_id, platform, content_type, slot) in self.creator_history

    def get_base_engagement(self, creator_id: str) -> float:
        """Get creator's base engagement multiplier, with fallback."""
        if creator_id in self.creators:
            return self.creators[creator_id].base_engagement
        return self.fallback.get_base_engagement_fallback()

    def get_cooldown_hours(self, creator_id: str) -> int:
        """Get creator's cooldown period between posts."""
        if creator_id in self.creators:
            return self.creators[creator_id].cooldown_hours
        return self.fallback.get_cooldown_fallback()

    def get_content_item(self, content_id: str) -> Optional[ContentItem]:
        """Get a content item by ID."""
        return self.content.get(content_id)

    @property
    def all_platforms(self) -> Set[str]:
        return self._all_platforms

    @property
    def all_content_types(self) -> Set[str]:
        return self._all_content_types

    @property
    def system_average(self) -> float:
        return self._system_average
