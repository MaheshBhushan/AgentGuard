from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agentguard.agents.base import AgentAdapter
from agentguard.agents.claude_adapter import ClaudeAdapter
from agentguard.agents.codex_adapter import CodexAdapter
from agentguard.core.analyzer import analyze_repository
from agentguard.core.config import AgentGuardConfig, load_config
from agentguard.core.feedback import generate_feedback
from agentguard.core.models import QualityReport

Analyze = Callable[[], Awaitable[QualityReport]]


class StopReason(StrEnum):
    PASSED = "passed"
    MAX_ITERATIONS = "max_iterations"
    NO_PROGRESS = "no_progress"
    REPEATED_FINDINGS = "repeated_findings"
    TIMEOUT = "timeout"
    AGENT_UNAVAILABLE = "agent_unavailable"
    AGENT_FAILED = "agent_failed"


@dataclass(frozen=True)
class FixLoopResult:
    reason: StopReason
    iterations: int
    report: QualityReport
    message: str = ""

    @property
    def exit_code(self) -> int:
        return 0 if self.reason is StopReason.PASSED else 2


def get_adapter(provider: str) -> AgentAdapter:
    adapters: dict[str, AgentAdapter] = {"codex": CodexAdapter(), "claude": ClaudeAdapter()}
    if provider not in adapters:
        raise ValueError(f"unknown agent provider: {provider}")
    return adapters[provider]


def _signature(report: QualityReport) -> tuple[tuple[str, str, int | None, str | None], ...]:
    return tuple(sorted((str(item.file), item.message, item.line, item.rule_id) for item in report.findings))


async def fix_loop(
    root: Path,
    *,
    config: AgentGuardConfig,
    adapter: AgentAdapter,
    analyze: Analyze,
) -> FixLoopResult:
    started = time.monotonic()
    report = await analyze()
    if report.passed:
        return FixLoopResult(StopReason.PASSED, 0, report)
    if not adapter.available():
        return FixLoopResult(StopReason.AGENT_UNAVAILABLE, 0, report, f"{adapter.name} CLI is not installed")
    previous_score = report.quality_score
    seen = {_signature(report)}
    for iteration in range(1, config.agent.max_iterations + 1):
        remaining = config.agent.timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return FixLoopResult(StopReason.TIMEOUT, iteration - 1, report)
        agent_result = await adapter.remediate(root, generate_feedback(report), remaining)
        if agent_result.timed_out:
            return FixLoopResult(StopReason.TIMEOUT, iteration, report, agent_result.error)
        if not agent_result.success:
            return FixLoopResult(StopReason.AGENT_FAILED, iteration, report, agent_result.error)
        updated = await analyze()
        if updated.passed:
            return FixLoopResult(StopReason.PASSED, iteration, updated)
        signature = _signature(updated)
        if signature in seen:
            return FixLoopResult(StopReason.REPEATED_FINDINGS, iteration, updated)
        if updated.quality_score <= previous_score:
            return FixLoopResult(StopReason.NO_PROGRESS, iteration, updated)
        seen.add(signature)
        previous_score, report = updated.quality_score, updated
    return FixLoopResult(StopReason.MAX_ITERATIONS, config.agent.max_iterations, report)


def run_fix_loop(root: Path) -> int:
    config = load_config(start=root)
    adapter = get_adapter(config.agent.provider)
    result = asyncio.run(
        fix_loop(
            root,
            config=config,
            adapter=adapter,
            analyze=lambda: analyze_repository(root, config=config),
        )
    )
    print(f"AgentGuard fix stopped: {result.reason.value} after {result.iterations} iteration(s).")
    if result.message:
        print(result.message)
    return result.exit_code
