from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_local_documentation_links_resolve() -> None:
    sources = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    missing: list[str] = []
    for source in sources:
        for target in re.findall(r"\[[^]]*\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if path and not (source.parent / path).resolve().exists():
                missing.append(f"{source.relative_to(ROOT)}: {target}")
    assert not missing


def test_readme_uses_release_action_and_observed_benchmark_claims() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    report = (ROOT / "benchmarks" / "release-report.md").read_text(encoding="utf-8")
    assert "uses: MaheshBhushan/AgentGuard@v1" in readme
    assert "AI-generated patches evaluated: 10" in report
    assert "Mean analyzer completeness: 100%" in report
    assert "10 patches, 100% completion among applicable analyzers" in readme
    assert "no recorded repair runs" in readme
