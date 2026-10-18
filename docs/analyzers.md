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

## Analyzer profiles

GitHub integrations can resolve deterministic analyzer bundles through
`agentguard.analyzers.profiles`:

- `auto` selects Python and JS/TS tools from repository manifests or source files and adds Semgrep
  when either language family is detected. Python tools include Bandit.
- `minimal` runs only built-in dependency and architecture checks.
- `python`, `typescript`, and `security` select their named tool families.
- `full` selects every registered family, including duplication checks.

Every managed external tool has an exact package version and an argument-vector install plan.
The profile exposes a deterministic cache key derived from those pins. Installation does not use a
shell, and a failed required-tool installation is represented as `UNAVAILABLE`, making the report
outcome `INCOMPLETE` rather than clean. Trivy remains an explicitly required external binary in the
security and full profiles because its installation is platform-specific.

To add an analyzer, implement the analyzer protocol, declare metadata and executable requirements, register it through the plugin mechanism, normalize all outcomes, and test success, malformed output, non-zero exit, absence, and timeout. Preserve the tool's rule identifier and severity rather than collapsing every result into a warning.

## Security findings and SARIF

Bandit scans changed Python files and retains rule IDs, severity, confidence, and source locations.
Deleted Python files are excluded. Semgrep scans the repository with `--config auto --metrics=off`.
The auto configuration fetches rules from the Semgrep Registry and requires network access.
Semgrep `ERROR`, `WARNING`, and `INFO` findings map to high, medium, and info severity.
Both analyzers accept findings exit code 1, report missing tools as unavailable, and report
timeouts, invalid JSON, scan errors, and other exit codes as failed analysis.

Run `agentguard check --format sarif > report.sarif` to export normalized findings as SARIF 2.1.0.
`agentguard compare main --format sarif` supports the same export. The command retains its usual
policy exit code even when it emits a report. Rule IDs include the analyzer name to avoid collisions.
Security rules carry GitHub's `security` tag and a severity score mapped from AgentGuard's severity:
critical 9.0, high 8.0, medium 5.0, low 2.0, and info 0.0. These scores represent severity categories.
They are not measured CVSS scores. Paths are repository-relative, URI-encoded locations.
SARIF marks execution as unsuccessful when analysis failed or a required analyzer was unavailable.
See [GitHub Actions](github-actions.md) for upload permissions and PR annotations.
