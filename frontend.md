# Frontend Plan — Creator Content Posting Optimizer
### PS4 · Professional Light Theme · Times New Roman

---

## Stack

- **Framework:** React (Vite)
- **Styling:** Plain CSS — no Tailwind, no component library
- **Font:** Times New Roman (system serif stack)
- **Theme:** Light only — `#1a1a1a` text, `#fafafa` surfaces, `#e0e0e0` borders
- **Charts:** Chart.js (heatmap + bar charts)
- **State:** React useState + useContext (no Redux needed)

---

## Design Tokens

```css
:root {
  --font:       'Times New Roman', Times, serif;
  --text-main:  #1a1a1a;
  --text-muted: #888888;
  --text-hint:  #bbbbbb;
  --bg-page:    #f5f5f5;
  --bg-card:    #ffffff;
  --bg-surface: #fafafa;
  --border:     #e0e0e0;
  --border-em:  #c0c0c0;
  --accent:     #1a1a1a;
  --green:      #2d7a3a;
  --green-bg:   #edf7f0;
  --amber:      #7a5a00;
  --amber-bg:   #fdf6e3;
  --red:        #8b1a1a;
  --red-bg:     #fff0f0;
  --purple:     #6b2178;
  --purple-bg:  #faf0fb;
  --radius:     3px;
  --radius-lg:  4px;
}
```

---

## File Structure

```
src/
├── main.jsx
├── App.jsx
├── index.css               ← global tokens + resets
├── components/
│   ├── TopBar.jsx
│   ├── StatCard.jsx
│   ├── Badge.jsx
│   ├── ScoreBar.jsx
│   ├── HeatmapGrid.jsx
│   ├── RecommendationTable.jsx
│   ├── ScoreBreakdown.jsx
│   ├── CreatorDNA.jsx
│   ├── CounterfactualPanel.jsx
│   ├── BatchCalendar.jsx
│   └── PipelineFlow.jsx
└── pages/
    ├── Dashboard.jsx       ← Screen 1
    ├── Optimize.jsx        ← Screen 2
    ├── CreatorProfile.jsx  ← Screen 3
    └── Schedule.jsx        ← Screen 4
```

---

## Screen 1 — Dashboard

**Route:** `/`

**Purpose:** Command center. Judges land here and immediately see the system is alive and working.

### Layout

```
┌─────────────────── TopBar ───────────────────┐
├──────────┬──────────┬──────────┬─────────────┤
│ Posts    │ Avg Lift │ Queued  │ Creators     │  ← 4 StatCards
│ 1,284    │ +34%     │ 427     │ 98           │
├────────────────────┬─────────────────────────┤
│ Recent recs table  │ Heatmap (IG + YT rows)  │
│                    │                          │
└────────────────────┴─────────────────────────┘
```

### Components

**StatCard** — muted 11px uppercase label, 22px Times New Roman number, 10px sub-label.

**RecommendationTable** — columns: Content ID · Platform (badge) · Slot · Decision (badge) · Score (number + bar). Rows sorted by score descending. Clicking a row navigates to `/optimize?id=...`.

**HeatmapGrid** — 2 rows (Instagram, YouTube) × 24 columns (hours). Cell darkness = activity score. Built with a CSS grid, each cell is a `div` with `background` set to `rgba(26,26,26, score)`. Hover shows a tooltip with exact score and hour.

### Key Detail

Top-right of TopBar shows a live status dot (green pulsing) labelled "System live" — small but signals the system is real-time capable.

---

## Screen 2 — Submit & Optimize

**Route:** `/optimize`

**Purpose:** The core demo screen. Submit content → watch the optimizer score all 48 platform×slot combinations → see the winner. This is the screen you demo to judges.

### Layout

```
┌─────────────────── TopBar ───────────────────┐
├─────────────────┬────────────────────────────┤
│ Submission form │ Best recommendation (green) │
│                 ├────────────────────────────┤
│ Creator DNA     │ All 48 candidates (ranked)  │
│ panel           ├────────────────────────────┤
│                 │ Score breakdown (weighted)  │
└─────────────────┴────────────────────────────┘
```

### Components

**Submission Form** (left sidebar)
- Creator dropdown
- Content type dropdown (Reel, Image, Long video, Story, Text)
- Submission hour slider (0–23, displays "9 AM" format)
- "Run Optimizer" button — triggers the backend call and animates results in

**Creator DNA Panel** (below form)
- Base multiplier, Instagram affinity, YouTube affinity
- 30-day trajectory (green "Trending up" / red "Trending down")
- Data richness percentage

**Best Recommendation Card** (top right, green border)
- Platform + time slot headline
- Score large in top-right corner
- "Schedule" or "Post now" badge
- Uplift vs. posting now (e.g. "+34% vs. posting now")

**Ranked Candidates Table**
- All evaluated (platform, slot) pairs sorted by score
- Rank column with ★ on row 1
- Score column with inline bar
- "vs. now" delta column (green positive, gray for zero)

**Score Breakdown Card**
- Four rows: Platform activity · Creator history · Base engagement · Content-type fit
- Each row: factor name · raw value × weight = contribution
- Total row with final composite score

### Key Detail

When "Run Optimizer" is clicked, results animate in row by row (CSS `@keyframes fadeInUp` with staggered delays). Makes it feel like the system is actually computing, not just loading.

---

## Screen 3 — Creator Profile & Counterfactual

**Route:** `/creators/:id`

**Purpose:** Deep-dive on one creator. Shows the system understands creators as individuals — not just global averages. The counterfactual table is the standout element here.

### Layout

