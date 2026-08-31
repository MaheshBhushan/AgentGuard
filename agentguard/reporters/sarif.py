from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from agentguard.core.models import Finding, QualityReport, Severity

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def _repository_path(repository: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(repository.resolve())
        except ValueError:
            return None
    normalized = PurePosixPath(str(path).replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        return None
    if not normalized.parts or normalized.parts[0].endswith(":"):
        return None
    return normalized.as_posix()


def _rule_id(finding: Finding) -> str:
    return f"{finding.analyzer}/{finding.rule_id or finding.category}"


def _level(severity: Severity) -> str:
    if severity in {Severity.CRITICAL, Severity.HIGH}:
        return "error"
    if severity is Severity.MEDIUM:
        return "warning"
    return "note"


def sarif_data(report: QualityReport) -> dict[str, Any]:
    located = [
        (finding, path, finding.line)
        for finding in report.findings
        if finding.line is not None
        and finding.line > 0
        and (path := _repository_path(report.repository, finding.file)) is not None
    ]
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding, path, line in located:
        rule_id = _rule_id(finding)
        rules.setdefault(
            rule_id,
            {
                "id": rule_id,
                "name": finding.rule_id or finding.category,
                "shortDescription": {"text": finding.message},
                "properties": {
                    "analyzer": finding.analyzer,
                    "category": finding.category,
                },
            },
        )
        message = finding.message
        if finding.remediation:
            message = f"{message}\n\nRemediation: {finding.remediation}"
        region: dict[str, int] = {"startLine": line}
        if finding.column is not None and finding.column > 0:
            region["startColumn"] = finding.column
        results.append(
            {
                "ruleId": rule_id,
                "level": _level(finding.severity),
                "message": {"text": message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": path, "uriBaseId": "%SRCROOT%"},
                            "region": region,
                        }
                    }
                ],
                "properties": {
                    "analyzer": finding.analyzer,
                    "category": finding.category,
                    "severity": finding.severity.value,
                },
            }
        )
    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AgentGuard",
                        "informationUri": "https://github.com/MaheshBhushan/AgentGuard",
                        "rules": list(rules.values()),
                    }
                },
                "originalUriBaseIds": {
                    "%SRCROOT%": {"uri": report.repository.resolve().as_uri() + "/"}
                },
                "results": results,
            }
        ],
    }


def render_sarif(report: QualityReport, *, indent: int | None = 2) -> str:
    return json.dumps(sarif_data(report), indent=indent, sort_keys=True)


class SarifReporter:
    def render(self, report: QualityReport) -> str:
        return render_sarif(report)
