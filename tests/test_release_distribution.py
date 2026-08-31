from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from scripts.validate_release_tag import expected_tag
from scripts.verify_distribution import verify

ROOT = Path(__file__).parents[1]
FULL_SHA = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def test_release_workflow_uses_trusted_publishing_and_minimal_permissions() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    )
    assert workflow["permissions"] == {"contents": "read"}
    publish = workflow["jobs"]["publish"]
    assert publish["environment"]["name"] == "pypi"
    assert publish["permissions"] == {
        "contents": "read",
        "id-token": "write",
        "attestations": "write",
    }
    assert any(
        str(step.get("uses", "")).startswith("pypa/gh-action-pypi-publish@")
        for step in publish["steps"]
    )
    test_publish = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "test-publish.yml").read_text(encoding="utf-8")
    )["jobs"]["test-publish"]
    assert test_publish["environment"]["name"] == "testpypi"
    publisher = test_publish["steps"][-1]
    assert publisher["with"]["repository-url"] == "https://test.pypi.org/legacy/"


def test_all_third_party_actions_are_pinned_to_full_shas() -> None:
    documents = [ROOT / "action.yml", *(ROOT / ".github" / "workflows").glob("*.yml")]
    for document in documents:
        data = yaml.safe_load(document.read_text(encoding="utf-8"))
        steps = data["runs"]["steps"] if "runs" in data else [
            step
            for job in data.get("jobs", {}).values()
            for step in job.get("steps", [])
        ]
        for step in steps:
            action = str(step.get("uses", ""))
            if action and action != "./":
                assert FULL_SHA.fullmatch(action), f"unpinned action in {document}: {action}"


def test_release_tag_matches_project_version() -> None:
    assert expected_tag(ROOT) == "v0.1.0"


def test_distribution_verifier_rejects_missing_artifacts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one wheel and one source distribution"):
        verify(tmp_path)
