# Analytics Tab — Implementation Plan
> Full logic for auth, data integration, and every metric panel. Built around the actual dataset schema.

---

## The big picture

The Analytics Tab is the mirror that shows a creator how they performed — historically, right now, and predictively. It lives inside the same app as the optimizer, is gated by login, and pulls from the same four CSVs (now tables in your DB). Every number on screen must trace back to a real column in a real table. No synthetic metrics.

---

## Part 1 — Auth & Login

Since there is no login system yet, build a minimal one that serves both the optimizer and analytics tab.

### What you need

```
User = { user_id, email, password_hash, creator_id, role }
```

`creator_id` is the foreign key that links a logged-in user to rows in `creators`, `historical_engagement`, and `content`. One user = one creator (for this scope).

### Schema

```sql
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    creator_id    INTEGER NOT NULL REFERENCES creators(creator_id),
    role          TEXT DEFAULT 'creator'   -- 'creator' | 'admin'
);

CREATE TABLE sessions (
    session_token TEXT PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    created_at    INTEGER NOT NULL,   -- unix timestamp
    expires_at    INTEGER NOT NULL
);
```

### Session flow

```
1. POST /auth/login
   body: { email, password }
   → verify hash → create session_token (uuid4) → set HttpOnly cookie
   → return { creator_id, creator_name }

2. Every protected route checks session_token cookie → resolves creator_id
   → injects creator_id into all downstream DB queries

3. POST /auth/logout → delete session row → clear cookie
```

### What session gives the analytics tab

Every analytics query is scoped by `creator_id` resolved from session. The tab never receives `creator_id` from the frontend — it always comes from the server-side session. This prevents one creator from viewing another's data.

---

## Part 2 — Database Tables (from CSVs)

Treat the 4 CSVs as the source of truth. Import them once and query from there.

```sql
-- From creators.csv
CREATE TABLE creators (
    creator_id      INTEGER PRIMARY KEY,
    base_engagement REAL NOT NULL,
    cooldown_hours  INTEGER NOT NULL
);

-- From content.csv
CREATE TABLE content (
    content_id         INTEGER PRIMARY KEY,
    creator_id         INTEGER NOT NULL REFERENCES creators(creator_id),
    content_type       TEXT NOT NULL CHECK(content_type IN ('SHORT','LONG')),
    created_timestamp  INTEGER NOT NULL,  -- hour 0-23 (submission hour)
    time_sensitivity   TEXT NOT NULL CHECK(time_sensitivity IN ('High','Medium','Low'))
);

-- From historical_engagement.csv
CREATE TABLE historical_engagement (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id     INTEGER NOT NULL,
    platform       TEXT NOT NULL CHECK(platform IN ('Instagram','YouTube')),
    content_type   TEXT NOT NULL CHECK(content_type IN ('SHORT','LONG')),
    time_slot      INTEGER NOT NULL CHECK(time_slot BETWEEN 0 AND 23),
    avg_engagement REAL NOT NULL,
    UNIQUE(creator_id, platform, content_type, time_slot)
);

-- From platform_activity.csv
CREATE TABLE platform_activity (
    platform       TEXT NOT NULL,
    time_slot      INTEGER NOT NULL,
    activity_score REAL NOT NULL,
    PRIMARY KEY (platform, time_slot)
);

-- Recommendations written by the optimizer (links analytics to decisions)
CREATE TABLE recommendations (
    rec_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id        INTEGER NOT NULL REFERENCES content(content_id),
    creator_id        INTEGER NOT NULL,
    platform          TEXT NOT NULL,
    recommended_slot  INTEGER NOT NULL,
    decision          TEXT NOT NULL,        -- 'POST_NOW' | 'SCHEDULE'
    score             REAL NOT NULL,
    submission_score  REAL NOT NULL,
    gain_pct          REAL NOT NULL,
    confidence        TEXT NOT NULL,
    created_at        INTEGER NOT NULL      -- unix timestamp
);
```

The `recommendations` table is written by the optimizer on every run. Analytics reads from it to show past decisions and their scores.

---

## Part 3 — Analytics Tab Structure

Six panels. Each maps to specific DB queries and specific columns.

