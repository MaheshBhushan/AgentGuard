# GitHub Actions

The repository contains a composite action for checking a pull request against its base revision.

```yaml
name: AgentGuard
on:
  pull_request:

permissions:
  contents: read
  security-events: write # Required only when annotations are enabled.

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: MaheshBhushan/AgentGuard@v1
```

The default `auto` profile detects Python and TypeScript projects, installs its pinned analyzers, and compares a pull request with the base SHA from the GitHub event. Full history is required to compute a trustworthy merge base; AgentGuard exits with checkout guidance when the history is insufficient rather than analyzing the wrong diff.

Every run appends a concise report to the GitHub step summary. The Action also exposes `verdict`, `quality-score`, `findings-count`, `policy-failures`, `analyzers-executed`, `analyzers-unavailable`, and `report-path`. Array outputs are compact JSON. By default, `fail`, `incomplete`, and `error` outcomes fail the step; customize this with `fail-on` only when intentionally observing results without gating.

Inputs override repository configuration, which overrides AgentGuard defaults. `minimum-score` and `timeout` are validated through the same strict configuration model. Analyzer commands use pinned profiles and argument arrays; input values are never interpolated into shell commands.

Set `upload-report: true` to retain the complete JSON report for seven days. Set `post-comment: true` and grant `pull-requests: write` to create one marker-owned bot comment that is updated on later runs. The default remains read-only. Fork pull requests and runs without write permission retain the step summary and analysis outputs without failing because a comment could not be posted.

Set `annotations: true` to upload file-specific findings as SARIF 2.1.0 through GitHub code
scanning. This requires `security-events: write`; keep the permission absent when annotations are
disabled. Locationless findings and findings with paths outside the repository remain visible in
JSON and the step summary but are intentionally omitted from SARIF. Fork pull requests may not be
allowed to upload SARIF with the event's restricted token, so annotations remain disabled by
default.

Until a versioned action is published, use `uses: ./` after checkout when testing from this repository.

## Release-candidate validation

The manual `consumer-smoke.yml` workflow exercises the current checkout as a composite Action on
Ubuntu without publishing it. Before promoting a release, create an immutable candidate tag and run
the same three-input smoke job from a separate disposable repository using
`uses: MaheshBhushan/AgentGuard@<candidate-tag>`. Verify pass, fail, incomplete, shallow-history,
read-only fork, JSON artifact, and optional SARIF paths against that exact tag before moving `v1`.

PR comments are optional. Grant `pull-requests: write` only when `post-comment` is enabled, and remember that write tokens are restricted for pull requests from forks. Step summaries and artifact uploads need no pull-request write permission.
