"""Stable models for reproducible AgentGuard benchmarks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkTask(BaseModel):
    """Inputs needed to reproduce evaluation of an agent-generated patch."""

    model_config = ConfigDict(extra="forbid")

    id: str
    repository: str
    initial_commit: str
    task_description: str
    generated_patch: str
    repaired_patch: str | None = None
    synthetic: bool = False


class BenchmarkMetrics(BaseModel):
    """Deterministic measurements collected for one patch."""

    model_config = ConfigDict(extra="forbid")

    cyclomatic_complexity: float = Field(ge=0)
    lines_changed: int = Field(ge=0)
    dependencies_introduced: int = Field(ge=0)
    tests_failed: int = Field(ge=0)
    tests_passed: int = Field(ge=0)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    duplicate_blocks: int = Field(ge=0)
    static_analysis_findings: int = Field(ge=0)
    security_findings: int = Field(ge=0)


class BenchmarkResult(BaseModel):
    """Before/after measurements for a benchmark task."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    task: BenchmarkTask
    baseline: BenchmarkMetrics
    agentguard: BenchmarkMetrics | None = None
    agentguard_iterations: int = Field(default=0, ge=0)
