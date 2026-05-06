# Architecture — Creator Content Posting Optimization System

> Team Parallax · 6-Layer Multiplicative Architecture

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                  LAYER 6: OUTPUT ENGINE                  │
│           Deterministic, Validated, Explainable          │
├─────────────────────────────────────────────────────────┤
│               LAYER 5: INTELLIGENCE CORE                 │
│    Joint Platform × Time Optimizer + Scheduling Logic    │
├─────────────────────────────────────────────────────────┤
│              LAYER 4: SCORING ENGINE                     │
│   Multi-Variable Weighted Scorer + Tie-Breaking Rules    │
├─────────────────────────────────────────────────────────┤
│             LAYER 3: PERSONALIZATION ENGINE              │
│    Creator DNA Profiles + Cold-Start Fallback Logic      │
├─────────────────────────────────────────────────────────┤
│              LAYER 2: DATA FUSION LAYER                  │
│     Platform Activity + Historical Engagement Merging    │
├─────────────────────────────────────────────────────────┤
│               LAYER 1: DATA FOUNDATION                   │
│    Loaders, Validators, Parsers, Schema Enforcement      │
└─────────────────────────────────────────────────────────┘
```

## Scoring Formula

```
SCORE(creator, platform, slot, type) =
    platform_activity(platform, slot)^0.30           [platform pulse]
  × creator_history(creator, platform, type, slot)^0.40  [personal history]
  × creator_base(creator)^0.15                       [creator power]
  × content_type_affinity(type, platform)^0.15       [content fit]
  × 100                                             [scale to 0-100]
```

### Why Multiplicative?

A zero on **any** factor tanks the score. This is correct because:
- Zero platform activity = nobody is online = don't post
- Zero creator history = no evidence of success = low confidence
- Additive scoring would let a strong creator compensate for a dead time slot — that's wrong

### Weight Rationale

| Factor | Weight | Signal Quality | Rationale |
|---|---|---|---|
| Creator History | 0.40 | 4,800 unique values | Highest granularity, most predictive |
| Platform Activity | 0.30 | Binary (0.6/1.0) | Important but only 2 possible values |
| Creator Base | 0.15 | 50 unique values | Baseline strength, less discriminative |
| Content-Type Fit | 0.15 | 4 unique values | Natural affinity, less discriminative |

## Content-Type Affinity Matrix

Derived from actual historical engagement means, **not hardcoded**:

| | Instagram | YouTube |
|---|---|---|
| **SHORT** | 1.000 (baseline) | 0.659 (0.547/0.830) |
| **LONG** | 0.682 (0.551/0.807) | 1.000 (baseline) |

SHORT belongs on Instagram. LONG belongs on YouTube. This is **measured**, not assumed.

## Scheduling Decision

```
if submission_hour == best_slot → POST_NOW
if |best_slot - submission_hour| ≤ 1 → POST_NOW  (not worth waiting)
if best_score ≥ current_score × threshold → SCHEDULE
else → POST_NOW
```

**Time sensitivity adjusts the threshold:**
- High → 1.05 (post sooner, only schedule for 5%+ gain)
- Medium → 1.10 (default, schedule for 10%+ gain)
- Low → 1.20 (schedule only for big gains)

## Key Design Decisions

### 1. Determinism (Issue #11)
Zero sources of randomness. Tie-breaking: highest score → earliest slot → alphabetical platform. Run twice, get byte-identical output. Proven by `tests/test_determinism.py`.

### 2. Joint Optimization (Issue #8)
We evaluate ALL 48 (2 platforms × 24 slots) combinations per content item. A video at peak Instagram time might outscore the "best" YouTube slot even if YouTube is the natural fit. We test every combination.

### 3. Cold-Start Handling (Issue #15)
When `data_richness < 0.3`: use global content-type averages for platform affinity, system-wide peak slots for timing, and flag confidence as LOW.

### 4. Time Sensitivity (Issue #9)
Most teams ignore `time_sensitivity`. We dynamically adjust the scheduling threshold — High content gets posted faster, Low content waits for bigger gains.

## Data Coverage

- **50/50** creators have full historical data (100% coverage)
- **4,800/4,800** historical engagement combinations (100% coverage)
- **48/48** platform activity scores (100% coverage)
- Cold-start path exists but is a safety net, not a real scenario in this dataset

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the optimizer
python main.py --data-dir data/raw --output results/recommendations.json

# Run tests
pytest tests/ -v

# Start the API server
python api.py

# Start the frontend (in another terminal)
cd frontend && npm install && npm run dev
```
