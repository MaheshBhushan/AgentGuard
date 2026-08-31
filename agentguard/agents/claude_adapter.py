from __future__ import annotations

import shutil
from pathlib import Path

from agentguard.agents.base import AgentRunResult
from agentguard.core.runner import run_process


class ClaudeAdapter:
    name = "claude"

    def available(self) -> bool:
        return shutil.which("claude") is not None

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult:
        result = await run_process(
            ["claude", "-p", "--permission-mode", "acceptEdits", prompt], cwd=root, timeout=timeout
        )
        return AgentRunResult(result.returncode == 0, result.stdout, result.stderr, result.timed_out)

