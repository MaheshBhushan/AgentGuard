from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalyzerStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class Finding(BaseModel):
    analyzer: str
    category: str
    severity: Severity
    message: str
    file: Path | None = None
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    rule_id: str | None = None
    remediation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzerResult(BaseModel):
    analyzer: str
    status: AnalyzerStatus = AnalyzerStatus.COMPLETED
    findings: list[Finding] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    duration_seconds: float = Field(default=0, ge=0)
    message: str | None = None
    version: str | None = None


class Metric(BaseModel):
    name: str
    value: float
    before: float | None = None
    unit: str | None = None

    @property
    def delta(self) -> float | None:
        return None if self.before is None else self.value - self.before


class PolicyResult(BaseModel):
    name: str
    passed: bool
    message: str
    actual: float | str | bool | None = None
    expected: float | str | bool | None = None


class ChangedFile(BaseModel):
    path: Path
    old_path: Path | None = None
    status: str
    additions: int = 0
    deletions: int = 0
    changed_lines: set[int] = Field(default_factory=set)


class ChangeSummary(BaseModel):
    base: str | None = None
    head: str = "working-tree"
    files: list[ChangedFile] = Field(default_factory=list)

    @property
    def additions(self) -> int:
        return sum(item.additions for item in self.files)

    @property
    def deletions(self) -> int:
        return sum(item.deletions for item in self.files)


class ScoreComponent(BaseModel):
    name: str
    penalty: float = Field(ge=0)
    reason: str


class QualityReport(BaseModel):
    repository: Path
    change: ChangeSummary
    analyzer_results: list[AnalyzerResult] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    policies: list[PolicyResult] = Field(default_factory=list)
    quality_score: float = Field(default=100, ge=0, le=100)
    score_components: list[ScoreComponent] = Field(default_factory=list)
    duration_seconds: float = Field(default=0, ge=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def findings(self) -> list[Finding]:
        return [finding for result in self.analyzer_results for finding in result.findings]

    @property
    def passed(self) -> bool:
        return all(policy.passed for policy in self.policies)
