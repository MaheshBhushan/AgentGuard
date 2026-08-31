# GitHub Actions

The repository contains a composite action for checking a pull request against its base revision.

```yaml
name: AgentGuard
on:
  pull_request:

permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: owner/agentguard@v1
```

The default `auto` profile detects Python and TypeScript projects, installs its pinned analyzers, and compares a pull request with the base SHA from the GitHub event. Full history is required to compute a trustworthy merge base; AgentGuard exits with checkout guidance when the history is insufficient rather than analyzing the wrong diff.

The Action exposes `verdict`, `quality-score`, `findings-count`, `policy-failures`, `analyzers-executed`, `analyzers-unavailable`, and `report-path`. Array outputs are compact JSON. By default, `fail`, `incomplete`, and `error` outcomes fail the step; customize this with `fail-on` only when intentionally observing results without gating.

Inputs override repository configuration, which overrides AgentGuard defaults. `minimum-score` and `timeout` are validated through the same strict configuration model. Analyzer commands use pinned profiles and argument arrays; input values are never interpolated into shell commands.

Until a versioned action is published, use `uses: ./` after checkout when testing from this repository. PR comments, annotations, and report artifact upload are reserved inputs for the next GitHub-reporting release and currently default off.

PR comments are optional. Grant `pull-requests: write` only to a separate step that posts the generated Markdown report, and remember that secrets/write tokens are restricted for pull requests from forks. Printing the report or uploading it as an artifact needs no pull-request write permission.
