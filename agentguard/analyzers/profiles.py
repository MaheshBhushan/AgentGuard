from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agentguard.analyzers.base import AnalyzerRegistry
from agentguard.core.models import AnalyzerResult, AnalyzerStatus
from agentguard.core.runner import ProcessResult, run_process


class AnalyzerProfile(StrEnum):
    AUTO = "auto"
    MINIMAL = "minimal"
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    SECURITY = "security"
    FULL = "full"


@dataclass(frozen=True)
class ToolPin:
    analyzer: str
    executable: str
    package: str
    version: str
    installer: str

    @property
    def command(self) -> tuple[str, ...]:
        requirement = f"{self.package}=={self.version}" if self.installer == "pip" else f"{self.package}@{self.version}"
        if self.installer == "pip":
            return (sys.executable, "-m", "pip", "install", requirement)
        return ("npm", "install", "--global", requirement)


@dataclass(frozen=True)
class ResolvedProfile:
    name: AnalyzerProfile
    languages: frozenset[str]
    analyzers: frozenset[str]
    tools: tuple[ToolPin, ...]

    @property
    def versions(self) -> dict[str, str]:
        versions: dict[str, str] = {}
        for tool in self.tools:
            versions.setdefault(tool.analyzer, tool.version)
        if "trivy" in self.analyzers:
            versions["trivy"] = "0.63.0"
        return versions

    @property
    def cache_key(self) -> str:
        payload = {
            "profile": self.name.value,
            "languages": sorted(self.languages),
            "external": {"trivy": self.versions["trivy"]}
            if "trivy" in self.analyzers
            else {},
            "tools": [
                [tool.analyzer, tool.package, tool.version, tool.installer] for tool in self.tools
            ],
        }
        digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()[:16]
        return f"agentguard-tools-{digest}"


@dataclass(frozen=True)
class ProfileInstallResult:
    profile: ResolvedProfile
    processes: tuple[ProcessResult, ...]

    @property
    def analyzer_results(self) -> list[AnalyzerResult]:
        return [
            AnalyzerResult(
                analyzer=tool.analyzer,
                status=AnalyzerStatus.UNAVAILABLE,
                required=True,
                version=tool.version,
                message=(process.stderr.strip() or f"failed to install {tool.package}"),
            )
            for tool, process in zip(self.profile.tools, self.processes, strict=True)
            if process.returncode != 0 or process.timed_out
        ]


PYTHON_ANALYZERS = frozenset({"ruff", "mypy", "radon", "pytest", "bandit"})
TYPESCRIPT_ANALYZERS = frozenset(
    {"eslint", "oxc", "tsc", "js-tests", "dependency-cruiser"}
)
SECURITY_ANALYZERS = frozenset({"bandit", "semgrep", "trivy"})
BUILTIN_ANALYZERS = frozenset({"dependency-delta", "architecture"})
DUPLICATION_ANALYZERS = frozenset({"jscpd"})

TOOL_PINS = (
    ToolPin("ruff", "ruff", "ruff", "0.11.13", "pip"),
    ToolPin("mypy", "mypy", "mypy", "1.16.0", "pip"),
    ToolPin("radon", "radon", "radon", "6.0.1", "pip"),
    ToolPin("pytest", "pytest", "pytest", "8.4.0", "pip"),
    ToolPin("pytest", "pytest", "pytest-cov", "6.1.1", "pip"),
    ToolPin("pytest", "pytest", "pytest-json-report", "1.5.0", "pip"),
    ToolPin("bandit", "bandit", "bandit", "1.8.3", "pip"),
    ToolPin("semgrep", "semgrep", "semgrep", "1.125.0", "pip"),
    ToolPin("eslint", "eslint", "eslint", "9.28.0", "npm"),
    ToolPin("oxc", "oxlint", "oxlint", "1.2.0", "npm"),
    ToolPin("tsc", "tsc", "typescript", "5.8.3", "npm"),
    ToolPin(
        "dependency-cruiser",
        "depcruise",
        "dependency-cruiser",
        "16.10.2",
        "npm",
    ),
    ToolPin("jscpd", "jscpd", "jscpd", "4.0.5", "npm"),
)


def detect_project_languages(root: Path) -> frozenset[str]:
    languages: set[str] = set()
    if any((root / name).is_file() for name in ("pyproject.toml", "requirements.txt")):
        languages.add("python")
    if (root / "package.json").is_file():
        languages.add("typescript")
    excluded = {".git", ".venv", "node_modules", "dist", "build"}
    if "python" not in languages and any(
        path.suffix in {".py", ".pyi"} and not excluded.intersection(path.parts)
        for path in root.rglob("*")
    ):
        languages.add("python")
    if "typescript" not in languages and any(
        path.suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
        and not excluded.intersection(path.parts)
        for path in root.rglob("*")
    ):
        languages.add("typescript")
    return frozenset(languages)


def resolve_profile(root: Path, profile: AnalyzerProfile | str) -> ResolvedProfile:
    requested = AnalyzerProfile(profile)
    languages = detect_project_languages(root)
    if requested is AnalyzerProfile.MINIMAL:
        analyzers = BUILTIN_ANALYZERS
    elif requested is AnalyzerProfile.PYTHON:
        analyzers = BUILTIN_ANALYZERS | PYTHON_ANALYZERS
    elif requested is AnalyzerProfile.TYPESCRIPT:
        analyzers = BUILTIN_ANALYZERS | TYPESCRIPT_ANALYZERS
    elif requested is AnalyzerProfile.SECURITY:
        analyzers = BUILTIN_ANALYZERS | SECURITY_ANALYZERS
    elif requested is AnalyzerProfile.FULL:
        analyzers = (
            BUILTIN_ANALYZERS
            | PYTHON_ANALYZERS
            | TYPESCRIPT_ANALYZERS
            | SECURITY_ANALYZERS
            | DUPLICATION_ANALYZERS
        )
    else:
        analyzers = BUILTIN_ANALYZERS
        if "python" in languages:
            analyzers |= PYTHON_ANALYZERS
        if "typescript" in languages:
            analyzers |= TYPESCRIPT_ANALYZERS
    tools = tuple(tool for tool in TOOL_PINS if tool.analyzer in analyzers)
    return ResolvedProfile(requested, languages, analyzers, tools)


def registry_for_profile(profile: ResolvedProfile) -> AnalyzerRegistry:
    from agentguard.analyzers import default_registry

    registry = AnalyzerRegistry(required=profile.analyzers, versions=profile.versions)
    for analyzer in default_registry().analyzers:
        if analyzer.metadata.name in profile.analyzers:
            registry.register(analyzer)
    return registry


ProcessRunner = Callable[..., Awaitable[ProcessResult]]


async def install_profile(
    profile: ResolvedProfile,
    *,
    cwd: Path,
    timeout: float = 300,
    runner: ProcessRunner = run_process,
) -> ProfileInstallResult:
    processes: list[ProcessResult] = []
    for tool in profile.tools:
        processes.append(await runner(tool.command, cwd=cwd, timeout=timeout))
    return ProfileInstallResult(profile, tuple(processes))
