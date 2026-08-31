from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from agentguard.core.feedback import actionable_findings
from agentguard.core.models import QualityReport


def render_terminal(report: QualityReport, *, color: bool = True) -> str:
    stream = StringIO()
    console = Console(file=stream, force_terminal=color, color_system="auto" if color else None)
    table = Table(title="AGENTGUARD CHANGE QUALITY REPORT")
    table.add_column("Metric")
    table.add_column("Result")
    table.add_row("Quality Score", f"{report.quality_score:g} / 100")
    table.add_row("Changed files", str(len(report.change.files)))
    table.add_row("Lines", f"+{report.change.additions} / -{report.change.deletions}")
    for metric in report.metrics:
        table.add_row(metric.name.replace("_", " ").title(), f"{metric.value:g}{' ' + metric.unit if metric.unit else ''}")
    verdicts = {
        "pass": "[green]SAFE TO MERGE[/green]",
        "fail": "[red]CHANGES REQUIRED[/red]",
        "incomplete": "[yellow]ANALYSIS INCOMPLETE[/yellow]",
        "error": "[red]ANALYSIS ERROR[/red]",
        "skipped": "[yellow]NO RELEVANT CHANGES[/yellow]",
    }
    table.add_row("Verdict", verdicts[report.outcome.value])
    console.print(table)
    findings = actionable_findings(report)
    if findings:
        console.print("\n[bold]Actionable regressions[/bold]")
        for finding in findings:
            console.print(f"{finding.severity.value.upper():8} {finding.file}:{finding.line or 1} {finding.message}")
    console.print(f"\nCompleted in {report.duration_seconds:.2f}s")
    return stream.getvalue()


class TerminalReporter:
    def render(self, report: QualityReport) -> str:
        return render_terminal(report)
