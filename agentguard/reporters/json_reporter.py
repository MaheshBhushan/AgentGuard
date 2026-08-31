from __future__ import annotations

import json
from typing import Any

from agentguard.core.models import AnalyzerStatus, QualityReport

SCHEMA_VERSION = "1.0"


def report_data(report: QualityReport) -> dict[str, Any]:
    data = report.model_dump(mode="json")
    data["schema_version"] = SCHEMA_VERSION
    data["verdict"] = "pass" if report.passed else "fail"
    data["findings"] = [finding.model_dump(mode="json") for finding in report.findings]
    data["analyzers_executed"] = [result.analyzer for result in report.analyzer_results if result.status is AnalyzerStatus.COMPLETED]
    data["analyzers_skipped"] = [
        {"analyzer": result.analyzer, "status": result.status, "reason": result.message}
        for result in report.analyzer_results
        if result.status is not AnalyzerStatus.COMPLETED
    ]
    return data


def render_json(report: QualityReport, *, indent: int | None = 2) -> str:
    return json.dumps(report_data(report), indent=indent, sort_keys=True)


class JsonReporter:
    def render(self, report: QualityReport) -> str:
        return render_json(report)

