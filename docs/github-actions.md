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
        with:
          base-ref: ${{ github.event.pull_request.base.sha }}
```

Until a versioned action is published, use `uses: ./` after checkout when testing from this repository. The action installs the checked-out AgentGuard source and runs `agentguard compare` with JSON output. A policy failure produces a non-zero job result.

PR comments are optional. Grant `pull-requests: write` only to a separate step that posts the generated Markdown report, and remember that secrets/write tokens are restricted for pull requests from forks. Printing the report or uploading it as an artifact needs no pull-request write permission.
