"""Remove only reproducible build caches; preserve databases, reports and datasets."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for relative in [
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "frontend/dist",
    "frontend/test-results",
    "frontend/playwright-report",
]:
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise RuntimeError("Invalid clean target")
    if target.exists():
        shutil.rmtree(target)
        print("Removed " + relative)
