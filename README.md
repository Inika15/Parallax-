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
