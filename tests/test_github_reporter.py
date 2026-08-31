from agentguard.reporters.github import GitHubReporter, render_github_markdown


def test_github_report_contains_gates_and_actionable_findings() -> None:
    report = {
        "quality_score": 81,
        "verdict": "changes requested",
        "policies": [{"name": "Tests", "passed": False, "message": "1 failed"}],
        "findings": [
            {
                "severity": "high",
                "file": "src/a.py",
                "line": 9,
                "message": "Complexity increased | limit exceeded",
                "remediation": "Extract validation",
            }
        ],
    }
    markdown = render_github_markdown(report)
    assert "**Quality score:** 81 / 100" in markdown
    assert "| Tests | ❌ Fail | 1 failed |" in markdown
    assert "`src/a.py:9`" in markdown
    assert "increased \\| limit" in markdown
    assert GitHubReporter().render(report) == markdown


def test_github_report_bounds_findings() -> None:
    report = {"findings": [{"message": str(index)} for index in range(25)]}
    markdown = render_github_markdown(report, max_findings=2)
    assert "23 additional findings omitted" in markdown
