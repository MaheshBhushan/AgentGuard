from __future__ import annotations

import shutil
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from agentguard import __version__
from agentguard.agents.loop import run_fix_loop
from agentguard.core.analyzer import analyze_repository_sync
from agentguard.core.config import AgentGuardConfig
from agentguard.core.feedback import generate_feedback
from agentguard.core.models import QualityReport
from agentguard.reporters.json_reporter import render_json
from agentguard.reporters.terminal import render_terminal

app = typer.Typer(no_args_is_help=True, help="Deterministic quality gates for AI-generated code.")
console = Console()


def _report(base: str | None, staged: bool) -> QualityReport:
    return analyze_repository_sync(base=base, staged=staged)


def _emit(report: QualityReport, output: str) -> None:
    if output == "json":
        typer.echo(render_json(report))
        return
    typer.echo(render_terminal(report, color=console.is_terminal), nl=False)


@app.command("init")
def init_config(force: bool = typer.Option(False, "--force")) -> None:
    """Create a conservative default configuration."""
    target = Path.cwd() / ".agentguard.yml"
    if target.exists() and not force:
        raise typer.BadParameter(f"{target.name} already exists; use --force to replace it")
    data = AgentGuardConfig().model_dump(mode="json", exclude_defaults=True)
    data["version"] = 1
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    typer.echo(f"Created {target}")


@app.command()
def check(
    diff: str | None = typer.Option(None, "--diff"),
    staged: bool = typer.Option(False, "--staged"),
    output: str = typer.Option("terminal", "--format", case_sensitive=False),
) -> None:
    """Analyze working-tree, staged, or revision changes."""
    if output not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    report = _report(diff, staged)
    _emit(report, output)
    if report.exit_code:
        raise typer.Exit(report.exit_code)


@app.command()
def compare(base: str, output: str = typer.Option("terminal", "--format")) -> None:
    """Compare the current tree with BASE."""
    report = _report(base, False)
    _emit(report, output)
    if report.exit_code:
        raise typer.Exit(report.exit_code)


@app.command()
def feedback(diff: str | None = typer.Option(None, "--diff")) -> None:
    """Print concise remediation instructions for the current change."""
    report = _report(diff, False)
    typer.echo(generate_feedback(report))


@app.command()
def fix() -> None:
    """Run the configured coding-agent repair loop when an adapter is installed."""
    raise typer.Exit(run_fix_loop(Path.cwd()))


@app.command()
def doctor() -> None:
    """Show optional analyzer availability."""
    table = Table("Analyzer", "Available")
    for executable in ("ruff", "mypy", "radon", "pytest", "coverage", "bandit", "semgrep", "trivy", "eslint", "oxlint", "tsc", "jscpd"):
        table.add_row(executable, "✓" if shutil.which(executable) else "✗")
    console.print(table)


@app.command("version")
def show_version() -> None:
    """Print the AgentGuard version."""
    typer.echo(__version__)
