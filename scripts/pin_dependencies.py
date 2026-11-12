"""Pin direct dependencies to the versions already resolved in the reviewed uv lock."""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

root = Path(__file__).resolve().parents[1]
packages = {p["name"]: p["version"] for p in tomllib.loads((root / "uv.lock").read_text())["package"]}
path = root / "pyproject.toml"
data = tomllib.loads(path.read_text())
content = path.read_text()
for requirement in data["project"]["dependencies"] + data["dependency-groups"]["dev"]:
    parsed = Requirement(requirement)
    version = packages[parsed.name.lower().replace("_", "-")]
    extras = "[" + ",".join(sorted(parsed.extras)) + "]" if parsed.extras else ""
    pinned = parsed.name + extras + "==" + version
    content = content.replace('"' + requirement + '"', '"' + pinned + '"')
path.write_text(content, encoding="utf-8")
print("Pinned all direct runtime and development dependencies to uv.lock")
