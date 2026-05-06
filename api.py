"""
PostOptima — FastAPI REST API Layer
====================================
Wraps the 6-layer Python engine with REST endpoints for the React frontend.

Usage:
    python api.py
    → Runs on http://localhost:8000
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Path setup ──────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.layer1_foundation.data_loader import (
    load_content_submissions, load_platform_activity,
    load_historical_engagement, load_creator_profiles,
)
from src.layer1_foundation.fallback_registry import FallbackRegistry
from src.layer2_fusion.context import EngagementContext
from src.layer2_fusion.preprocessor import compute_platform_stats
from src.layer3_personalization.creator_dna import build_creator_dna
from src.layer3_personalization.cold_start import (
    build_cold_start_profile, compute_global_type_averages,
    compute_global_peak_slots, is_cold_start,
)
from src.layer4_scoring.scorer import compute_score, compute_score_with_breakdown
from src.layer5_intelligence.optimizer import joint_optimize, get_top_k_recommendations
from src.layer5_intelligence.scheduler import decide_schedule
from src.layer5_intelligence.affinity_matrix import get_content_platform_affinity
from src.layer6_output.output_formatter import format_recommendation
from src.layer6_output.evaluator import compute_eval_metrics
from extras.trajectory import compute_trajectory

# ─── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")
logger = logging.getLogger("api")

# ─── Load Data Once at Startup ───────────────────────────────────────
DATA_DIR = os.environ.get("DATA_DIR", "data/raw")

content = load_content_submissions(os.path.join(DATA_DIR, "content.csv"))
activity = load_platform_activity(os.path.join(DATA_DIR, "platform_activity.csv"))
history = load_historical_engagement(os.path.join(DATA_DIR, "historical_engagement.csv"))
creators = load_creator_profiles(os.path.join(DATA_DIR, "creators.csv"))
fallback = FallbackRegistry()

context = EngagementContext(
    content=content, platform_activity=activity,
    creator_history=history, creators=creators, fallback=fallback,
)
platform_stats = compute_platform_stats(activity)
global_type_avg = compute_global_type_averages(history, context.all_content_types)
global_peak_slots = compute_global_peak_slots(history, context.all_platforms)

# Build all DNA profiles
dna_profiles = {}
for cid, profile in creators.items():
    dna = build_creator_dna(
        cid, profile.base_engagement, profile.cooldown_hours,
        history, context.all_platforms, context.all_content_types,
        context.system_average,
    )
    if is_cold_start(dna):
        dna = build_cold_start_profile(
            cid, profile.base_engagement, profile.cooldown_hours,
            context.all_platforms, context.all_content_types,
            global_type_avg, global_peak_slots,
        )
    dna_profiles[cid] = dna

# Pre-compute all recommendations using the SAME engine as main.py
# This ensures frontend sees identical scores to the CLI pipeline
RESULTS_FILE = os.path.join(ROOT_DIR, "results", "recommendations.json")

def _load_or_compute_recommendations():
    """Load recommendations from main.py's output, or run pipeline if missing."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            recs = json.load(f)
        # Enrich with content metadata for the API
        enriched = []
        for rec in recs:
            cid = str(rec["content_id"])
            item = content.get(cid)
            enriched.append({
                **rec,
                "creator_id": item.creator_id if item else "?",
                "content_type": item.content_type if item else "?",
                "submission_hour": item.created_timestamp if item else 0,
                "time_sensitivity": item.time_sensitivity if item else "Medium",
            })
        return enriched
    else:
        # Fallback: run main.py pipeline
        logger.warning("results/recommendations.json not found — running pipeline...")
        import subprocess
        subprocess.run([sys.executable, "main.py", "--data-dir", DATA_DIR,
                       "--output", RESULTS_FILE], cwd=str(ROOT_DIR), check=True)
        return _load_or_compute_recommendations()

all_recommendations = _load_or_compute_recommendations()
metrics = compute_eval_metrics(all_recommendations, context)
logger.info(f"Loaded {len(all_recommendations)} recommendations. Composite: {metrics['composite_score']:.4f}")

