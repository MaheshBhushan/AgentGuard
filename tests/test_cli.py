from pathlib import Path

from typer.testing import CliRunner

import agentguard.cli.app as cli
from agentguard.cli.app import app
from agentguard.core.models import (
    AnalyzerResult,
    AnalyzerStatus,
    ChangedFile,
    ChangeSummary,
    PolicyResult,
    QualityReport,
)

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_init(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".agentguard.yml").exists()


def test_bad_format() -> None:
    result = runner.invoke(app, ["check", "--format", "xml"])
    assert result.exit_code == 2


def test_check_exit_code_follows_policies(monkeypatch, tmp_path) -> None:
    failed = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("app.py"), status="modified")]),
        policies=[PolicyResult(name="gate", passed=False, message="failed")],
    )
    monkeypatch.setattr(cli, "_report", lambda base, staged: failed)
    result = runner.invoke(app, ["check", "--format", "json"])
    assert result.exit_code == 1
    assert '"verdict": "fail"' in result.stdout


def test_check_exit_code_distinguishes_incomplete_analysis(monkeypatch, tmp_path) -> None:
    incomplete = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("app.py"), status="modified")]),
        analyzer_results=[
            AnalyzerResult(
                analyzer="required-tool",
                status=AnalyzerStatus.UNAVAILABLE,
                required=True,
            )
        ],
    )
    monkeypatch.setattr(cli, "_report", lambda base, staged: incomplete)
    result = runner.invoke(app, ["check", "--format", "json"])
    assert result.exit_code == 3
    assert '"verdict": "incomplete"' in result.stdout


def test_check_exit_code_distinguishes_analyzer_error(monkeypatch, tmp_path) -> None:
    errored = QualityReport(
        repository=tmp_path,
        change=ChangeSummary(files=[ChangedFile(path=Path("app.py"), status="modified")]),
        analyzer_results=[
            AnalyzerResult(analyzer="broken-tool", status=AnalyzerStatus.FAILED)
        ],
    )
    monkeypatch.setattr(cli, "_report", lambda base, staged: errored)
    result = runner.invoke(app, ["check", "--format", "json"])
    assert result.exit_code == 2
    assert '"verdict": "error"' in result.stdout


def test_check_explicitly_skips_empty_change(monkeypatch, tmp_path) -> None:
    skipped = QualityReport(repository=tmp_path, change=ChangeSummary())
    monkeypatch.setattr(cli, "_report", lambda base, staged: skipped)
    result = runner.invoke(app, ["check", "--format", "json"])
    assert result.exit_code == 0
    assert '"verdict": "skipped"' in result.stdout
