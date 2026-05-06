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

##  Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the optimization pipeline
python main.py --data-dir data/raw --output results/recommendations.json

# 3. Start the API server
python api.py

# 4. Launch the frontend (in a new terminal)
cd frontend && npm install && npm run dev
```

> **Windows users:** Simply run `run.bat` to start everything.

- 🔗 **Dashboard:** http://localhost:5173
- 📡 **API Docs:** http://localhost:8000/docs

---

##  System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INPUT: 4 CSV Datasets                            │
│  content.csv │ creators.csv │ platform_activity.csv │ historical.csv│
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────▼─────────────────────┐
         │     Layer 1: Foundation                    │
         │     Data Loading → Schema Validation       │
         │     → State Machine → Fallback Handling    │
         ├───────────────────────────────────────────-┤
         │     Layer 2: Fusion                        │
         │     EngagementContext → Platform Stats     │
         │     → Peak Hour Detection                  │
         ├────────────────────────────────────────────┤
         │     Layer 3: Personalization               │
         │     Creator DNA Profiling → Cold-Start     │
         │     → Content-Type Averages                │
         ├────────────────────────────────────────────┤
         │     Layer 4: Scoring Engine                │
         │     Weighted Sum (4-Factor)                │
         │     → Sensitivity Risk Routing             │
         │     → First-Hour Velocity Bonus            │
         ├────────────────────────────────────────────┤
         │     Layer 5: Intelligence                  │
         │     Joint 48-Combo Optimizer               │
         │     → Cooldown Scheduler → Momentum        │
         │     → Engagement Trajectory                │
         ├────────────────────────────────────────────┤
         │     Layer 6: Output                        │
         │     Formatter → Evaluator → NL Explainer   │
         │     → Score Traces → Coverage Validation   │
         └─────────────────────────┬──────────────────┘
                                   │
         ┌─────────────────────────▼──────────────────┐
         │  OUTPUT: recommendations.json              │
         │  → FastAPI REST API → React Dashboard      │
         └────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
parallax/
├── main.py                          # CLI pipeline entry (6-layer engine)
├── api.py                           # FastAPI REST API server
├── requirements.txt                 # Python dependencies
├── run.bat                          # One-click Windows launcher
│
├── src/                             # Core engine (6 layers)
│   ├── layer1_foundation/           # Data loader, schemas, state machine
│   ├── layer2_fusion/               # EngagementContext, preprocessor
│   ├── layer3_personalization/      # Creator DNA, cold-start handling
│   ├── layer4_scoring/              # Weighted scorer, sensitivity risk
│   ├── layer5_intelligence/         # Optimizer, scheduler, momentum
│   └── layer6_output/               # Formatter, evaluator, explainer
│
├── frontend/                        # React + Vite dashboard
│   └── src/
│       ├── pages/                   # Dashboard, Optimize, Schedule, Analytics
│       ├── components/              # Shared UI components
│       └── api.js                   # Backend API client with error handling
│
├── data/raw/                        # Input datasets
│   ├── content.csv                  # 100 content submissions
│   ├── creators.csv                 # 50 creator profiles
│   ├── platform_activity.csv        # 48 platform × slot activity scores
│   └── historical_engagement.csv    # 4800 engagement records
│
├── tests/                           # Test suite
│   ├── test_scorer.py               # Scoring function unit tests
│   ├── test_optimizer.py            # Joint optimizer tests
│   ├── test_scheduler.py            # Scheduling decision tests
│   ├── test_determinism.py          # SHA256 reproducibility test
│   └── test_api.py                  # API endpoint validation
│
├── extras/                          # Extended analysis modules
│   ├── trajectory.py                # Engagement trajectory analysis
│   ├── counterfactual.py            # What-if scenario engine
│   ├── heatmap.py                   # Activity heatmap generation
│   └── batch_scheduler.py           # Batch scheduling utilities
│
└── docs/ARCHITECTURE.md             # Detailed architecture documentation
```

---

##  Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Engine** | Python 3.11 | 6-layer optimization pipeline |
| **API Server** | FastAPI + Uvicorn | REST API with Swagger docs |
| **Frontend** | React 18 + Vite | Interactive dashboard UI |
| **Data Processing** | Pandas, NumPy | CSV ingestion & matrix ops |
| **Charts** | Recharts | Heatmaps & engagement visualizations |
| **Icons** | Lucide React | Modern icon system |
| **Routing** | React Router DOM | SPA navigation |

---

## Evaluation Metrics

| Metric | Score | Description |
|--------|-------|-------------|
| Engagement Score | **0.8346** | Avg recommendation quality (0–1) |
| Timing Effectiveness | **0.7600** | Alignment with peak activity windows |
| Platform Quality | **0.8557** | Content-type ↔ platform affinity match |
| Efficiency Score | **0.9500** | POST_NOW vs SCHEDULE decision quality |
| **Composite Score** | **0.8501** | Equal-weighted aggregate |

---

##  Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Joint 48-combo optimization** | Scores ALL (platform, slot) pairs simultaneously — eliminates sequential bias |
| **Weighted sum scoring** | Standard recommendation system approach; interpretable, auditable, debuggable |
| **Cooldown-aware batch scheduling** | Groups by creator, processes HIGH sensitivity first, prevents slot conflicts |
| **Sensitivity risk routing** | Penalizes sensitive content at peak hours where diverse audience increases suppression risk |
| **First-hour velocity bonus** | Posts near submission time get engagement velocity boost (algorithmic momentum) |
| **Data-derived affinity matrix** | SHORT→Instagram, LONG→YouTube derived from 4800 historical engagement records |
| **Deterministic tie-breaking** | Highest score → earliest slot → alphabetical platform (SHA256-verified reproducibility) |

---

##  Frontend Features

| Page | Features |
|------|----------|
| **Dashboard** | Recommendations table, score bars, activity heatmap, stats cards |
| **Optimize** | Per-creator optimization with real-time scoring |
| **Schedule** | Drag-and-drop calendar with score-delta tooltips and move history |
| **Creators** | Creator DNA profiles, engagement patterns, content affinity |
| **Analytics** | Platform comparison charts, engagement trend analysis |

---

##  Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Individual test suites
python tests/test_determinism.py    # Verify pipeline reproducibility
python tests/test_scorer.py         # Scoring function edge cases
python tests/test_optimizer.py      # Joint optimizer correctness
python tests/test_scheduler.py      # POST_NOW vs SCHEDULE logic
python tests/test_api.py            # API endpoint validation
```

---

##  API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Aggregate statistics |
| `GET` | `/api/recommendations?limit=N` | Top N recommendations |
| `GET` | `/api/heatmap` | Platform activity heatmap data |
| `GET` | `/api/creators` | All creator profiles |
| `POST` | `/api/optimize` | Run optimization for specific creator |
