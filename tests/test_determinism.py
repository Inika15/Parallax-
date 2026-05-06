"""Determinism test — how_to_win.md Priority 7."""
import hashlib, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from main import run_pipeline

recs1, _ = run_pipeline("data/raw", "results/run1.json")
recs2, _ = run_pipeline("data/raw", "results/run2.json")

h1 = hashlib.sha256(json.dumps(recs1, sort_keys=True).encode()).hexdigest()
h2 = hashlib.sha256(json.dumps(recs2, sort_keys=True).encode()).hexdigest()
match = h1 == h2

print()
print("=" * 40)
if match:
    print("  DETERMINISM TEST: PASS")
else:
    print("  DETERMINISM TEST: FAIL")
print(f"  Run 1 hash: {h1[:20]}")
print(f"  Run 2 hash: {h2[:20]}")
print(f"  Identical:  {match}")
print("=" * 40)
