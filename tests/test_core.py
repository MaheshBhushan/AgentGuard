from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from agentguard.core.config import load_config
from agentguard.core.git_diff import changed_languages, parse_diff
from agentguard.core.models import AnalyzerResult, Finding, Severity
from agentguard.core.policy_engine import evaluate_policies
from agentguard.core.runner import run_process
from agentguard.core.scoring import calculate_score


def test_yaml_and_toml_config(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".agentguard.yml"
    yaml_path.write_text("version: 1\nquality:\n  minimum_score: 91\n", encoding="utf-8")
    assert load_config(yaml_path).quality.minimum_score == 91
    toml_path = tmp_path / "agentguard.toml"
    toml_path.write_text("version = 1\n[quality]\nminimum_score = 92\n", encoding="utf-8")
    assert load_config(toml_path).quality.minimum_score == 92


def test_invalid_config() -> None:
    try:
        load_config(Path("missing"))
    except FileNotFoundError:
        return
    raise AssertionError("missing explicit configuration must fail")


def test_parse_diff_tracks_lines_and_languages() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,2 +1,3 @@
 old
-gone
+new
+more
"""
    change = parse_diff(diff)
    assert change.additions == 2
    assert change.deletions == 1
    assert change.files[0].changed_lines == {2, 3}
    assert changed_languages(change) == {"python"}


def test_runner_timeout(tmp_path: Path) -> None:
    result = asyncio.run(run_process([sys.executable, "-c", "import time; time.sleep(1)"], cwd=tmp_path, timeout=0.01))
    assert result.timed_out
    assert result.returncode == -1


def test_runner_cancellation_propagates(tmp_path: Path) -> None:
    async def cancel_process() -> None:
        task = asyncio.create_task(
            run_process(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                cwd=tmp_path,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("process task did not propagate cancellation")

    asyncio.run(cancel_process())


def test_model_validation() -> None:
    try:
        Finding(analyzer="x", category="lint", severity=Severity.LOW, message="x", line=0)
    except ValidationError:
        return
    raise AssertionError("line zero must be rejected")


def test_score_and_policies() -> None:
    result = AnalyzerResult(analyzer="security", findings=[Finding(analyzer="security", category="security", severity=Severity.HIGH, message="unsafe")])
    score, components = calculate_score([result], {"tests_failed": 1})
    assert score == 72
    assert sum(item.penalty for item in components) == 28
    policies = evaluate_policies(load_config(), score, {"tests_failed": 1}, [result])
    assert {policy.name for policy in policies if not policy.passed} == {"minimum_score", "tests_pass", "security"}
