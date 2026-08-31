"""Stable models for reproducible AgentGuard benchmarks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkTask(BaseModel):
    """Inputs needed to reproduce evaluation of an agent-generated patch."""

    model_config = ConfigDict(extra="forbid")

    id: str
    repository: str
    initial_commit: str
    generated_commit: str | None = None
    task_description: str
    generated_patch: str
    repaired_patch: str | None = None
    synthetic: bool = False


class BenchmarkMetrics(BaseModel):
    """Deterministic measurements collected for one patch."""

    model_config = ConfigDict(extra="forbid")

    cyclomatic_complexity: float | None = Field(default=None, ge=0)
    lines_changed: int = Field(ge=0)
    dependencies_introduced: int | None = Field(default=None, ge=0)
    tests_failed: int | None = Field(default=None, ge=0)
    tests_passed: int | None = Field(default=None, ge=0)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    duplicate_blocks: int | None = Field(default=None, ge=0)
    static_analysis_findings: int | None = Field(default=None, ge=0)
    security_findings: int | None = Field(default=None, ge=0)


class BenchmarkObservation(BaseModel):
    """Execution evidence accompanying deterministic patch metrics."""

    model_config = ConfigDict(extra="forbid")

    profile: str
    verdict: str
    analyzer_completeness_percent: float = Field(ge=0, le=100)
    analyzers_completed: list[str] = Field(default_factory=list)
    analyzers_unavailable: list[str] = Field(default_factory=list)
    duration_seconds: float = Field(ge=0)
    analyzer_durations_seconds: dict[str, float] = Field(default_factory=dict)
    false_positive_review: Literal["not_reviewed", "reviewed_none", "reviewed_present"] = (
        "not_reviewed"
    )


class BenchmarkResult(BaseModel):
    """Before/after measurements for a benchmark task."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    task: BenchmarkTask
    baseline: BenchmarkMetrics
    observation: BenchmarkObservation | None = None
    agentguard: BenchmarkMetrics | None = None
    agentguard_iterations: int = Field(default=0, ge=0)
