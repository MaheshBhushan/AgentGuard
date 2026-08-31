# Contributing

Thanks for improving AgentGuard. Please discuss large behavior or schema changes in an issue before implementation.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pre-commit install
pytest
ruff check .
mypy agentguard
agentguard check --diff HEAD~1
```

Use Python 3.12+, `pathlib`, strict type annotations, machine-readable tool output, and subprocess argument lists without `shell=True`. New analyzer integrations need normalization tests, missing-tool behavior, timeout handling, and documentation.

Keep pull requests focused. Add or update tests for behavior changes and explain user-visible schema changes in `CHANGELOG.md`. Do not commit generated reports, virtual environments, coverage output, or dependency directories.

See [docs/contributing.md](docs/contributing.md) for analyzer and documentation guidance. By participating, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
