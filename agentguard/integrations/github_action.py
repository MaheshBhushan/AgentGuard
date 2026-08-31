from __future__ import annotations

import asyncio
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from agentguard.analyzers.profiles import install_profile, registry_for_profile, resolve_profile
from agentguard.core.analyzer import analyze_repository
from agentguard.core.config import AgentGuardConfig, load_config
from agentguard.core.models import AnalyzerStatus, Outcome, QualityReport
from agentguard.reporters.json_reporter import render_json, report_data


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def resolve_base(root: Path, env: Mapping[str, str]) -> str:
    requested = env.get("AGENTGUARD_INPUT_BASE_REF", "auto").strip()
    if requested and requested != "auto":
        base = requested
    else:
        event_path = env.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise ValueError("base-ref is required outside a pull_request event")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict) or not isinstance(pull_request.get("base"), dict):
            raise ValueError("base-ref=auto requires a pull_request event")
        base = str(pull_request["base"].get("sha") or "")
        if not base:
            raise ValueError("pull_request event does not contain a base SHA")
    try:
        _git(root, "merge-base", base, "HEAD")
    except RuntimeError as error:
        raise RuntimeError(
            f"cannot compare HEAD with {base}; checkout full history with fetch-depth: 0"
        ) from error
    return base


def _boolean(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return normalized == "true"


def _config(root: Path, env: Mapping[str, str]) -> tuple[AgentGuardConfig, float]:
    config_value = env.get("AGENTGUARD_INPUT_CONFIG", "").strip()
    path = root / config_value if config_value else None
    config = load_config(path=path, start=root)
    values = config.model_dump(mode="python")
    minimum_score = env.get("AGENTGUARD_INPUT_MINIMUM_SCORE", "").strip()
    if minimum_score:
        values["quality"]["minimum_score"] = float(minimum_score)
    timeout = float(env.get("AGENTGUARD_INPUT_TIMEOUT", "300"))
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    values["agent"]["timeout_seconds"] = timeout
    return AgentGuardConfig.model_validate(values), timeout


def _write_outputs(path: Path, report: QualityReport, report_path: Path) -> None:
    data = report_data(report)
    values = {
        "verdict": report.outcome.value,
        "quality-score": f"{report.quality_score:g}",
        "findings-count": str(len(report.findings)),
        "policy-failures": json.dumps(
            [policy.name for policy in report.policies if not policy.passed], separators=(",", ":")
        ),
        "analyzers-executed": json.dumps(data["analyzers_executed"], separators=(",", ":")),
        "analyzers-unavailable": json.dumps(
            [
                result.analyzer
                for result in report.analyzer_results
                if result.status is AnalyzerStatus.UNAVAILABLE
            ],
            separators=(",", ":"),
        ),
        "report-path": str(report_path),
    }
    with path.open("a", encoding="utf-8") as stream:
        for name, value in values.items():
            stream.write(f"{name}={value}\n")


async def run(env: Mapping[str, str] = os.environ) -> int:
    root = Path(env.get("GITHUB_WORKSPACE", Path.cwd())).resolve()
    base = resolve_base(root, env)
    config, timeout = _config(root, env)
    profile = resolve_profile(root, env.get("AGENTGUARD_INPUT_PROFILE", "auto"))
    installation_results = []
    if _boolean(env.get("AGENTGUARD_INPUT_INSTALL_ANALYZERS", "true"), "install-analyzers"):
        installation = await install_profile(profile, cwd=root, timeout=timeout)
        installation_results = installation.analyzer_results
    report = await analyze_repository(
        root, base=base, config=config, registry=registry_for_profile(profile)
    )
    report.analyzer_results.extend(installation_results)
    report_path = root / ".agentguard" / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_json(report) + "\n", encoding="utf-8")
    output_path = env.get("GITHUB_OUTPUT")
    if output_path:
        _write_outputs(Path(output_path), report, report_path)
    fail_on = {
        Outcome(value.strip())
        for value in env.get("AGENTGUARD_INPUT_FAIL_ON", "fail,incomplete,error").split(",")
        if value.strip()
    }
    return report.exit_code if report.outcome in fail_on else 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(run()))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"AgentGuard Action error: {error}")
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
