from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import BaseModel, ValidationError

from agentguard.core.config import AgentGuardConfig, load_config
from agentguard.core.models import ChangedFile, ChangeSummary, QualityReport, QualityReportDocument
from agentguard.reporters.json_reporter import render_json

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("model", "schema_name"),
    (
        (AgentGuardConfig, "config-v1.schema.json"),
        (QualityReportDocument, "report-v1.schema.json"),
    ),
)
def test_checked_in_schemas_are_current(model: type[BaseModel], schema_name: str) -> None:
    expected = json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
    assert (ROOT / "schemas" / schema_name).read_text(encoding="utf-8") == expected


def test_unknown_config_key_reports_precise_path() -> None:
    with pytest.raises(ValidationError) as error:
        AgentGuardConfig.model_validate({"quality": {"minimum_score": 80, "mystery": True}})
    assert error.value.errors()[0]["loc"] == ("quality", "mystery")
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_config_version_one_is_required() -> None:
    with pytest.raises(ValidationError) as error:
        AgentGuardConfig.model_validate({"version": 2})
    assert error.value.errors()[0]["loc"] == ("version",)


def test_example_config_validates() -> None:
    assert load_config(ROOT / "examples" / ".agentguard.yml").version == 1


def test_json_report_is_stable_except_documented_volatile_fields(tmp_path: Path) -> None:
    def report() -> dict[str, object]:
        value = QualityReport(
            repository=tmp_path,
            change=ChangeSummary(files=[ChangedFile(path=Path("app.py"), status="modified")]),
        )
        return cast(dict[str, object], json.loads(render_json(value)))

    first, second = report(), report()
    for value in (first, second):
        value.pop("generated_at")
        value.pop("duration_seconds")
    assert first == second
