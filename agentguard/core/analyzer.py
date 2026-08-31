from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path

from agentguard.analyzers.base import AnalysisContext, AnalyzerRegistry
from agentguard.core.config import AgentGuardConfig, load_config
from agentguard.core.git_diff import changed_languages, get_change, repository_root
from agentguard.core.models import Metric, QualityReport
from agentguard.core.policy_engine import evaluate_policies
from agentguard.core.scoring import calculate_score

RegistryFactory = Callable[[], AnalyzerRegistry]


def default_registry() -> AnalyzerRegistry:
    """Build the installed analyzer registry without making integrations mandatory."""
    try:
        from agentguard.analyzers import default_registry as build_registry
    except ImportError:
        return AnalyzerRegistry()
    return build_registry()


async def analyze_repository(
    root: Path | None = None,
    *,
    base: str | None = None,
    staged: bool = False,
    config: AgentGuardConfig | None = None,
    registry: AnalyzerRegistry | None = None,
) -> QualityReport:
    started = time.monotonic()
    repo = repository_root(root)
    resolved_config = config or load_config(start=repo)
    change = get_change(repo, base=base, staged=staged)
    context = AnalysisContext(repo, change, resolved_config)
    results = await (registry or default_registry()).run(context, changed_languages(change))
    raw_metrics: dict[str, float] = {}
    for result in results:
        for name, value in result.metrics.items():
            raw_metrics[name] = raw_metrics.get(name, 0) + value
    score, components = calculate_score(results, raw_metrics)
    policies = evaluate_policies(resolved_config, score, raw_metrics, results)
    return QualityReport(
        repository=repo,
        change=change,
        analyzer_results=results,
        metrics=[Metric(name=name, value=value) for name, value in sorted(raw_metrics.items())],
        policies=policies,
        quality_score=score,
        score_components=components,
        duration_seconds=time.monotonic() - started,
    )


def analyze_repository_sync(
    root: Path | None = None,
    *,
    base: str | None = None,
    staged: bool = False,
    config: AgentGuardConfig | None = None,
    registry: AnalyzerRegistry | None = None,
) -> QualityReport:
    return asyncio.run(
        analyze_repository(root, base=base, staged=staged, config=config, registry=registry)
    )
