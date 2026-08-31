from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


async def run_process(
    command: Sequence[str], *, cwd: Path, timeout: float = 120, env: Mapping[str, str] | None = None
) -> ProcessResult:
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        return ProcessResult(tuple(command), -1, stdout.decode(errors="replace"), stderr.decode(errors="replace"), time.monotonic() - started, True)
    except asyncio.CancelledError:
        process.kill()
        await process.communicate()
        raise
    return ProcessResult(tuple(command), process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace"), time.monotonic() - started)
