from agentguard.core.config import AgentGuardConfig
from agentguard.core.models import AnalyzerResult, PolicyResult, Severity


def evaluate_policies(config: AgentGuardConfig, score: float, metrics: dict[str, float], results: list[AnalyzerResult]) -> list[PolicyResult]:
    policies = [
        PolicyResult(name="minimum_score", passed=score >= config.quality.minimum_score, message=f"score {score:g} must be at least {config.quality.minimum_score:g}", actual=score, expected=config.quality.minimum_score),
        PolicyResult(name="complexity_increase", passed=metrics.get("complexity_increase", 0) <= config.complexity.max_complexity_increase, message="complexity increase limit", actual=metrics.get("complexity_increase", 0), expected=config.complexity.max_complexity_increase),
        PolicyResult(name="coverage_drop", passed=metrics.get("coverage_drop", 0) <= config.tests.max_coverage_drop, message="coverage drop limit", actual=metrics.get("coverage_drop", 0), expected=config.tests.max_coverage_drop),
        PolicyResult(name="new_dependencies", passed=metrics.get("new_dependencies", 0) <= config.dependencies.max_new_dependencies, message="new dependency limit", actual=metrics.get("new_dependencies", 0), expected=config.dependencies.max_new_dependencies),
        PolicyResult(name="duplication", passed=metrics.get("duplicate_blocks", 0) <= config.duplication.max_new_blocks, message="new duplicate block limit", actual=metrics.get("duplicate_blocks", 0), expected=config.duplication.max_new_blocks),
    ]
    if config.tests.require_pass:
        policies.append(PolicyResult(name="tests_pass", passed=metrics.get("tests_failed", 0) == 0, message="tests must pass", actual=metrics.get("tests_failed", 0), expected=0))
    blocked = {Severity(level) for level in config.security.fail_on}
    security = [finding for result in results for finding in result.findings if finding.category == "security" and finding.severity in blocked]
    policies.append(PolicyResult(name="security", passed=not security, message="no blocked security findings", actual=len(security), expected=0))
    return policies
