from __future__ import annotations

import shutil
from pathlib import Path

from agentguard.agents.base import AgentRunResult
from agentguard.core.runner import run_process


class CodexAdapter:
    name = "codex"

    def available(self) -> bool:
        return shutil.which("codex") is not None

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult:
        result = await run_process(["codex", "exec", "--full-auto", prompt], cwd=root, timeout=timeout)
        return AgentRunResult(result.returncode == 0, result.stdout, result.stderr, result.timed_out)

