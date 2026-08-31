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

## Release evidence

`benchmarks/release-commits.txt` pins ten real agent-generated patches from AgentGuard's public history. Regenerate their observed records and aggregate report with:

```console
python scripts/collect_release_benchmarks.py
```

The collector creates detached temporary Git worktrees, runs the current `minimal` profile against each parent-to-commit diff, removes each worktree, and writes `benchmarks/release-results.jsonl` plus `benchmarks/release-report.md`. The records identify both commits, analyzer completion, total runtime, available per-analyzer timings, and false-positive review state. Unmeasured complexity, tests, coverage, duplication, and security values are `null`; they are never converted to zero. No repair results are claimed because these historical patches do not have recorded AgentGuard-guided repair runs.

Runtime fields are observations and vary across machines. Reproducibility checks normalize `duration_seconds`, `analyzer_durations_seconds`, and the Markdown median-runtime line; all other collected fields are expected to remain byte-equivalent for the pinned engine and commits.

## Performance budgets

Release review uses informational budgets rather than flaky wall-clock CI failures:

- core Git/diff/orchestration overhead should remain below 1 second for an ordinary patch;
- analyzer durations must be reported independently when the analyzer provides timing;
- irrelevant analyzers must not run;
- every subprocess remains bounded by its configured timeout.

A budget regression is investigated from repeated runs on the same machine before becoming a blocking threshold.
