from __future__ import annotations

import asyncio
from pathlib import Path

from agentguard.analyzers.profiles import (
    AnalyzerProfile,
    install_profile,
    registry_for_profile,
    resolve_profile,
)
from agentguard.core.models import AnalyzerStatus, ChangeSummary, QualityReport
from agentguard.core.runner import ProcessResult


def test_auto_profile_detects_only_python_tools(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
    profile = resolve_profile(tmp_path, "auto")
    assert profile.languages == {"python"}
    assert "ruff" in profile.analyzers
    assert "eslint" not in profile.analyzers
    assert all("==" in tool.command[-1] or "@" in tool.command[-1] for tool in profile.tools)


def test_auto_profile_detects_mixed_source_tree(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "app.ts").write_text("", encoding="utf-8")
    profile = resolve_profile(tmp_path, AnalyzerProfile.AUTO)
    assert profile.languages == {"python", "typescript"}
    assert {"ruff", "eslint", "dependency-delta", "architecture"} <= profile.analyzers


def test_minimal_profile_has_no_install_commands(tmp_path: Path) -> None:
    profile = resolve_profile(tmp_path, "minimal")
    assert profile.analyzers == {"dependency-delta", "architecture"}
    assert profile.tools == ()


def test_profile_cache_key_is_deterministic(tmp_path: Path) -> None:
    first = resolve_profile(tmp_path, "full")
    second = resolve_profile(tmp_path, "full")
    assert first.cache_key == second.cache_key
    assert first.cache_key.startswith("agentguard-tools-")
    assert first.versions["trivy"] == "0.63.0"


def test_profile_registry_contains_only_selected_analyzers(tmp_path: Path) -> None:
    profile = resolve_profile(tmp_path, "python")
    registry = registry_for_profile(profile)
    assert {analyzer.metadata.name for analyzer in registry.analyzers} == profile.analyzers


def test_install_failure_becomes_required_unavailable_result(tmp_path: Path) -> None:
    profile = resolve_profile(tmp_path, "python")

    async def failed_runner(
        command: tuple[str, ...], *, cwd: Path, timeout: float
    ) -> ProcessResult:
        del cwd, timeout
        return ProcessResult(command, 1, "", "index unavailable", 0.1)

    result = asyncio.run(install_profile(profile, cwd=tmp_path, runner=failed_runner))
    assert result.analyzer_results
    assert all(item.status is AnalyzerStatus.UNAVAILABLE for item in result.analyzer_results)
    assert all(item.required for item in result.analyzer_results)
    report = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(),
        analyzer_results=result.analyzer_results,
    )
    assert report.exit_code == 3


def test_successful_install_preserves_pinned_commands(tmp_path: Path) -> None:
    profile = resolve_profile(tmp_path, "typescript")
    commands: list[tuple[str, ...]] = []

    async def successful_runner(
        command: tuple[str, ...], *, cwd: Path, timeout: float
    ) -> ProcessResult:
        del cwd, timeout
        commands.append(command)
        return ProcessResult(command, 0, "", "", 0.1)

    result = asyncio.run(install_profile(profile, cwd=tmp_path, runner=successful_runner))
    assert commands == [tool.command for tool in profile.tools]
    assert result.analyzer_results == []
