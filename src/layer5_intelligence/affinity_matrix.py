"""
Layer 5 — Content-Type × Platform Affinity Matrix

Data-derived from historical engagement means:
  Instagram SHORT mean: 0.830  |  YouTube SHORT mean: 0.547
  Instagram LONG mean:  0.551  |  YouTube LONG mean:  0.807

Affinity = 1.0 for natural fit, ~0.66 for mismatch.
"""

from typing import Dict, Tuple

# Data-derived affinity matrix (from ps4_logic.md)
# SHORT → Instagram is baseline 1.0 ; YouTube SHORT = 0.547/0.830 ≈ 0.659
# LONG  → YouTube is baseline 1.0 ;  Instagram LONG = 0.551/0.807 ≈ 0.682
_AFFINITY_MATRIX: Dict[Tuple[str, str], float] = {
    ("SHORT", "Instagram"): 1.0,
    ("SHORT", "YouTube"):   0.659,   # 0.547 / 0.830
    ("LONG",  "YouTube"):   1.0,
    ("LONG",  "Instagram"): 0.682,   # 0.551 / 0.807
}

DEFAULT_AFFINITY = 1.0


def get_content_platform_affinity(content_type: str, platform: str) -> float:
    """Get the data-derived affinity score for a content type on a platform."""
    return _AFFINITY_MATRIX.get((content_type, platform), DEFAULT_AFFINITY)


def get_affinity_matrix() -> Dict[Tuple[str, str], float]:
    """Return the full affinity matrix (read-only copy)."""
    return dict(_AFFINITY_MATRIX)
