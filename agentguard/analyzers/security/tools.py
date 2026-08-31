from __future__ import annotations

from agentguard.analyzers._shared import completed, finding, invoke, json_data
from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus


class SemgrepAnalyzer:
    metadata = AnalyzerMetadata("semgrep", "security", frozenset())

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "semgrep",
            ["semgrep", "scan", "--config", "auto", "--json", "--metrics=off", "."],
            context,
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data = json_data(process.stdout) or {}
            findings = [
                finding(
                    "semgrep",
                    "security",
                    item.get("extra", {}).get("message", "security finding"),
                    file=item.get("path"),
                    line=item.get("start", {}).get("line"),
                    column=item.get("start", {}).get("col"),
                    rule=item.get("check_id"),
                    level=item.get("extra", {}).get("severity"),
                    metadata={"lines": item.get("extra", {}).get("lines")},
                )
                for item in data.get("results", [])
            ]
        except (ValueError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="semgrep",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("semgrep", process, findings)


class TrivyAnalyzer:
    metadata = AnalyzerMetadata("trivy", "security", frozenset())

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        process = await invoke(
            "trivy",
            ["trivy", "fs", "--format", "json", "--scanners", "vuln,secret,misconfig", "."],
            context,
        )
        if isinstance(process, AnalyzerResult):
            return process
        try:
            data = json_data(process.stdout) or {}
            findings = []
            for result in data.get("Results", []):
                for item in result.get("Vulnerabilities", []):
                    findings.append(
                        finding(
                            "trivy",
                            "security",
                            item.get("Title")
                            or item.get("Description")
                            or item.get("VulnerabilityID", "vulnerability"),
                            file=result.get("Target"),
                            rule=item.get("VulnerabilityID"),
                            level=item.get("Severity"),
                            remediation=item.get("FixedVersion"),
                        )
                    )
                for key in ("Secrets", "Misconfigurations"):
                    for item in result.get(key, []):
                        findings.append(
                            finding(
                                "trivy",
                                "security",
                                item.get("Title") or item.get("RuleID", key[:-1]),
                                file=result.get("Target"),
                                line=item.get("StartLine"),
                                rule=item.get("RuleID") or item.get("ID"),
                                level=item.get("Severity"),
                            )
                        )
        except (ValueError, TypeError) as exc:
            return AnalyzerResult(
                analyzer="trivy",
                status=AnalyzerStatus.FAILED,
                duration_seconds=process.duration_seconds,
                message=f"invalid JSON output: {exc}",
            )
        return completed("trivy", process, findings)
