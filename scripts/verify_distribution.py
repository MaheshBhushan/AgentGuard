from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

REQUIRED = {"agentguard/__init__.py", "agentguard/cli/app.py"}
FORBIDDEN_PARTS = {".env", ".git", "__pycache__", "archive", "node_modules"}


def _relative_names(path: Path) -> set[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return set(archive.namelist())
    with tarfile.open(path) as archive:
        names = archive.getnames()
    prefix = names[0].split("/", 1)[0]
    return {name.removeprefix(f"{prefix}/") for name in names}


def verify(directory: Path) -> None:
    artifacts = sorted(directory.glob("agentguard_quality-*"))
    if len(artifacts) != 2 or not any(path.suffix == ".whl" for path in artifacts):
        raise ValueError("expected exactly one wheel and one source distribution")
    for artifact in artifacts:
        names = _relative_names(artifact)
        missing = REQUIRED - names
        if missing:
            raise ValueError(f"{artifact.name} is missing: {', '.join(sorted(missing))}")
        unsafe = sorted(
            name for name in names if FORBIDDEN_PARTS.intersection(Path(name).parts)
        )
        if unsafe:
            raise ValueError(f"{artifact.name} contains forbidden paths: {', '.join(unsafe)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_distribution.py DIST_DIRECTORY")
    verify(Path(sys.argv[1]))
