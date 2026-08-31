"""Aggregate benchmark measurements without inventing missing values."""

from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean
from typing import cast

from agentguard.benchmarks.models import BenchmarkMetrics, BenchmarkResult

METRICS: tuple[tuple[str, str], ...] = (
    ("Cyclomatic complexity", "cyclomatic_complexity"),
    ("Lines changed", "lines_changed"),
    ("Static analysis findings", "static_analysis_findings"),
    ("Duplicate blocks", "duplicate_blocks"),
    ("Test failures", "tests_failed"),
    ("Tests passed", "tests_passed"),
    ("Coverage (%)", "coverage_percent"),
    ("New dependencies", "dependencies_introduced"),
    ("Security findings", "security_findings"),
)


def _mean(results: list[BenchmarkResult], side: str, field: str) -> float | None:
    values: list[float] = []
    for result in results:
        metrics: BenchmarkMetrics | None = getattr(result, side)
        if metrics is not None and (value := getattr(metrics, field)) is not None:
            values.append(float(value))
    return fmean(values) if values else None


def aggregate_results(results: Iterable[BenchmarkResult]) -> dict[str, object]:
    """Return means for each measured baseline and repaired-patch metric."""
    collected = list(results)
    return {
        "patches_evaluated": len(collected),
        "patches_repaired": sum(result.agentguard is not None for result in collected),
        "metrics": {
            field: {
                "baseline": _mean(collected, "baseline", field),
                "agentguard": _mean(collected, "agentguard", field),
            }
            for _, field in METRICS
        },
    }


def _display(value: float | None) -> str:
    if value is None:
        return "N/A"
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}"


def render_markdown(results: Iterable[BenchmarkResult]) -> str:
    """Render an aggregate comparison table suitable for documentation."""
    collected = list(results)
    aggregate = aggregate_results(collected)
    metrics = cast(dict[str, dict[str, float | None]], aggregate["metrics"])
    lines = [
        "# AgentGuard Benchmark Report",
        "",
        f"AI-generated patches evaluated: {aggregate['patches_evaluated']}",
        f"Patches with AgentGuard repair results: {aggregate['patches_repaired']}",
        "",
        "| Metric | Baseline | AgentGuard |",
        "|---|---:|---:|",
    ]
    for label, field in METRICS:
        values = metrics[field]
        lines.append(
            f"| {label} | {_display(values['baseline'])} | "
            f"{_display(values['agentguard'])} |"
        )
    if collected and all(result.task.synthetic for result in collected):
        lines.extend(("", "> All results in this report are synthetic sample data."))
    return "\n".join(lines) + "\n"
