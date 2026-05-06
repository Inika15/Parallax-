# PS4 — Implementation Logic Plan
> Grounded in the actual dataset. Every decision below is backed by what the CSVs contain.

---

## What the data actually looks like

### `content.csv` — 100 rows
| Field | Values |
|---|---|
| `content_type` | `SHORT` (53), `LONG` (47) — only 2 types, not 5 |
| `time_sensitivity` | `High` (29), `Medium` (40), `Low` (31) |
| `created_timestamp` | Integer 0–23 (submission hour) |
| `creator_id` | 1–50 |

**Critical:** The content types are `SHORT` and `LONG` — not `video/image/reel/story/text`. Your affinity matrix and scoring must use these exact strings.

---

### `creators.csv` — 50 rows, zero missing
| Field | Range | Notes |
|---|---|---|
| `base_engagement` | 0.61 – 1.38, mean ≈ 0.96 | Multiplicative weight on score |
| `cooldown_hours` | 2, 4, 6, 8, 12 | Discrete values only |

No cold-start problem exists — all 50 creators have data. Your cold-start code path is a fallback for safety, not a real scenario here.

---

### `historical_engagement.csv` — 4,800 rows, 100% coverage
- 50 creators × 2 platforms × 2 content types × 24 slots = **exactly 4,800 combinations**
- `avg_engagement` range: 0.255 – 1.250

**Key insight — platform × content_type affinity is already in the data:**

| Platform | Content Type | Mean Engagement |
|---|---|---|
| Instagram | SHORT | 0.830 |
| Instagram | LONG | 0.551 |
| YouTube | LONG | 0.807 |
| YouTube | SHORT | 0.547 |

SHORT belongs on Instagram. LONG belongs on YouTube. This is not assumed — it's measured. Your affinity matrix must reflect these exact ratios.

**Best time slots (global avg across all creators):**
- Instagram: slots 7, 12, 16
- YouTube: slots 19, 4, 23

---

### `platform_activity.csv` — 48 rows (2 platforms × 24 slots)
The activity scores are **binary step functions**, not smooth curves:

```
Instagram: 0.6 for slots 0–17, 1.0 for slots 18–22, 0.6 for slot 23
YouTube:   0.6 for slots 0–19, 1.0 for slots 20–23
```

This means platform activity alone is not a fine-grained signal — it just tells you "is it prime time or not." The historical engagement scores carry all the granularity.

---

## Scoring Function — exact formula

```
score(creator, platform, slot, content_type) =
    platform_activity(platform, slot)          [W=0.30]
  × creator_history(creator, platform, type, slot) [W=0.40]
  × base_engagement(creator)                   [W=0.15]
  × content_type_affinity(type, platform)      [W=0.15]
```

### Content-type affinity matrix (derived from data)

```python
AFFINITY = {
    ("SHORT", "Instagram"): 1.0,       # baseline
    ("SHORT", "YouTube"):   0.547/0.830,  # ≈ 0.659 — penalize mismatch
    ("LONG",  "YouTube"):   1.0,
    ("LONG",  "Instagram"): 0.551/0.807,  # ≈ 0.682 — penalize mismatch
}
```

Or simpler: normalize so the "right" platform = 1.0, wrong = ~0.66.

