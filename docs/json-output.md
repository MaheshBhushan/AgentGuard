# JSON output

`agentguard check --format json` emits report schema `1.0`. The checked-in [JSON Schema](../schemas/report-v1.schema.json) is the machine-readable contract for integrations.

Within report major version `1`, fields are not removed or given incompatible meanings. Additive fields may appear in minor schema releases. Consumers should use `schema_version` to select a compatible parser.

`verdict` is one of `pass`, `fail`, `incomplete`, `error`, or `skipped`; `exit_code` contains the corresponding process result. Analyzer results, normalized findings, metrics, policies, score components, and the derived analyzer summaries remain available in the same document.

`generated_at` and `duration_seconds` are volatile. All other fields are deterministic for the same repository state, configuration, and analyzer results.
