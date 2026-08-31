# Configuration

AgentGuard reads `.agentguard.yml` (or a configured TOML file). Run `agentguard init` to generate defaults based on detected languages. Unknown or invalid values should fail with a useful path-specific validation error.

```yaml
version: 1

quality:
  minimum_score: 80

complexity:
  max_function_complexity: 15
  max_complexity_increase: 10

tests:
  require_pass: true
  max_coverage_drop: 1.0
  # command: [python, -m, pytest]

security:
  fail_on: [critical, high]

dependencies:
  max_new_dependencies: 3
  forbidden: [lodash]

duplication:
  max_new_blocks: 2

architecture:
  max_file_lines: 500
  max_function_lines: 80
  forbidden_imports:
    - from: domain
      to: infrastructure

agent:
  provider: codex
  max_iterations: 5
  timeout_seconds: 900

exclude:
  - node_modules/**
  - .venv/**
  - dist/**
  - build/**
```

Commands should be represented as argument arrays when supported, which preserves cross-platform behavior and avoids shell interpretation. Repository configuration is untrusted input: it must not enable unbounded execution or interpolate shell syntax.

Policy limits are independent. `minimum_score` gates the aggregate score; tests, security severities, coverage drop, dependency growth, duplication, and architecture limits can each fail separately. Omitted optional sections use documented defaults rather than silently disabling required safety behavior.
