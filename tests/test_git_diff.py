from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentguard.core.git_diff import get_change


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def repository(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "tests@example.com")
    git(root, "config", "user.name", "AgentGuard tests")


def commit_all(root: Path, message: str) -> None:
    git(root, "add", ".")
    git(root, "commit", "-qm", message)


def test_change_uses_merge_base_and_excludes_preexisting_branch_changes(tmp_path: Path) -> None:
    repository(tmp_path)
    source = tmp_path / "source.py"
    source.write_text("base\n", encoding="utf-8")
    commit_all(tmp_path, "base")
    main = git(tmp_path, "branch", "--show-current")

    git(tmp_path, "checkout", "-qb", "feature")
    source.write_text("base\nfeature\n", encoding="utf-8")
    commit_all(tmp_path, "feature")

    git(tmp_path, "checkout", "-q", main)
    (tmp_path / "main.py").write_text("main\n", encoding="utf-8")
    commit_all(tmp_path, "main")
    git(tmp_path, "checkout", "-q", "feature")

    change = get_change(tmp_path, base=main)
    assert [item.path for item in change.files] == [Path("source.py")]
    assert change.files[0].changed_lines == {2}


def test_change_handles_rename_delete_and_spaces(tmp_path: Path) -> None:
    repository(tmp_path)
    old = tmp_path / "old name.py"
    deleted = tmp_path / "deleted.py"
    old.write_text("one\ntwo\n", encoding="utf-8")
    deleted.write_text("gone\n", encoding="utf-8")
    commit_all(tmp_path, "base")
    base = git(tmp_path, "rev-parse", "HEAD")

    old.rename(tmp_path / "new name.py")
    deleted.unlink()
    git(tmp_path, "add", "-A")
    change = get_change(tmp_path, base=base)

    files = {item.path: item for item in change.files}
    assert files[Path("new name.py")].status == "renamed"
    assert files[Path("new name.py")].old_path == Path("old name.py")
    assert files[Path("deleted.py")].status == "deleted"


def test_initial_repository_includes_untracked_files(tmp_path: Path) -> None:
    repository(tmp_path)
    path = tmp_path / "first file.py"
    path.write_text("one\ntwo\n", encoding="utf-8")

    change = get_change(tmp_path)

    assert len(change.files) == 1
    assert change.files[0].path == Path("first file.py")
    assert change.files[0].status == "added"
    assert change.files[0].changed_lines == {1, 2}


def test_shallow_clone_reports_missing_base(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    repository(source)
    path = source / "app.py"
    path.write_text("one\n", encoding="utf-8")
    commit_all(source, "first")
    first = git(source, "rev-parse", "HEAD")
    path.write_text("one\ntwo\n", encoding="utf-8")
    commit_all(source, "second")

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", source.as_uri(), str(clone)], check=True
    )
    with pytest.raises(RuntimeError, match="[Nn]ot a valid (commit|object)|unknown revision"):
        get_change(clone, base=first)
