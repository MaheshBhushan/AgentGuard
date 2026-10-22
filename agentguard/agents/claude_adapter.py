from __future__ import annotations

import shutil
from pathlib import Path

from agentguard.agents.base import AgentRunResult, agent_env, wrap_findings
from agentguard.core.runner import run_process

# File tools only: no Bash, no web, no MCP servers. Edits are auto-accepted inside
# the repository; anything that would prompt is denied.
CLAUDE_TOOLS = "Read,Grep,Glob,Edit,MultiEdit,Write"
CLAUDE_DENIED = "Bash,WebFetch,WebSearch,Task,Agent,NotebookEdit"


def claude_command(prompt: str) -> list[str]:
    return [
        "claude", "-p", wrap_findings(prompt),
        "--permission-mode", "acceptEdits",
        "--permission-prompts", "none",
        "--strict-mcp-config",
        "--tools", CLAUDE_TOOLS,
        "--disallowedTools", CLAUDE_DENIED,
    ]


class ClaudeAdapter:
    name = "claude"

    def available(self) -> bool:
        return shutil.which("claude") is not None

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult:
        result = await run_process(claude_command(prompt), cwd=root, timeout=timeout, env=agent_env(), inherit_env=False)
        return AgentRunResult(result.returncode == 0, result.stdout, result.stderr, result.timed_out)

