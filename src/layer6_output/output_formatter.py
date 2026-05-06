"""
Layer 6 — Output Formatter
Issues: #12 (Output Format), #19 (Explainability)

Produces clean, validated, explainable JSON output.
Every recommendation passes a final validation check before output.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_PLATFORMS = {"Instagram", "YouTube"}
VALID_DECISIONS = {"POST_NOW", "SCHEDULE"}


def format_recommendation(
    content_id: str,
    platform: str,
    recommended_slot: int,
    decision: str,
    score: float,
    confidence: str,
    explanation: dict,
) -> Dict[str, Any]:
    """Format a single recommendation into the output schema."""
    rec = {
        "content_id": content_id,
        "platform": platform,
        "recommended_slot": recommended_slot,
        "decision": decision,
        "score": score,
        "confidence": confidence,
        "explanation": explanation,
    }
    return rec


def validate_output(rec: Dict[str, Any]) -> tuple:
    """
    Final validation before output.
    Returns (is_valid, error_message).
    """
    errors = []

    if rec.get("platform") not in VALID_PLATFORMS:
        errors.append(f"Invalid platform: {rec.get('platform')}")

    if rec.get("decision") not in VALID_DECISIONS:
        errors.append(f"Invalid decision: {rec.get('decision')}")

    slot = rec.get("recommended_slot")
    if not isinstance(slot, int) or slot < 0 or slot > 23:
        errors.append(f"Invalid slot: {slot}")

    score = rec.get("score")
    if score is None or not isinstance(score, (int, float)):
        errors.append(f"Invalid score type: {type(score)}")

    if not rec.get("content_id"):
        errors.append("Missing content_id")

    if errors:
        return False, "; ".join(errors)
    return True, None


def format_all_recommendations(
    recommendations: List[Dict[str, Any]],
    output_path: Optional[str] = None,
) -> str:
    """
    Format and validate all recommendations, optionally write to file.
    Returns JSON string.
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

    output = json.dumps(validated, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        logger.info(f"Wrote {len(validated)} recommendations to {output_path}")

    return output
