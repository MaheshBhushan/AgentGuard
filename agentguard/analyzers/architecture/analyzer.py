"""Small, deterministic architecture rules for changed Python files."""

from __future__ import annotations

import ast
from pathlib import Path

from agentguard.analyzers.base import AnalysisContext, AnalyzerMetadata
from agentguard.core.models import AnalyzerResult, Finding, Severity


def _module_name(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


class ArchitectureAnalyzer:
    metadata = AnalyzerMetadata(
        name="architecture",
        category="architecture",
        languages=frozenset({"python"}),
    )

    async def analyze(self, context: AnalysisContext) -> AnalyzerResult:
        findings: list[Finding] = []
        rules = context.config.architecture
        forbidden_dependencies = (
            rules.forbidden_dependencies | context.config.dependencies.forbidden
        )
        for changed in context.change.files:
            if changed.path.suffix != ".py" or changed.status == "deleted":
                continue
            path = context.root / changed.path
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(changed.path))
            except (OSError, SyntaxError, UnicodeError) as error:
                findings.append(
                    Finding(
                        analyzer=self.metadata.name,
                        category="architecture",
                        severity=Severity.MEDIUM,
                        message=f"Could not inspect architecture: {error}",
                        file=changed.path,
                        rule_id="architecture-parse-error",
                    )
                )
                continue
            lines = source.splitlines()
            if len(lines) > rules.max_file_lines:
                findings.append(
                    Finding(
                        analyzer=self.metadata.name,
                        category="architecture",
                        severity=Severity.MEDIUM,
                        message=f"File has {len(lines)} lines; limit is {rules.max_file_lines}",
                        file=changed.path,
                        line=1,
                        rule_id="max-file-lines",
                        remediation="Split the changed file into focused modules.",
                        metadata={"actual": len(lines), "limit": rules.max_file_lines},
                    )
                )
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    length = (node.end_lineno or node.lineno) - node.lineno + 1
                    if length > rules.max_function_lines:
                        findings.append(
                            Finding(
                                analyzer=self.metadata.name,
                                category="architecture",
                                severity=Severity.MEDIUM,
                                message=(
                                    f"Function {node.name} has {length} lines; "
                                    f"limit is {rules.max_function_lines}"
                                ),
                                file=changed.path,
                                line=node.lineno,
                                rule_id="max-function-lines",
                                remediation="Extract a cohesive helper from this function.",
                                metadata={"actual": length, "limit": rules.max_function_lines},
                            )
                        )
            source_module = _module_name(changed.path)
            for imported, line in _imports(tree):
                for rule in rules.forbidden_imports:
                    if _matches(source_module, rule["from"]) and _matches(imported, rule["to"]):
                        findings.append(
                            Finding(
                                analyzer=self.metadata.name,
                                category="architecture",
                                severity=Severity.HIGH,
                                message=f"{source_module} must not import {imported}",
                                file=changed.path,
                                line=line,
                                rule_id="forbidden-import",
                                remediation=f"Remove the dependency on {rule['to']} from {rule['from']}.",
                            )
                        )
                top_level = imported.split(".", 1)[0].lower().replace("_", "-")
                if top_level in {item.lower().replace("_", "-") for item in forbidden_dependencies}:
                    findings.append(
                        Finding(
                            analyzer=self.metadata.name,
                            category="architecture",
                            severity=Severity.HIGH,
                            message=f"Forbidden dependency imported: {imported}",
                            file=changed.path,
                            line=line,
                            rule_id="forbidden-dependency",
                            remediation=f"Remove or replace {top_level}.",
                        )
                    )
        return AnalyzerResult(
            analyzer=self.metadata.name,
            findings=findings,
            metrics={
                "architecture_violations": float(
                    sum(finding.rule_id != "architecture-parse-error" for finding in findings)
                )
            },
        )
