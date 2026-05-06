"""
Standout Feature 1: Engagement Heatmap Generator

Visual CLI output showing engagement potential across all 24 slots × 2 platforms.
Judges can SEE the recommendation, not just read it.

Usage:
    python -m extras.heatmap --data-dir data/raw --creator 24 --content-type LONG
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.layer1_foundation.data_loader import (
    load_platform_activity, load_historical_engagement, load_creator_profiles,
)
from src.layer1_foundation.fallback_registry import FallbackRegistry
from src.layer2_fusion.context import EngagementContext
from src.layer4_scoring.scorer import compute_score
from src.layer5_intelligence.affinity_matrix import get_content_platform_affinity


# ANSI color codes for terminal
COLORS = [
    "\033[48;5;17m",   # Deep blue (lowest)
    "\033[48;5;19m",
    "\033[48;5;21m",
    "\033[48;5;27m",
    "\033[48;5;33m",
    "\033[48;5;39m",
    "\033[48;5;45m",   # Cyan
    "\033[48;5;46m",   # Green
    "\033[48;5;118m",
    "\033[48;5;190m",  # Yellow
    "\033[48;5;220m",
    "\033[48;5;208m",  # Orange
    "\033[48;5;196m",  # Red (highest)
]
RESET = "\033[0m"
BOLD = "\033[1m"


def score_to_color(score: float, min_s: float, max_s: float) -> str:
    """Map a score to a color index."""
    if max_s == min_s:
        idx = len(COLORS) // 2
    else:
        ratio = (score - min_s) / (max_s - min_s)
        idx = int(ratio * (len(COLORS) - 1))
        idx = max(0, min(idx, len(COLORS) - 1))
    return COLORS[idx]


def generate_heatmap(
    creator_id: str,
    content_type: str,
    context: EngagementContext,
):
    """Generate and print an engagement heatmap for a creator."""
    platforms = sorted(context.all_platforms)
    
    # Compute all scores
    scores = {}
    all_scores = []
    for platform in platforms:
        content_fit = get_content_platform_affinity(content_type, platform)
        for slot in range(24):
            s = compute_score(
                platform_activity=context.get_platform_activity(platform, slot),
                creator_history=context.get_creator_history(creator_id, platform, content_type, slot),
                creator_base=context.get_base_engagement(creator_id),
                content_fit=content_fit,
            )
            scores[(platform, slot)] = s
            all_scores.append(s)

    min_s = min(all_scores)
    max_s = max(all_scores)

    # Find best
    best_key = max(scores, key=scores.get)
    best_platform, best_slot = best_key

    # Print header
    print(f"\n{BOLD}Engagement Heatmap: Creator {creator_id} | Content: {content_type}{RESET}")
    print("=" * 78)
    
    # Hour labels
    print(f"{'Platform':<12}", end="")
    for h in range(24):
        print(f"{h:>3}", end="")
    print(f"  {'Best':>6}")
    print("-" * 78)

    # Rows
    for platform in platforms:
        print(f"{platform:<12}", end="")
        best_for_platform = -1
        best_slot_for_platform = 0
        
        for slot in range(24):
            s = scores[(platform, slot)]
            color = score_to_color(s, min_s, max_s)
            marker = " * " if (platform, slot) == best_key else f"{s:3.0f}"
            print(f"{color}{marker}{RESET}", end="")
            
            if s > best_for_platform:
                best_for_platform = s
                best_slot_for_platform = slot

        print(f"  h={best_slot_for_platform:>2}")

    # Legend
    print("-" * 78)
    print("Legend: ", end="")
    for i, c in enumerate(COLORS):
        val = min_s + (max_s - min_s) * i / (len(COLORS) - 1)
        print(f"{c} {val:4.0f} {RESET}", end="")
    print()
    print(f"\n{BOLD}>>> BEST: {best_platform} at hour {best_slot} (score: {scores[best_key]:.1f}){RESET}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Engagement Heatmap Generator")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--creator", required=True)
    parser.add_argument("--content-type", default="SHORT", choices=["SHORT", "LONG"])
    args = parser.parse_args()

    activity = load_platform_activity(os.path.join(args.data_dir, "platform_activity.csv"))
    history = load_historical_engagement(os.path.join(args.data_dir, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(args.data_dir, "creators.csv"))
    fallback = FallbackRegistry()
    context = EngagementContext(
        content={}, platform_activity=activity,
        creator_history=history, creators=creators, fallback=fallback,
    )
    generate_heatmap(args.creator, args.content_type, context)
