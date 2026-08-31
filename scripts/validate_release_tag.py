from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def expected_tag(project: Path) -> str:
    data = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    return f"v{data['project']['version']}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_release_tag.py TAG")
    expected = expected_tag(Path.cwd())
    if sys.argv[1] != expected:
        raise SystemExit(f"tag {sys.argv[1]} must equal {expected}")
