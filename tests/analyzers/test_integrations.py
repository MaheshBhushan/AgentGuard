from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agentguard.analyzers._shared import completed, invoke
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata, AnalyzerRegistry
from agentguard.analyzers.python.tools import RuffAnalyzer
from agentguard.analyzers.typescript import detect_test_runner, package_manager
from agentguard.core.config import AgentGuardConfig
from agentguard.core.models import AnalyzerStatus, ChangedFile, ChangeSummary
from agentguard.core.runner import ProcessResult


def context(root: Path) -> AnalysisContext:
    change = ChangeSummary(
        files=[ChangedFile(path=Path("src/example.py"), status="M", changed_lines={1})]
    )
    return AnalysisContext(root=root, change=change, config=AgentGuardConfig())


def test_missing_executable_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("agentguard.analyzers._shared.executable", lambda _root, _name: None)
    result = asyncio.run(invoke("ruff", ["ruff", "check"], context(tmp_path)))
    assert result.status == AnalyzerStatus.UNAVAILABLE
    assert "pip install ruff" in (result.message or "")


def test_ruff_json_is_normalized(tmp_path: Path, monkeypatch) -> None:
    payload = [
        {
            "code": "F401",
            "message": "unused import",
            "filename": "src/example.py",
            "location": {"row": 2, "column": 1},
            "fix": None,
        }
    ]

    async def fake_invoke(*_args, **_kwargs):
        return ProcessResult(("ruff",), 1, json.dumps(payload), "", 0.1)

    monkeypatch.setattr("agentguard.analyzers.python.tools.invoke", fake_invoke)
    result = asyncio.run(RuffAnalyzer().analyze(context(tmp_path)))
    assert result.status == AnalyzerStatus.COMPLETED
    assert result.findings[0].rule_id == "F401"
    assert result.findings[0].line == 2


def test_ruff_malformed_json_is_analyzer_failure(tmp_path: Path, monkeypatch) -> None:
    async def fake_invoke(*_args, **_kwargs):
        return ProcessResult(("ruff",), 1, "not-json", "", 0.1)

    monkeypatch.setattr("agentguard.analyzers.python.tools.invoke", fake_invoke)
    result = asyncio.run(RuffAnalyzer().analyze(context(tmp_path)))
    assert result.status == AnalyzerStatus.FAILED
    assert result.findings == []
    assert (result.message or "").startswith("invalid JSON output:")


def test_invalid_nonzero_exit_discards_parsed_findings() -> None:
    process = ProcessResult(("tool",), 2, "", "configuration failed", 0.1)
    result = completed("tool", process, [], {"issues": 1.0}, valid_codes={0, 1})
    assert result.status == AnalyzerStatus.FAILED
    assert result.findings == []
    assert result.metrics == {}
    assert result.message == "configuration failed"


def test_analyzer_crash_is_normalized(tmp_path: Path) -> None:
    class CrashingAnalyzer:
        metadata = AnalyzerMetadata("crash", "lint", frozenset())

        async def analyze(self, _context: AnalysisContext):
            raise ValueError("bad output")

    registry = AnalyzerRegistry()
    registry.register(CrashingAnalyzer())
    results = asyncio.run(registry.run(context(tmp_path), {"python"}))
    assert results[0].status == AnalyzerStatus.FAILED
    assert results[0].findings == []
    assert results[0].message == "analyzer crashed: ValueError: bad output"


def test_package_manager_prefers_declared_value(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"packageManager":"pnpm@10.0.0"}', encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    assert package_manager(tmp_path) == "pnpm"


def test_package_manager_detects_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bun.lock").touch()
    assert package_manager(tmp_path) == "bun"


def test_javascript_test_runner_detection() -> None:
    assert detect_test_runner({"devDependencies": {"vitest": "1"}}) == "vitest"
    assert detect_test_runner({"scripts": {"test": "jest --runInBand"}}) == "jest"
