from agentguard.analyzers.architecture import ArchitectureAnalyzer
from agentguard.analyzers.base import AnalysisContext, Analyzer, AnalyzerMetadata, AnalyzerRegistry
from agentguard.analyzers.dependencies import DependencyAnalyzer
from agentguard.analyzers.duplication import JscpdAnalyzer
from agentguard.analyzers.python import (
    BanditAnalyzer,
    MypyAnalyzer,
    PytestCoverageAnalyzer,
    RadonAnalyzer,
    RuffAnalyzer,
)
from agentguard.analyzers.security import SemgrepAnalyzer, TrivyAnalyzer
from agentguard.analyzers.typescript import (
    DependencyCruiserAnalyzer,
    ESLintAnalyzer,
    JavaScriptTestsAnalyzer,
    OxcAnalyzer,
    TscAnalyzer,
)


def default_registry() -> AnalyzerRegistry:
    registry = AnalyzerRegistry()
    for analyzer in (
        RuffAnalyzer(),
        MypyAnalyzer(),
        RadonAnalyzer(),
        PytestCoverageAnalyzer(),
        BanditAnalyzer(),
        ESLintAnalyzer(),
        OxcAnalyzer(),
        TscAnalyzer(),
        JavaScriptTestsAnalyzer(),
        DependencyCruiserAnalyzer(),
        SemgrepAnalyzer(),
        TrivyAnalyzer(),
        JscpdAnalyzer(),
        DependencyAnalyzer(),
        ArchitectureAnalyzer(),
    ):
        registry.register(analyzer)
    return registry


__all__ = [
    "AnalysisContext",
    "Analyzer",
    "AnalyzerMetadata",
    "AnalyzerRegistry",
    "default_registry",
]
