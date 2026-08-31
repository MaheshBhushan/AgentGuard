from typer.testing import CliRunner

import agentguard.cli.app as cli
from agentguard.cli.app import app
from agentguard.core.models import ChangeSummary, PolicyResult, QualityReport

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
        change=ChangeSummary(),
        policies=[PolicyResult(name="gate", passed=False, message="failed")],
    )
    monkeypatch.setattr(cli, "_report", lambda base, staged: failed)
    result = runner.invoke(app, ["check", "--format", "json"])
    assert result.exit_code == 1
    assert '"verdict": "fail"' in result.stdout
