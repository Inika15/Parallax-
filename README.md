# Creator Content Posting Optimization System

## Team Information
- **Team Name**: Parallax
- **Year**: 1
- **All-Female Team**: Yes

## Architecture Overview

Our system uses a 6-layer multiplicative scoring architecture. For each content item, we jointly evaluate all 48 candidate combinations (2 platforms × 24 time slots) using a weighted geometric product of four signals:

**Optimal Posting Time:** We score every hour on every platform simultaneously. The joint optimizer picks the global best (platform, slot) pair — not just the best slot on one platform. Tie-breaking is deterministic: highest score → earliest slot → alphabetical platform.

**Platform Selection:** We derive content-type affinity from measured historical engagement means (SHORT averages 0.830 on Instagram vs 0.547 on YouTube). SHORT content routes to Instagram; LONG to YouTube — data-driven, not hardcoded.

**Balancing Signals:** The multiplicative formula — `PA^0.30 × CH^0.40 × CB^0.15 × CF^0.15 × 100` — weights creator-specific history most heavily (40%), ensuring a creator with strong personal engagement at an off-peak hour can outperform a generic peak slot. Zero on any factor tanks the score.

**Scheduling Decision:** We compare the optimal-slot score against the current-slot score using time-sensitivity-adjusted thresholds (High: 5%, Medium: 10%, Low: 20% improvement required). Urgent content posts sooner; flexible content waits for peak windows. Posts within 1 hour of optimal always post immediately.

---

*Keep your description concise and focused on your core decision-making logic.*

**Note:** Please do not change the format or spelling of anything in this README. The fields are extracted using a script, so any changes to the structure or formatting may break the extraction process.
