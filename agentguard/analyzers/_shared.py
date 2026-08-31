from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from agentguard.analyzers.base import AnalysisContext
from agentguard.core.models import AnalyzerResult, AnalyzerStatus, Finding, Severity
from agentguard.core.runner import ProcessResult, run_process

INSTALL: dict[str, str] = {
    "ruff": "pip install ruff",
    "mypy": "pip install mypy",
    "radon": "pip install radon",
    "pytest": "pip install pytest pytest-cov pytest-json-report",
    "bandit": "pip install bandit",
    "semgrep": "pip install semgrep",
    "trivy": "install Trivy from https://trivy.dev",
    "eslint": "add eslint to the project devDependencies",
    "oxlint": "add oxlint to the project devDependencies",
    "tsc": "add typescript to the project devDependencies",
    "jscpd": "add jscpd to the project devDependencies",
    "depcruise": "add dependency-cruiser to the project devDependencies",
}


def executable(root: Path, name: str) -> str | None:
    local = (
        root / "node_modules" / ".bin" / (f"{name}.cmd" if __import__("os").name == "nt" else name)
    )
    return str(local) if local.is_file() else shutil.which(name)


def unavailable(name: str, executable_name: str | None = None) -> AnalyzerResult:
    tool = executable_name or name
    return AnalyzerResult(
        analyzer=name,
        status=AnalyzerStatus.UNAVAILABLE,
        message=f"{tool} is unavailable; {INSTALL.get(tool, f'install {tool}')}",
    )


def targets(context: AnalysisContext, suffixes: set[str]) -> list[str]:
    return [
        str(item.path)
        for item in context.change.files
        if item.status not in {"D", "deleted"} and item.path.suffix.lower() in suffixes
    ]


async def invoke(
    name: str, command: list[str], context: AnalysisContext
) -> ProcessResult | AnalyzerResult:
    binary = executable(context.root, command[0])
    if binary is None:
        return unavailable(name, command[0])
    result = await run_process(
        [binary, *command[1:]], cwd=context.root, timeout=context.config.agent.timeout_seconds
    )
    if result.timed_out:
        return AnalyzerResult(
            analyzer=name,
            status=AnalyzerStatus.FAILED,
            duration_seconds=result.duration_seconds,
            message="analyzer timed out",
        )
    return result


def json_data(text: str) -> Any:
    return json.loads(text or "null")


def severity(value: str | int | None) -> Severity:
    if isinstance(value, int):
        return Severity.HIGH if value >= 2 else Severity.MEDIUM if value == 1 else Severity.LOW
    normalized = str(value or "medium").lower()
    return Severity(normalized) if normalized in Severity._value2member_map_ else Severity.MEDIUM


def finding(
    name: str,
    category: str,
    message: str,
    *,
    file: str | Path | None = None,
    line: int | None = None,
    column: int | None = None,
    rule: str | None = None,
    level: str | int | None = None,
    remediation: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    return Finding(
        analyzer=name,
        category=category,
        severity=severity(level),
        message=message,
        file=Path(file) if file else None,
        line=max(1, line) if line is not None else None,
        column=max(1, column) if column is not None else None,
        rule_id=rule,
        remediation=remediation,
        metadata=metadata or {},
    )


def completed(
    name: str,
    process: ProcessResult,
    findings: list[Finding],
    metrics: dict[str, float] | None = None,
    *,
    valid_codes: set[int] | None = None,
) -> AnalyzerResult:
    valid_codes = valid_codes or {0, 1}
    status = (
        AnalyzerStatus.COMPLETED if process.returncode in valid_codes else AnalyzerStatus.FAILED
    )
    return AnalyzerResult(
        analyzer=name,
        status=status,
        findings=findings if status == AnalyzerStatus.COMPLETED else [],
        metrics=(metrics or {}) if status == AnalyzerStatus.COMPLETED else {},
        duration_seconds=process.duration_seconds,
        message=None
        if status == AnalyzerStatus.COMPLETED
        else (process.stderr.strip() or f"exited with {process.returncode}"),
    )
