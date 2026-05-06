"""
Layer 6 — Natural Language Explainer (perfect.md Layer 20)
Postiz pattern: generatePostsDraft AI → deterministic template-based explanation.

Every recommendation gets a one-sentence justification built from score components.
No ML required — pure template logic from the data.
"""

from ..layer5_intelligence.affinity_matrix import get_content_platform_affinity


def generate_explanation_sentence(
    content_id: int,
    creator_id: str,
    content_type: str,
    platform: str,
    slot: int,
    decision: str,
    score: float,
    history_score: float,
    activity_score: float,
    gain_pct: float = 0.0,
) -> str:
    """
    Generate a human-readable explanation for a recommendation.
    Deterministic — same inputs always produce the same string.
    """
    time_label = f"{slot}:00" if slot >= 10 else f"0{slot}:00"
    type_str = "Short-form" if content_type == "SHORT" else "Long-form"
    affinity = get_content_platform_affinity(content_type, platform)

    parts = []

    # Lead with engagement insight
    if history_score > 0.85:
        parts.append(
            f"Creator {creator_id} has historically strong engagement "
            f"on {platform} at {time_label}"
        )
    elif history_score > 0.6:
        parts.append(
            f"{time_label} on {platform} offers solid engagement "
            f"for creator {creator_id}"
        )
    else:
        parts.append(
            f"{time_label} on {platform} is the best available slot "
            f"for creator {creator_id}"
        )

    # Platform activity context
    if activity_score == 1.0:
        parts.append("platform activity is at its peak")
    else:
        parts.append(
            "this slot is outside the platform's peak window "
            "but personal history compensates"
        )

    # Content fit
    if affinity >= 1.0:
        parts.append(
            f"{type_str} content has a natural affinity advantage on {platform}"
        )
    else:
        parts.append(
            f"{type_str} content faces a slight affinity penalty on {platform} "
            "but engagement data overrides"
        )

    # Scheduling rationale
    if decision == "SCHEDULE" and gain_pct > 20:
        parts.append(
            f"scheduling yields {gain_pct:.0f}% better engagement than posting now"
        )
    elif decision == "POST_NOW":
        parts.append("posting now captures nearly optimal engagement")

    return ". ".join(parts) + "."


def build_score_trace(
    creator_id: str,
    platform: str,
    slot: int,
    content_type: str,
    activity: float,
    history: float,
    base: float,
    affinity: float,
) -> str:
    """
    Traceable score string (perfect.md Layer 14).
    Fully auditable — every number in output can be decoded.
    """
    return (
        f"creator={creator_id}|platform={platform}|slot={slot:02d}|"
        f"type={content_type}|activity={activity:.2f}|"
        f"history={history:.3f}|base={base:.2f}|affinity={affinity:.3f}"
    )
