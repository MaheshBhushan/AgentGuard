from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AgentRunResult:
    success: bool
    output: str
    error: str = ""
    timed_out: bool = False


class AgentAdapter(Protocol):
    name: str

    def available(self) -> bool: ...

    async def remediate(self, root: Path, prompt: str, timeout: float) -> AgentRunResult: ...

