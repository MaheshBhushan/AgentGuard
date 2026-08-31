from __future__ import annotations

from collections import Counter

from agentguard.core.models import AnalyzerResult, ScoreComponent, Severity

PENALTIES = {Severity.INFO: 0, Severity.LOW: 1, Severity.MEDIUM: 3, Severity.HIGH: 8, Severity.CRITICAL: 15}


def calculate_score(results: list[AnalyzerResult], metrics: dict[str, float]) -> tuple[float, list[ScoreComponent]]:
    counts = Counter(finding.severity for result in results for finding in result.findings)
    components = [ScoreComponent(name=f"{severity.value}_findings", penalty=count * PENALTIES[severity], reason=f"{count} {severity.value} finding(s) × {PENALTIES[severity]}") for severity, count in counts.items() if PENALTIES[severity]]
    extras = {
        "tests_failed": (20, "failing tests"),
        "coverage_drop": (2, "coverage percentage points lost"),
        "complexity_increase": (0.5, "complexity points added"),
        "duplicate_blocks": (3, "new duplicate blocks"),
        "new_dependencies": (2, "new dependencies"),
        "architecture_violations": (8, "architecture violations"),
    }
    for key, (weight, label) in extras.items():
        value = max(0, metrics.get(key, 0))
        if value:
            components.append(ScoreComponent(name=key, penalty=value * weight, reason=f"{value:g} {label} × {weight:g}"))
    return max(0.0, 100 - sum(item.penalty for item in components)), components

