# Creator Content Posting Optimization System

## Team Information
- **Team Name**: Parallax
- **Year**: 1
- **All-Female Team**: Yes

## Architecture Overview

Our system uses a **6-layer architecture** with **joint 48-combination optimization** (2 platforms × 24 slots) per content item.

**Optimal posting time:** For each content item, we score all 48 (platform, slot) candidates using a weighted sum: `Score = W1×platform_activity + W2×creator_history + W3×base_engagement + W4×content_affinity` (W1=0.30, W2=0.40, W3=0.15, W4=0.15). The globally highest-scoring combination wins. Deterministic tie-breaking: highest score → earliest slot → alphabetical platform.

**Platform selection:** Derived from the joint optimizer — not hardcoded. Data-derived affinity matrix (SHORT→Instagram ≈1.206, LONG→YouTube ≈1.189) guides preference, but per-creator historical engagement (W2=0.40) can override when individual data contradicts the aggregate trend.

**Balancing activity vs history:** Platform activity (step function: 0.6 or 1.0) provides a baseline bonus for peak windows. Creator history (continuous: 0.255–1.250) is weighted 33% higher, giving individual engagement patterns dominant influence over global platform trends.

**POST_NOW vs SCHEDULE:** Time-sensitivity-aware thresholds (High=1.05×, Medium=1.10×, Low=1.20×). If optimal score exceeds current-slot score by the threshold, SCHEDULE. Submission at/near optimal slot → POST_NOW. Cooldown-aware batch scheduling prevents per-creator slot conflicts.

**Note:** Please do not change the format or spelling of anything in this README. The fields are extracted using a script, so any changes to the structure or formatting may break the extraction process.

---

## System Architecture

```
DATA (CSVs)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Foundation                                            │
│  Data Loader → Schema Validation → State Machine → Fallbacks   │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Fusion                                                │
│  EngagementContext → Platform Stats → Preprocessor              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Personalization                                       │
│  Creator DNA Profiling → Cold-Start Handling → Type Averages    │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Scoring Engine                                        │
│  Weighted Sum (4-factor) → Sensitivity Risk → Velocity Bonus    │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: Intelligence                                          │
│  Joint 48-Combo Optimizer → Cooldown Scheduler → Momentum       │
│  → Engagement Trajectory → Affinity Matrix                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 6: Output                                                │
│  Formatter → Evaluator → NL Explainer → Score Traces            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
OUTPUT (recommendations.json)  →  REST API  →  React Frontend
```

## Directory Structure

```
parallax/
├── main.py                       # CLI pipeline (6-layer engine)
├── api.py                        # FastAPI REST API
├── requirements.txt              # Python dependencies
├── run.bat                       # Quick-start script
├── data/raw/                     # Input datasets
│   ├── content.csv               # 100 content submissions
│   ├── creators.csv              # 50 creator profiles
│   ├── platform_activity.csv     # 48 hourly activity scores
│   └── historical_engagement.csv # 4800 engagement records
├── src/
│   ├── layer1_foundation/        # Data loading, schemas, state machine
│   ├── layer2_fusion/            # EngagementContext, preprocessor
│   ├── layer3_personalization/   # Creator DNA, cold-start profiles
│   ├── layer4_scoring/           # Weighted scorer, weights, sensitivity
│   ├── layer5_intelligence/      # Optimizer, scheduler, momentum
│   └── layer6_output/            # Formatter, evaluator, explainer
├── frontend/                     # React + Vite dashboard
│   └── src/
│       ├── pages/                # Dashboard, Optimize, Schedule, Analytics
│       ├── components/           # Shared UI components
│       └── api.js                # Backend API client
├── tests/                        # Test suite
│   ├── test_scorer.py            # Scoring function tests
│   ├── test_optimizer.py         # Optimizer logic tests
│   ├── test_scheduler.py         # Scheduling decision tests
│   └── test_determinism.py       # Pipeline reproducibility test
├── extras/                       # Extended features
│   ├── trajectory.py             # Engagement trajectory analysis
│   ├── counterfactual.py         # What-if analysis
│   └── heatmap.py                # Activity visualization
├── docs/ARCHITECTURE.md          # Detailed architecture document
└── results/                      # Pipeline output (gitignored)
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Joint 48-combo optimization | Scores ALL (platform, slot) pairs simultaneously — no sequential bias |
| Weighted sum scoring | Standard recommendation system approach; interpretable and auditable |
| Cooldown-aware batch scheduling | Groups by creator, processes HIGH sensitivity first, prevents conflicts |
| Algorithm-aware sensitivity routing | Penalizes sensitive content at peak hours (diverse audience = suppression risk) |
| First-hour velocity bonus | Posts near submission time get engagement velocity boost |
| Deterministic tie-breaking | Highest score → earliest slot → alphabetical platform for reproducibility |
| Data-derived affinity matrix | SHORT→Instagram, LONG→YouTube from historical engagement statistics |

## Evaluation Metrics

| Metric | Score |
|--------|-------|
| Engagement Score | 0.8346 |
| Timing Effectiveness | 0.7600 |
| Platform Quality | 0.8557 |
| Efficiency Score | 0.9500 |
| **Composite Score** | **0.8501** |

## How to Run

```bash
# Backend
pip install -r requirements.txt
python main.py --data-dir data/raw --output results/recommendations.json
python api.py

# Frontend
cd frontend
npm install
npm run dev
```
