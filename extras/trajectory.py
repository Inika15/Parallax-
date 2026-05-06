"""
Standout Feature 3: Creator Trajectory Tracker

Detects if a creator's engagement is trending up or down on each platform.
Factors trajectory into scoring via affinity boost/reduction.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from statistics import mean
from typing import Dict, Tuple


def compute_trajectory(
    creator_id: str,
    creator_history: Dict[Tuple[str, str, str, int], float],
    platforms: set,
) -> Dict[str, float]:
    """
    Compute engagement trajectory per platform.
    
    Compares avg engagement in peak hours (slots 12-23) vs off-peak (0-11)
    as a proxy for trending. Returns multiplier per platform:
    - > 1.0: trending up
    - < 1.0: trending down
    - = 1.0: neutral
    """
    result = {}

    for platform in platforms:
        early_scores = []
        late_scores = []

        for (cid, plat, _, slot), score in creator_history.items():
            if cid == creator_id and plat == platform:
                if slot < 12:
                    early_scores.append(score)
                else:
                    late_scores.append(score)

        if early_scores and late_scores:
            early_avg = mean(early_scores)
            late_avg = mean(late_scores)
            if early_avg > 0:
                trend = late_avg / early_avg
                # Clamp to reasonable range [0.8, 1.2]
                result[platform] = max(0.8, min(1.2, trend))
            else:
                result[platform] = 1.0
        else:
            result[platform] = 1.0

    return result


def print_trajectory_report(
    creator_id: str,
    trajectories: Dict[str, float],
):
    """Print a visual trajectory report."""
    print(f"\n  Creator {creator_id} Trajectory:")
    for platform, trend in sorted(trajectories.items()):
        pct = (trend - 1.0) * 100
        if pct > 0:
            arrow = "↑"
            status = f"+{pct:.1f}%"
        elif pct < 0:
            arrow = "↓"
            status = f"{pct:.1f}%"
        else:
            arrow = "→"
            status = "0.0%"
        
        bar_len = int(abs(pct) / 2)
        bar = "█" * bar_len
        print(f"    {platform:10s}: {arrow} {status:>7s} {bar}")
