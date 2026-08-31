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
    new_line: int | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[-1]
            current = ChangedFile(path=Path(path), status="modified")
            files.append(current)
            new_line = None
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
            new_line = int(match.group(1))
        elif current and line.startswith("+") and not line.startswith("+++"):
            current.additions += 1
            if new_line is not None:
                current.changed_lines.add(new_line)
                new_line += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            current.deletions += 1
        elif current and new_line is not None and not line.startswith("\\"):
            new_line += 1
    return ChangeSummary(base=base, head=head, files=files)


def get_change(root: Path, *, base: str | None = None, staged: bool = False) -> ChangeSummary:
    args = ["diff", "--no-ext-diff", "--find-renames", "--unified=0"]
    if staged:
        args.append("--cached")
    if base:
        merge_base = _git(root, "merge-base", base, "HEAD").strip()
        if not merge_base:
            raise RuntimeError(f"no merge base found for {base} and HEAD")
        args.append(merge_base)
    change = parse_diff(_git(root, *args), base=base)
    if base is None and not staged:
        tracked_paths = {item.path for item in change.files}
        for value in _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
            if not value:
                continue
            path = Path(value)
            if path in tracked_paths:
                continue
            try:
                additions = len((root / path).read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeError):
                additions = 0
            change.files.append(
                ChangedFile(
                    path=path,
                    status="added",
                    additions=additions,
                    changed_lines=set(range(1, additions + 1)),
                )
            )
    return change


def changed_languages(change: ChangeSummary) -> set[str]:
    mapping = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript"}
    return {mapping[item.path.suffix.lower()] for item in change.files if item.path.suffix.lower() in mapping}


def finding_is_changed(path: Path, line: int | None, change: ChangeSummary) -> bool:
    return any(item.path == path and (line is None or line in item.changed_lines) for item in change.files)
