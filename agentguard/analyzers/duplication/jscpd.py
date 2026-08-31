from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agentguard.analyzers._shared import completed, finding, invoke
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus


class JscpdAnalyzer:
    metadata = AnalyzerMetadata("jscpd", "duplication", frozenset())

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        with tempfile.TemporaryDirectory(prefix="agentguard-jscpd-") as directory:
            process = await invoke(
                "jscpd",
                [
                    "jscpd",
                    "--reporters",
                    "json",
                    "--output",
                    directory,
                    "--ignore",
                    "**/node_modules/**,**/.venv/**",
                    ".",
                ],
                context,
            )
            if isinstance(process, AnalyzerResult):
                return process
            report = Path(directory) / "jscpd-report.json"
            try:
                data = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
                duplicates = data.get("duplicates", [])
                findings = [
                    finding(
                        "jscpd",
                        "duplication",
                        f"Duplicate block ({item.get('lines', 0)} lines)",
                        file=item.get("firstFile", {}).get("name"),
                        line=item.get("firstFile", {}).get("start"),
                        rule="duplicate-block",
                        level="medium",
                        metadata={
                            "duplicate_file": item.get("secondFile", {}).get("name"),
                            "duplicate_line": item.get("secondFile", {}).get("start"),
                        },
                    )
                    for item in duplicates
                ]
            except (OSError, ValueError, TypeError) as exc:
                return AnalyzerResult(
                    analyzer="jscpd",
                    status=AnalyzerStatus.FAILED,
                    duration_seconds=process.duration_seconds,
                    message=f"invalid JSON report: {exc}",
                )
            return completed(
                "jscpd", process, findings, {"duplicate_blocks": float(len(duplicates))}
            )