# ─── FastAPI App ─────────────────────────────────────────────────────
app = FastAPI(title="PostOptima API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ──────────────────────────────────────────────────
class OptimizeRequest(BaseModel):
    creator_id: str
    content_type: str   # SHORT or LONG
    submission_hour: int
    time_sensitivity: str = "Medium"


# ─── Endpoints ───────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "live", "items": len(content), "creators": len(creators)}


@app.get("/api/stats")
def get_stats():
    schedule_count = sum(1 for r in all_recommendations if r["decision"] == "SCHEDULE")
    scores = [r["score"] for r in all_recommendations]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Compute avg lift
    lifts = []
    for r in all_recommendations:
        ex = r.get("explanation", {})
        current = ex.get("current_slot_score", 0)
        optimal = ex.get("optimal_slot_score", 0)
        if current > 0:
            lifts.append((optimal - current) / current * 100)
    avg_lift = sum(lifts) / len(lifts) if lifts else 0

    return {
        "total_posts": len(all_recommendations),
        "avg_score": round(avg_score, 1),
        "avg_lift": round(avg_lift, 1),
        "scheduled": schedule_count,
        "post_now": len(all_recommendations) - schedule_count,
        "total_creators": len(creators),
        "metrics": metrics,
    }


@app.get("/api/recommendations")
def get_recommendations(limit: int = 100, sort_by: str = "score"):
    recs = sorted(all_recommendations, key=lambda r: -r.get("score", 0))
    return recs[:limit]


@app.get("/api/heatmap")
def get_heatmap():
    """Returns platform activity as a 2D grid for the heatmap visualization."""
    data = {}
    for platform in sorted(context.all_platforms):
        slots = []
        for hour in range(24):
            slots.append({
                "hour": hour,
                "activity": context.get_platform_activity(platform, hour),
            })
        data[platform] = slots
    return data


@app.get("/api/creators")
def list_creators():
    result = []
    for cid, profile in sorted(creators.items(), key=lambda x: int(x[0])):
        dna = dna_profiles.get(cid)
        creator_recs = [r for r in all_recommendations if r["creator_id"] == cid]
        avg_score = sum(r["score"] for r in creator_recs) / len(creator_recs) if creator_recs else 0

        result.append({
            "creator_id": cid,
            "base_engagement": profile.base_engagement,
            "cooldown_hours": profile.cooldown_hours,
            "total_posts": len(creator_recs),
            "avg_score": round(avg_score, 1),
            "data_richness": round(dna.data_richness, 2) if dna else 0,
            "is_cold_start": is_cold_start(dna) if dna else True,
        })
    return result


@app.get("/api/creators/{creator_id}")
def get_creator(creator_id: str):
    profile = creators.get(creator_id)
    if not profile:
        return {"error": "Creator not found"}

    dna = dna_profiles.get(creator_id)
    trajectories = compute_trajectory(creator_id, history, context.all_platforms)
    creator_recs = [r for r in all_recommendations if r["creator_id"] == creator_id]

    return {
        "creator_id": creator_id,
        "base_engagement": profile.base_engagement,
        "cooldown_hours": profile.cooldown_hours,
        "platform_affinity": dna.platform_affinity if dna else {},
        "type_affinity": dna.type_affinity if dna else {},
        "peak_slots": dna.peak_slots if dna else {},
        "data_richness": round(dna.data_richness, 2) if dna else 0,
        "is_cold_start": is_cold_start(dna) if dna else True,
        "trajectory": trajectories,
        "recommendations": creator_recs,
    }


@app.get("/api/creators/{creator_id}/heatmap")
def get_creator_heatmap(creator_id: str, content_type: str = "SHORT"):
    """Engagement heatmap for a specific creator."""
    data = {}
    for platform in sorted(context.all_platforms):
        content_fit = get_content_platform_affinity(content_type, platform)
        slots = []
        for hour in range(24):
            score = compute_score(
                platform_activity=context.get_platform_activity(platform, hour),
                creator_history=context.get_creator_history(creator_id, platform, content_type, hour),
                creator_base=context.get_base_engagement(creator_id),
                content_fit=content_fit,
            )
            slots.append({"hour": hour, "score": round(score, 2)})
        data[platform] = slots
    return data


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    """Run the optimizer on a custom submission."""
    cid = req.creator_id
    ctype = req.content_type.upper()

    dna = dna_profiles.get(cid)
    if not dna:
        dna = build_cold_start_profile(
            cid, 1.0, 4, context.all_platforms,
            context.all_content_types, global_type_avg, global_peak_slots,
        )

    # Get all 48 candidates
    top_all = get_top_k_recommendations(
        f"custom_{cid}", cid, ctype, dna, context, k=48,
    )

    best = top_all[0]
    worst = top_all[-1]

    sched = decide_schedule(
        cid, ctype, req.submission_hour,
        best.platform, best.recommended_slot, best.score,
        req.time_sensitivity, context,
    )

    # Build candidates list
    candidates = []
    for i, rec in enumerate(top_all):
        candidates.append({
            "rank": i + 1,
            "platform": rec.platform,
            "slot": rec.recommended_slot,
            "score": rec.score,
            "breakdown": rec.breakdown,
        })

    # Compute lift
    current_score = sched["current_slot_score"]
    lift_pct = ((best.score - current_score) / current_score * 100) if current_score > 0 else 0

    return {
        "best": {
            "platform": best.platform,
            "recommended_slot": best.recommended_slot,
            "score": best.score,
            "decision": sched["decision"],
            "confidence": best.confidence,
            "breakdown": best.breakdown,
        },
        "worst": {
            "platform": worst.platform,
            "slot": worst.recommended_slot,
            "score": worst.score,
        },
        "current_score": current_score,
        "lift_percent": round(lift_pct, 1),
        "schedule_info": sched,
        "candidates": candidates,
        "creator_dna": {
            "base_multiplier": dna.base_multiplier,
            "platform_affinity": dna.platform_affinity,
            "type_affinity": dna.type_affinity,
            "data_richness": round(dna.data_richness, 2),
            "is_cold_start": is_cold_start(dna),
            "trajectory": compute_trajectory(cid, history, context.all_platforms),
        },
    }


@app.get("/api/counterfactual/{content_id}")
def counterfactual(content_id: str):
    item = context.get_content_item(content_id)
    if not item:
        return {"error": "Content not found"}

    dna = dna_profiles.get(item.creator_id)
    if not dna:
        return {"error": "Creator DNA not found"}

    top_all = get_top_k_recommendations(
        content_id, item.creator_id, item.content_type, dna, context, k=48,
    )

    best = top_all[0]
    worst = top_all[-1]
    avg_score = sum(r.score for r in top_all) / len(top_all)

    return {
        "content_id": content_id,
        "creator_id": item.creator_id,
        "optimal": {"platform": best.platform, "slot": best.recommended_slot, "score": best.score},
        "worst": {"platform": worst.platform, "slot": worst.recommended_slot, "score": worst.score},
        "random_baseline": round(avg_score, 2),
        "optimizer_value": round(best.score - avg_score, 2),
        "improvement_pct": round((best.score - worst.score) / worst.score * 100, 1) if worst.score > 0 else 0,
    }



# ══════════════════════════════════════════════════════════════════════
# Analytics Endpoints (from analytics_plan.md)
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/analytics/scorecard/{creator_id}")
def analytics_scorecard(creator_id: str):
    """Panel 1 — Creator Scorecard: base engagement, global avg, best platform/type."""
    profile = creators.get(creator_id)
    if not profile:
        return {"error": "Creator not found"}

    # Compute global avg engagement for this creator
    creator_scores = [v for (cid, _, _, _), v in history.items() if cid == creator_id]
    global_avg = sum(creator_scores) / len(creator_scores) if creator_scores else 0

    # Best platform
    platform_avgs = {}
    for (cid, plat, _, _), v in history.items():
        if cid == creator_id:
            platform_avgs.setdefault(plat, []).append(v)
    best_platform = max(platform_avgs, key=lambda p: sum(platform_avgs[p]) / len(platform_avgs[p])) if platform_avgs else "Unknown"

    # Best content type
    type_avgs = {}
    for (cid, _, ct, _), v in history.items():
        if cid == creator_id:
            type_avgs.setdefault(ct, []).append(v)
    best_type = max(type_avgs, key=lambda t: sum(type_avgs[t]) / len(type_avgs[t])) if type_avgs else "Unknown"

    # Total submissions
    creator_content = [c for c in content.values() if c.creator_id == creator_id]

    # Engagement label
    be = profile.base_engagement
    label = "Power Creator" if be > 1.10 else "Average" if be >= 0.80 else "Below Average"

    return {
        "creator_id": creator_id,
        "base_engagement": be,
        "engagement_label": label,
        "global_avg_engagement": round(global_avg, 3),
        "best_platform": best_platform,
        "best_content_type": best_type,
        "cooldown_hours": profile.cooldown_hours,
        "total_submissions": len(creator_content),
    }


@app.get("/api/analytics/heatmap/{creator_id}")
def analytics_heatmap(creator_id: str):
    """Panel 2 — Personalized Engagement Heatmap: 24 × 2 grid, normalized per creator."""
    data = {}
    all_scores = []

    for platform in sorted(context.all_platforms):
        slots = []
        for hour in range(24):
            # Average across content types
            scores_for_slot = []
            for ct in context.all_content_types:
                val = history.get((creator_id, platform, ct, hour), 0)
                if val > 0:
                    scores_for_slot.append(val)
            avg = sum(scores_for_slot) / len(scores_for_slot) if scores_for_slot else 0
            is_peak = context.get_platform_activity(platform, hour) >= 1.0
            slots.append({"hour": hour, "score": round(avg, 3), "is_peak": is_peak})
            all_scores.append(avg)
        data[platform] = slots

    # Find personal peak
    global_min = min(all_scores) if all_scores else 0
    global_max = max(all_scores) if all_scores else 1
    best_slot = None
    best_score = -1
    for plat, slots in data.items():
        for s in slots:
            if s["score"] > best_score:
                best_score = s["score"]
                best_slot = {"platform": plat, "hour": s["hour"]}

    return {
        "heatmap": data,
        "global_min": round(global_min, 3),
        "global_max": round(global_max, 3),
        "personal_peak": best_slot,
    }


@app.get("/api/analytics/platform-breakdown/{creator_id}")
def analytics_platform_breakdown(creator_id: str):
    """Panel 3 — Platform × Content Type breakdown with affinity ratio."""
    breakdown = {}
    for platform in sorted(context.all_platforms):
        for ct in sorted(context.all_content_types):
            scores = []
            best_slot = 0
            best_val = -1
            for hour in range(24):
                val = history.get((creator_id, platform, ct, hour), 0)
                scores.append(val)
                if val > best_val:
                    best_val = val
                    best_slot = hour
            avg = sum(scores) / len(scores) if scores else 0
            breakdown[f"{platform}_{ct}"] = {
                "platform": platform,
                "content_type": ct,
                "avg_engagement": round(avg, 3),
                "peak_engagement": round(best_val, 3),
                "best_slot": best_slot,
            }

    # Platform affinity ratio
    ig_avg = sum(v for (cid, p, _, _), v in history.items() if cid == creator_id and p == "Instagram") / max(1, sum(1 for (cid, p, _, _) in history if cid == creator_id and p == "Instagram"))
    yt_avg = sum(v for (cid, p, _, _), v in history.items() if cid == creator_id and p == "YouTube") / max(1, sum(1 for (cid, p, _, _) in history if cid == creator_id and p == "YouTube"))
    ratio = round(ig_avg / yt_avg, 2) if yt_avg > 0 else 0
    affinity_text = f"You perform {ratio}× better on Instagram than YouTube overall." if ratio > 1 else f"You perform {round(1/ratio, 2) if ratio > 0 else 0}× better on YouTube than Instagram overall."

    return {
        "breakdown": breakdown,
        "ig_avg": round(ig_avg, 3),
        "yt_avg": round(yt_avg, 3),
        "affinity_ratio": ratio,
        "affinity_text": affinity_text,
    }


@app.get("/api/analytics/content-history/{creator_id}")
def analytics_content_history(creator_id: str):
    """Panel 4 — Content Performance History table."""
    creator_content = [c for c in content.values() if c.creator_id == creator_id]
    rows = []
    for item in sorted(creator_content, key=lambda c: int(c.content_id), reverse=True):
        rec = next((r for r in all_recommendations if r["content_id"] == item.content_id), None)
        ex = rec.get("explanation", {}) if rec else {}
        current = ex.get("current_slot_score", 0)
        optimal = ex.get("optimal_slot_score", 0)
        gain = ((optimal - current) / current * 100) if current > 0 else 0

        rows.append({
            "content_id": item.content_id,
            "content_type": item.content_type,
            "submitted_hour": item.created_timestamp,
            "time_sensitivity": item.time_sensitivity,
            "platform": rec["platform"] if rec else None,
            "recommended_slot": rec["recommended_slot"] if rec else None,
            "decision": rec["decision"] if rec else "Pending",
            "score": rec["score"] if rec else None,
            "gain_pct": round(gain, 1),
            "confidence": rec["confidence"] if rec else None,
            "is_hook_score": item.content_type == "SHORT" and rec and rec["score"] > 75,
        })
    return rows


@app.get("/api/analytics/timing-audit/{creator_id}")
def analytics_timing_audit(creator_id: str):
    """Panel 5 — Submission Timing Audit: gap between when you post vs when you should."""
    creator_content = [c for c in content.values() if c.creator_id == creator_id]
    creator_recs = [r for r in all_recommendations if r["creator_id"] == creator_id]

    if not creator_content:
        return {"error": "No content found"}

    hours = [c.created_timestamp for c in creator_content]
    avg_hour = sum(hours) / len(hours)

    # Personal peak hour (from historical engagement)
    slot_scores = {}
    for (cid, _, _, slot), v in history.items():
        if cid == creator_id:
            slot_scores.setdefault(slot, []).append(v)
    peak_hour = max(slot_scores, key=lambda s: sum(slot_scores[s]) / len(slot_scores[s])) if slot_scores else 12

    # Peak window submissions (18-22)
    peak_submissions = sum(1 for h in hours if 18 <= h <= 22)
    peak_pct = round(peak_submissions / len(hours) * 100, 1)

    # Avg gain across SCHEDULE decisions
    sched_gains = []
    for r in creator_recs:
        ex = r.get("explanation", {})
        current = ex.get("current_slot_score", 0)
        optimal = ex.get("optimal_slot_score", 0)
        if current > 0 and r["decision"] == "SCHEDULE":
            sched_gains.append((optimal - current) / current * 100)
    avg_gain = round(sum(sched_gains) / len(sched_gains), 1) if sched_gains else 0

    # Hour distribution (24 bars)
    distribution = [0] * 24
    for h in hours:
        distribution[h] += 1

    # Personal engagement curve (24h)
    engagement_curve = []
    for h in range(24):
        vals = [v for (cid, _, _, slot), v in history.items() if cid == creator_id and slot == h]
        engagement_curve.append(round(sum(vals) / len(vals), 3) if vals else 0)

    return {
        "avg_submission_hour": round(avg_hour, 1),
        "personal_peak_hour": peak_hour,
        "gap_hours": abs(round(avg_hour - peak_hour)),
        "peak_window_pct": peak_pct,
        "avg_potential_gain": avg_gain,
        "total_submissions": len(creator_content),
        "scheduled_count": sum(1 for r in creator_recs if r["decision"] == "SCHEDULE"),
        "posted_now_count": sum(1 for r in creator_recs if r["decision"] == "POST_NOW"),
        "hour_distribution": distribution,
        "engagement_curve": engagement_curve,
    }


@app.get("/api/analytics/optimizer-impact/{creator_id}")
def analytics_optimizer_impact(creator_id: str):
    """Panel 6 — Optimizer Impact: quantifies the system's value for this creator."""
    creator_recs = [r for r in all_recommendations if r["creator_id"] == creator_id]
    if not creator_recs:
        return {"error": "No recommendations found"}

    scores = [r["score"] for r in creator_recs]
    best_score = max(scores)
    best_rec = max(creator_recs, key=lambda r: r["score"])

    # Compute submission scores and gains
    uplifts = []
    gains = []
    for r in creator_recs:
        ex = r.get("explanation", {})
        current = ex.get("current_slot_score", 0)
        optimal = ex.get("optimal_slot_score", 0)
        if current > 0:
            uplifts.append(optimal - current)
            gains.append((optimal - current) / current * 100)

    # Worst counterfactual
    dna = dna_profiles.get(creator_id)
    worst_score = min(scores) if scores else 0

    # Confidence breakdown
    high = sum(1 for r in creator_recs if r["confidence"] == "HIGH")
    medium = sum(1 for r in creator_recs if r["confidence"] == "MEDIUM")
    low = sum(1 for r in creator_recs if r["confidence"] == "LOW")

    schedule_rate = sum(1 for r in creator_recs if r["decision"] == "SCHEDULE") / len(creator_recs) * 100

    return {
        "best_score": best_score,
        "best_recommendation": {
            "platform": best_rec["platform"],
            "slot": best_rec["recommended_slot"],
            "content_id": best_rec["content_id"],
        },
        "worst_score": worst_score,
        "score_gap": round(best_score - worst_score, 1),
        "avg_score_uplift": round(sum(uplifts) / len(uplifts), 2) if uplifts else 0,
        "avg_gain_pct": round(sum(gains) / len(gains), 1) if gains else 0,
        "max_single_gain": round(max(gains), 1) if gains else 0,
        "schedule_rate_pct": round(schedule_rate, 1),
        "confidence_breakdown": {"HIGH": high, "MEDIUM": medium, "LOW": low},
        "total_recommendations": len(creator_recs),
    }


# ─── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
