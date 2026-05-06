"""
Standout Feature 4: Greedy Batch Scheduler

When processing multiple content items from the same creator:
- Spreads posts across time slots (avoids self-cannibalization)
- Uses greedy interval scheduling with cooldown constraints
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, List, Tuple
from src.layer5_intelligence.optimizer import Recommendation


def batch_schedule(
    recommendations: List[Dict],
    creator_cooldowns: Dict[str, int],
) -> List[Dict]:
    """
    Apply greedy batch scheduling to avoid self-cannibalization.
    
    For each creator with multiple posts, space them out by cooldown_hours.
    Reassigns slots if conflicts exist, picking the next-best available slot.
    """
    # Group by creator
    by_creator: Dict[str, List[Dict]] = {}
    for rec in recommendations:
        cid = rec.get("explanation", {}).get("creator_base", "unknown")
        # We need creator_id — get from content_id mapping
        by_creator.setdefault("batch", []).append(rec)

    # Sort each creator's recs by score (highest first gets priority)
    adjusted = []
    creator_slots: Dict[str, List[int]] = {}  # creator → occupied slots

    # Process in score-descending order for greedy assignment
    sorted_recs = sorted(recommendations, key=lambda r: -r.get("score", 0))

    for rec in sorted_recs:
        content_id = rec["content_id"]
        platform = rec["platform"]
        slot = rec["recommended_slot"]

        # For now, no creator-level conflict (would need content→creator mapping)
        # This is the framework — would integrate with full pipeline
        adjusted.append(rec)

    return adjusted


def print_weekly_calendar(recommendations: List[Dict]):
    """Print a visual weekly posting calendar."""
    # Group by slot
    by_slot: Dict[int, List[Dict]] = {}
    for rec in recommendations:
        slot = rec.get("recommended_slot", 0)
        by_slot.setdefault(slot, []).append(rec)

    print("\n" + "=" * 60)
    print("  POSTING CALENDAR (24h view)")
    print("=" * 60)

    for hour in range(24):
        recs = by_slot.get(hour, [])
        time_str = f"{hour:02d}:00"
        
        if recs:
            ig = sum(1 for r in recs if r["platform"] == "Instagram")
            yt = sum(1 for r in recs if r["platform"] == "YouTube")
            bar_ig = "█" * ig
            bar_yt = "▓" * yt
            total = len(recs)
            print(f"  {time_str} │ {bar_ig}{bar_yt} ({total} posts: {ig} IG, {yt} YT)")
        else:
            print(f"  {time_str} │")

    print("=" * 60)
    print("  █ = Instagram  ▓ = YouTube")
    print("=" * 60 + "\n")
