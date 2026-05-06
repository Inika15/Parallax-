"""
Layer 1 — Data Loaders
Issues: #1, #2, #3, #4 (Load all 4 datasets)

Four clean CSV loaders — each fast, validated, and fault-tolerant.
All data is loaded into O(1) lookup structures (dicts with composite keys).
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .validator import (
    validate_content_record,
    validate_platform_activity_record,
    validate_engagement_record,
    validate_creator_record,
)

logger = logging.getLogger(__name__)


# ─── Data Models ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ContentItem:
    """A single content submission from a creator."""
    content_id: str
    creator_id: str
    content_type: str        # SHORT or LONG
    created_timestamp: int   # Hour 0-23
    time_sensitivity: str    # High, Medium, or Low


@dataclass(frozen=True)
class CreatorProfile:
    """A creator's base engagement profile."""
    creator_id: str
    base_engagement: float   # Multiplier (e.g., 1.11)
    cooldown_hours: int      # Minimum hours between posts


# ─── Type Aliases ────────────────────────────────────────────────────
# Dict[content_id → ContentItem]
ContentMap = Dict[str, ContentItem]

# Dict[(platform, time_slot) → activity_score]
PlatformActivityMap = Dict[Tuple[str, int], float]

# Dict[(creator_id, platform, content_type, time_slot) → avg_engagement]
HistoricalEngagementMap = Dict[Tuple[str, str, str, int], float]

# Dict[creator_id → CreatorProfile]
CreatorMap = Dict[str, CreatorProfile]


# ─── Loader Functions ────────────────────────────────────────────────

def load_content_submissions(filepath: str) -> ContentMap:
    """
    Load content submission data from CSV.
    Issue #1: Load and Parse Content Submission Data
    
    Args:
        filepath: Path to content.csv
        
    Returns:
        Dict mapping content_id → ContentItem
    """
    content_map: ContentMap = {}
    skipped = 0
    path = Path(filepath)
    
    if not path.exists():
        logger.error(f"Content file not found: {filepath}")
        return content_map

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # start=2 (header is row 1)
            is_valid, error = validate_content_record(row)
            if not is_valid:
                logger.warning(f"Skipping content row {row_num}: {error}")
                skipped += 1
                continue

            item = ContentItem(
                content_id=str(row["content_id"]).strip(),
                creator_id=str(row["creator_id"]).strip(),
                content_type=str(row["content_type"]).strip().upper(),
                created_timestamp=int(row["created_timestamp"]),
                time_sensitivity=str(row.get("time_sensitivity", "Medium")).strip().capitalize(),
            )
            content_map[item.content_id] = item

    logger.info(f"Loaded {len(content_map)} content items ({skipped} skipped)")
    return content_map


def load_platform_activity(filepath: str) -> PlatformActivityMap:
    """
    Load platform activity scores from CSV.
    Issue #2: Load and Parse Platform Activity Data
    
    Args:
        filepath: Path to platform_activity.csv
        
    Returns:
        Dict mapping (platform, time_slot) → activity_score
    """
    activity_map: PlatformActivityMap = {}
    skipped = 0
    path = Path(filepath)

    if not path.exists():
        logger.error(f"Platform activity file not found: {filepath}")
        return activity_map

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            is_valid, error = validate_platform_activity_record(row)
            if not is_valid:
                logger.warning(f"Skipping platform activity row {row_num}: {error}")
                skipped += 1
                continue

            platform = str(row["platform"]).strip()
            slot = int(row["time_slot"])
            score = float(row["activity_score"])
            activity_map[(platform, slot)] = score

    logger.info(f"Loaded {len(activity_map)} platform activity entries ({skipped} skipped)")
    return activity_map


def load_historical_engagement(filepath: str) -> HistoricalEngagementMap:
    """
    Load historical engagement data from CSV.
    Issue #3: Load and Parse Historical Engagement Data
    
    Uses composite key (creator_id, platform, content_type, time_slot)
    for O(1) lookup during scoring.
    
    Args:
        filepath: Path to historical_engagement.csv
        
    Returns:
        Dict mapping (creator_id, platform, content_type, time_slot) → avg_engagement
    """
    engagement_map: HistoricalEngagementMap = {}
    skipped = 0
    path = Path(filepath)

    if not path.exists():
        logger.error(f"Historical engagement file not found: {filepath}")
        return engagement_map

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            is_valid, error = validate_engagement_record(row)
            if not is_valid:
                logger.warning(f"Skipping engagement row {row_num}: {error}")
                skipped += 1
                continue

            key = (
                str(row["creator_id"]).strip(),
                str(row["platform"]).strip(),
                str(row["content_type"]).strip().upper(),
                int(row["time_slot"]),
            )
            engagement_map[key] = float(row["avg_engagement"])

    logger.info(f"Loaded {len(engagement_map)} historical engagement entries ({skipped} skipped)")
    return engagement_map


def load_creator_profiles(filepath: str) -> CreatorMap:
    """
    Load creator profile data from CSV.
    Issue #4: Load and Parse Creator Base Engagement Data
    
    Args:
        filepath: Path to creators.csv
        
    Returns:
        Dict mapping creator_id → CreatorProfile
    """
    creator_map: CreatorMap = {}
    skipped = 0
    path = Path(filepath)

    if not path.exists():
        logger.error(f"Creator profiles file not found: {filepath}")
        return creator_map

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            is_valid, error = validate_creator_record(row)
            if not is_valid:
                logger.warning(f"Skipping creator row {row_num}: {error}")
                skipped += 1
                continue

            profile = CreatorProfile(
                creator_id=str(row["creator_id"]).strip(),
                base_engagement=float(row["base_engagement"]),
                cooldown_hours=int(row.get("cooldown_hours", "0")),
            )
            creator_map[profile.creator_id] = profile

    logger.info(f"Loaded {len(creator_map)} creator profiles ({skipped} skipped)")
    return creator_map
