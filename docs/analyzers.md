# Analyzers

AgentGuard runs analyzers only when their language/category is relevant to the changed files. External tools are optional and detected without executing repository shell scripts during discovery.

| Analyzer | Area | Preferred output | Typical installation |
| --- | --- | --- | --- |
| Ruff | Python lint | JSON | `pip install ruff` |
| mypy | Python types | structured/text normalization | `pip install mypy` |
| Radon | Python complexity | JSON | `pip install radon` |
| pytest | Python tests | report/JUnit output | `pip install pytest` |
| coverage.py | Python coverage | JSON | `pip install coverage` |
| Bandit | Python security | JSON | `pip install bandit` |
| ESLint | JS/TS lint | JSON | project dev dependency |
| OXC | JS/TS lint | machine-readable output | project dev dependency |
| `tsc` | TypeScript types | compiler diagnostics | project dev dependency |
| Vitest/Jest | JS/TS tests | reporter output | project dev dependency |
| dependency-cruiser | JS/TS architecture | JSON | project dev dependency |
| Semgrep | multi-language security | JSON | `pip install semgrep` |
| Trivy | repository security | JSON | platform package/binary |
| jscpd | duplication | JSON | project/global npm package |

Package-manager detection reads `package.json` and recognized lock files for npm, pnpm, Yarn, or Bun. AgentGuard must not infer vulnerability claims from version strings: only a real security scanner may report vulnerabilities.

To add an analyzer, implement the analyzer protocol, declare metadata and executable requirements, register it through the plugin mechanism, normalize all outcomes, and test success, malformed output, non-zero exit, absence, and timeout. Preserve the tool's rule identifier and severity rather than collapsing every result into a warning.
