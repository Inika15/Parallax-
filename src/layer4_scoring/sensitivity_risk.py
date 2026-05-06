"""
Sensitivity Risk Engine — Algorithm-Aware Scheduling
=====================================================
From PS4 research document:
  "Sensitive content shown to the wrong test audience in the first hour
   can trigger 'Not Interested' signals that permanently suppress the post."

INSIGHT: HIGH sensitivity content at PEAK activity hours = HIGH RISK
         because peak hours have the most random/diverse audience.

Risk Score = sensitivity_level × platform_activity
  - High sensitivity + peak slot → penalize (risk of suppression)
  - Low sensitivity + peak slot → no penalty (safe for broad audience)

This creates "algorithm-aware" routing:
  - HIGH sensitivity content gets routed to off-peak hours (loyal audience)
  - LOW sensitivity content gets routed to peak hours (maximum reach)
"""

import logging

logger = logging.getLogger(__name__)

# Risk weight multipliers per sensitivity level
# Higher = more risk from being at peak hours
SENSITIVITY_RISK_WEIGHTS = {
    "High":   0.15,   # 15% score penalty at peak hours
    "Medium": 0.05,   # 5% penalty
    "Low":    0.00,   # No penalty — low sensitivity content WANTS peak hours
}

# Audience diversity threshold — slots with activity >= this have random audiences
PEAK_DIVERSITY_THRESHOLD = 0.85


def compute_sensitivity_risk(
    time_sensitivity: str,
    platform_activity: float,
) -> float:
    """
    Compute a risk factor (0.0–1.0) for sensitive content at high-activity slots.
    
    Returns a PENALTY that should be subtracted from the score.
    Higher = more risky = worse slot for sensitive content.
    
    Logic (from Instagram/YouTube algorithm research):
      - Peak hours have diverse, random test audiences
      - Sensitive content needs loyal, niche audiences
      - Therefore: sensitive content should AVOID peak hours
    """
    risk_weight = SENSITIVITY_RISK_WEIGHTS.get(time_sensitivity, 0.05)
    
    # Only apply risk when activity is above diversity threshold
    if platform_activity < PEAK_DIVERSITY_THRESHOLD:
        return 0.0  # Off-peak = safe for sensitive content
    
    # Risk increases linearly with how far above the threshold
    excess_activity = platform_activity - PEAK_DIVERSITY_THRESHOLD
    risk = risk_weight * (excess_activity / (1.0 - PEAK_DIVERSITY_THRESHOLD))
    
    return round(min(risk, risk_weight), 4)


def compute_first_hour_velocity_bonus(
    submission_hour: int,
    recommended_slot: int,
) -> float:
    """
    First-hour velocity bonus (from Instagram algorithm research).
    
    Instagram's 60-minute window: content shown to test audience first.
    If you post at your optimal time, you maximize the test audience quality.
    
    Bonus = 1.0 if posting within 1 hour of submission (captures velocity)
    Decays as the gap between submission and recommended slot grows.
    """
    gap = abs(recommended_slot - submission_hour)
    # Wrap around 24h
    if gap > 12:
        gap = 24 - gap
    
    if gap == 0:
        return 0.03   # 3% bonus — immediate posting captures velocity
    elif gap <= 2:
        return 0.01   # 1% bonus — still close
    else:
        return 0.00   # No bonus — scheduled for later


def get_sensitivity_routing_label(
    time_sensitivity: str,
    platform_activity: float,
) -> str:
    """Human-readable label for the sensitivity routing decision."""
    risk = compute_sensitivity_risk(time_sensitivity, platform_activity)
    
    if risk == 0:
        return "SAFE"
    elif risk < 0.05:
        return "LOW_RISK"
    elif risk < 0.10:
        return "MODERATE_RISK"
    else:
        return "HIGH_RISK"
