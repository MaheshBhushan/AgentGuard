from __future__ import annotations

from agentguard.core.git_diff import finding_is_changed
from agentguard.core.models import Finding, QualityReport, Severity

_ORDER = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3, Severity.INFO: 4}


def actionable_findings(report: QualityReport, limit: int = 12) -> list[Finding]:
    changed = [
        finding
        for finding in report.findings
        if finding.file is not None
        and finding_is_changed(finding.file, finding.line, report.change)
        and finding.severity is not Severity.INFO
    ]
    return sorted(changed, key=lambda item: (_ORDER[item.severity], str(item.file), item.line or 0))[:limit]


def generate_feedback(report: QualityReport, limit: int = 12) -> str:
    findings = actionable_findings(report, limit)
    if not findings:
        return "No actionable regressions were introduced by this patch."
    lines = ["Fix only these regressions introduced by the current patch:"]
    for finding in findings:
        location = f"{finding.file}:{finding.line or 1}"
        action = finding.remediation or finding.message
        metric = f" ({finding.metadata['before']} → {finding.metadata['after']})" if {"before", "after"} <= finding.metadata.keys() else ""
        lines.append(f"- {location} [{finding.rule_id or finding.category}]{metric}: {action}")
    lines.append("Preserve observable behavior and do not rewrite unrelated code.")
    return "\n".join(lines)

