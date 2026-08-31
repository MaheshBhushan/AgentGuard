# AgentGuard benchmarks

Benchmark records pair deterministic measurements of an agent-generated patch
with optional measurements after an AgentGuard-guided repair. Records contain
the repository, initial commit, task description, patches, and iteration count.

The fixture in `fixtures/synthetic-results.jsonl` is synthetic and exists only
to test the pipeline. It is not evidence of AgentGuard effectiveness.

```console
python scripts/aggregate_benchmarks.py benchmarks/fixtures/synthetic-results.jsonl
```

Both JSON arrays and one-result-per-line JSONL are supported.

The release dataset is non-synthetic evidence collected from the ten commits in
`release-commits.txt`. Rebuild it from the repository root with:

```console
python scripts/collect_release_benchmarks.py
```

The current dataset measures the built-in `minimal` profile. Missing categories
remain `null`, and the lack of recorded repair runs is represented by
`agentguard: null` rather than inferred improvement.
