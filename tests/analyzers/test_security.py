from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agentguard.analyzers.base import AnalysisContext
from agentguard.analyzers.python.tools import BanditAnalyzer
from agentguard.analyzers.security.tools import SemgrepAnalyzer
from agentguard.core.config import AgentGuardConfig
from agentguard.core.models import (
    AnalyzerStatus,
    ChangedFile,
    ChangeSummary,
    QualityReport,
    Severity,
)
from agentguard.core.policy_engine import evaluate_policies
from agentguard.core.runner import ProcessResult
from agentguard.reporters.sarif import sarif_data


def context(root: Path) -> AnalysisContext:
    return AnalysisContext(
        root,
        ChangeSummary(files=[ChangedFile(path=Path("src/example.py"), status="M")]),
        AgentGuardConfig(),
    )


@pytest.mark.parametrize(
    ("analyzer", "module", "item", "expected_severity"),
    [
        (
            BanditAnalyzer(),
            "agentguard.analyzers.python.tools",
            {
                "issue_text": "Unsafe deserialization",
                "filename": "src/example.py",
                "line_number": 4,
                "col_offset": 0,
                "test_id": "B301",
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
            },
            Severity.HIGH,
        ),
        *[
            (
                SemgrepAnalyzer(),
                "agentguard.analyzers.security.tools",
                {
                    "check_id": "python.security.eval",
                    "path": "src/example.py",
                    "start": {"line": 4, "col": 1},
                    "extra": {"message": "Unsafe eval", "severity": level},
                },
                severity,
            )
            for level, severity in [
                ("ERROR", Severity.HIGH),
                ("WARNING", Severity.MEDIUM),
                ("INFO", Severity.INFO),
                ("CRITICAL", Severity.CRITICAL),
            ]
        ],
    ],
)
def test_security_findings_reach_policy_and_sarif(
    tmp_path, monkeypatch, analyzer, module, item, expected_severity
) -> None:
    async def invoke(name, command, ctx):
        assert name == analyzer.metadata.name
        assert ctx.root == tmp_path
        assert "--json" in command or "json" in command
        return ProcessResult(tuple(command), 1, json.dumps({"results": [item]}), "", 0.1)

    monkeypatch.setattr(f"{module}.invoke", invoke)
    ctx = context(tmp_path)
    result = asyncio.run(analyzer.analyze(ctx))
    assert result.status is AnalyzerStatus.COMPLETED
    finding = result.findings[0]
    assert finding.severity is expected_severity
    assert finding.file == Path("src/example.py")
    assert (finding.line, finding.column) == (4, 1)
    if result.analyzer == "bandit":
        assert finding.metadata["confidence"] == "HIGH"
    policies = evaluate_policies(ctx.config, 100, {}, [result])
    security = next(policy for policy in policies if policy.name == "security")
    assert security.passed == (expected_severity not in {Severity.HIGH, Severity.CRITICAL})
    report = QualityReport(
        repository=tmp_path, change=ctx.change, analyzer_results=[result], policies=policies
    )
    run = sarif_data(report)["runs"][0]
    assert run["invocations"] == [{"executionSuccessful": True}]
    assert run["results"][0]["ruleId"] == f"{result.analyzer}/{finding.rule_id}"
    assert run["results"][0]["locations"][0]["physicalLocation"]["region"] == {
        "startLine": 4,
        "startColumn": 1,
    }
    assert run["tool"]["driver"]["rules"][0]["properties"]["tags"] == ["security"]


@pytest.mark.parametrize(
    ("analyzer", "module"),
    [
        (BanditAnalyzer(), "agentguard.analyzers.python.tools"),
        (SemgrepAnalyzer(), "agentguard.analyzers.security.tools"),
    ],
)
@pytest.mark.parametrize(
    ("stdout", "code", "expected"),
    [
        ('{"results": [], "errors": []}', 0, AnalyzerStatus.COMPLETED),
        ('{"results": [], "errors": []}', 2, AnalyzerStatus.FAILED),
        ('{"results": [], "errors": [{"message": "parse failed"}]}', 0, AnalyzerStatus.FAILED),
        ("not-json", 0, AnalyzerStatus.FAILED),
        ("", 0, AnalyzerStatus.FAILED),
        ("null", 0, AnalyzerStatus.FAILED),
        ("{}", 0, AnalyzerStatus.FAILED),
        ('{"results": [null]}', 0, AnalyzerStatus.FAILED),
        ('{"results": [], "errors": "invalid"}', 0, AnalyzerStatus.FAILED),
    ],
)
def test_security_scan_outcomes(tmp_path, monkeypatch, analyzer, module, stdout, code, expected):
    async def invoke(*args):
        return ProcessResult((analyzer.metadata.name,), code, stdout, "tool failed", 0.1)

    monkeypatch.setattr(f"{module}.invoke", invoke)
    result = asyncio.run(analyzer.analyze(context(tmp_path)))
    assert result.status is expected
    assert result.findings == []
    if expected is AnalyzerStatus.FAILED:
        assert result.message


@pytest.mark.parametrize("analyzer", [BanditAnalyzer(), SemgrepAnalyzer()])
def test_security_missing_tool_and_timeout(tmp_path, monkeypatch, analyzer):
    monkeypatch.setattr("agentguard.analyzers._shared.executable", lambda *args: None)
    result = asyncio.run(analyzer.analyze(context(tmp_path)))
    assert result.status is AnalyzerStatus.UNAVAILABLE
    assert f"pip install {analyzer.metadata.name}" in result.message

    monkeypatch.setattr("agentguard.analyzers._shared.executable", lambda *args: "scanner")

    async def timed_out(*args, **kwargs):
        return ProcessResult(("scanner",), -1, "", "", 0.1, timed_out=True)

    monkeypatch.setattr("agentguard.analyzers._shared.run_process", timed_out)
    result = asyncio.run(analyzer.analyze(context(tmp_path)))
    assert result.status is AnalyzerStatus.FAILED
    assert result.message == "analyzer timed out"


def test_bandit_skips_deleted_python_targets(tmp_path, monkeypatch):
    async def unexpected(*args):
        raise AssertionError("Bandit must not run without targets")

    monkeypatch.setattr("agentguard.analyzers.python.tools.invoke", unexpected)
    ctx = context(tmp_path)
    ctx.change.files[0].status = "D"
    assert asyncio.run(BanditAnalyzer().analyze(ctx)).status is AnalyzerStatus.SKIPPED