```
┌─────────────────────────────────────────────────────┐
│  PANEL 1: Creator Scorecard (top bar)               │
├─────────────────────────┬───────────────────────────┤
│  PANEL 2: Engagement    │  PANEL 3: Platform        │
│  Heatmap (24h × 2 plat) │  Breakdown                │
├─────────────────────────┴───────────────────────────┤
│  PANEL 4: Content Performance History               │
├─────────────────────────┬───────────────────────────┤
│  PANEL 5: Submission    │  PANEL 6: Optimizer       │
│  Timing Audit           │  Impact                   │
└─────────────────────────┴───────────────────────────┘
```

---

## Panel 1 — Creator Scorecard

The top bar. Always visible. Updates on page load.

### Metrics shown

| Metric | Source | Formula |
|---|---|---|
| Base engagement | `creators` | `base_engagement` — raw value |
| Global avg engagement | `historical_engagement` | `AVG(avg_engagement) WHERE creator_id = ?` |
| Best platform | `historical_engagement` | Platform with higher `AVG(avg_engagement)` |
| Best content type | `historical_engagement` | Content type with higher `AVG(avg_engagement)` |
| Cooldown window | `creators` | `cooldown_hours` — shown as a label |
| Total submissions | `content` | `COUNT(*) WHERE creator_id = ?` |

### Query

```sql
SELECT
    c.base_engagement,
    c.cooldown_hours,
    COUNT(ct.content_id)                                AS total_submissions,
    ROUND(AVG(he.avg_engagement), 3)                    AS global_avg_engagement,
    (SELECT platform FROM historical_engagement
     WHERE creator_id = c.creator_id
     GROUP BY platform ORDER BY AVG(avg_engagement) DESC LIMIT 1) AS best_platform,
    (SELECT content_type FROM historical_engagement
     WHERE creator_id = c.creator_id
     GROUP BY content_type ORDER BY AVG(avg_engagement) DESC LIMIT 1) AS best_content_type
FROM creators c
LEFT JOIN content ct ON ct.creator_id = c.creator_id
LEFT JOIN historical_engagement he ON he.creator_id = c.creator_id
WHERE c.creator_id = ?
GROUP BY c.creator_id;
```

### Display logic

- `base_engagement` < 0.80 → show "Below average" label (red)
- `base_engagement` 0.80–1.10 → "Average" (neutral)
- `base_engagement` > 1.10 → "Power creator" (green)
- `best_platform` renders with a platform badge (Instagram pink / YouTube red)

---

## Panel 2 — Engagement Heatmap

The standout visual. A 24×2 grid (rows = hours 0–23, columns = Instagram / YouTube) where cell color = `avg_engagement` for this creator at that hour and platform, averaged across content types.

### Query

```sql
SELECT
    platform,
    time_slot,
    ROUND(AVG(avg_engagement), 3) AS avg_score
FROM historical_engagement
WHERE creator_id = ?
GROUP BY platform, time_slot
ORDER BY platform, time_slot;
```

### Rendering logic

- Build a 24-row × 2-column table in HTML
- Color scale: min engagement → `#E1F5EE` (pale teal), max → `#0F6E56` (dark teal)
- Normalize: `cell_color_intensity = (score - global_min) / (global_max - global_min)`
- Overlay platform activity tier: slots with `activity_score = 1.0` get a small "peak" badge on the cell border
- Hover tooltip shows: `Hour {slot}:00 · {platform} · avg_engagement = {score} · Platform activity: {0.6 or 1.0}`
- Mark the creator's personal peak slot with a pin icon (darkest cell + bold border)

### What this tells the creator

The heatmap answers "when should I post on which platform" entirely from their own historical data — not from global benchmarks. If creator 28 (the top performer) has a spike at 3 AM on Instagram, their heatmap shows it. Nobody else's does.

---

## Panel 3 — Platform Breakdown

Side-by-side comparison: Instagram vs YouTube, across both content types.

### Metrics

| Metric | Formula |
|---|---|
| Avg engagement by platform | `AVG(avg_engagement) GROUP BY platform` |
| Avg engagement by platform × type | `AVG(avg_engagement) GROUP BY platform, content_type` |
| Best slot per platform | `time_slot ORDER BY avg_engagement DESC LIMIT 1` per platform |
| Platform affinity ratio | `avg_Instagram / avg_YouTube` — if > 1.2, creator is "Instagram-native" |

