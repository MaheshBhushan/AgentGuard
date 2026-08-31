from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from agentguard.analyzers._shared import (
    completed,
    finding,
    invoke,
    json_data,
    targets,
)
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus

JS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}


def package_manager(root: Path) -> str:
    package = (
        json.loads((root / "package.json").read_text(encoding="utf-8"))
        if (root / "package.json").is_file()
        else {}
    )
    declared = str(package.get("packageManager", "")).split("@", 1)[0]
    if declared in {"npm", "pnpm", "yarn", "bun"}:
        return declared
    for lock, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
    ):
        if (root / lock).exists():
            return manager
    return "npm"


def detect_test_runner(package: dict[str, Any]) -> str | None:
    dependencies = {
        **dict(package.get("dependencies", {})),
        **dict(package.get("devDependencies", {})),
    }
    script = str(dict(package.get("scripts", {})).get("test", ""))
    for runner in ("vitest", "jest"):
        if runner in dependencies or runner in script:
            return runner
    return None


class ESLintAnalyzer:
    metadata = AnalyzerMetadata("eslint", "lint", frozenset({"javascript", "typescript"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "eslint", ["eslint", "--format", "json", *targets(context, JS)], context
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data = json_data(process.stdout) or []
            findings = [
                finding(
                    "eslint",
                    "lint",
                    item["message"],
                    file=result.get("filePath"),
                    line=item.get("line"),
                    column=item.get("column"),
                    rule=item.get("ruleId"),
                    level=item.get("severity"),
                    remediation=item.get("suggestions", [{}])[0].get("desc")
                    if item.get("suggestions")
                    else None,
                )
                for result in data
                for item in result.get("messages", [])
            ]
        except (ValueError, KeyError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="eslint",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("eslint", process, findings, valid_codes={0, 1})


class OxcAnalyzer:
    metadata = AnalyzerMetadata("oxc", "lint", frozenset({"javascript", "typescript"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "oxc", ["oxlint", "--format", "json", *targets(context, JS)], context
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            raw = json_data(process.stdout) or {}
            items = raw if isinstance(raw, list) else raw.get("diagnostics", [])
            findings = [
                finding(
                    "oxc",
                    "lint",
                    item.get("message", "lint finding"),
                    file=item.get("filename") or item.get("file"),
                    line=item.get("labels", [{}])[0].get("span", {}).get("line")
                    or item.get("line"),
                    rule=item.get("code"),
                    level=item.get("severity"),
                )
                for item in items
            ]
        except (ValueError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="oxc",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("oxc", process, findings)


class TscAnalyzer:
    metadata = AnalyzerMetadata("tsc", "typing", frozenset({"typescript"}))
    _line = re.compile(r"^(.+?)\((\d+),(\d+)\): error (TS\d+): (.*)$")

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke("tsc", ["tsc", "--noEmit", "--pretty", "false"], context)
        if isinstance(process, AnalyzerResult):
            return process
        findings = [
            finding(
                "tsc",
                "typing",
                match.group(5),
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                rule=match.group(4),
                level="medium",
            )
            for line in process.stdout.splitlines()
            if (match := self._line.match(line))
        ]
        return completed("tsc", process, findings, valid_codes={0, 1, 2})


class JavaScriptTestsAnalyzer:
    metadata = AnalyzerMetadata("js-tests", "tests", frozenset({"javascript", "typescript"}))

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        package_file = context.root / "package.json"
        if not package_file.is_file():
            return AnalyzerResult(
                analyzer="js-tests", status=AnalyzerStatus.SKIPPED, message="package.json not found"
            )
        package = json.loads(package_file.read_text(encoding="utf-8"))
        if "test" not in package.get("scripts", {}):
            return AnalyzerResult(
                analyzer="js-tests",
                status=AnalyzerStatus.SKIPPED,
                message="package.json has no test script",
            )
        runner = detect_test_runner(package)
        with tempfile.TemporaryDirectory(prefix="agentguard-js-tests-") as directory:
            output = Path(directory) / "results.json"
            if runner == "vitest":
                command = [runner, "run", "--reporter=json", f"--outputFile={output}"]
            elif runner == "jest":
                command = [runner, "--json", f"--outputFile={output}"]
            else:
                manager = package_manager(context.root)
                command = [manager, "test"]
            process = await invoke("js-tests", command, context)
            if isinstance(process, AnalyzerResult):
                return process
            failed = process.returncode != 0
            metrics = {"tests_failed": float(failed)}
            report_error: str | None = None
            if output.is_file():
                try:
                    report = json.loads(output.read_text(encoding="utf-8"))
                    metrics = {
                        "tests_passed": float(report.get("numPassedTests", 0)),
                        "tests_failed": float(report.get("numFailedTests", 0)),
                        "tests_skipped": float(report.get("numPendingTests", 0)),
                    }
                except (OSError, ValueError, TypeError) as exc:
                    metrics["report_parse_failed"] = 1.0
                    report_error = str(exc)
            findings = (
                [
                    finding(
                        "js-tests",
                        "tests",
                        "JavaScript test command failed",
                        rule="test-failure",
                        level="high",
                        metadata={"stderr": process.stderr[-2000:]},
                    )
                ]
                if failed
                else []
            )
            if report_error:
                findings.append(
                    finding(
                        "js-tests",
                        "tests",
                        f"Could not parse JavaScript test report: {report_error}",
                        rule="invalid-test-report",
                        level="medium",
                    )
                )
            return completed("js-tests", process, findings, metrics, valid_codes={0, 1})


class DependencyCruiserAnalyzer:
    metadata = AnalyzerMetadata(
        "dependency-cruiser", "architecture", frozenset({"javascript", "typescript"})
    )

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "dependency-cruiser",
            ["depcruise", "--output-type", "json", *targets(context, JS)],
            context,
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data = json_data(process.stdout) or {}
            findings = [
                finding(
                    "dependency-cruiser",
                    "architecture",
                    violation.get("rule", {}).get("comment") or "dependency rule violated",
                    file=violation.get("from"),
                    rule=violation.get("rule", {}).get("name"),
                    level="medium",
                    metadata={"to": violation.get("to")},
                )
                for violation in data.get("summary", {}).get("violations", [])
            ]
        except (ValueError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="dependency-cruiser",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("dependency-cruiser", process, findings)
