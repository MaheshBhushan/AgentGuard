"""Dependency manifest delta analysis using only standard-library parsers."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, AnalyzerStatus, Finding, Severity

_REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")
_MANIFEST_NAMES = {"pyproject.toml", "package.json"}
_LOCKFILE_ECOSYSTEMS = {
    "poetry.lock": "python",
    "uv.lock": "python",
    "package-lock.json": "javascript",
    "pnpm-lock.yaml": "javascript",
    "yarn.lock": "javascript",
    "bun.lock": "javascript",
    "bun.lockb": "javascript",
}


def _python_name(specification: str) -> str | None:
    text = specification.strip()
    if not text or text.startswith(("#", "-")):
        return None
    match = _REQUIREMENT_NAME.match(text)
    return match.group(1).lower().replace("_", "-") if match else None


def parse_manifest(path: Path, content: bytes) -> tuple[set[str], set[str]]:
    """Return normalized runtime and development dependency names."""
    if path.name == "package.json":
        data = json.loads(content)
        return set(data.get("dependencies", {})), set(data.get("devDependencies", {}))
    if path.name == "pyproject.toml":
        data = tomllib.loads(content.decode())
        project = data.get("project", {})
        runtime = {name for item in project.get("dependencies", []) if (name := _python_name(item))}
        development = {
            name
            for group, items in project.get("optional-dependencies", {}).items()
            if group.lower() in {"dev", "test", "tests"}
            for item in items
            if (name := _python_name(item))
        }
        poetry = data.get("tool", {}).get("poetry", {})
        runtime.update(name.lower() for name in poetry.get("dependencies", {}) if name != "python")
        for group in poetry.get("group", {}).values():
            development.update(name.lower() for name in group.get("dependencies", {}))
        return runtime, development
    if path.name.startswith("requirements") or path.parent.name == "requirements":
        dependencies = {
            name
            for line in content.decode().splitlines()
            if (name := _python_name(line)) is not None
        }
        is_dev = any(token in path.name.lower() for token in ("dev", "test"))
        return (set(), dependencies) if is_dev else (dependencies, set())
    return set(), set()


def _is_manifest(path: Path) -> bool:
    return (
        path.name in _MANIFEST_NAMES | _LOCKFILE_ECOSYSTEMS.keys()
        or path.name.startswith("requirements")
        or (path.parent.name == "requirements" and path.suffix == ".txt")
    )


def _baseline(root: Path, revision: str, path: Path) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path.as_posix()}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


class DependencyAnalyzer:
    metadata = AnalyzerMetadata(
        name="dependency-delta",
        category="dependencies",
        languages=frozenset(),
    )

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        changed = [item for item in context.change.files if _is_manifest(item.path)]
        if not changed:
            return AnalyzerResult(
                analyzer=self.metadata.name,
                status=AnalyzerStatus.SKIPPED,
                message="no dependency manifests changed",
            )
        added: set[str] = set()
        removed: set[str] = set()
        dev_added: set[str] = set()
        missing_baselines: list[str] = []
        ecosystems = {
            _LOCKFILE_ECOSYSTEMS[item.path.name]
            for item in changed
            if item.path.name in _LOCKFILE_ECOSYSTEMS
        }
        revision = context.change.base or "HEAD"
        for item in changed:
            current_content = (
                (context.root / item.path).read_bytes() if item.status != "deleted" else b""
            )
            before_content = _baseline(context.root, revision, item.old_path or item.path)
            if before_content is None and item.status != "added":
                missing_baselines.append(item.path.as_posix())
                continue
            before_runtime, before_dev = (
                parse_manifest(item.path, before_content)
                if before_content is not None
                else (set(), set())
            )
            after_runtime, after_dev = parse_manifest(item.path, current_content)
            added.update(after_runtime - before_runtime)
            removed.update(before_runtime - after_runtime)
            dev_added.update(after_dev - before_dev)
        findings = [
            Finding(
                analyzer=self.metadata.name,
                category="dependencies",
                severity=Severity.LOW,
                message=f"Dependency introduced: {name}",
                file=next((item.path for item in changed), None),
                rule_id="dependency-added",
                metadata={"dependency": name, "development": False},
            )
            for name in sorted(added)
        ]
        findings.extend(
            Finding(
                analyzer=self.metadata.name,
                category="dependencies",
                severity=Severity.INFO,
                message=f"Development dependency introduced: {name}",
                file=next((item.path for item in changed), None),
                rule_id="development-dependency-added",
                metadata={"dependency": name, "development": True},
            )
            for name in sorted(dev_added)
        )
        return AnalyzerResult(
            analyzer=self.metadata.name,
            findings=findings,
            metrics={
                "new_dependencies": float(len(added)),
                "removed_dependencies": float(len(removed)),
                "new_dev_dependencies": float(len(dev_added)),
                "dependency_count_delta": float(len(added) + len(dev_added) - len(removed)),
            },
            message="; ".join(
                part
                for part in (
                    "baseline unavailable for: " + ", ".join(missing_baselines)
                    if missing_baselines
                    else "",
                    "lockfile ecosystem detected: " + ", ".join(sorted(ecosystems))
                    if ecosystems
                    else "",
                )
                if part
            )
            or None,
        )
