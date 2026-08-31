from __future__ import annotations

import json
from pathlib import Path

from agentguard.core.models import AnalyzerResult, ChangeSummary, Finding, QualityReport, Severity
from agentguard.reporters.sarif import render_sarif, sarif_data


def test_sarif_maps_python_and_typescript_findings(tmp_path: Path) -> None:
    report = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(),
        analyzer_results=[
            AnalyzerResult(
                analyzer="tools",
                findings=[
                    Finding(
                        analyzer="ruff",
                        category="lint",
                        severity=Severity.MEDIUM,
                        message="Unused import",
                        file=Path("src/app.py"),
                        line=3,
                        column=1,
                        rule_id="F401",
                        remediation="Remove the import.",
                    ),
                    Finding(
                        analyzer="eslint",
                        category="lint",
                        severity=Severity.HIGH,
                        message="Unexpected any",
                        file=Path("web/app.ts"),
                        line=8,
                        rule_id="no-explicit-any",
                    ),
                ],
            )
        ],
    )

    data = sarif_data(report)
    run = data["runs"][0]
    assert data["version"] == "2.1.0"
    assert {rule["id"] for rule in run["tool"]["driver"]["rules"]} == {
        "ruff/F401",
        "eslint/no-explicit-any",
    }
    assert [result["level"] for result in run["results"]] == ["warning", "error"]
    python = run["results"][0]
    assert python["locations"][0]["physicalLocation"] == {
        "artifactLocation": {"uri": "src/app.py", "uriBaseId": "%SRCROOT%"},
        "region": {"startLine": 3, "startColumn": 1},
    }
    assert "Remediation: Remove the import." in python["message"]["text"]
    assert json.loads(render_sarif(report)) == data


def test_sarif_omits_locationless_and_unsafe_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "secret.py"
    report = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(),
        analyzer_results=[
            AnalyzerResult(
                analyzer="security",
                findings=[
                    Finding(
                        analyzer="semgrep",
                        category="security",
                        severity=Severity.CRITICAL,
                        message="Repository finding",
                    ),
                    Finding(
                        analyzer="semgrep",
                        category="security",
                        severity=Severity.HIGH,
                        message="Traversal",
                        file=Path("../secret.py"),
                        line=1,
                    ),
                    Finding(
                        analyzer="bandit",
                        category="security",
                        severity=Severity.HIGH,
                        message="Outside",
                        file=outside,
                        line=1,
                    ),
                ],
            )
        ],
    )

    assert len(report.findings) == 3
    assert sarif_data(report)["runs"][0]["results"] == []


def test_sarif_omits_invalid_constructed_line(tmp_path: Path) -> None:
    invalid = Finding.model_construct(
        analyzer="tool",
        category="lint",
        severity=Severity.LOW,
        message="Invalid location",
        file=Path("app.py"),
        line=0,
        column=0,
        rule_id=None,
        remediation=None,
        metadata={},
    )
    report = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(),
        analyzer_results=[AnalyzerResult(analyzer="tool", findings=[invalid])],
    )
    assert sarif_data(report)["runs"][0]["results"] == []
