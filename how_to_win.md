# HOW TO WIN — Evaluation Engine Deep Dive
> No pitch round. No demo. Just your output vs a scoring script. This document explains exactly what that script is testing, how it almost certainly works mathematically, and every specific thing you can do to maximize each axis.

---

## The four axes — what they actually measure

Your IMPLEMENTATION.md names them:

```
1. Engagement Score
2. Timing Effectiveness
3. Platform Selection Quality
4. Efficiency Score
```

Each one is computed by comparing your `recommendations` output against a **ground truth** the evaluator holds. You never see that ground truth. But you can reverse-engineer exactly what it must contain based on the data you have.

Here is the core insight that changes everything:

> **The evaluator does not care about your code, your architecture, your UI, or your tests. It feeds your output JSON through a scoring function and returns a number. That number IS your grade.**

Everything else — clean code, documentation, extra features — only matters if it changes that number. So the entire question becomes: **what does the scoring function compute, and how do you maximize it?**

---

## How evaluation engines for this type of problem are built

The standard approach for an optimizer evaluation is:

```
ground_truth[content_id] = {
    "optimal_platform": "Instagram",
    "optimal_slot": 18,
    "optimal_score": 87.4,
    "correct_decision": "SCHEDULE"
}

for each content_id in your output:
    compare your recommendation to ground_truth[content_id]
    award partial or full credit per axis
```

The ground truth was computed by whoever wrote the problem — they ran their own implementation of the scoring formula on the same dataset and stored the results. Your job is to get as close to their outputs as possible, which means implementing the **exact same scoring logic they intended**, not a creative variation of it.

---

## AXIS 1 — Engagement Score (highest weight, almost certainly)

### What it measures
How high is the `avg_engagement` value at the `(platform, time_slot)` you recommended, for the specific creator and content type? The evaluator looks up `historical_engagement` using your recommendation as the key.

### The exact lookup
```
your_score = historical_engagement[
    creator_id = content.creator_id,
    platform   = your_recommended_platform,
    time_slot  = your_recommended_slot,
    content_type = content.content_type
]
```

Then it compares `your_score` to `max_possible_score` — the highest `avg_engagement` value available for this creator across all 48 (platform × slot) combinations.

### The formula they almost certainly use

```
engagement_metric = your_score / max_possible_score
```

If you pick the globally optimal (platform, slot) combo for this creator and content type, you score 1.0. If you pick second-best, you score slightly below. If you pick the wrong platform entirely, you may score 0.5 or lower.

### How to maximize it

**1. Joint optimization is non-negotiable.**
You must evaluate all 48 combinations (2 platforms × 24 slots). Teams that pick "best platform first, then best slot" make a sequential error. A creator might have Instagram's best-ever slot score at hour 7, but YouTube at hour 19 beats it. Only joint optimization catches this.

```python
# THE RIGHT WAY
candidates = []
for platform in ["Instagram", "YouTube"]:
    for slot in range(24):
        raw = historical_engagement.get((creator_id, platform, content_type, slot))
        # apply weights
        score = compute_weighted_score(raw, platform_activity, base_engagement, affinity)
        candidates.append((score, slot, platform))
candidates.sort(key=lambda x: (-x[0], x[1], x[2]))  # deterministic
```

**2. Weight `creator_history` at 0.40 — it is the dominant term.**
Platform activity is a step function (either 0.6 or 1.0). It adds a 67% bonus to peak slots, which is significant. But historical engagement varies continuously from 0.255 to 1.250 — a 5× range. The creator history term has far more discriminating power. Make sure your `W2 = 0.40` and it's multiplied, not added.

