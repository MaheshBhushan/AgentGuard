from __future__ import annotations

import re
from typing import Any

from agentguard.analyzers._shared import completed, finding, invoke, json_data, targets
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus

PYTHON = {".py", ".pyi"}


class RuffAnalyzer:
    metadata = AnalyzerMetadata("ruff", "lint", frozenset({"python"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "ruff", ["ruff", "check", "--output-format", "json", *targets(context, PYTHON)], context
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            items = json_data(process.stdout) or []
            findings = [
                finding(
                    "ruff",
                    "lint",
                    item["message"],
                    file=item.get("filename"),
                    line=item.get("location", {}).get("row"),
                    column=item.get("location", {}).get("column"),
                    rule=item.get("code"),
                    level="medium",
                    remediation=(item.get("fix") or {}).get("message"),
                )
                for item in items
            ]
        except (ValueError, KeyError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="ruff",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("ruff", process, findings)


class MypyAnalyzer:
    metadata = AnalyzerMetadata("mypy", "typing", frozenset({"python"}))
    _line = re.compile(r"^(.*?):(\d+)(?::(\d+))?: (error|warning|note): (.*?)(?:  \[([^]]+)\])?$")

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "mypy",
            [
                "mypy",
                "--show-column-numbers",
                "--show-error-codes",
                "--no-error-summary",
                "--explicit-package-bases",
                *targets(context, PYTHON),
            ],
            context,
        )
        if isinstance(process, AnalyzerResult):
            return process
        findings = []
        for line in process.stdout.splitlines():
            match = self._line.match(line)
            if match:
                file, row, column, level, message, rule = match.groups()
                findings.append(
                    finding(
                        "mypy",
                        "typing",
                        message,
                        file=file,
                        line=int(row),
                        column=int(column) if column else None,
                        rule=rule,
                        level="low" if level == "note" else "medium",
                    )
                )
        return completed("mypy", process, findings)


class RadonAnalyzer:
    metadata = AnalyzerMetadata("radon", "complexity", frozenset({"python"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "radon", ["radon", "cc", "--json", *targets(context, PYTHON)], context
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data: dict[str, list[dict[str, Any]]] = json_data(process.stdout) or {}
            blocks = [block for values in data.values() for block in values]
            findings = [
                finding(
                    "radon",
                    "complexity",
                    f"{block.get('type', 'block')} {block['name']} has complexity {block['complexity']}",
                    file=file,
                    line=block.get("lineno"),
                    rule="cyclomatic-complexity",
                    level="medium",
                    remediation=f"Reduce complexity to at most {context.config.complexity.max_function_complexity}.",
                    metadata={"complexity": block["complexity"], "rank": block.get("rank")},
                )
                for file, values in data.items()
                for block in values
                if block.get("complexity", 0) > context.config.complexity.max_function_complexity
            ]
        except (ValueError, KeyError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="radon",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed(
            "radon",
            process,
            findings,
            {"complexity": float(sum(block.get("complexity", 0) for block in blocks))},
        )


class BanditAnalyzer:
    metadata = AnalyzerMetadata("bandit", "security", frozenset({"python"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "bandit", ["bandit", "-f", "json", "-q", *targets(context, PYTHON)], context
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data = json_data(process.stdout) or {}
            findings = [
                finding(
                    "bandit",
                    "security",
                    item["issue_text"],
                    file=item.get("filename"),
                    line=item.get("line_number"),
                    rule=item.get("test_id"),
                    level=item.get("issue_severity"),
                    metadata={"confidence": item.get("issue_confidence")},
                )
                for item in data.get("results", [])
            ]
        except (ValueError, KeyError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="bandit",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("bandit", process, findings)
