"""Aggregate benchmark measurements without inventing missing values."""

from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean, median
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
        "mean_analyzer_completeness": (
            fmean(
                result.observation.analyzer_completeness_percent
                for result in collected
                if result.observation is not None
            )
            if any(result.observation is not None for result in collected)
            else None
        ),
        "median_runtime_seconds": (
            median(
                result.observation.duration_seconds
                for result in collected
                if result.observation is not None
            )
            if any(result.observation is not None for result in collected)
            else None
        ),
        "false_positive_reviews": {
            state: sum(
                result.observation is not None and result.observation.false_positive_review == state
                for result in collected
            )
            for state in ("not_reviewed", "reviewed_none", "reviewed_present")
        },
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
    reviews = cast(dict[str, int], aggregate["false_positive_reviews"])
    review_summary = f"False-positive review: {reviews['not_reviewed']} not reviewed, "
    review_summary += f"{sum(reviews.values()) - reviews['not_reviewed']} reviewed"
    lines = [
        "# AgentGuard Benchmark Report",
        "",
        f"AI-generated patches evaluated: {aggregate['patches_evaluated']}",
        f"Patches with AgentGuard repair results: {aggregate['patches_repaired']}",
        f"Mean analyzer completeness: {_display(cast(float | None, aggregate['mean_analyzer_completeness']))}%",
        f"Median runtime: {_display(cast(float | None, aggregate['median_runtime_seconds']))}s",
        review_summary,
        "",
        "| Metric | Baseline | AgentGuard |",
        "|---|---:|---:|",
    ]
    for label, field in METRICS:
        values = metrics[field]
        lines.append(
            f"| {label} | {_display(values['baseline'])} | {_display(values['agentguard'])} |"
        )
    if collected and all(result.task.synthetic for result in collected):
        lines.extend(("", "> All results in this report are synthetic sample data."))
    return "\n".join(lines) + "\n"