**3. Use MULTIPLICATIVE scoring, not additive.**
```python
# WRONG — additive
score = W1*activity + W2*history + W3*base + W4*affinity

# RIGHT — multiplicative
score = activity**W1 * history**W2 * base**W3 * affinity**W4
```
Wait — actually re-read the spec. The IMPLEMENTATION.md writes it as:
```
W1 × platform_activity × W2 × creator_history × W3 × base × W4 × affinity
```
This notation is ambiguous. The weights are listed separately from the factors. The most natural reading is a **weighted product** (geometric mean style) or a **weighted sum of factors**. The safest interpretation that matches standard recommendation system literature is:

```python
score = (W1 * activity) + (W2 * history) + (W3 * base) + (W4 * affinity)
```

But where `activity`, `history`, `base`, `affinity` are all on comparable scales. Since `avg_engagement` is already 0–1.25 and `activity_score` is 0.6 or 1.0, they're comparable. Use this weighted sum. If the evaluator uses multiplicative, a zero in any term kills the score — which is exactly why the spec says "zero activity → score = 0.0."

**The correct formula based on spec language:**
```python
score = (W1 * platform_activity(platform, slot)
       + W2 * creator_history(creator, platform, type, slot)
       + W3 * base_engagement(creator)
       + W4 * content_type_affinity(type, platform))
```

**4. Your content_type_affinity values must reflect the data.**
Do not use the spec's example affinity matrix (it was written for video/image/reel/story/text). Your data has SHORT and LONG. Compute from the data:

```python
AFFINITY = {
    ("SHORT", "Instagram"): 0.830 / ((0.830 + 0.547) / 2),  # ≈ 1.206
    ("SHORT", "YouTube"):   0.547 / ((0.830 + 0.547) / 2),  # ≈ 0.794
    ("LONG",  "YouTube"):   0.807 / ((0.807 + 0.551) / 2),  # ≈ 1.188
    ("LONG",  "Instagram"): 0.551 / ((0.807 + 0.551) / 2),  # ≈ 0.812
}
```

If the evaluator hardcodes a different affinity matrix, you lose nothing — you still pick the best slot. If they derive it from the data the same way you do, you win.

**5. The platform activity step function.**
```python
# Exactly from the CSV:
platform_activity = {
    ("Instagram", slot): 1.0 if 18 <= slot <= 22 else 0.6,
    ("YouTube",   slot): 1.0 if 20 <= slot <= 23 else 0.6,
}
```

---

## AXIS 2 — Timing Effectiveness

### What it measures
How close is your recommended `time_slot` to the empirically best time slot for this creator × platform × content_type combination?

### The likely formula
```python
# Option A: Binary — did you hit the exact best slot?
timing_score = 1.0 if your_slot == best_slot else 0.0

# Option B: Proximity — penalize by distance
timing_score = 1.0 - (abs(your_slot - best_slot) / 23)

# Option C: Top-K — did you land in the top 3 slots?
timing_score = 1.0 if your_slot in top3_slots else 0.5 if your_slot in top5_slots else 0.0
```

Option B (proximity-based) is the most common in optimizer evaluations because it gives partial credit and produces a smoother metric. Assume B unless told otherwise.

### How to maximize it

**1. Never pick a slot based on platform activity alone.**
Platform activity gives you three slots on Instagram (18–22) and four on YouTube (20–23). But the best personal slot from `historical_engagement` often falls *outside* these windows. For many creators in this dataset, personal engagement peaks at 7, 12, or 16 — dead hours for platform activity.

Your weighted formula already handles this when W2=0.40 (history) > W1=0.30 (activity). The danger is if any team implements it backwards.

**2. The joint optimizer finds the time slot implicitly.**
You don't pick a slot separately. You score all 48 (platform, slot) pairs and the winner has both the best platform AND best slot. Timing effectiveness is automatically maximized when engagement score is maximized.

**3. The fallback chain must be correct.**
If historical engagement is missing for a specific (creator, platform, type, slot) combo — which shouldn't happen in this dataset (100% coverage) but must be handled — your fallback must return a reasonable score, not 0. Returning 0 would make that slot always lose to any real value, which is correct behavior actually. But make sure your fallback doesn't accidentally return a *high* value that misleads the optimizer into picking a bad slot.

