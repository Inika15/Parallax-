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

# Pre-compute all recommendations
all_recommendations = []
for item_id in sorted(content.keys(), key=lambda x: int(x)):
    item = content[item_id]
    dna = dna_profiles.get(item.creator_id)
    if not dna:
        dna = build_cold_start_profile(
            item.creator_id, 1.0, 4,
            context.all_platforms, context.all_content_types,
            global_type_avg, global_peak_slots,
        )

    best = joint_optimize(item.content_id, item.creator_id, item.content_type, dna, context)
    sched = decide_schedule(
        item.creator_id, item.content_type, item.created_timestamp,
        best.platform, best.recommended_slot, best.score,
        item.time_sensitivity, context,
    )

    rec = {
        "content_id": item.content_id,
        "creator_id": item.creator_id,
        "content_type": item.content_type,
        "submission_hour": item.created_timestamp,
        "time_sensitivity": item.time_sensitivity,
        "platform": best.platform,
        "recommended_slot": best.recommended_slot,
        "decision": sched["decision"],
        "score": best.score,
        "confidence": best.confidence,
        "explanation": {
            "platform_activity": best.breakdown["platform_activity_raw"],
            "creator_history_score": best.breakdown["creator_history_raw"],
            "creator_base": best.breakdown["creator_base_raw"],
            "content_fit": best.breakdown["content_fit_raw"],
            "current_slot_score": sched["current_slot_score"],
            "optimal_slot_score": sched["optimal_slot_score"],
            "schedule_threshold_met": sched["threshold_met"],
        },
    }
    all_recommendations.append(rec)

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


# ─── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
