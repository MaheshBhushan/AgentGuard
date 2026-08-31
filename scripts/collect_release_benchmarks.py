"""Measure pinned AgentGuard patches with the current deterministic engine."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import tempfile
from pathlib import Path

from agentguard.analyzers.profiles import registry_for_profile, resolve_profile
from agentguard.benchmarks import (
    BenchmarkMetrics,
    BenchmarkObservation,
    BenchmarkResult,
    BenchmarkTask,
    render_markdown,
    write_jsonl,
)
from agentguard.core.analyzer import analyze_repository
from agentguard.core.models import AnalyzerStatus

REPOSITORY = "https://github.com/MaheshBhushan/AgentGuard.git"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


async def measure(root: Path, commit: str) -> BenchmarkResult:
    parent = git(root, "rev-parse", f"{commit}^")
    subject = git(root, "show", "-s", "--format=%s", commit)
    with tempfile.TemporaryDirectory(prefix="agentguard-benchmark-") as temporary:
        checkout = Path(temporary) / "checkout"
        git(root, "worktree", "add", "--detach", str(checkout), commit)
        try:
            profile = resolve_profile(checkout, "minimal")
            report = await analyze_repository(
                checkout,
                base=parent,
                registry=registry_for_profile(profile),
            )
        finally:
            git(root, "worktree", "remove", str(checkout))
    considered = [
        result for result in report.analyzer_results if result.status is not AnalyzerStatus.SKIPPED
    ]
    completed = sum(result.status is AnalyzerStatus.COMPLETED for result in considered)
    completeness = 100 * completed / len(considered) if considered else 100
    metric_values = {metric.name: metric.value for metric in report.metrics}
    completed_analyzers = {
        result.analyzer
        for result in report.analyzer_results
        if result.status is AnalyzerStatus.COMPLETED
    }
    return BenchmarkResult(
        task=BenchmarkTask(
            id=f"agentguard-{commit[:12]}",
            repository=REPOSITORY,
            initial_commit=parent,
            generated_commit=commit,
            task_description=subject,
            generated_patch=commit,
            synthetic=False,
        ),
        baseline=BenchmarkMetrics(
            lines_changed=report.change.additions + report.change.deletions,
            dependencies_introduced=(
                int(metric_values.get("new_dependencies", 0))
                if "dependency-delta" in completed_analyzers
                else None
            ),
            static_analysis_findings=(
                sum(finding.category == "architecture" for finding in report.findings)
                if "architecture" in completed_analyzers
                else None
            ),
        ),
        observation=BenchmarkObservation(
            profile="minimal",
            verdict=report.outcome.value,
            analyzer_completeness_percent=completeness,
            analyzers_completed=sorted(completed_analyzers),
            analyzers_unavailable=[
                result.analyzer
                for result in report.analyzer_results
                if result.status is AnalyzerStatus.UNAVAILABLE
            ],
            duration_seconds=report.duration_seconds,
            analyzer_durations_seconds={
                result.analyzer: result.duration_seconds
                for result in report.analyzer_results
                if result.duration_seconds > 0
            },
            false_positive_review="not_reviewed",
        ),
    )


async def collect(root: Path, commits: list[str]) -> list[BenchmarkResult]:
    return [await measure(root, commit) for commit in commits]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--commits", type=Path, default=Path("benchmarks/release-commits.txt"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/release-results.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("benchmarks/release-report.md"))
    args = parser.parse_args()
    root = args.repository.resolve()
    commits = [line for line in args.commits.read_text(encoding="utf-8").splitlines() if line]
    results = asyncio.run(collect(root, commits))
    write_jsonl(args.output, results)
    args.report.write_text(render_markdown(results), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