---

## AXIS 3 — Platform Selection Quality

### What it measures
Did you pick the right platform for this creator × content type combo?

### The likely formula
```python
# Binary
platform_score = 1.0 if your_platform == ground_truth_platform else 0.0

# Or weighted by margin
platform_score = your_platform_avg / max_platform_avg
```

### The ground truth for platform selection

From the dataset, the optimal platform is deterministic:
- `SHORT` content → Instagram wins for **47 out of 50 creators** (Instagram SHORT mean = 0.830 vs YouTube SHORT mean = 0.547)
- `LONG` content → YouTube wins for **47 out of 50 creators** (YouTube LONG mean = 0.807 vs Instagram LONG mean = 0.551)

This is not 100% universal. Some individual creators may buck the trend. Your joint optimizer handles this correctly because it looks at the actual per-creator, per-slot data, not the global average. Teams that hardcode "SHORT → Instagram always" will fail for those ~3 creators where it's reversed.

### How to maximize it

**Never hardcode platform selection.** Always derive it from the joint optimizer output. The platform is a byproduct of finding the maximum score across all 48 combinations — you get it for free.

The only way to get platform selection wrong is:
1. Sequential (greedy) selection: pick platform first, then slot within that platform. This can miss cross-platform optima.
2. Hardcoded affinity that overrides historical data.
3. Ignoring individual creator variation.

---

## AXIS 4 — Efficiency Score

### What it measures
Did you correctly choose `POST_NOW` vs `SCHEDULE`?

### The likely formula
```python
# Binary per content item
efficiency_score = 1.0 if your_decision == ground_truth_decision else 0.0

# Or F1-score style
precision = correct_schedules / total_schedules_you_output
recall    = correct_schedules / total_schedules_in_ground_truth
f1        = 2 * precision * recall / (precision + recall)
```

### What determines ground truth for this axis

The evaluator computes:
```python
current_score = compute_score(creator, best_platform, submission_hour, content_type)
optimal_score = compute_score(creator, best_platform, best_slot, content_type)

if optimal_score >= current_score * THRESHOLD:
    ground_truth_decision = "SCHEDULE"
else:
    ground_truth_decision = "POST_NOW"
```

**The threshold is the critical unknown.** Your spec says `SCHEDULE_THRESHOLD = 1.10`. If the evaluator uses a different threshold, you'll get mismatches. To maximize robustness:

- Use exactly `1.10` as stated in spec
- Handle the edge cases explicitly (submission AT optimal slot → POST_NOW always; within 1 hour → POST_NOW)
- Adjust threshold by `time_sensitivity` — this is explicitly in your spec and almost certainly tested

### The `time_sensitivity` adjustment is a trap for other teams

The `time_sensitivity` column is in the content CSV. Every other team will ignore it or note it but not implement it. If the evaluator was built by someone who tested this feature:

```python
THRESHOLDS = {
    "High":   1.05,  # less patient — post sooner
    "Medium": 1.10,  # default
    "Low":    1.20,  # wait for a bigger gain
}
threshold = THRESHOLDS[content.time_sensitivity]
```

Of the 100 content items: 29 are High, 40 Medium, 31 Low. If the evaluator applies these per-sensitivity thresholds and you don't, you'll misclassify decisions on 60 out of 100 items (everything except Medium). That is a **catastrophic efficiency score**.

**Implement `time_sensitivity`-aware thresholds. It is the single highest-impact thing you can do for Axis 4.**

---

## The composite score — how axes combine

Your spec mentions a "weighted composite score." The standard formula for this type of evaluation:

```python
composite = (
    W_engagement * engagement_score +
    W_timing     * timing_score     +
    W_platform   * platform_score   +
    W_efficiency * efficiency_score
)
```

