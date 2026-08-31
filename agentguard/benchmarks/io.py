"""JSON and JSONL persistence for benchmark results."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from agentguard.benchmarks.models import BenchmarkResult


def read_results(path: Path) -> list[BenchmarkResult]:
    """Read benchmark results from JSON or JSONL."""
    if path.suffix == ".jsonl":
        return [
            BenchmarkResult.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else [payload]
    return [BenchmarkResult.model_validate(item) for item in items]


def write_json(path: Path, results: Iterable[BenchmarkResult]) -> None:
    """Write a deterministic, human-readable JSON result file."""
    payload = [result.model_dump(mode="json") for result in results]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, results: Iterable[BenchmarkResult]) -> None:
    """Write one compact benchmark result per line."""
    lines = (result.model_dump_json() for result in results)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
