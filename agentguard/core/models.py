from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"
    ERROR = "error"
    SKIPPED = "skipped"

    @property
    def exit_code(self) -> int:
        return {
            Outcome.PASS: 0,
            Outcome.SKIPPED: 0,
            Outcome.FAIL: 1,
            Outcome.ERROR: 2,
            Outcome.INCOMPLETE: 3,
        }[self]


class Finding(ReportModel):
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


class AnalyzerResult(ReportModel):
    analyzer: str
    status: AnalyzerStatus = AnalyzerStatus.COMPLETED
    required: bool = False
    findings: list[Finding] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    duration_seconds: float = Field(default=0, ge=0)
    message: str | None = None
    version: str | None = None


class Metric(ReportModel):
    name: str
    value: float
    before: float | None = None
    unit: str | None = None

    @property
    def delta(self) -> float | None:
        return None if self.before is None else self.value - self.before


class PolicyResult(ReportModel):
    name: str
    passed: bool
    message: str
    actual: float | str | bool | None = None
    expected: float | str | bool | None = None


class ChangedFile(ReportModel):
    path: Path
    old_path: Path | None = None
    status: str
    additions: int = 0
    deletions: int = 0
    changed_lines: set[int] = Field(default_factory=set)


class ChangeSummary(ReportModel):
    base: str | None = None
    head: str = "working-tree"
    files: list[ChangedFile] = Field(default_factory=list)

    @property
    def additions(self) -> int:
        return sum(item.additions for item in self.files)

    @property
    def deletions(self) -> int:
        return sum(item.deletions for item in self.files)


class ScoreComponent(ReportModel):
    name: str
    penalty: float = Field(ge=0)
    reason: str


class QualityReport(ReportModel):
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
        return self.outcome in {Outcome.PASS, Outcome.SKIPPED}

    @property
    def outcome(self) -> Outcome:
        if any(result.status is AnalyzerStatus.FAILED for result in self.analyzer_results):
            return Outcome.ERROR
        if any(
            result.required and result.status is AnalyzerStatus.UNAVAILABLE
            for result in self.analyzer_results
        ):
            return Outcome.INCOMPLETE
        if not self.change.files:
            return Outcome.SKIPPED
        if any(not policy.passed for policy in self.policies):
            return Outcome.FAIL
        return Outcome.PASS

    @property
    def exit_code(self) -> int:
        return self.outcome.exit_code


class SkippedAnalyzer(ReportModel):
    analyzer: str
    status: AnalyzerStatus
    reason: str | None = None


class QualityReportDocument(ReportModel):
    repository: Path
    change: ChangeSummary
    analyzer_results: list[AnalyzerResult] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    policies: list[PolicyResult] = Field(default_factory=list)
    quality_score: float = Field(default=100, ge=0, le=100)
    score_components: list[ScoreComponent] = Field(default_factory=list)
    duration_seconds: float = Field(default=0, ge=0)
    generated_at: datetime
    schema_version: Literal["1.0"] = "1.0"
    verdict: Outcome
    exit_code: int = Field(ge=0, le=3)
    findings: list[Finding] = Field(default_factory=list)
    analyzers_executed: list[str] = Field(default_factory=list)
    analyzers_skipped: list[SkippedAnalyzer] = Field(default_factory=list)
