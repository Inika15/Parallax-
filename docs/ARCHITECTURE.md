# Architecture — Creator Content Posting Optimization System

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                      │
│  Auth → Onboarding → Dashboard → Optimize → Creators → Schedule     │
│                          → Analytics                                 │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ REST API (http://localhost:8000)
┌──────────────────────────▼───────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                    │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ Layer 1      │  │ Layer 2      │  │ Layer 3                    │  │
│  │ Data Loader  │→│ Preprocessor │→│ Creator DNA                │  │
│  │ + State Mach │  │ + Context    │  │ + Cold Start               │  │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘  │
│         │                                        │                   │
│  ┌──────▼──────────────────────────────────────▼─────────────────┐  │
│  │                    Layer 4: Scoring Engine                     │  │
│  │  Score = W1×activity + W2×history + W3×base + W4×affinity     │  │
│  │  + Sensitivity Risk Routing + First-Hour Velocity Bonus       │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │              Layer 5: Intelligence Engine                     │  │
│  │  Joint 48-combo Optimizer → Cooldown Scheduler                │  │
│  │  → Momentum Scoring → Engagement Trajectory                   │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │                 Layer 6: Output + Explainability              │  │
│  │  NL Explanations → Score Traces → Coverage Validation         │  │
│  │  → Output Formatting → Evaluation Metrics                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
parallax/
├── main.py                    # CLI pipeline entry point
├── api.py                     # FastAPI REST API
├── data/
│   └── raw/                   # Input CSVs
│       ├── content.csv        # 100 content submissions
│       ├── creators.csv       # 50 creator profiles
│       ├── platform_activity.csv  # 48 platform×slot activity scores
│       └── historical_engagement.csv  # 4800 engagement records
├── results/
│   └── recommendations.json   # Pipeline output (100 recommendations)
├── src/
│   ├── layer1_foundation/     # Data loading, schemas, state machine
│   ├── layer2_fusion/         # EngagementContext, preprocessor
│   ├── layer3_personalization/ # Creator DNA, cold-start handling
│   ├── layer4_scoring/        # Weighted sum scorer, weights, sensitivity risk
│   ├── layer5_intelligence/   # Joint optimizer, cooldown scheduler, momentum
│   └── layer6_output/         # Formatter, evaluator, explainer
├── frontend/                  # React + Vite frontend
│   └── src/
│       ├── pages/             # Dashboard, Optimize, Creators, Schedule, Analytics
│       ├── components/        # Shared UI components
│       └── api.js             # Backend API client
├── extras/                    # Trajectory computation
├── tests/                     # Determinism test, API test
└── docs/
    └── reference/             # Research & planning documents
```

## Scoring Formula

```
Score = (0.30 × platform_activity + 0.40 × creator_history
       + 0.15 × base_engagement + 0.15 × content_affinity) × 88.0
```

**Sensitivity Risk Adjustment:**
```
adjusted = base_score × (1.0 - risk_penalty) + velocity_bonus × 100
risk_penalty = f(time_sensitivity, platform_activity)  # 0-15% for HIGH at peak
velocity_bonus = f(submission_hour, recommended_slot)   # 0-3% for near-submission
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Joint 48-combo optimization | Scores ALL (platform, slot) pairs simultaneously instead of sequential selection |
| Weighted sum (not multiplicative) | Standard recommendation system approach; one zero factor doesn't collapse entire score |
| Cooldown-aware batch scheduling | Groups by creator, processes HIGH sensitivity first, prevents slot conflicts |
| Sensitivity risk routing | Penalizes sensitive content at peak hours (random audience = higher suppression risk) |
| Deterministic tie-breaking | Highest score → earliest slot → alphabetical platform for reproducibility |
| API loads from pipeline output | Single source of truth — frontend and CLI show identical results |

## Data Flow

1. `main.py` reads CSVs → builds EngagementContext → scores all 48 combos per item
2. Results written to `results/recommendations.json` with full explanations
3. `api.py` loads recommendations.json at startup → serves via REST API
4. Frontend fetches from API → renders dashboard, calendar, analytics
