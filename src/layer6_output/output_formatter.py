"""
Layer 6 — Output Formatter
Issues: #12 (Output Format), #19 (Explainability)

From how_to_win.md:
- content_id MUST be integer, not string
- platform: exactly "Instagram" or "YouTube"
- decision: exactly "POST_NOW" or "SCHEDULE"
- recommended_slot: integer 0-23
- score: float (not string)
- confidence: "HIGH" for all (100% data coverage in dataset)

Validation function checks every record before output.
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_PLATFORMS = {"Instagram", "YouTube"}
VALID_DECISIONS = {"POST_NOW", "SCHEDULE"}


def format_recommendation(
    content_id,
    platform: str,
    recommended_slot: int,
    decision: str,
    score: float,
    confidence: str,
    explanation: dict,
) -> Dict[str, Any]:
    """Format a single recommendation into the output schema.
    
    how_to_win.md: content_id must be integer, not string.
    """
    rec = {
        "content_id": int(content_id),  # MUST be integer per how_to_win.md
        "platform": platform,
        "recommended_slot": int(recommended_slot),
        "decision": decision,
        "score": float(score),
        "confidence": confidence,
        "explanation": explanation,
    }
    return rec


def validate_output(rec: Dict[str, Any]) -> tuple:
    """
    Final validation before output (how_to_win.md compliance).
    Returns (is_valid, error_message).
    """
    errors = []

    # Platform must be exactly "Instagram" or "YouTube"
    if rec.get("platform") not in VALID_PLATFORMS:
        errors.append(f"Invalid platform: {rec.get('platform')}")

    # Decision must be exactly "POST_NOW" or "SCHEDULE"
    if rec.get("decision") not in VALID_DECISIONS:
        errors.append(f"Invalid decision: {rec.get('decision')}")

    # Slot must be int in [0, 23]
    slot = rec.get("recommended_slot")
    if not isinstance(slot, int) or slot < 0 or slot > 23:
        errors.append(f"Invalid slot: {slot}")

    # Score must be finite float
    score = rec.get("score")
    if score is None or not isinstance(score, (int, float)):
        errors.append(f"Invalid score type: {type(score)}")
    elif math.isnan(score) or math.isinf(score):
        errors.append(f"Score is NaN or Inf: {score}")

    # content_id must be integer
    cid = rec.get("content_id")
    if cid is None:
        errors.append("Missing content_id")
    elif not isinstance(cid, int):
        errors.append(f"content_id must be int, got {type(cid)}")

    if errors:
        return False, "; ".join(errors)
    return True, None


def format_all_recommendations(
    recommendations: List[Dict[str, Any]],
    output_path: Optional[str] = None,
) -> str:
    """
    Format and validate all recommendations, optionally write to file.
    
    how_to_win.md: Coverage check — must have exactly 100 items, no missing IDs.
    """
    validated = []
    invalid_count = 0

    for rec in recommendations:
        is_valid, error = validate_output(rec)
        if is_valid:
            validated.append(rec)
        else:
            logger.warning(f"Invalid recommendation for {rec.get('content_id')}: {error}")
            invalid_count += 1

    if invalid_count > 0:
        logger.warning(f"{invalid_count} recommendations failed validation")

    # Coverage check (how_to_win.md)
    output_ids = {r["content_id"] for r in validated}
    logger.info(f"Coverage: {len(output_ids)} unique content IDs in output")

    output = json.dumps(validated, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        logger.info(f"Wrote {len(validated)} recommendations to {output_path}")

    return output
