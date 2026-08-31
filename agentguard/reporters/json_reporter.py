from __future__ import annotations

import json
from typing import Any, Literal

from agentguard.core.models import (
    AnalyzerStatus,
    QualityReport,
    QualityReportDocument,
    SkippedAnalyzer,
)

SCHEMA_VERSION: Literal["1.0"] = "1.0"


def report_data(report: QualityReport) -> dict[str, Any]:
    document = QualityReportDocument(
        **report.model_dump(),
        schema_version=SCHEMA_VERSION,
        verdict=report.outcome,
        exit_code=report.exit_code,
        findings=report.findings,
        analyzers_executed=[
            result.analyzer
            for result in report.analyzer_results
            if result.status is AnalyzerStatus.COMPLETED
        ],
        analyzers_skipped=[
            SkippedAnalyzer(analyzer=result.analyzer, status=result.status, reason=result.message)
            for result in report.analyzer_results
            if result.status is not AnalyzerStatus.COMPLETED
        ],
    )
    return document.model_dump(mode="json")


def render_json(report: QualityReport, *, indent: int | None = 2) -> str:
    return json.dumps(report_data(report), indent=indent, sort_keys=True)


class JsonReporter:
    def render(self, report: QualityReport) -> str:
        return render_json(report)
