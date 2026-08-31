# Architecture

AgentGuard separates repository discovery, tool execution, normalization, evaluation, and presentation. The core has no coding-agent provider dependency.

```mermaid
flowchart TD
  CLI[Typer CLI] --> CFG[Pydantic configuration]
  CLI --> GIT[Git change discovery]
  GIT --> CTX[Analysis context]
  CFG --> CTX
  CTX --> RUN[Concurrent analyzer runner]
  RUN --> PLUG[Analyzer plugins]
  PLUG --> RES[Normalized AnalyzerResult]
  RES --> MET[Metrics and scoring]
  MET --> POL[Independent policy results]
  POL --> REP[Terminal / JSON / GitHub reporters]
  REP --> ADP[Optional agent adapters]
```

The Git layer models working-tree, staged, revision, and branch comparisons, including line ranges, additions/deletions, renames, and deletions. Analyzers receive an immutable context and return normalized results rather than printing directly. The runner filters by changed language and executable availability, applies timeouts, and may run independent tools concurrently.

An analyzer plugin declares its name, category, supported languages, executable requirements, version/availability information, and an analysis operation. An unavailable optional analyzer returns a skipped/unavailable result with installation guidance. Extensions should not leak tool-specific structures into policies or reporters.

Findings retain category and severity plus file, line, column, rule identifier, remediation, and metadata. Metrics represent measured values and deltas. A quality report combines repository/change identity, analyzer results, findings, metrics, score breakdown, policies, verdict, and duration.

Before/after measurements may require temporary Git worktrees or reading both blob versions. Implementations must avoid modifying the user's index or working tree. Caches are valid only when their key includes analyzer/version, configuration, relevant file content, and comparison identity.
