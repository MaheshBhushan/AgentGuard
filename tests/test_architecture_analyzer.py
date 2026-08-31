import asyncio
from pathlib import Path

from agentguard.analyzers.architecture import ArchitectureAnalyzer
from agentguard.analyzers.base import AnalysisContext
from agentguard.core.config import AgentGuardConfig, ArchitectureConfig, DependenciesConfig
from agentguard.core.models import ChangedFile, ChangeSummary


def test_architecture_rules_cover_imports_dependencies_and_size(tmp_path: Path) -> None:
    path = Path("src/domain/service.py")
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_text(
        "import lodash\nfrom infrastructure.db import save\n\ndef oversized():\n    x = 1\n    return x\n",
        encoding="utf-8",
    )
    config = AgentGuardConfig(
        architecture=ArchitectureConfig(
            forbidden_imports=[{"from": "domain", "to": "infrastructure"}],
            forbidden_dependencies={"lodash"},
            max_file_lines=5,
            max_function_lines=2,
        ),
        dependencies=DependenciesConfig(forbidden={"another-package"}),
    )
    context = AnalysisContext(
        root=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=path, status="modified")]),
        config=config,
    )
    result = asyncio.run(ArchitectureAnalyzer().analyze(context))
    assert {finding.rule_id for finding in result.findings} == {
        "forbidden-import",
        "forbidden-dependency",
        "max-file-lines",
        "max-function-lines",
    }
    assert result.metrics["architecture_violations"] == 4


def test_architecture_analyzer_ignores_deleted_files(tmp_path: Path) -> None:
    context = AnalysisContext(
        root=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("gone.py"), status="deleted")]),
        config=AgentGuardConfig(),
    )
    result = asyncio.run(ArchitectureAnalyzer().analyze(context))
    assert result.findings == []
