"""
Layer 1 — Input Validation & Schema Enforcement
Issues: #16 (Input Validation), #15 (Missing Data)

Validates all input records against strict schemas.
Invalid records are logged and skipped — the system never crashes on bad data.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Valid Enumerations ──────────────────────────────────────────────
VALID_CONTENT_TYPES = frozenset({"SHORT", "LONG"})
VALID_PLATFORMS = frozenset({"Instagram", "YouTube"})
VALID_TIME_SLOTS = frozenset(range(0, 24))
VALID_SENSITIVITIES = frozenset({"High", "Medium", "Low"})


class ValidationError(Exception):
    """Raised when a record fails schema validation."""
    pass


def validate_content_record(record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a content submission record.
    
    Expected fields:
        content_id (str/int), creator_id (str/int), content_type (str),
        created_timestamp (int 0-23), time_sensitivity (str)
    
    Returns:
        (is_valid, error_message or None)
    """
    try:
        # Required fields
        for field in ("content_id", "creator_id", "content_type", "created_timestamp"):
            if field not in record or record[field] is None or str(record[field]).strip() == "":
                return False, f"Missing required field: {field}"

        # Content type
        ctype = str(record["content_type"]).strip().upper()
        if ctype not in VALID_CONTENT_TYPES:
            return False, f"Invalid content_type: '{record['content_type']}'. Must be one of {VALID_CONTENT_TYPES}"

        # Time slot
        try:
            slot = int(record["created_timestamp"])
        except (ValueError, TypeError):
            return False, f"Invalid created_timestamp: '{record['created_timestamp']}'. Must be integer 0-23"
        if slot not in VALID_TIME_SLOTS:
            return False, f"created_timestamp {slot} out of range [0, 23]"

        # Time sensitivity (optional — defaults to Medium if missing)
        sensitivity = str(record.get("time_sensitivity", "Medium")).strip().capitalize()
        if sensitivity not in VALID_SENSITIVITIES:
            return False, f"Invalid time_sensitivity: '{record.get('time_sensitivity')}'"

        return True, None

    except Exception as e:
        return False, f"Unexpected validation error: {e}"


def validate_platform_activity_record(record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a platform activity record.
    
    Expected fields:
        platform (str), time_slot (int 0-23), activity_score (float >= 0)
    """
    try:
        # Platform
        platform = str(record.get("platform", "")).strip()
        if platform not in VALID_PLATFORMS:
            return False, f"Invalid platform: '{platform}'. Must be one of {VALID_PLATFORMS}"

        # Time slot
        try:
            slot = int(record["time_slot"])
        except (ValueError, TypeError):
            return False, f"Invalid time_slot: '{record.get('time_slot')}'"
        if slot not in VALID_TIME_SLOTS:
            return False, f"time_slot {slot} out of range [0, 23]"

        # Activity score
        try:
            score = float(record["activity_score"])
        except (ValueError, TypeError):
            return False, f"Invalid activity_score: '{record.get('activity_score')}'"
        if score < 0.0:
            return False, f"activity_score must be >= 0.0, got {score}"

        return True, None

    except Exception as e:
        return False, f"Unexpected validation error: {e}"


def validate_engagement_record(record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a historical engagement record.
    
    Expected fields:
        creator_id (str/int), platform (str), content_type (str),
        time_slot (int 0-23), avg_engagement (float >= 0)
    """
    try:
        for field in ("creator_id", "platform", "content_type", "time_slot", "avg_engagement"):
            if field not in record or record[field] is None or str(record[field]).strip() == "":
                return False, f"Missing required field: {field}"

        platform = str(record["platform"]).strip()
        if platform not in VALID_PLATFORMS:
            return False, f"Invalid platform: '{platform}'"

        ctype = str(record["content_type"]).strip().upper()
        if ctype not in VALID_CONTENT_TYPES:
            return False, f"Invalid content_type: '{record['content_type']}'"

        try:
            slot = int(record["time_slot"])
        except (ValueError, TypeError):
            return False, f"Invalid time_slot: '{record.get('time_slot')}'"
        if slot not in VALID_TIME_SLOTS:
            return False, f"time_slot {slot} out of range [0, 23]"

        try:
            score = float(record["avg_engagement"])
        except (ValueError, TypeError):
            return False, f"Invalid avg_engagement: '{record.get('avg_engagement')}'"
        if score < 0.0:
            return False, f"avg_engagement must be >= 0.0, got {score}"

        return True, None

    except Exception as e:
        return False, f"Unexpected validation error: {e}"


def validate_creator_record(record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a creator profile record.
    
    Expected fields:
        creator_id (str/int), base_engagement (float >= 0), cooldown_hours (int >= 0)
    """
    try:
        for field in ("creator_id", "base_engagement"):
            if field not in record or record[field] is None or str(record[field]).strip() == "":
                return False, f"Missing required field: {field}"

        try:
            base = float(record["base_engagement"])
        except (ValueError, TypeError):
            return False, f"Invalid base_engagement: '{record.get('base_engagement')}'"
        if base < 0.0:
            return False, f"base_engagement must be >= 0.0, got {base}"

        # Cooldown hours (optional, defaults to 0)
        cooldown = record.get("cooldown_hours", "0")
        try:
            cd = int(cooldown)
        except (ValueError, TypeError):
            return False, f"Invalid cooldown_hours: '{cooldown}'"
        if cd < 0:
            return False, f"cooldown_hours must be >= 0, got {cd}"

        return True, None

    except Exception as e:
        return False, f"Unexpected validation error: {e}"