### Query

```sql
SELECT
    platform,
    content_type,
    ROUND(AVG(avg_engagement), 3)  AS avg_eng,
    MAX(avg_engagement)            AS peak_eng,
    (SELECT time_slot FROM historical_engagement h2
     WHERE h2.creator_id = h1.creator_id
       AND h2.platform = h1.platform
       AND h2.content_type = h1.content_type
     ORDER BY avg_engagement DESC LIMIT 1) AS best_slot
FROM historical_engagement h1
WHERE creator_id = ?
GROUP BY platform, content_type;
```

### Display logic

Four stat cards arranged in a 2×2 grid:

```
Instagram × SHORT    |    Instagram × LONG
YouTube × SHORT      |    YouTube × LONG
```

Each card shows: avg engagement, peak engagement, best posting hour. Highlight the winning cell (highest avg) with a green border. The platform affinity ratio is shown as a sentence: *"You perform 1.52× better on Instagram than YouTube overall."*

---

## Panel 4 — Content Performance History

A sortable table of every content submission this creator made, plus the optimizer's recommendation for it.

### Columns

| Column | Source |
|---|---|
| Content ID | `content.content_id` |
| Type | `content.content_type` |
| Submitted at | `content.created_timestamp` (formatted as "Hour 6:00") |
| Time sensitivity | `content.time_sensitivity` |
| Recommended platform | `recommendations.platform` |
| Recommended slot | `recommendations.recommended_slot` |
| Decision | `recommendations.decision` — badge: POST_NOW (green) / SCHEDULE (amber) |
| Optimizer score | `recommendations.score` |
| Gain vs. submission | `recommendations.gain_pct` — formatted as "+42.8%" |
| Confidence | `recommendations.confidence` — HIGH / MEDIUM / LOW |

### Query

```sql
SELECT
    ct.content_id,
    ct.content_type,
    ct.created_timestamp   AS submitted_hour,
    ct.time_sensitivity,
    r.platform,
    r.recommended_slot,
    r.decision,
    ROUND(r.score, 1)      AS score,
    ROUND(r.gain_pct, 1)   AS gain_pct,
    r.confidence
FROM content ct
LEFT JOIN recommendations r ON r.content_id = ct.content_id
WHERE ct.creator_id = ?
ORDER BY ct.content_id DESC;
```

### Display logic

- Default sort: most recent content first
- Sortable columns: score (desc), gain_pct (desc), submitted_hour (asc)
- `gain_pct` coloring: > 30% = green, 10–30% = amber, < 10% = gray
- `decision = POST_NOW` and `gain_pct > 30%` → add a warning tooltip: "You submitted at peak time — great instinct!"
- `decision = SCHEDULE` with `time_sensitivity = High` → flag row: "High-urgency content was deferred — review"
- Rows with no recommendation (content submitted but optimizer not yet run) → grayed out with "Pending" label

---

## Panel 5 — Submission Timing Audit

Answers: "Are you actually posting at good times, or are you leaving engagement on the table?"

### Metrics

| Metric | Formula |
|---|---|
| Avg submission hour | `AVG(created_timestamp)` from `content WHERE creator_id = ?` |
| Peak hour (personal) | `time_slot` with highest `avg_engagement`, aggregated across platforms |
| Submission vs. peak gap | `ABS(avg_submission_hour - personal_peak_hour)` |
| % submissions in peak window | Count of content where `created_timestamp IN (18,19,20,21,22)` / total |
| Wasted potential | Avg `gain_pct` across all SCHEDULE decisions — how much was left on the table |

### Query

```sql
SELECT
    ROUND(AVG(ct.created_timestamp), 1)  AS avg_submission_hour,
    COUNT(*)                             AS total_submissions,
    SUM(CASE WHEN ct.created_timestamp BETWEEN 18 AND 22 THEN 1 ELSE 0 END) AS peak_submissions,
    ROUND(AVG(r.gain_pct), 1)           AS avg_potential_gain,
    SUM(CASE WHEN r.decision = 'SCHEDULE' THEN 1 ELSE 0 END) AS scheduled_count,
    SUM(CASE WHEN r.decision = 'POST_NOW' THEN 1 ELSE 0 END) AS posted_now_count
FROM content ct
LEFT JOIN recommendations r ON r.content_id = ct.content_id
WHERE ct.creator_id = ?;
```

