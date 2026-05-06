"""
Standout Feature 2: Counterfactual Explainer

For every recommendation, shows "what if" — what score would the creator 
have gotten at the WORST possible time? Quantifies the system's value.

Usage:
    python -m extras.counterfactual --data-dir data/raw --content-id 1
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.layer1_foundation.data_loader import *
from src.layer1_foundation.fallback_registry import FallbackRegistry
from src.layer2_fusion.context import EngagementContext
from src.layer3_personalization.creator_dna import build_creator_dna
from src.layer5_intelligence.optimizer import joint_optimize, get_top_k_recommendations


def counterfactual_analysis(content_id: str, context: EngagementContext):
    """Run counterfactual analysis for a content item."""
    item = context.get_content_item(content_id)
    if not item:
        print(f"Content ID {content_id} not found.")
        return

    creator = context.creators.get(item.creator_id)
    base = creator.base_engagement if creator else 1.0
    cooldown = creator.cooldown_hours if creator else 4

    dna = build_creator_dna(
        item.creator_id, base, cooldown,
        context.creator_history, context.all_platforms,
        context.all_content_types, context.system_average,
    )

    # Get top 5 and bottom recommendation
    top5 = get_top_k_recommendations(
        content_id, item.creator_id, item.content_type, dna, context, k=48
    )

    best = top5[0]
    worst = top5[-1]

    print(f"\n{'='*60}")
    print(f"  COUNTERFACTUAL ANALYSIS: Content {content_id}")
    print(f"  Creator: {item.creator_id} | Type: {item.content_type}")
    print(f"{'='*60}")
    print(f"\n  BEST scenario:")
    print(f"    Platform: {best.platform} at hour {best.recommended_slot}")
    print(f"    Score:    {best.score:.1f}")
    print(f"\n  WORST scenario:")
    print(f"    Platform: {worst.platform} at hour {worst.recommended_slot}")
    print(f"    Score:    {worst.score:.1f}")
    improvement = ((best.score - worst.score) / worst.score * 100) if worst.score > 0 else float('inf')
    print(f"\n  VALUE OF OPTIMIZATION: +{improvement:.1f}% improvement")
    print(f"  Score difference:     +{best.score - worst.score:.1f} points")
    print(f"\n  Top 5 alternatives:")
    for i, rec in enumerate(top5[:5], 1):
        print(f"    {i}. {rec.platform:10s} @ hour {rec.recommended_slot:2d} → {rec.score:.1f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--content-id", required=True)
    args = parser.parse_args()

    content = load_content_submissions(os.path.join(args.data_dir, "content.csv"))
    activity = load_platform_activity(os.path.join(args.data_dir, "platform_activity.csv"))
    history = load_historical_engagement(os.path.join(args.data_dir, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(args.data_dir, "creators.csv"))
    fallback = FallbackRegistry()
    context = EngagementContext(content=content, platform_activity=activity,
                                creator_history=history, creators=creators, fallback=fallback)
    counterfactual_analysis(args.content_id, context)
