from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agentguard.analyzers._shared import completed, finding, invoke
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus


class PytestCoverageAnalyzer:
    metadata = AnalyzerMetadata("pytest", "tests", frozenset({"python"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        command = context.config.tests.command or ["pytest"]
        with tempfile.TemporaryDirectory(prefix="agentguard-pytest-") as directory:
            report = Path(directory) / "pytest.json"
            coverage = Path(directory) / "coverage.json"
            process = await invoke(
                "pytest",
                [
                    *command,
                    "--json-report",
                    f"--json-report-file={report}",
                    "--cov",
                    f"--cov-report=json:{coverage}",
                ],
                context,
            )
            if isinstance(process, AnalyzerResult):
                return process
            findings = []
            metrics: dict[str, float] = {}
            try:
                if report.is_file():
                    data = json.loads(report.read_text(encoding="utf-8"))
                    summary = data.get("summary", {})
                    metrics.update(
                        {
                            f"tests_{key}": float(summary.get(key, 0))
                            for key in ("passed", "failed", "skipped")
                        }
                    )
                    for test in data.get("tests", []):
                        if test.get("outcome") == "failed":
                            findings.append(
                                finding(
                                    "pytest",
                                    "tests",
                                    test.get("call", {}).get("longrepr", "test failed"),
                                    file=test.get("nodeid", "").split("::")[0],
                                    rule="test-failure",
                                    level="high",
                                )
                            )
                if coverage.is_file():
                    metrics["coverage_percent"] = float(
                        json.loads(coverage.read_text(encoding="utf-8"))["totals"][
                            "percent_covered"
                        ]
                    )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                return AnalyzerResult(
                    analyzer="pytest",
                    status=AnalyzerStatus.FAILED,
                    duration_seconds=process.duration_seconds,
                    message=f"invalid test report: {exc}",
                )
            return completed("pytest", process, findings, metrics, valid_codes={0, 1, 5})
