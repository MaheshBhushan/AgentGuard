from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest
import yaml

import agentguard.integrations.github_action as action
from agentguard.core.models import (
    AnalyzerResult,
    AnalyzerStatus,
    ChangedFile,
    ChangeSummary,
    PolicyResult,
    QualityReport,
)

ROOT = Path(__file__).parents[1]


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def test_action_metadata_exposes_marketplace_contract() -> None:
    metadata = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert metadata["runs"]["using"] == "composite"
    assert metadata["branding"] == {"icon": "shield", "color": "blue"}
    assert {
        "base-ref",
        "config",
        "profile",
        "minimum-score",
        "fail-on",
        "timeout",
        "install-analyzers",
        "post-comment",
        "annotations",
        "upload-report",
        "token",
    } <= metadata["inputs"].keys()
    assert {
        "verdict",
        "quality-score",
        "findings-count",
        "policy-failures",
        "analyzers-executed",
        "analyzers-unavailable",
        "report-path",
    } == metadata["outputs"].keys()
    upload = next(
        step for step in metadata["runs"]["steps"] if step.get("name") == "Upload AgentGuard report"
    )
    assert upload["uses"] == "actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4"
    assert "inputs.upload-report == 'true'" in upload["if"]
    sarif = next(
        step for step in metadata["runs"]["steps"] if step.get("name") == "Upload AgentGuard SARIF"
    )
    assert sarif["uses"] == "github/codeql-action/upload-sarif@cdf488f595d80d6e07e03d4674febd5ab45fa938"
    assert "inputs.annotations == 'true'" in sarif["if"]
    assert sarif["with"]["sarif_file"].endswith("/.agentguard/report.sarif")


def test_auto_base_uses_pull_request_sha(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agentguard@example.invalid")
    _git(tmp_path, "config", "user.name", "AgentGuard")
    (tmp_path / "file.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "file.txt")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "file.txt").write_text("head\n", encoding="utf-8")
    _git(tmp_path, "commit", "-qam", "head")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"base": {"sha": base}}}), encoding="utf-8")
    assert (
        action.resolve_base(
            tmp_path, {"AGENTGUARD_INPUT_BASE_REF": "auto", "GITHUB_EVENT_PATH": str(event)}
        )
        == base
    )


def test_missing_history_has_checkout_guidance(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    with pytest.raises(RuntimeError, match="fetch-depth: 0"):
        action.resolve_base(tmp_path, {"AGENTGUARD_INPUT_BASE_REF": "missing"})


def test_entrypoint_writes_outputs_and_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "github-output"
    summary = tmp_path / "step-summary"
    report = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("app.py"), status="modified")]),
        analyzer_results=[
            AnalyzerResult(analyzer="ruff"),
            AnalyzerResult(analyzer="mypy", status=AnalyzerStatus.UNAVAILABLE, required=True),
        ],
        policies=[PolicyResult(name="score", passed=True, message="passed")],
        quality_score=91,
    )

    async def analyze(*args: object, **kwargs: object) -> QualityReport:
        return report

    monkeypatch.setattr(action, "resolve_base", lambda root, env: "main")
    monkeypatch.setattr(action, "analyze_repository", analyze)
    result = asyncio.run(
        action.run(
            {
                "GITHUB_WORKSPACE": str(tmp_path),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(summary),
                "AGENTGUARD_INPUT_PROFILE": "minimal",
            }
        )
    )
    assert result == 3
    values = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    assert values["verdict"] == "incomplete"
    assert values["quality-score"] == "91"
    assert json.loads(values["analyzers-executed"]) == ["ruff"]
    assert json.loads(values["analyzers-unavailable"]) == ["mypy"]
    assert Path(values["report-path"]).is_file()
    sarif = tmp_path / ".agentguard" / "report.sarif"
    assert sarif.is_file()
    assert json.loads(sarif.read_text(encoding="utf-8"))["version"] == "2.1.0"
    markdown = summary.read_text(encoding="utf-8")
    assert "**Analysis completeness:** 50%" in markdown
    assert "**Verdict:** incomplete" in markdown


def test_comment_updates_existing_bot_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"number": 7, "pull_request": {"number": 7, "head": {"repo": {"fork": False}}}}),
        encoding="utf-8",
    )
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    def request(
        url: str, token: str, method: str = "GET", payload: dict[str, str] | None = None
    ) -> object:
        del token
        calls.append((url, method, payload))
        if method == "GET":
            return [
                {
                    "url": "https://api.github.com/comments/9",
                    "body": action.COMMENT_MARKER,
                    "user": {"type": "Bot"},
                }
            ]
        return {"id": 9}

    monkeypatch.setattr(action, "_github_request", request)
    assert action.post_comment(
        "report",
        {
            "GITHUB_EVENT_PATH": str(event),
            "GITHUB_REPOSITORY": "owner/repo",
            "AGENTGUARD_INPUT_TOKEN": "secret",
        },
    )
    assert [method for _, method, _ in calls] == ["GET", "PATCH"]
    assert calls[1][0] == "https://api.github.com/comments/9"
    assert calls[1][2] == {"body": f"{action.COMMENT_MARKER}\nreport"}


def test_comment_permission_failure_and_fork_degrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = tmp_path / "event.json"
    environment = {
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_REPOSITORY": "owner/repo",
        "AGENTGUARD_INPUT_TOKEN": "read-only",
    }
    event.write_text(
        json.dumps({"pull_request": {"number": 2, "head": {"repo": {"fork": False}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(action, "_github_request", lambda *args, **kwargs: None)
    assert not action.post_comment("report", environment)

    def unexpected(*args: object, **kwargs: object) -> object:
        raise AssertionError("fork comment API must not be called")

    event.write_text(
        json.dumps({"pull_request": {"number": 2, "head": {"repo": {"fork": True}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(action, "_github_request", unexpected)
    assert not action.post_comment("report", environment)
