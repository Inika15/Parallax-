"""
Standout Feature 5: Data Richness Dashboard

Prints comprehensive data coverage metrics on startup.
Integrated into main.py — this module provides standalone analysis.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, Set, Tuple


def compute_coverage_stats(
    content_count: int,
    creator_count: int,
    history: Dict[Tuple[str, str, str, int], float],
    platforms: Set[str],
    content_types: Set[str],
) -> Dict:
    """Compute comprehensive data coverage statistics."""
    
    creators_in_history = {cid for (cid, _, _, _) in history}
    
    # Platform coverage (how many hours have data)
    platform_hours = {}
    for p in platforms:
        hours = {slot for (_, plat, _, slot) in history if plat == p}
        platform_hours[p] = len(hours)

    # Content type coverage per platform
    plat_type_coverage = {}
    for p in platforms:
        types = {ct for (_, plat, ct, _) in history if plat == p}
        plat_type_coverage[p] = types

    # Engagement score distribution
    scores = list(history.values())
    score_stats = {
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
        "mean": sum(scores) / len(scores) if scores else 0,
    }

    return {
        "total_content": content_count,
        "total_creators": creator_count,
        "creators_with_history": len(creators_in_history),
        "history_records": len(history),
        "platform_hour_coverage": platform_hours,
        "platform_type_coverage": {p: list(t) for p, t in plat_type_coverage.items()},
        "score_stats": score_stats,
    }


def print_full_dashboard(stats: Dict):
    """Print the full data richness dashboard."""
    print("\n" + "=" * 60)
    print("  DATA RICHNESS DASHBOARD (Extended)")
    print("=" * 60)
    
    coverage_pct = (stats["creators_with_history"] / max(stats["total_creators"], 1)) * 100
    print(f"  Creators:   {stats['creators_with_history']}/{stats['total_creators']} "
          f"({coverage_pct:.1f}% coverage)")
    print(f"  Content:    {stats['total_content']} items")
    print(f"  History:    {stats['history_records']} records")
    
    print(f"\n  Platform Coverage:")
    for p, hours in stats["platform_hour_coverage"].items():
        types = stats["platform_type_coverage"].get(p, [])
        print(f"    {p}: {hours}h/24h | types: {', '.join(sorted(types))}")
    
    ss = stats["score_stats"]
    print(f"\n  Engagement Scores:")
    print(f"    Min: {ss['min']:.3f}  Mean: {ss['mean']:.3f}  Max: {ss['max']:.3f}")
    
    print("=" * 60 + "\n")
