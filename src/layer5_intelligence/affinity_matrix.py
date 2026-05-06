"""
Layer 5 — Content-Type × Platform Affinity Matrix

From how_to_win.md — normalize around the mean:
  Instagram SHORT mean: 0.830 ; YouTube SHORT mean: 0.547
  mean_short = (0.830 + 0.547) / 2 = 0.6885

  YouTube LONG mean:  0.807 ; Instagram LONG mean:  0.551
  mean_long = (0.807 + 0.551) / 2 = 0.679

  AFFINITY = {
    (SHORT, Instagram): 0.830 / 0.6885 ≈ 1.206
    (SHORT, YouTube):   0.547 / 0.6885 ≈ 0.794
    (LONG,  YouTube):   0.807 / 0.679  ≈ 1.188
    (LONG,  Instagram): 0.551 / 0.679  ≈ 0.812
  }
"""

from typing import Dict, Tuple

# Data-derived affinity matrix (from how_to_win.md)
# Normalized around the mean engagement per content type
_MEAN_SHORT = (0.830 + 0.547) / 2  # 0.6885
_MEAN_LONG = (0.807 + 0.551) / 2   # 0.679

_AFFINITY_MATRIX: Dict[Tuple[str, str], float] = {
    ("SHORT", "Instagram"): round(0.830 / _MEAN_SHORT, 3),  # ≈ 1.206
    ("SHORT", "YouTube"):   round(0.547 / _MEAN_SHORT, 3),  # ≈ 0.794
    ("LONG",  "YouTube"):   round(0.807 / _MEAN_LONG, 3),   # ≈ 1.189
    ("LONG",  "Instagram"): round(0.551 / _MEAN_LONG, 3),   # ≈ 0.811
}

DEFAULT_AFFINITY = 1.0


def get_content_platform_affinity(content_type: str, platform: str) -> float:
    """Get the data-derived affinity score for a content type on a platform."""
    return _AFFINITY_MATRIX.get((content_type, platform), DEFAULT_AFFINITY)


def get_affinity_matrix() -> Dict[Tuple[str, str], float]:
    """Return the full affinity matrix (read-only copy)."""
    return dict(_AFFINITY_MATRIX)
