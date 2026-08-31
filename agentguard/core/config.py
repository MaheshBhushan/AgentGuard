from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualityConfig(ConfigModel):
    minimum_score: float = Field(default=80, ge=0, le=100)


class ComplexityConfig(ConfigModel):
    max_function_complexity: int = Field(default=15, ge=1)
    max_complexity_increase: float = Field(default=10, ge=0)


class TestsConfig(ConfigModel):
    require_pass: bool = True
    max_coverage_drop: float = Field(default=1.0, ge=0)
    command: list[str] | None = None


class SecurityConfig(ConfigModel):
    fail_on: set[str] = Field(default_factory=lambda: {"critical", "high"})


class DependenciesConfig(ConfigModel):
    max_new_dependencies: int = Field(default=3, ge=0)
    forbidden: set[str] = Field(default_factory=set)


class DuplicationConfig(ConfigModel):
    max_new_blocks: int = Field(default=2, ge=0)


class AgentConfig(ConfigModel):
    provider: str = "codex"
    max_iterations: int = Field(default=5, ge=1, le=20)
    timeout_seconds: float = Field(default=600, gt=0)


class ArchitectureConfig(ConfigModel):
    forbidden_imports: list[dict[str, str]] = Field(default_factory=list)
    forbidden_dependencies: set[str] = Field(default_factory=set)
    max_file_lines: int = Field(default=500, ge=1)
    max_function_lines: int = Field(default=80, ge=1)


class AgentGuardConfig(ConfigModel):
    version: Literal[1] = 1
    quality: QualityConfig = Field(default_factory=QualityConfig)
    complexity: ComplexityConfig = Field(default_factory=ComplexityConfig)
    tests: TestsConfig = Field(default_factory=TestsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    dependencies: DependenciesConfig = Field(default_factory=DependenciesConfig)
    duplication: DuplicationConfig = Field(default_factory=DuplicationConfig)
    architecture: ArchitectureConfig = Field(default_factory=ArchitectureConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    exclude: list[str] = Field(default_factory=lambda: ["node_modules", ".venv", "dist", "build"])


def load_config(path: Path | None = None, start: Path | None = None) -> AgentGuardConfig:
    config_path = path or find_config(start or Path.cwd())
    if config_path is None:
        return AgentGuardConfig()
    raw: Any
    with config_path.open("rb") as stream:
        raw = tomllib.load(stream) if config_path.suffix == ".toml" else yaml.safe_load(stream)
    return AgentGuardConfig.model_validate(raw or {})


def find_config(start: Path) -> Path | None:
    for directory in (start.resolve(), *start.resolve().parents):
        for name in (".agentguard.yml", ".agentguard.yaml", "agentguard.toml"):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None
