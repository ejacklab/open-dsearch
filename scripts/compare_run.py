#!/usr/bin/env python3
"""Run comparison: Python pipeline vs Rust pipeline on same topic."""
import subprocess, time, sys, json
from pathlib import Path

TOPIC = "Rust async patterns"
QUERIES = 3
PY_COLLECTION = "/tmp/zvec-python-test"
RUST_COLLECTION = "/tmp/zvec-rust-test"

def timed(cmd, label):
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - t0
    print(r.stdout)
    if r.stderr:
        print("[STDERR]", r.stderr[:500])
    print(f"[{label}] elapsed: {elapsed:.1f}s")
    return elapsed, r.returncode

# Clean collections
for p in [PY_COLLECTION, RUST_COLLECTION]:
    subprocess.run(["rm", "-rf", p], check=False)

# 1. Python pipeline
python_script = Path(__file__).parent / "research_python.py"
py_elapsed, py_rc = timed(
    ["python3", str(python_script), TOPIC,
     "-Q", str(QUERIES),
     "--index", "--index-collection", PY_COLLECTION,
     "-m", "json", "-n", "10"],
    "PYTHON PIPELINE"
)

# 2. Rust pipeline
rust_binary = Path(__file__).parent / "rust" / "target" / "release" / "research"
rust_elapsed, rust_rc = timed(
    [str(rust_binary), "--topic", TOPIC,
     "--queries", str(QUERIES),
     "--mode", "json"],
    "RUST PIPELINE"
)

# 3. Query both collections
push_script = Path(__file__).parent / "push_zvec.py"
for name, coll in [("Python", PY_COLLECTION), ("Rust", RUST_COLLECTION)]:
    print(f"\n{'='*60}")
    print(f"ZVec QUERY RESULTS: {name} collection")
    print(f"{'='*60}")
    r = subprocess.run(
        ["python3", str(push_script), "query", "async concurrency",
         "-n", "5", "-t", TOPIC, "-c", coll],
        capture_output=True, text=True, timeout=15
    )
    print(r.stdout or "(no output)")
    if r.stderr:
        print("[STDERR]", r.stderr[:200])

# 4. Stats for both
for name, coll in [("Python", PY_COLLECTION), ("Rust", RUST_COLLECTION)]:
    r = subprocess.run(
        ["python3", str(push_script), "stats", "-c", coll],
        capture_output=True, text=True, timeout=10
    )
    print(f"{name} collection stats: {r.stdout.strip()}")

# 5. Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"Python pipeline: {py_elapsed:.1f}s (rc={py_rc})")
print(f"Rust pipeline:   {rust_elapsed:.1f}s (rc={rust_rc})")
if py_elapsed and rust_elapsed:
    print(f"Speed ratio:     Python is {rust_elapsed/max(py_elapsed,0.1):.1f}x {'slower' if rust_elapsed > py_elapsed else 'faster'}")