### Display logic

Render as a mini-report, not a table:

- Horizontal bar: "X% of your submissions land in peak platform hours"
- If `avg_potential_gain > 20%` → show callout: *"On average, the optimizer found a {avg_potential_gain}% better slot than when you submitted. Consider batching your posts and scheduling."*
- Bar chart: submission hour distribution (24 bars, highlight peak window in teal)
- Overlaid line: personal engagement curve from Panel 2 (same 24h axis) — so the creator can visually see the mismatch between when they submit vs when they should post

---

## Panel 6 — Optimizer Impact

The "value of the system" panel. Shows what the optimizer gave this creator, quantified.

### Metrics

| Metric | Description |
|---|---|
| Best recommendation | Highest scoring `(platform, slot)` the optimizer ever found for this creator |
| Worst counterfactual | Lowest possible score if they'd posted at the worst slot |
| Avg score uplift | `AVG(score - submission_score)` across all recommendations |
| Total potential gain | `SUM(gain_pct)` — cumulative lift if all recommendations had been followed |
| Schedule rate | % of items where `decision = SCHEDULE` |
| Confidence breakdown | Count of HIGH / MEDIUM / LOW recommendations |

### Query

```sql
SELECT
    MAX(r.score)                                    AS best_score,
    MIN(r.submission_score)                         AS worst_submission_score,
    ROUND(AVG(r.score - r.submission_score), 2)     AS avg_score_uplift,
    ROUND(AVG(r.gain_pct), 1)                       AS avg_gain_pct,
    MAX(r.gain_pct)                                 AS max_single_gain,
    SUM(CASE WHEN r.decision='SCHEDULE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS schedule_rate_pct,
    SUM(CASE WHEN r.confidence='HIGH' THEN 1 ELSE 0 END)   AS high_confidence_count,
    SUM(CASE WHEN r.confidence='MEDIUM' THEN 1 ELSE 0 END) AS medium_confidence_count,
    SUM(CASE WHEN r.confidence='LOW' THEN 1 ELSE 0 END)    AS low_confidence_count
FROM recommendations r
WHERE r.creator_id = ?;
```

### Display logic

- Hero number: `avg_score_uplift` shown large — "The optimizer improved your average score by **+{uplift} points**"
- Counterfactual highlight: "Your worst possible post would have scored {worst_submission_score}. Your best optimizer recommendation scored {best_score}. That's a {best_score - worst_submission_score:.1f}pt gap."
- Donut chart: HIGH / MEDIUM / LOW confidence split
- Bar: max single gain — "Your single biggest opportunity: +{max_single_gain:.1f}% on content #{best_content_id}"
- This is the "Demo God moment" panel — the number a judge reads and says "wow"

---

## Part 4 — Insights drawn from Instagram/Creator analytics standards (applied to this system)

The reel linked (DWoFdQcDT4y) is inaccessible via robots.txt, but based on what Instagram's native analytics, creator documentation, and modern dashboards consistently surface as the critical signals, here is what to incorporate:

### Metric 1: Watch-time equivalent → Engagement retention curve
Instagram's 2025 "Views Insights" update added drop-off curves for Reels. Our system doesn't have watch time, but `avg_engagement` across 24 slots is the equivalent: plot how engagement decays (or peaks) across the day for this creator. Show the retention curve per platform. The shape of that curve is the key diagnostic.

### Metric 2: Sends-to-reach ratio (Adam Mosseri's top metric)
Instagram's head publicly called out sends-per-reach as the metric the algorithm weighs most. In our system, the proxy is: `gain_pct` on SHORT content posted to Instagram — short content with high engagement = high share-worthiness. Flag content where optimizer score > 80 as "share-optimized".

### Metric 3: Follower vs non-follower reach split
Instagram shows what % of reach came from non-followers. Our system can simulate this: `platform_activity_score = 1.0` slots reach beyond followers. Show a label: "Posts at peak hours reach {peak_pct}% wider audience based on platform activity."