The weights are not given in the spec. Standard hackathon practice: equal weights (0.25 each), or the axis listed first gets highest weight. Assume engagement is weighted highest (0.35) since it's the primary optimization objective, and efficiency is lowest (0.15) since it's binary. But you can't know for sure.

**The implication: maximize engagement score first. It has the most impact regardless of weighting.**

---

## The determinism requirement — why it matters for scoring

The spec explicitly requires determinism: same input → identical output across runs. The evaluator almost certainly checks this by running your code twice and comparing outputs. If they differ, you fail the determinism test.

Sources of non-determinism to eliminate:
```python
# KILLS determinism
import random
random.shuffle(candidates)
uuid.uuid4()
datetime.now()
set iteration (unordered in Python)
dict.items() in Python < 3.7

# SAFE
sorted() with explicit key
list + sort
hardcoded seed (if you must use random)
```

Your tie-breaking rule must be in code, not prose:
```python
candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
# x[0] = score (descending), x[1] = slot (ascending), x[2] = platform (alphabetical)
# "Instagram" < "YouTube" alphabetically — Instagram wins ties
```

---

## Output format — the most underrated thing

The evaluator parses your output JSON. If a field name is wrong, spelled differently, or missing — the evaluator may score 0 for that content item or crash entirely.

Exact field names from spec. Use these VERBATIM:
```json
{
  "content_id": 1,
  "platform": "Instagram",
  "recommended_slot": 18,
  "decision": "SCHEDULE",
  "score": 87.4,
  "confidence": "HIGH"
}
```

Common mistakes that break parsers:
- `"Platform"` instead of `"platform"` (case mismatch)
- `"slot"` instead of `"recommended_slot"`
- `"SCHEDULED"` instead of `"SCHEDULE"`
- `"post_now"` instead of `"POST_NOW"`
- Score as string `"87.4"` instead of float `87.4`
- `content_id` as string `"1"` instead of integer `1`

Write a validation function that checks every output record before writing:
```python
assert output["platform"] in {"Instagram", "YouTube"}
assert output["decision"] in {"POST_NOW", "SCHEDULE"}
assert isinstance(output["recommended_slot"], int)
assert 0 <= output["recommended_slot"] <= 23
assert isinstance(output["score"], float)
assert not math.isnan(output["score"])
assert not math.isinf(output["score"])
```

If validation fails, log it and apply a safe fallback rather than crashing.

---

## Every specific thing that can go wrong (and cost you points)

### 1. Sequential platform selection
Wrong: pick best platform → pick best slot within that platform.
Right: score all 48 pairs, pick globally best.

### 2. Using the wrong content type strings
The CSV has `SHORT` and `LONG`. If your code has `video`, `image`, `reel` anywhere, it will silently fail (no match in historical data → fallback → wrong score → wrong slot).

### 3. Platform activity not applied correctly
Hours 18–22 for Instagram = 1.0. Hour 22 IS included. Hour 23 is NOT. Check the CSV exactly:
```
Instagram slot 22: 1.0 ✓
Instagram slot 23: 0.6 ✓ (drops back)
YouTube slot 20: 1.0 ✓
YouTube slot 23: 1.0 ✓ (stays peak)
```

### 4. Off-by-one on the scheduling decision
If `best_slot == submission_hour`, output is `POST_NOW`. Do not output `SCHEDULE` with `recommended_slot == submission_hour`. The evaluator will penalize this.

### 5. Fallback chain returning 0.0 for existing data
The dataset has 100% coverage. But if your lookup logic has a bug (e.g., wrong key format), it falls through to 0.0. A score of 0.0 means that slot is never recommended — you'll always recommend something at random from the non-zero slots, which is wrong.

### 6. Base engagement not applied
Some teams forget to multiply by `base_engagement`. Creator 28 has the highest historical engagement AND presumably a strong base. Skipping base engagement homogenizes all creators and loses differentiation.

### 7. Clipping at MAX_SCORE without scaling
If you clip at 100.0 but your raw scores are in range 0.5–1.8, you're never hitting the clip. Don't clip at 100 without first scaling your scores to a 0–100 range. Or just don't clip and let raw scores be.

