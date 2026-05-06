"""
Test Determinism — how_to_win.md Priority 7.
=============================================
Run the full optimizer pipeline twice on identical input.
Assert byte-identical output (SHA-256 hash comparison).
"""

import hashlib
import json
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from main import run_pipeline


def test_determinism():
    """Run the pipeline twice — SHA-256 hashes must match."""
    recs1, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run1.json"))
    recs2, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run2.json"))

    h1 = hashlib.sha256(json.dumps(recs1, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(recs2, sort_keys=True).encode()).hexdigest()

    assert h1 == h2, f"Pipeline NOT deterministic! Hash1={h1[:20]} Hash2={h2[:20]}"


def test_recommendation_count():
    """Every content item must produce exactly one recommendation."""
    recs, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run_count.json"))
    assert len(recs) == 100, f"Expected 100 recs, got {len(recs)}"


def test_valid_platforms():
    """All recommendations must use valid platform names."""
    recs, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run_plat.json"))
    for r in recs:
        assert r["platform"] in {"Instagram", "YouTube"}, f"Invalid platform: {r['platform']}"


def test_valid_decisions():
    """All decisions must be POST_NOW or SCHEDULE."""
    recs, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run_dec.json"))
    for r in recs:
        assert r["decision"] in {"POST_NOW", "SCHEDULE"}, f"Invalid decision: {r['decision']}"


def test_valid_slots():
    """All recommended slots must be in [0, 23]."""
    recs, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run_slot.json"))
    for r in recs:
        assert 0 <= r["recommended_slot"] <= 23, f"Invalid slot: {r['recommended_slot']}"


def test_content_ids_are_integers():
    """All content_ids must be integers per how_to_win.md."""
    recs, _ = run_pipeline("data/raw", os.path.join(ROOT, "results", "run_ids.json"))
    for r in recs:
        assert isinstance(r["content_id"], int), f"content_id must be int, got {type(r['content_id'])}"