### Metric 4: Content-type performance gap
Instagram's Creator Insights shows Reels vs Posts vs Stories side by side. Our equivalent: the `SHORT vs LONG` split in Panel 3. Emphasize the delta — if SHORT performs 1.52× better on Instagram, say it explicitly as a recommendation.

### Metric 5: Peak active time overlay
Instagram's audience insights show when followers are most active by hour. Our system has this exactly: `platform_activity` gives peak hours, and `historical_engagement` gives personal peak. Panel 5 overlays both. The visual gap between "when you post" and "when your audience is active" is the most actionable insight on the entire tab.

### Metric 6: Engagement trend (trajectory)
Instagram Insights shows 30-day trends. Our system has `avg_engagement` per slot per creator — compute a synthetic trend by comparing the top 5 slots' scores versus the bottom 5. If the spread is wide, the creator has strong peak slots worth exploiting. If flat, timing matters less than content type.

### Metric 7: Completion rate analog
The first 3 seconds of a Reel determine completion. In our system, SHORT content's engagement score IS this signal — SHORT at peak slots = content that hooks. Add a "hook score" label to any SHORT content recommendation with score > 75.

---

## Part 5 — API Endpoints

```
GET  /api/analytics/scorecard          → Panel 1 data
GET  /api/analytics/heatmap            → Panel 2 data (48 rows)
GET  /api/analytics/platform-breakdown → Panel 3 data
GET  /api/analytics/content-history    → Panel 4 data (paginated)
GET  /api/analytics/timing-audit       → Panel 5 data
GET  /api/analytics/optimizer-impact   → Panel 6 data
```

All endpoints:
- Read `creator_id` from server-side session cookie — never from query param
- Return `401` if no valid session exists
- Return `200 + JSON` with exact field names matching the queries above
- No endpoint takes `creator_id` as input from the client

---

## Part 6 — File structure

```
analytics/
├── auth/
│   ├── login.py          # POST /auth/login — hash check, session create
│   ├── logout.py         # POST /auth/logout — session delete
│   └── middleware.py     # session_required decorator for all analytics routes
├── db/
│   ├── schema.sql        # all CREATE TABLE statements above
│   └── seed.py           # import CSVs into SQLite
├── routes/
│   ├── scorecard.py
│   ├── heatmap.py
│   ├── platform_breakdown.py
│   ├── content_history.py
│   ├── timing_audit.py
│   └── optimizer_impact.py
├── frontend/
│   ├── analytics.html    # the tab
│   ├── login.html        # login page
│   └── analytics.js      # fetch each panel, render heatmap grid, charts
└── tests/
    ├── test_auth.py       # login/logout/session expiry
    ├── test_analytics.py  # all 6 panel queries with fixture data
    └── test_isolation.py  # creator A cannot see creator B's data
```

---

## Part 7 — What makes this analytcs tab genuinely stand out

### 1. The heatmap is personalized, not generic
Every creator's heatmap looks different. Creator 28 (the top performer in the dataset) peaks at different slots than creator 1. The color scale is normalized per creator — not globally. A low-engagement creator still sees their relative best hours clearly.

### 2. The timing audit panel shows the gap nobody talks about
Most analytics dashboards show when your audience is active. This one shows the gap between when YOU actually submit content and when you should. That delta, visualized on the same 24h axis, is the most immediately actionable insight in the entire tab.

### 3. The optimizer impact panel quantifies the system's value
Every judge, every user wants to know: "what did this actually do for me?" Panel 6 answers with a number. Not a description. A specific point-score uplift derived from their own data.

### 4. Confidence tiers are honest
Not every recommendation is equally trustworthy. The confidence field (HIGH/MEDIUM/LOW) surfaces data quality. Showing this in Panel 6's donut chart signals mature engineering thinking — the system knows what it doesn't know.

### 5. The session architecture prevents data leakage
`creator_id` is never passed from the frontend. It is always resolved server-side from the session. This is a real engineering decision, not a handwave. In your README and demo, mention it explicitly: "Analytics data is session-scoped — you can only see your own history."