# Benchmarking

The benchmark framework measures whether a repaired AI-generated patch improves against the original patch. A task identifies a repository, initial commit, task description, generated patch, and optional repaired patch. Runs store raw normalized metrics and environment/tool versions as JSON or JSONL.

Measured fields include complexity, changed lines, dependencies, test status, coverage, duplicated blocks, static-analysis and security findings, and repair iterations. Aggregation compares only compatible measurements; unavailable tools remain unavailable rather than being counted as zero.

```text
AI-generated patches evaluated: N

Metric                    Baseline     AgentGuard
Complexity growth         measured     measured
Static analysis issues    measured     measured
Duplicate code            measured     measured
Test regressions          measured     measured
New dependencies          measured     measured
```

Sample fixture data is synthetic and exists to test parsing and aggregation. It must be labeled `synthetic: true` and must never be presented as evidence of product effectiveness. Reproducible public results should pin repository revisions, tool versions, configuration, platform, agent/provider settings, and random seeds where relevant.
