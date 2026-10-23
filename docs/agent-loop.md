# Agent feedback and repair loop

`agentguard feedback` turns regressions into short, file-specific instructions. It prioritizes changed-line findings and reports the measured before/after value, the responsible file or symbol, the applicable threshold, and the smallest required outcome. It does not request unrelated rewrites.

`agentguard fix` is provider-neutral at its core:

1. Analyze the selected Git change.
2. Generate structured remediation instructions.
3. Invoke the configured Codex CLI or Claude Code CLI adapter.
4. Let that agent edit the repository.
5. Analyze again and stop on passing policies.

The loop always has a maximum iteration count and per-command timeout. It stops on command failure, repeated identical findings, an unchanged diff/report fingerprint, or exhausted iterations. It never commits, pushes, changes branches, or discards user changes.

Finding text comes from the repository under analysis, so the loop treats it as untrusted. The prompt wraps findings in a `<findings>` block labelled as data, never as instructions. Claude Code runs with `acceptEdits`, only the file tools (`Read`, `Grep`, `Glob`, `Edit`, `MultiEdit`, `Write`), no Bash, web, or MCP tools, and `--permission-prompts none`. Codex runs with `--sandbox workspace-write`, network access off, and the core shell environment. Both children receive only a short allowlist of environment variables (`agentguard/agents/base.py`), so CI tokens never reach the agent.

```yaml
agent:
  provider: codex  # or claude
  max_iterations: 5
  timeout_seconds: 900
```

Provider executables and authentication remain user-managed. Run `agentguard doctor` before enabling the loop. Review the working tree after any automated repair; deterministic gates reduce risk but do not prove semantic correctness.
