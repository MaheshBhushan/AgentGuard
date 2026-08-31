from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agentguard.agents.base import AgentRunResult
from agentguard.agents.loop import StopReason, fix_loop
from agentguard.core.config import AgentGuardConfig
from agentguard.core.feedback import actionable_findings, generate_feedback
from agentguard.core.models import (
    AnalyzerResult,
    ChangedFile,
    ChangeSummary,
    Finding,
    PolicyResult,
    QualityReport,
    Severity,
)
from agentguard.reporters.json_reporter import render_json


def report(*findings: Finding, passed: bool = False, score: float = 70) -> QualityReport:
    return QualityReport(
        repository=Path("/repo"),
        change=ChangeSummary(files=[ChangedFile(path=Path("src/app.py"), status="modified", changed_lines={3, 8})]),
        analyzer_results=[AnalyzerResult(analyzer="test", findings=list(findings))],
        policies=[PolicyResult(name="gate", passed=passed, message="gate")],
        quality_score=score,
    )


def test_json_has_stable_agent_fields() -> None:
    data = json.loads(render_json(report(passed=True, score=100)))
    assert data["schema_version"] == "1.0"
    assert data["verdict"] == "pass"
    assert data["analyzers_executed"] == ["test"]
    assert data["findings"] == []


def test_feedback_is_changed_line_only_and_prioritized() -> None:
    low = Finding(analyzer="x", category="lint", severity=Severity.LOW, message="low", file=Path("src/app.py"), line=3)
    high = Finding(analyzer="x", category="complexity", severity=Severity.HIGH, message="high", remediation="split function", file=Path("src/app.py"), line=8, metadata={"before": 8, "after": 24})
    unrelated = Finding(analyzer="x", category="lint", severity=Severity.CRITICAL, message="old", file=Path("src/app.py"), line=99)
    current = report(low, high, unrelated)
    assert actionable_findings(current) == [high, low]
    feedback = generate_feedback(current)
    assert "8 → 24" in feedback
    assert "split function" in feedback
    assert "old" not in feedback


class FakeAdapter:
    name = "fake"

    def __init__(self, *, available: bool = True, success: bool = True) -> None:
        self.is_available = available
        self.success = success

    def available(self) -> bool:
        return self.is_available

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult:
        return AgentRunResult(self.success, "", "failed" if not self.success else "")


def test_fix_loop_stops_for_missing_adapter() -> None:
    current = report()

    async def analyze() -> QualityReport:
        return current

    result = asyncio.run(fix_loop(Path("/repo"), config=AgentGuardConfig(), adapter=FakeAdapter(available=False), analyze=analyze))
    assert result.reason is StopReason.AGENT_UNAVAILABLE
    assert result.iterations == 0


def test_fix_loop_stops_on_repeated_findings() -> None:
    finding = Finding(analyzer="x", category="lint", severity=Severity.HIGH, message="same", file=Path("src/app.py"), line=3)
    current = report(finding)

    async def analyze() -> QualityReport:
        return current

    result = asyncio.run(fix_loop(Path("/repo"), config=AgentGuardConfig(), adapter=FakeAdapter(), analyze=analyze))
    assert result.reason is StopReason.REPEATED_FINDINGS
    assert result.iterations == 1


def test_fix_loop_stops_on_agent_failure() -> None:
    current = report()

    async def analyze() -> QualityReport:
        return current

    result = asyncio.run(fix_loop(Path("/repo"), config=AgentGuardConfig(), adapter=FakeAdapter(success=False), analyze=analyze))
    assert result.reason is StopReason.AGENT_FAILED
