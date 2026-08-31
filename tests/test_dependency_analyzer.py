import asyncio
import json
import subprocess
from pathlib import Path

from agentguard.analyzers.base import AnalysisContext
from agentguard.analyzers.dependencies import DependencyAnalyzer
from agentguard.analyzers.dependencies.analyzer import parse_manifest
from agentguard.core.config import AgentGuardConfig
from agentguard.core.models import ChangedFile, ChangeSummary


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_parse_python_manifests_distinguishes_development_dependencies() -> None:
    runtime, development = parse_manifest(
        Path("pyproject.toml"),
        b'[project]\ndependencies=["Requests>=2"]\n[project.optional-dependencies]\ndev=["pytest"]\n',
    )
    assert runtime == {"requests"}
    assert development == {"pytest"}
    assert parse_manifest(Path("requirements/dev.txt"), b"ruff==1\n")[1] == {"ruff"}


def test_dependency_delta_counts_add_remove_and_dev(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    manifest = tmp_path / "package.json"
    manifest.write_text(
        json.dumps({"dependencies": {"old": "1"}, "devDependencies": {}}), encoding="utf-8"
    )
    _git(tmp_path, "add", "package.json")
    _git(tmp_path, "commit", "-qm", "baseline")
    manifest.write_text(
        json.dumps({"dependencies": {"new": "1"}, "devDependencies": {"vitest": "1"}}),
        encoding="utf-8",
    )
    context = AnalysisContext(
        root=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("package.json"), status="modified")]),
        config=AgentGuardConfig(),
    )
    result = asyncio.run(DependencyAnalyzer().analyze(context))
    assert result.metrics == {
        "new_dependencies": 1,
        "removed_dependencies": 1,
        "new_dev_dependencies": 1,
        "dependency_count_delta": 1,
    }
    assert {finding.metadata["dependency"] for finding in result.findings} == {"new", "vitest"}


def test_missing_dependency_baseline_is_explicit(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    context = AnalysisContext(
        root=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("requirements.txt"), status="modified")]),
        config=AgentGuardConfig(),
    )
    result = asyncio.run(DependencyAnalyzer().analyze(context))
    assert result.message == "baseline unavailable for: requirements.txt"
    assert result.metrics["new_dependencies"] == 0


def test_lockfile_identifies_ecosystem_without_vulnerability_claims(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    context = AnalysisContext(
        root=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("uv.lock"), status="added")]),
        config=AgentGuardConfig(),
    )
    result = asyncio.run(DependencyAnalyzer().analyze(context))
    assert result.message == "lockfile ecosystem detected: python"
    assert result.findings == []
