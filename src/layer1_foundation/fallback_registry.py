"""
Layer 1 — Fallback Registry
Issue #15: Handle Missing or Incomplete Data

Provides tiered fallback values when data is missing.
Fallback chain: Exact match → Platform average → Creator global average → System default

The system NEVER crashes on missing data — it degrades gracefully.
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# ─── System-Wide Defaults ────────────────────────────────────────────
# These are the absolute last resort when no data exists at all.
DEFAULT_ENGAGEMENT = 0.5
DEFAULT_PLATFORM_ACTIVITY = 0.5
DEFAULT_BASE_ENGAGEMENT = 1.0
DEFAULT_CONTENT_TYPE_AFFINITY = 1.0
DEFAULT_COOLDOWN_HOURS = 4


class FallbackRegistry:
    """
    Centralized fallback value provider.
    
    Maintains running averages at multiple granularities so that
    when an exact lookup misses, we can fall back to progressively
    broader averages rather than using a single hard-coded default.
    """

    def __init__(self):
        # Platform-level averages: platform → avg_activity
        self._platform_avg_activity: Dict[str, float] = {}
        
        # Creator-level averages: creator_id → avg_engagement
        self._creator_avg_engagement: Dict[str, float] = {}
        
        # Platform × content_type averages: (platform, content_type) → avg
        self._platform_type_avg: Dict[Tuple[str, str], float] = {}
        
        # Global system average engagement
        self._system_avg_engagement: float = DEFAULT_ENGAGEMENT
        
        # Global system average platform activity
        self._system_avg_activity: float = DEFAULT_PLATFORM_ACTIVITY

    def set_platform_avg_activity(self, platform: str, avg: float):
        self._platform_avg_activity[platform] = avg

    def set_creator_avg_engagement(self, creator_id: str, avg: float):
        self._creator_avg_engagement[creator_id] = avg

    def set_platform_type_avg(self, platform: str, content_type: str, avg: float):
        self._platform_type_avg[(platform, content_type)] = avg

    def set_system_avg_engagement(self, avg: float):
        self._system_avg_engagement = avg

    def set_system_avg_activity(self, avg: float):
        self._system_avg_activity = avg

    # ─── Fallback Getters ────────────────────────────────────────────

    def get_engagement_fallback(
        self,
        creator_id: str,
        platform: str,
        content_type: str,
    ) -> float:
        """
        Tiered fallback for missing historical engagement:
        1. Platform × content_type average
        2. Creator global average
        3. System-wide average
        4. Hard-coded default
        """
        # Tier 1: Platform × content_type average
        key = (platform, content_type)
        if key in self._platform_type_avg:
            logger.debug(f"Fallback tier 1 (platform×type avg) for {creator_id}/{platform}/{content_type}")
            return self._platform_type_avg[key]

        # Tier 2: Creator global average
        if creator_id in self._creator_avg_engagement:
            logger.debug(f"Fallback tier 2 (creator avg) for {creator_id}/{platform}/{content_type}")
            return self._creator_avg_engagement[creator_id]

        # Tier 3: System-wide average
        logger.debug(f"Fallback tier 3 (system avg) for {creator_id}/{platform}/{content_type}")
        return self._system_avg_engagement

    def get_platform_activity_fallback(self, platform: str) -> float:
        """
        Fallback for missing platform activity:
        1. Platform average across all slots
        2. System-wide activity average
        3. Hard-coded default
        """
        if platform in self._platform_avg_activity:
            return self._platform_avg_activity[platform]
        return self._system_avg_activity

    def get_base_engagement_fallback(self) -> float:
        """Fallback for missing creator base engagement."""
        return DEFAULT_BASE_ENGAGEMENT

    def get_cooldown_fallback(self) -> int:
        """Fallback for missing cooldown hours."""
        return DEFAULT_COOLDOWN_HOURS