```
┌─────────────────── TopBar ───────────────────┐
├─────────────────┬────────────────────────────┤
│ Creator card    │ Counterfactual analysis     │
│ (avatar, tags,  │                             │
│  stats, DNA)    ├────────────────────────────┤
│                 │ Scheduling pipeline flow    │
│ Data richness   │                             │
│ breakdown       │                             │
└─────────────────┴────────────────────────────┘
```

### Components

**Creator Card**
- Initials avatar (circle, 32px)
- Name + content type tags (small bordered chips)
- Stats: total posts optimized, avg score, best platform, peak slot
- 30-day trajectory per platform

**Data Richness Panel**
- History records count
- Platforms covered (e.g. 2/2)
- Content types covered (e.g. 5/5)
- Hours with data (e.g. 23/24)
- If richness < 30%: shows "Cold-start mode — using global averages" warning badge

**Counterfactual Analysis Table**
- Optimal post score (recommended)
- Worst possible slot score
- Random baseline (average across all slots)
- Value of optimizer = optimal − baseline (shown in green, bold)
- Below: a "what-if" section — user can pick any platform+slot and see projected score vs. optimal

**Scheduling Pipeline Flow**
- Horizontal step diagram: Content arrives → Score 48 slots → Pick best → Compare vs. now → POST NOW / SCHEDULE → Output JSON → Dispatch
- Each step is a small bordered box, connected by arrows
- Pure HTML/CSS, no SVG needed

---

## Screen 4 — Batch Schedule

**Route:** `/schedule`

**Purpose:** Shows the weekly calendar of all queued posts. Proves the greedy interval scheduler is working — posts are spread out, never stacked on the same creator at the same hour.

### Layout

```
┌─────────────────── TopBar ───────────────────┐
│ Week of May 6–12, 2026          [← Prev Week] [Next Week →] │
├────────┬─────┬─────┬─────┬─────┬─────┬─────┬──────┤
│ Hour   │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun  │
├────────┼─────┼─────┼─────┼─────┼─────┼─────┼──────┤
│ 12 PM  │  ▪  │     │  ▪  │     │  ▪  │     │  ▪   │
│  6 PM  │ ███ │ ███ │ ███ │ ███ │ ███ │ ███ │ ███  │
│  8 PM  │     │  ▪  │     │  ▪  │     │     │  ▪   │
└────────┴─────┴─────┴─────┴─────┴─────┴─────┴──────┘
  Legend: ███ Instagram peak   ▪ YouTube   ░ Story
```

### Components

**BatchCalendar**
- CSS grid: 8 columns (hour label + 7 days), N rows (hours that have posts)
- Each cell is a colored block — color encodes platform (Instagram = dark, YouTube = warm orange, Story = purple)
- Clicking a cell opens a small inline popover: creator name, content type, score, decision
- Prev/Next week navigation

**Legend Strip** — below the calendar, 10px serif labels with color swatches

### Key Detail

The calendar visually proves the greedy interval scheduler — no two posts from the same creator share the same hour on the same day. If you hover over 6 PM row, a tooltip says "Peak Instagram slot — 7 posts queued across 7 creators (no overlap)".

---

## TopBar (Global)

Present on all screens.

```
PostOptima          Dashboard  Creators  Schedule  Analytics          ● System live
```

- Left: product name in 14px Times New Roman, font-weight 500
- Center: nav links — active link has a 1px bottom border in `#1a1a1a`
- Right: green dot + "System live" in 10px muted serif
- Full-width, white background, 1px bottom border `#e0e0e0`
- Sticky at top

---

## Badge Component

Used everywhere for platform and decision labels.

```
Platform:   Instagram → purple pill    YouTube → red pill
Decision:   Post now  → green pill     Schedule → amber pill
```

CSS:
```css
.badge {
  font-family: 'Times New Roman', serif;
  font-size: 9px;
  padding: 2px 7px;
  border-radius: 2px;
  letter-spacing: 0.04em;
  border: 1px solid;
  display: inline-block;
}
.badge-ig       { background: #faf0fb; color: #6b2178; border-color: #e0b8e8; }
.badge-yt       { background: #fff0f0; color: #8b1a1a; border-color: #f0c0c0; }
.badge-now      { background: #edf7f0; color: #1a5e2a; border-color: #c3e6cb; }
.badge-schedule { background: #fdf6e3; color: #7a5a00; border-color: #f0d78a; }
```

---

## Standout Details That Win

**Animated optimizer run** — results stagger in row by row when "Run Optimizer" fires. 150ms delay between rows. Makes the algorithm feel real.

**Counterfactual delta** — every recommendation shows "+X% vs. posting now" in green. Judges immediately understand the system's value without reading any documentation.

**Data richness warning** — if a creator has sparse data, a small amber badge says "Cold-start mode." Shows the system handles edge cases gracefully, not just the happy path.

**Heatmap on Dashboard** — a 2×24 grid of activity scores is something no basic project shows. It communicates depth instantly.

**Greedy calendar** — the batch schedule screen proves the system solves the harder problem (multi-creator scheduling with no overlap), not just the single-item problem.

**Score breakdown transparency** — showing the weighted formula live (not just the final number) signals the system is explainable, not a black box. Judges love this.

---

## Build Order

| Day | Work |
|---|---|
| 1 | Global CSS tokens, TopBar, Badge, StatCard, routing skeleton |
| 2 | Screen 2 — Optimize (form + ranked table + score breakdown) |
| 3 | Screen 1 — Dashboard (heatmap + recs table + stat cards) |
| 4 | Screen 3 — Creator profile + counterfactual panel |
| 5 | Screen 4 — Batch calendar + polish + demo flow rehearsal |

---

*Professional. Explainable. Built to win.*