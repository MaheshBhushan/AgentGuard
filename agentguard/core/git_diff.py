from __future__ import annotations

import re
import subprocess
from pathlib import Path

from agentguard.core.models import ChangedFile, ChangeSummary

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def repository_root(path: Path | None = None) -> Path:
    return Path(_git(path or Path.cwd(), "rev-parse", "--show-toplevel").strip())


def current_branch(root: Path) -> str:
    return _git(root, "branch", "--show-current").strip() or "HEAD"


def parse_diff(text: str, base: str | None = None, head: str = "working-tree") -> ChangeSummary:
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[-1]
            current = ChangedFile(path=Path(path), status="modified")
            files.append(current)
        elif current and line.startswith("new file mode"):
            current.status = "added"
        elif current and line.startswith("deleted file mode"):
            current.status = "deleted"
        elif current and line.startswith("rename from "):
            current.old_path = Path(line[12:])
            current.status = "renamed"
        elif current and line.startswith("rename to "):
            current.path = Path(line[10:])
        elif current and (match := _HUNK.match(line)):
            start, count = int(match.group(1)), int(match.group(2) or 1)
            current.changed_lines.update(range(start, start + count))
        elif current and line.startswith("+") and not line.startswith("+++"):
            current.additions += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            current.deletions += 1
    return ChangeSummary(base=base, head=head, files=files)


def get_change(root: Path, *, base: str | None = None, staged: bool = False) -> ChangeSummary:
    args = ["diff", "--no-ext-diff", "--find-renames"]
    if staged:
        args.append("--cached")
    if base:
        args.append(base)
    return parse_diff(_git(root, *args), base=base)


def changed_languages(change: ChangeSummary) -> set[str]:
    mapping = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript"}
    return {mapping[item.path.suffix.lower()] for item in change.files if item.path.suffix.lower() in mapping}


def finding_is_changed(path: Path, line: int | None, change: ChangeSummary) -> bool:
    return any(item.path == path and (line is None or line in item.changed_lines) for item in change.files)
