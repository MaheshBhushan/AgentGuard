from __future__ import annotations

import shutil
from pathlib import Path

from agentguard.agents.base import AgentRunResult, agent_env, wrap_findings
from agentguard.core.runner import run_process


def codex_command(prompt: str) -> list[str]:
    # workspace-write confines writes to the repository, network stays off, and
    # shell commands get only the core environment variables.
    return [
        "codex", "exec",
        "--sandbox", "workspace-write",
        "-c", "sandbox_workspace_write.network_access=false",
        "-c", 'shell_environment_policy.inherit="core"',
        wrap_findings(prompt),
    ]


class CodexAdapter:
    name = "codex"

    def available(self) -> bool:
        return shutil.which("codex") is not None

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult:
        result = await run_process(codex_command(prompt), cwd=root, timeout=timeout, env=agent_env(), inherit_env=False)
        return AgentRunResult(result.returncode == 0, result.stdout, result.stderr, result.timed_out)

