from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from agentguard.analyzers.base import AnalysisContext
from agentguard.analyzers.profiles import registry_for_profile, resolve_profile
from agentguard.core.config import AgentGuardConfig
from agentguard.core.git_diff import changed_languages
from agentguard.core.models import ChangedFile, ChangeSummary, Outcome, QualityReport

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("files", "expected_languages"),
    [
        ({"pyproject.toml": "[project]\nname='sample'\n", "app.py": "value = 1\n"}, {"python"}),
        (
            {
                "pyproject.toml": "[project]\nname='sample'\n",
                "package.json": "{}\n",
                "app.py": "value = 1\n",
                "app.ts": "export const value = 1;\n",
            },
            {"python", "typescript"},
        ),
        (
            {"package.json": '{"scripts": {}}\n', "app.ts": "export const value = 1;\n"},
            {"typescript"},
        ),
    ],
    ids=["python", "mixed", "typescript-without-tests"],
)
def test_required_tools_missing_never_produce_clean_release_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    files: dict[str, str],
    expected_languages: set[str],
) -> None:
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    change = ChangeSummary(
        files=[
            ChangedFile(
                path=Path(name),
                status="added",
                additions=len(content.splitlines()),
                changed_lines=set(range(1, len(content.splitlines()) + 1)),
            )
            for name, content in files.items()
        ]
    )
    profile = resolve_profile(tmp_path, "auto")
    assert profile.languages == expected_languages
    monkeypatch.setattr("agentguard.analyzers._shared.executable", lambda _root, _name: None)
    results = asyncio.run(
        registry_for_profile(profile).run(
            AnalysisContext(tmp_path, change, AgentGuardConfig()), changed_languages(change)
        )
    )
    report = QualityReport(repository=tmp_path, change=change, analyzer_results=results)
    assert report.outcome is Outcome.INCOMPLETE
    assert any(result.required and result.status == "unavailable" for result in results)


def test_consumer_smoke_workflow_uses_local_action_contract() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "consumer-smoke.yml").read_text(encoding="utf-8")
    )
    step = next(
        step
        for step in workflow["jobs"]["consumer-smoke"]["steps"]
        if step.get("name") == "Run local AgentGuard candidate"
    )
    assert step["uses"] == "./"
    assert step["with"] == {
        "base-ref": "HEAD~1",
        "profile": "minimal",
        "install-analyzers": "false",
    }
