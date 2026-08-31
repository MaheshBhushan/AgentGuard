from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentguard.core.config import AgentGuardConfig
from agentguard.core.models import AnalyzerResult, AnalyzerStatus, ChangeSummary


@dataclass(frozen=True)
class AnalyzerMetadata:
    name: str
    category: str
    languages: frozenset[str]
    executable: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class AnalysisContext:
    root: Path
    change: ChangeSummary
    config: AgentGuardConfig


class Analyzer(Protocol):
    metadata: AnalyzerMetadata

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult: ...


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        if analyzer.metadata.name in self._analyzers:
            raise ValueError(f"analyzer already registered: {analyzer.metadata.name}")
        self._analyzers[analyzer.metadata.name] = analyzer

    @property
    def analyzers(self) -> tuple[Analyzer, ...]:
        return tuple(self._analyzers.values())

    async def run(self, context: AnalysisContext, languages: set[str]) -> list[AnalyzerResult]:
        results: list[AnalyzerResult] = []
        tasks: list[asyncio.Task[AnalyzerResult]] = []
        for analyzer in self.analyzers:
            metadata = analyzer.metadata
            if metadata.languages and not metadata.languages.intersection(languages):
                results.append(
                    AnalyzerResult(
                        analyzer=metadata.name,
                        status=AnalyzerStatus.SKIPPED,
                        message="irrelevant to changed languages",
                    )
                )
            elif metadata.executable and shutil.which(metadata.executable) is None:
                results.append(
                    AnalyzerResult(
                        analyzer=metadata.name,
                        status=AnalyzerStatus.UNAVAILABLE,
                        message=f"Install '{metadata.executable}' to enable this analyzer",
                    )
                )
            else:
                tasks.append(asyncio.create_task(analyzer.analyze(context)))
        return results + list(await asyncio.gather(*tasks))
