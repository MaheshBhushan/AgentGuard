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