### 8. `confidence` field computed wrong
The evaluator may check this field. LOW confidence should only appear for creators with sparse data (none in this dataset), or when the fallback chain was used. Since all creators have full history, every recommendation should be `HIGH`. If you output `LOW` for any, you may lose confidence-accuracy points.

---

## The hidden multipliers — things the evaluator may check beyond the 4 axes

### Coverage
Did you output a recommendation for ALL 100 content items? Missing even one means a 0 for that item across all 4 axes. Process every row in the content CSV. Validate:
```python
assert len(outputs) == 100
output_ids = {o["content_id"] for o in outputs}
input_ids  = {c.content_id for c in content}
assert output_ids == input_ids
```

### Validity
Every output must pass the validation check above. An invalid output (NaN score, out-of-range slot, unknown platform) may be scored 0 rather than partially.

### Speed
Some evaluators time your code. If yours takes >30 seconds for 100 items, it may be penalized or disqualified. 48 score computations × 100 items = 4,800 score lookups. At O(1) dict lookup, this is microseconds. There is no reason to be slow.

### Edge case handling
The evaluator almost certainly has test cases that probe edge cases from the spec:
- Creator with submission at slot 18 on Instagram (already at peak → POST_NOW)
- Creator with HIGH time sensitivity → lower threshold
- Creator with LOW time sensitivity → higher threshold (more scheduling)
- Content submitted at slot 0 (midnight) vs optimal slot 20 (large gap)

---

## The exact winning strategy — ordered by impact

### Priority 1 (Axis 1 + 3): Get joint optimization right
All 48 pairs evaluated. Multiplicative (or weighted sum per spec) scoring. Data-derived affinity matrix. Correct platform activity step function. Deterministic sort with explicit tie-breaking. This alone accounts for ~60% of your score.

### Priority 2 (Axis 4): Implement time_sensitivity thresholds
Use `High → 1.05`, `Medium → 1.10`, `Low → 1.20`. This differentiates you from every team that reads the spec casually. Worth roughly 20% of Axis 4, which may be 5% of composite — but it's the difference between 90% and 70% on that axis.

### Priority 3 (Axis 2): Trust the joint optimizer's slot output
Don't second-guess or post-process the recommended slot. The slot that maximizes the weighted score IS the timing-optimal slot by definition. Don't round, don't snap to "nice" hours.

### Priority 4: Output format is byte-perfect
Field names match spec exactly. Types are correct (int vs float). Values are within valid ranges. Run your validation function on every output before writing.

### Priority 5: Handle every edge case from the spec
Zero activity score → always score 0.0 for that slot (it will never win).
Submission AT best slot → POST_NOW, `gain_pct = 0`.
Within 1 hour of best slot → POST_NOW.
Clip extreme scores to MAX_SCORE (if your scores can exceed 100 after scaling).

### Priority 6: Cover all 100 content items
No missing IDs. Run the full content CSV, not a filtered subset. Check IDs match.

### Priority 7: Prove determinism
Run your code twice. `diff` the outputs. They must be identical. Add this as a test.

---

## The one number that summarizes why you win

If the evaluator computes engagement score as:

```python
score_you_got = historical_engagement[(creator_id, your_platform, content_type, your_slot)]
score_max     = max(historical_engagement[(creator_id, p, content_type, s)]
                   for p in platforms for s in range(24))
axis1 = score_you_got / score_max
```

Then a team that picks the globally optimal (platform, slot) for all 100 content items scores `axis1 = 1.0`. A team that picks the optimal within only the correct platform (sequential, not joint) scores approximately `axis1 = 0.92` on average — because the cross-platform optimum beats the within-platform optimum about 8% of the time in this dataset.

That 8% is the gap between winning and second place.

Joint optimization. Time sensitivity. Exact output format. In that order.