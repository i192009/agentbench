"""Prove gate process exit codes with a good and deliberately broken agent."""

import json
import subprocess
import sys
from pathlib import Path

root = Path("artifacts/ci-proof")
root.mkdir(parents=True, exist_ok=True)
results = {}
for version, expected, name in [("v1", 0, "baseline"), ("v2-faulty", 1, "controlled-regression")]:
    with (root / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            [sys.executable, "scripts/ci_gate.py", "--version", version, "--output", str(root / name)],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    results[name] = {
        "version": version,
        "expected_exit_code": expected,
        "actual_exit_code": result.returncode,
    }
    if result.returncode != expected:
        print((root / f"{name}.log").read_text())
        raise SystemExit(f"{name}: expected exit {expected}, got {result.returncode}")
(root / "exit-codes.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
