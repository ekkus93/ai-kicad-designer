"""Fail-closed independent M2h2 source-stabilization checks.

Verifies historical native render integrity, local documentation links, and
absence of CP-SAT dependencies and fixture-specific production lookup tables.
It does not certify native readability or promote comparative acceptance.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from ai_kicad.m2a import ROOT
from analyze_m2h2_historical_composition import _verified_svg_by_case
from run_m2h2_structural_audit import FIXTURE_LITERAL_PATTERN, audit_paths

EXPECTED_HISTORICAL_CASES = 90
EXPECTED_HISTORICAL_INVENTORY = (
    "759f49bf715da357d70f4fb4ae5513594328acb3ba8612031866ac6788a21fe0"
)
HISTORICAL_MANIFEST = (
    "fixtures/m2h2/human_composition_baseline_2026-10-08/"
    "native_render_archive_manifest_42ab8452.json"
)
DOCUMENTS = (
    "docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md",
    "docs/M2H2_NATIVE_ENGINEERING_REVIEW_2026-10-13.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PROHIBITED_SOLVER_ROOTS = frozenset({"ortools", "pulp", "cvxpy", "mip"})


def check_frozen_inventory(svg_count: int, inventory_hash: str) -> list[str]:
    issues = []
    if svg_count != EXPECTED_HISTORICAL_CASES:
        issues.append(f"historical SVG count changed: {svg_count}")
    if inventory_hash != EXPECTED_HISTORICAL_INVENTORY:
        issues.append(f"historical SVG inventory changed: {inventory_hash}")
    return issues


def check_local_links(repo_root: Path, document: Path) -> list[str]:
    """Check file targets while allowing remote and in-document anchors."""
    errors = []
    for target in MARKDOWN_LINK.findall(document.read_text()):
        target = target.strip().strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        resolved = (document.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(repo_root.resolve()) or not resolved.exists():
            errors.append(f"{document.relative_to(repo_root)}: missing link {target}")
    return errors


def prohibited_source_imports(source: str, filename: str) -> list[str]:
    """Detect direct and literal dynamic solver imports in production modules."""
    problems = []
    tree = ast.parse(source, filename=filename)

    def check(module: str, line: int) -> None:
        if module.split(".", 1)[0] in PROHIBITED_SOLVER_ROOTS:
            problems.append(f"{filename}:{line}: prohibited solver import {module}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                check(name.name, node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module:
            check(node.module, node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            dynamic_import = (
                isinstance(func, ast.Name)
                and func.id == "__import__"
                or isinstance(func, ast.Attribute)
                and func.attr == "import_module"
            )
            if (
                dynamic_import
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                check(node.args[0].value, node.lineno)
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if FIXTURE_LITERAL_PATTERN.search(key.value):
                        problems.append(
                            f"{filename}:{key.lineno}: fixture-specific lookup key {key.value}"
                        )
    return problems


def source_audit(root: Path = ROOT) -> dict:
    """Run all checks against source files and the original archived evidence."""
    issues = []
    source_root = root / "src/ai_kicad"
    modules = sorted(source_root.glob("m2*.py"))
    if not modules:
        issues.append("no M2 production modules found")
    for path in modules:
        issues.extend(prohibited_source_imports(path.read_text(), str(path.relative_to(root))))
    for relative in DOCUMENTS:
        document = root / relative
        if not document.is_file():
            issues.append(f"missing source-stabilization document: {relative}")
        else:
            issues.extend(check_local_links(root, document))
    structural = audit_paths([source_root])
    if not structural["pass"]:
        issues.append(f"structural anti-overfitting violations: {structural['finding_count']}")
    try:
        svg_by_case, provenance = _verified_svg_by_case(root, root / HISTORICAL_MANIFEST)
        issues.extend(
            check_frozen_inventory(len(svg_by_case), provenance["inventory_sha256"])
        )
    except (OSError, ValueError, KeyError) as exc:
        issues.append(f"historical native archive failed verification: {exc}")
    return {
        "schema_version": "m2h2.source-stabilization-audit.1",
        "historical_case_count_expected": EXPECTED_HISTORICAL_CASES,
        "historical_inventory_expected": EXPECTED_HISTORICAL_INVENTORY,
        "modules_audited": len(modules),
        "documents_audited": list(DOCUMENTS),
        "errors": issues,
        "pass": not issues,
    }


def main() -> None:
    report = source_audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
