"""
Creator Content Posting Optimization System — Main Entry Point
================================================================

Full pipeline with 22 Postiz-inspired layers:
  Load → Fuse → Profile → Momentum → Batch/Cooldown → Score → Explain → Validate → Output

Usage:
    python main.py
    python main.py --data-dir data/raw --output results/recommendations.json
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter
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
from src.layer1_foundation.state_machine import (
    ContentState, StatefulContent, generate_fallback_recommendation,
)
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
from src.layer4_scoring.weights import DEFAULT_WEIGHTS, SCHEDULE_THRESHOLDS, NEAR_SLOT_HOURS
from src.layer5_intelligence.optimizer import joint_optimize
from src.layer5_intelligence.scheduler import decide_schedule
from src.layer5_intelligence.cooldown_scheduler import (
    CreatorScheduleLock, group_by_creator, joint_optimize_with_cooldown,
)
from src.layer5_intelligence.momentum import (
    compute_all_momentum_scores, compute_engagement_trajectory,
)
from src.layer5_intelligence.affinity_matrix import get_content_platform_affinity
from src.layer6_output.output_formatter import (
    format_recommendation,
    validate_output,
    format_all_recommendations,
)
from src.layer6_output.evaluator import compute_eval_metrics
from src.layer6_output.explainer import (
    generate_explanation_sentence, build_score_trace,
)


# ─── Logging ─────────────────────────────────────────────────────────
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )


# ─── Data Richness Dashboard (Layer 18) ─────────────────────────────
def print_dashboard(context: EngagementContext, dna_profiles: dict, momentum_scores: dict):
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

    # Submission hour distribution (Layer 15)
    hour_counts = Counter(item.created_timestamp for item in context.content.values())
    peak_submit_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0

    # Momentum stats
    avg_momentum = sum(momentum_scores.values()) / max(len(momentum_scores), 1)

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
    print(f"  Avg Momentum Score:  {avg_momentum:.3f}")
    print(f"  Peak Submit Hour:    {peak_submit_hour}:00 ({hour_counts.get(peak_submit_hour, 0)} items)")
    print("=" * 60 + "\n")


# ─── Coverage Validator (Layer 10) ───────────────────────────────────
def validate_coverage(content_items: dict, recommendations: list) -> dict:
    """Ensure 100% coverage — no dropped items."""
    input_ids = set(content_items.keys())
    output_ids = {str(r["content_id"]) for r in recommendations}
    missing = input_ids - output_ids

    report = {
        "total_input": len(input_ids),
        "total_output": len(output_ids),
        "missing_ids": sorted(missing),
        "coverage_pct": len(output_ids) / max(len(input_ids), 1) * 100,
        "status": "COMPLETE" if not missing else "INCOMPLETE",
    }
    return report


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

    # ── Layer 17: Compute Momentum Scores ────────────────────────────
    print("⚡ Layer 17: Computing momentum scores...")
    momentum_scores = compute_all_momentum_scores(context)
    t_momentum = time.perf_counter()
    print(f"   ✅ Momentum computed in {(t_momentum - t_dna)*1000:.0f}ms")

    # Print dashboard
    print_dashboard(context, dna_profiles, momentum_scores)

    # ── LAYERS 4-5: Cooldown-Aware Batch Optimization ────────────────
    print("🧠 Layers 4-5: Cooldown-aware batch optimization...")

    # Build stateful content items (Layer 1 state machine)
    stateful_items = []
    for item_id in sorted(content.keys(), key=lambda x: int(x)):
        item = content[item_id]
        si = StatefulContent(
            content_id=int(item.content_id),
            creator_id=item.creator_id,
            content_type=item.content_type,
            created_timestamp=item.created_timestamp,
            time_sensitivity=item.time_sensitivity,
        )
        stateful_items.append(si)

    # Group by creator for batch processing (Layer 5)
    groups = group_by_creator(stateful_items)

    # Process each creator's batch with cooldown lock (Layer 2)
    recommendations = []
    error_count = 0

    for creator_id, items in sorted(groups.items(), key=lambda x: int(x[0])):
        # Get cooldown from creator profile
        cooldown = 4  # default
        if creator_id in creators:
            cooldown = creators[creator_id].cooldown_hours

        # Create per-creator schedule lock
        lock = CreatorScheduleLock(creator_id=creator_id, cooldown_hours=cooldown)

        # Get or build DNA profile
        if creator_id in dna_profiles:
            dna = dna_profiles[creator_id]
        else:
            dna = build_cold_start_profile(
                creator_id=creator_id,
                base_engagement=1.0,
                cooldown_hours=4,
                all_platforms=context.all_platforms,
                all_content_types=context.all_content_types,
                global_type_averages=global_type_avg,
                global_peak_slots=global_peak_slots,
            )

        for si in items:
            try:
                # Joint optimization with cooldown (Layer 2+4)
                best_platform, best_slot, best_score, breakdown = (
                    joint_optimize_with_cooldown(
                        content_id=str(si.content_id),
                        creator_id=si.creator_id,
                        content_type=si.content_type,
                        context=context,
                        lock=lock,
                    )
                )

                si.transition(ContentState.OPTIMIZED)

                # Scheduling decision
                schedule_result = decide_schedule(
                    creator_id=si.creator_id,
                    content_type=si.content_type,
                    submission_hour=si.created_timestamp,
                    best_platform=best_platform,
                    best_slot=best_slot,
                    best_score=best_score,
                    time_sensitivity=si.time_sensitivity,
                    context=context,
                )

                decision = schedule_result["decision"]
                si.transition(
                    ContentState.SCHEDULED if decision == "SCHEDULE"
                    else ContentState.COMPLETE
                )

                # Gain percentage
                current = schedule_result["current_slot_score"]
                optimal = schedule_result["optimal_slot_score"]
                gain_pct = round(
                    (optimal - current) / max(current, 0.01) * 100, 1
                ) if current > 0 else 0.0

                # Natural language explanation (Layer 20)
                nl_explanation = generate_explanation_sentence(
                    content_id=si.content_id,
                    creator_id=si.creator_id,
                    content_type=si.content_type,
                    platform=best_platform,
                    slot=best_slot,
                    decision=decision,
                    score=best_score,
                    history_score=breakdown["creator_history_raw"],
                    activity_score=breakdown["platform_activity_raw"],
                    gain_pct=gain_pct,
                )

                # Score trace (Layer 14)
                affinity = get_content_platform_affinity(si.content_type, best_platform)
                trace = build_score_trace(
                    si.creator_id, best_platform, best_slot,
                    si.content_type,
                    breakdown["platform_activity_raw"],
                    breakdown["creator_history_raw"],
                    breakdown["creator_base_raw"],
                    affinity,
                )

                # Engagement trajectory (Layer 12)
                trajectory = compute_engagement_trajectory(
                    si.creator_id, best_platform, context
                )

                # Full explanation block
                explanation = {
                    "platform_activity": breakdown["platform_activity_raw"],
                    "creator_history_score": breakdown["creator_history_raw"],
                    "creator_base": breakdown["creator_base_raw"],
                    "content_fit": breakdown["content_fit_raw"],
                    "current_slot_score": current,
                    "optimal_slot_score": optimal,
                    "gain_pct": gain_pct,
                    "schedule_threshold_met": schedule_result["threshold_met"],
                    "time_sensitivity": si.time_sensitivity,
                    "momentum": momentum_scores.get(si.creator_id, 0.5),
                    "trajectory": trajectory["trend"],
                    "trajectory_factor": trajectory["trajectory_factor"],
                    "cooldown_respected": True,
                    "score_trace": trace,
                    "natural_language": nl_explanation,
                }

                rec = format_recommendation(
                    content_id=si.content_id,
                    platform=best_platform,
                    recommended_slot=best_slot,
                    decision=decision,
                    score=best_score,
                    confidence=dna.confidence_label if hasattr(dna, 'confidence_label') else "HIGH",
                    explanation=explanation,
                )
                si.recommendation = rec
                recommendations.append(rec)

            except Exception as e:
                logger.error(f"Error optimizing content #{si.content_id}: {e}")
                si.error = str(e)
                si.transition(ContentState.ERROR)
                fallback_rec = generate_fallback_recommendation(si)
                si.recommendation = fallback_rec
                recommendations.append(fallback_rec)
                error_count += 1

    # Sort by content_id for deterministic output
    recommendations.sort(key=lambda r: r["content_id"])

    t_optimize = time.perf_counter()
    print(f"   ✅ Processed {len(recommendations)} items in {(t_optimize - t_momentum)*1000:.0f}ms")
    if error_count > 0:
        print(f"   ⚠️  {error_count} items used fallback recommendations")

    # ── LAYER 6: Output & Evaluate ───────────────────────────────────
    print("🖨️  Layer 6: Formatting output...")

    # Coverage validation (Layer 10)
    coverage = validate_coverage(content, recommendations)
    if coverage["status"] != "COMPLETE":
        logger.warning(f"Coverage incomplete! Missing: {coverage['missing_ids']}")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    output_json = format_all_recommendations(recommendations, output_path)

    # Evaluation metrics
    metrics = compute_eval_metrics(recommendations, context)

    # Input hash for determinism proof (Layer 21)
    input_hash = hashlib.sha256(
        open(os.path.join(data_dir, "content.csv"), "rb").read()
    ).hexdigest()[:12]

    t_end = time.perf_counter()

    # ── Summary ──────────────────────────────────────────────────────
    schedule_count = sum(1 for r in recommendations if r["decision"] == "SCHEDULE")
    postnow_count = len(recommendations) - schedule_count

    platform_dist = {}
    for r in recommendations:
        p = r["platform"]
        platform_dist[p] = platform_dist.get(p, 0) + 1

    # Cooldown stats
    cooldown_violations = 0
    for creator_id, items in groups.items():
        slots = [r["recommended_slot"] for r in recommendations
                 if str(r["content_id"]) in {str(i.content_id) for i in items}
                 and r["decision"] == "SCHEDULE"]
        cd = creators[creator_id].cooldown_hours if creator_id in creators else 4
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                if abs(slots[i] - slots[j]) < cd:
                    cooldown_violations += 1

    print("\n" + "=" * 60)
    print("  📊  RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total recommendations:  {len(recommendations)}")
    print(f"  SCHEDULE decisions:     {schedule_count}")
    print(f"  POST_NOW decisions:     {postnow_count}")
    for p, count in sorted(platform_dist.items()):
        print(f"  {p} selections:  {count}")
    print(f"  Cooldown violations:    {cooldown_violations}")
    print(f"  Coverage:               {coverage['coverage_pct']:.0f}% ({coverage['status']})")
    print(f"  Input hash:             {input_hash}")
    print(f"\n  📈 Evaluation Metrics:")
    print(f"     Engagement Score:     {metrics['engagement_score']:.4f}")
    print(f"     Timing Effectiveness: {metrics['timing_effectiveness']:.4f}")
    print(f"     Platform Quality:     {metrics['platform_quality']:.4f}")
    print(f"     Efficiency Score:     {metrics['efficiency_score']:.4f}")
    print(f"     ─────────────────────────────")
    print(f"     Composite Score:      {metrics['composite_score']:.4f}")
    print(f"\n  ⏱️  Total pipeline time:  {(t_end - t_start)*1000:.0f}ms")
    print(f"  💾 Output written to:    {output_path}")
    print("=" * 60 + "\n")

    # Save metrics
    metrics_path = output_path.replace(".json", "_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump({
            **metrics,
            "input_hash": input_hash,
            "coverage": coverage,
            "cooldown_violations": cooldown_violations,
            "pipeline_time_ms": round((t_end - t_start) * 1000),
        }, f, indent=2)

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
