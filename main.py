"""
Creator Content Posting Optimization System — Main Entry Point
================================================================

Full pipeline: Load → Fuse → Profile → Score → Optimize → Schedule → Output

Usage:
    python main.py
    python main.py --data-dir data/raw --output results/recommendations.json
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# ─── Setup Python path ──────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.layer1_foundation.data_loader import (
    load_content_submissions,
    load_platform_activity,
    load_historical_engagement,
    load_creator_profiles,
)
from src.layer1_foundation.fallback_registry import FallbackRegistry
from src.layer2_fusion.context import EngagementContext
from src.layer2_fusion.preprocessor import compute_platform_stats
from src.layer3_personalization.creator_dna import build_creator_dna
from src.layer3_personalization.cold_start import (
    build_cold_start_profile,
    compute_global_type_averages,
    compute_global_peak_slots,
    is_cold_start,
    COLD_START_THRESHOLD,
)
from src.layer4_scoring.weights import DEFAULT_WEIGHTS
from src.layer5_intelligence.optimizer import joint_optimize, joint_optimize_with_cooldown
from src.layer5_intelligence.scheduler import decide_schedule
from src.layer6_output.output_formatter import (
    format_recommendation,
    validate_output,
    format_all_recommendations,
)
from src.layer6_output.evaluator import compute_eval_metrics


# ─── Logging ─────────────────────────────────────────────────────────
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )


# ─── Data Richness Dashboard ────────────────────────────────────────
def print_dashboard(context: EngagementContext, dna_profiles: dict):
    """Print a startup dashboard showing data coverage."""
    total_creators = len(context.creators)
    creators_with_history = len({
        cid for (cid, _, _, _) in context.creator_history
    })
    cold_start_count = sum(
        1 for dna in dna_profiles.values() if is_cold_start(dna)
    )

    platforms = sorted(context.all_platforms)
    platform_coverage = {}
    for p in platforms:
        covered_slots = sum(
            1 for s in range(24)
            if (p, s) in context.platform_activity
        )
        platform_coverage[p] = f"{covered_slots}h/24h"

    content_types = sorted(context.all_content_types)

    print("\n" + "=" * 60)
    print("  🛡️  DATA RICHNESS DASHBOARD")
    print("=" * 60)
    print(f"  Creator Coverage:    {creators_with_history}/{total_creators} "
          f"creators have history ({creators_with_history/max(total_creators,1)*100:.1f}%)")
    plat_str = " | ".join(f"{p}: {c}" for p, c in platform_coverage.items())
    print(f"  Platform Coverage:   {plat_str}")
    type_str = " ".join(f"{t} ✅" for t in content_types)
    print(f"  Content Type Cover:  {type_str}")
    print(f"  Cold-Start Creators: {cold_start_count} (using global averages)")
    print(f"  Total Content Items: {len(context.content)}")
    print(f"  System Avg Engage:   {context.system_average:.3f}")
    print("=" * 60 + "\n")


# ─── Main Pipeline ──────────────────────────────────────────────────
def run_pipeline(data_dir: str, output_path: str, verbose: bool = False):
    setup_logging(verbose)
    logger = logging.getLogger("main")

    t_start = time.perf_counter()
    print("\n🚀 Creator Content Posting Optimization System")
    print("─" * 50)

    # ── LAYER 1: Load Data ───────────────────────────────────────────
    print("📦 Layer 1: Loading data...")
    content = load_content_submissions(os.path.join(data_dir, "content.csv"))
    activity = load_platform_activity(os.path.join(data_dir, "platform_activity.csv"))
    history = load_historical_engagement(os.path.join(data_dir, "historical_engagement.csv"))
    creators = load_creator_profiles(os.path.join(data_dir, "creators.csv"))
    t_load = time.perf_counter()
    print(f"   ✅ Loaded in {(t_load - t_start)*1000:.0f}ms")

    # Log scoring configuration
    from src.layer4_scoring.weights import DEFAULT_WEIGHTS
    print(f"   ⚙️  Weights: PA={DEFAULT_WEIGHTS.w_platform_activity} CH={DEFAULT_WEIGHTS.w_creator_history} "
          f"CB={DEFAULT_WEIGHTS.w_creator_base} CF={DEFAULT_WEIGHTS.w_content_fit}")

    # ── LAYER 2: Fuse Data ───────────────────────────────────────────
    print("🔗 Layer 2: Building EngagementContext...")
    fallback = FallbackRegistry()
    context = EngagementContext(
        content=content,
        platform_activity=activity,
        creator_history=history,
        creators=creators,
        fallback=fallback,
    )
    platform_stats = compute_platform_stats(activity)
    t_fuse = time.perf_counter()
    print(f"   ✅ Context built in {(t_fuse - t_load)*1000:.0f}ms")

    # ── LAYER 3: Build Creator DNA Profiles ──────────────────────────
    print("🧬 Layer 3: Building Creator DNA profiles...")
    global_type_avg = compute_global_type_averages(history, context.all_content_types)
    global_peak_slots = compute_global_peak_slots(history, context.all_platforms)

    dna_profiles = {}
    for cid, profile in creators.items():
        dna = build_creator_dna(
            creator_id=cid,
            base_engagement=profile.base_engagement,
            cooldown_hours=profile.cooldown_hours,
            creator_history=history,
            all_platforms=context.all_platforms,
            all_content_types=context.all_content_types,
            system_average=context.system_average,
        )

        # Apply cold-start if needed
        if is_cold_start(dna):
            dna = build_cold_start_profile(
                creator_id=cid,
                base_engagement=profile.base_engagement,
                cooldown_hours=profile.cooldown_hours,
                all_platforms=context.all_platforms,
                all_content_types=context.all_content_types,
                global_type_averages=global_type_avg,
                global_peak_slots=global_peak_slots,
            )

        dna_profiles[cid] = dna

    t_dna = time.perf_counter()
    print(f"   ✅ Built {len(dna_profiles)} profiles in {(t_dna - t_fuse)*1000:.0f}ms")

    # Print dashboard
    print_dashboard(context, dna_profiles)

    # ── LAYERS 4+5: Score + Optimize + Schedule ──────────────────────
    print("🧠 Layers 4-5: Scoring & Optimizing (with cooldown enforcement)...")
    recommendations = []
    occupied_slots = {}  # creator_id → set of (platform, slot) for cooldown tracking

    for item_id in sorted(content.keys(), key=lambda x: int(x)):  # deterministic order
        item = content[item_id]

        # Get or create DNA profile
        if item.creator_id in dna_profiles:
            dna = dna_profiles[item.creator_id]
        else:
            # Creator not in profiles — build cold-start
            dna = build_cold_start_profile(
                creator_id=item.creator_id,
                base_engagement=1.0,
                cooldown_hours=4,
                all_platforms=context.all_platforms,
                all_content_types=context.all_content_types,
                global_type_averages=global_type_avg,
                global_peak_slots=global_peak_slots,
            )

        # Joint optimization with cooldown constraint enforcement
        best = joint_optimize_with_cooldown(
            content_id=item.content_id,
            creator_id=item.creator_id,
            content_type=item.content_type,
            creator_dna=dna,
            context=context,
            occupied_slots=occupied_slots,
        )

        # Track occupied slot for this creator's cooldown window
        if item.creator_id not in occupied_slots:
            occupied_slots[item.creator_id] = set()
        occupied_slots[item.creator_id].add((best.platform, best.recommended_slot))

        # Scheduling decision
        schedule_result = decide_schedule(
            creator_id=item.creator_id,
            content_type=item.content_type,
            submission_hour=item.created_timestamp,
            best_platform=best.platform,
            best_slot=best.recommended_slot,
            best_score=best.score,
            time_sensitivity=item.time_sensitivity,
            context=context,
        )

        # Format output
        explanation = {
            "platform_activity": best.breakdown["platform_activity_raw"],
            "creator_history_score": best.breakdown["creator_history_raw"],
            "creator_base": best.breakdown["creator_base_raw"],
            "content_fit": best.breakdown["content_fit_raw"],
            "current_slot_score": schedule_result["current_slot_score"],
            "optimal_slot_score": schedule_result["optimal_slot_score"],
            "schedule_threshold_met": schedule_result["threshold_met"],
            "time_sensitivity": item.time_sensitivity,
        }

        rec = format_recommendation(
            content_id=item.content_id,
            platform=best.platform,
            recommended_slot=best.recommended_slot,
            decision=schedule_result["decision"],
            score=best.score,
            confidence=best.confidence,
            explanation=explanation,
        )
        recommendations.append(rec)

    t_optimize = time.perf_counter()
    print(f"   ✅ Processed {len(recommendations)} items in {(t_optimize - t_dna)*1000:.0f}ms")

    # ── LAYER 6: Output & Evaluate ───────────────────────────────────
    print("🖨️  Layer 6: Formatting output...")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    output_json = format_all_recommendations(recommendations, output_path)

    # Evaluation metrics
    metrics = compute_eval_metrics(recommendations, context)
    t_end = time.perf_counter()

    # ── Summary ──────────────────────────────────────────────────────
    schedule_count = sum(1 for r in recommendations if r["decision"] == "SCHEDULE")
    postnow_count = len(recommendations) - schedule_count

    platform_dist = {}
    for r in recommendations:
        p = r["platform"]
        platform_dist[p] = platform_dist.get(p, 0) + 1

    print("\n" + "=" * 60)
    print("  📊  RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total recommendations:  {len(recommendations)}")
    print(f"  SCHEDULE decisions:     {schedule_count}")
    print(f"  POST_NOW decisions:     {postnow_count}")
    for p, count in sorted(platform_dist.items()):
        print(f"  {p} selections:  {count}")
    print(f"\n  📈 Evaluation Metrics:")
    print(f"     Engagement Score:     {metrics['engagement_score']:.4f}")
    print(f"     Timing Effectiveness: {metrics['timing_effectiveness']:.4f}")
    print(f"     Platform Quality:     {metrics['platform_quality']:.4f}")
    print(f"     Efficiency Score:     {metrics['efficiency_score']:.4f}")
    print(f"     ─────────────────────────────")
    print(f"     Composite Score:      {metrics['composite_score']:.4f}")
    print(f"\n  ⏱️  Total pipeline time:  {(t_end - t_start)*1000:.0f}ms")
    print(f"  💾 Output written to:    {output_path}")
    print("=" * 60)
    print(f"\n  🎯 COMPOSITE SCORE: {metrics['composite_score']:.4f}")
    print("=" * 60 + "\n")

    # Save metrics
    metrics_path = output_path.replace(".json", "_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return recommendations, metrics


# ─── CLI ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Creator Content Posting Optimization System (PS4)"
    )
    parser.add_argument(
        "--data-dir", default="data/raw",
        help="Directory containing input CSV files (default: data/raw)"
    )
    parser.add_argument(
        "--output", default="results/recommendations.json",
        help="Output file path (default: results/recommendations.json)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    run_pipeline(args.data_dir, args.output, args.verbose)


if __name__ == "__main__":
    main()