### Composite score (multiplicative, not additive)
Multiplicative is correct here because a zero on any factor should tank the score (e.g., zero platform activity = don't post). Additive would let a great creator compensate for a dead slot.

### Tie-breaking (must be deterministic)
1. Higher score wins
2. Equal score → earlier time slot wins
3. Equal slot → alphabetically first platform wins (`Instagram` < `YouTube`)

Never use `random`, `uuid`, or `time.now()` anywhere in scoring or tie-breaking.

---

## Scheduling Decision

```python
SCHEDULE_THRESHOLD = 1.10   # only schedule if gain > 10%
NEAR_THRESHOLD_HOURS = 1    # don't schedule if optimal slot is within 1 hour

def decide(content_item, context):
    sub_hour = content_item.created_timestamp
    best_slot, best_platform, best_score = joint_optimize(content_item, context)
    current_score = score(content_item.creator_id, best_platform, sub_hour, content_item.content_type)

    if best_slot == sub_hour:
        return "POST_NOW"
    if abs(best_slot - sub_hour) <= NEAR_THRESHOLD_HOURS:
        return "POST_NOW"
    if best_score >= current_score * SCHEDULE_THRESHOLD:
        return "SCHEDULE"
    return "POST_NOW"
```

**Time sensitivity adjustment:**
- `High` → lower the threshold to 1.05 (post sooner, don't wait)
- `Low` → raise the threshold to 1.20 (only schedule for a big gain)
- `Medium` → use 1.10 (default)

This is a real differentiator — most teams will ignore `time_sensitivity`.

---

## Fallback Chain (Layer 1)

Since coverage is 100%, this rarely fires — but must exist:

```
1. Exact match: (creator_id, platform, content_type, slot) → use directly
2. Platform + type average: mean over all slots for this creator/platform/type
3. Creator + platform average: mean over all types and slots for this creator/platform
4. Creator global average: mean of all historical rows for this creator
5. System default: 0.683 (global mean of all avg_engagement values)
```

---

## Joint Optimizer

Evaluate all 2 × 24 = 48 candidate (platform, slot) pairs per content item. Return the best.

```python
def joint_optimize(content_item, context):
    creator_id = content_item.creator_id
    ctype = content_item.content_type
    candidates = []

    for platform in ["Instagram", "YouTube"]:
        for slot in range(24):
            s = compute_score(creator_id, platform, slot, ctype, context)
            candidates.append((s, slot, platform))  # slot before platform for tie-breaking

    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    best_score, best_slot, best_platform = candidates[0]
    return best_slot, best_platform, best_score
```

48 evaluations per item × 100 items = 4,800 score calls total. This is fast enough to run synchronously with no queue.

---

## Data Loading — exact structures

```python
# O(1) lookup for all hot paths

platform_activity: dict[tuple[str, int], float]
# key: ("Instagram", 18) → 1.0

creator_history: dict[tuple[int, str, str, int], float]
# key: (creator_id, "Instagram", "SHORT", 18) → 0.84

creator_base: dict[int, float]
# key: creator_id → base_engagement

content: dict[int, ContentItem]
# key: content_id → ContentItem
```

Load once at startup. Immutable after construction. All 100 content items + all 4800 history rows fit comfortably in memory.

---

## Output Format

```json
{
  "content_id": 1,
  "creator_id": 24,
  "platform": "Instagram",
  "recommended_slot": 18,
  "decision": "SCHEDULE",
  "score": 87.4,
  "confidence": "HIGH",
  "time_sensitivity": "Medium",
  "explanation": {
    "platform_activity": 1.0,
    "creator_history": 0.84,
    "base_engagement": 1.11,
    "content_type_affinity": 1.0,
    "submission_slot": 6,
    "submission_slot_score": 61.2,
    "optimal_slot_score": 87.4,
    "gain_pct": 42.8,
    "schedule_threshold_used": 1.10
  }
}
```

Validate before output:
- `platform` ∈ `{"Instagram", "YouTube"}`
- `decision` ∈ `{"POST_NOW", "SCHEDULE"}`
- `recommended_slot` ∈ `[0, 23]`
- `score` is finite float, not NaN, not Inf
- `content_id` exists in input

---

## What makes this stand out

### 1. Time sensitivity actually changes behavior
Most teams will compute a best slot and always output `SCHEDULE` if it differs from now. You dynamically adjust the scheduling threshold based on `time_sensitivity`. A `High` content piece that's submitted at slot 8 will post now if the best slot is slot 9 — a `Low` piece waits for a bigger gain. This is visible in the output via `schedule_threshold_used`.

### 2. Affinity matrix is data-derived, not hardcoded
You compute SHORT/LONG × Instagram/YouTube weights from the actual engagement means in the CSV, not from a made-up table. In your explainability output, note: "Affinity score derived from historical data (Instagram SHORT mean: 0.830 vs YouTube SHORT mean: 0.547)."

### 3. Counterfactual in every output
Include `worst_slot_score` alongside `optimal_slot_score`. The delta between them quantifies the system's value. "Without this system, creator 24 would have posted at 2 AM and scored 18. We recommended 6 PM on Instagram and scored 87 — a 69pt lift." This number is what judges remember.

### 4. Platform activity is not the primary signal
Instagram and YouTube have 17-hour and 20-hour dead zones where `activity_score = 0.6`. Historical engagement varies continuously across all 24 slots. Your scoring correctly weights history at 0.40 and activity at 0.30 so that a creator with strong personal engagement at a "dead" hour can still beat a generic peak slot. Show this in at least one example in your README.

### 5. Determinism is provable
Run your optimizer twice on the same input. Output is byte-identical. Add a test that asserts this. Mention it in your README. Most teams can't prove this.

---

## Edge cases to handle explicitly

| Case | What happens |
|---|---|
| Content submitted at optimal slot | `decision = POST_NOW` immediately, no scheduling needed |
| Optimal slot is 1 hour away | `POST_NOW` (not worth waiting) |
| All slots score equally for a creator | Tie-break: slot 0, platform "Instagram" |
| `base_engagement` is very high (1.38) | Score can exceed 1.0 — clip at `MAX_SCORE = 100.0` |
| Two content items from same creator overlap (cooldown) | Skip occupied slots in the candidate list; pick next best |
| `time_sensitivity = High`, content already at prime time | `POST_NOW` always, regardless of score delta |

---

## File structure

```
ps4/
├── main.py                  # entry point: load → optimize → output
├── data_loader.py           # 4 loaders, returns typed dicts
├── context.py               # EngagementContext dataclass + query methods
├── scorer.py                # compute_score(), weights as constants at top
├── optimizer.py             # joint_optimize(), 48 candidates, deterministic sort
├── scheduler.py             # decide(), threshold logic per time_sensitivity
├── output_formatter.py      # format + validate recommendation dict
├── evaluator.py             # compute all 4 eval metrics
├── config.py                # W1=0.30, W2=0.40, W3=0.15, W4=0.15, thresholds
└── tests/
    ├── test_scorer.py
    ├── test_optimizer.py
    ├── test_scheduler.py
    └── test_determinism.py  # run twice, assert identical output
```

---

## Eval metric intuitions

- **Engagement score** — did you pick high-engagement (platform, slot, type) combos? Maximize by weighting creator history heavily (0.40).
- **Timing effectiveness** — how close is your slot to the empirically best slot? Your joint optimizer checks all 48 candidates so this should be near-optimal.
- **Platform quality** — did SHORT go to Instagram and LONG go to YouTube? Your affinity matrix enforces this.
- **Efficiency score** — did you correctly decide POST_NOW vs SCHEDULE? Depends on the threshold logic and time_sensitivity adjustment being correct.

All four are improved by the same core: a well-weighted multiplicative scorer + deterministic joint optimizer + threshold-based scheduler that reads time_sensitivity.