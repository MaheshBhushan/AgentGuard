import asyncio
import re
import subprocess
from pathlib import Path

from agentguard.benchmarks import (
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkTask,
    aggregate_results,
    read_results,
    render_markdown,
    write_json,
    write_jsonl,
)
from scripts.collect_release_benchmarks import collect

ROOT = Path(__file__).parents[1]


def result(*, repaired: bool = True) -> BenchmarkResult:
    baseline = BenchmarkMetrics(
        cyclomatic_complexity=20,
        lines_changed=10,
        dependencies_introduced=1,
        tests_failed=1,
        tests_passed=4,
        coverage_percent=None,
        duplicate_blocks=2,
        static_analysis_findings=3,
        security_findings=1,
    )
    fixed = baseline.model_copy(
        update={"cyclomatic_complexity": 12, "tests_failed": 0, "security_findings": 0}
    )
    return BenchmarkResult(
        task=BenchmarkTask(
            id="sample",
            repository="https://example.invalid/repo.git",
            initial_commit="abc123",
            task_description="Synthetic task",
            generated_patch="generated.patch",
            repaired_patch="repaired.patch" if repaired else None,
            synthetic=True,
        ),
        baseline=baseline,
        agentguard=fixed if repaired else None,
        agentguard_iterations=1 if repaired else 0,
    )


def test_json_and_jsonl_round_trip(tmp_path: Path) -> None:
    expected = [result()]
    for writer, suffix in ((write_json, ".json"), (write_jsonl, ".jsonl")):
        path = tmp_path / f"results{suffix}"
        writer(path, expected)
        assert read_results(path) == expected


def test_aggregate_does_not_invent_missing_repaired_metrics() -> None:
    aggregate = aggregate_results([result(repaired=False)])
    assert aggregate["patches_repaired"] == 0
    assert aggregate["metrics"]["tests_failed"]["agentguard"] is None


def test_markdown_labels_synthetic_data() -> None:
    markdown = render_markdown([result()])
    assert "AI-generated patches evaluated: 1" in markdown
    assert "| Test failures | 1 | 0 |" in markdown
    assert "synthetic sample data" in markdown


def _without_times(value: BenchmarkResult) -> dict[str, object]:
    data = value.model_dump(mode="json")
    observation = data.get("observation")
    if isinstance(observation, dict):
        observation.pop("duration_seconds")
        observation.pop("analyzer_durations_seconds")
    return data


def test_release_dataset_is_real_pinned_and_reproducible() -> None:
    commits = [
        line
        for line in (ROOT / "benchmarks" / "release-commits.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    expected = read_results(ROOT / "benchmarks" / "release-results.jsonl")
    assert len(commits) == len(expected) == 10
    assert all(not result.task.synthetic for result in expected)
    for commit, result in zip(commits, expected, strict=True):
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        assert result.task.generated_commit == commit
        assert result.observation is not None
        assert result.observation.false_positive_review == "not_reviewed"

    regenerated = asyncio.run(collect(ROOT, commits))
    assert [_without_times(result) for result in regenerated] == [
        _without_times(result) for result in expected
    ]
    checked_report = (ROOT / "benchmarks" / "release-report.md").read_text(encoding="utf-8")
    normalize_runtime = lambda text: re.sub(
        r"Median runtime: .*s", "Median runtime: <volatile>", text
    )
    assert normalize_runtime(render_markdown(regenerated)) == normalize_runtime(checked_report)
