"""Structural anti-overfitting audit for active M2 production modules."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_ROOTS = (ROOT / "src/ai_kicad",)
PRODUCTION_GLOB = "m2*.py"

FIXTURE_LITERAL_PATTERN = re.compile(
    r"\b(?:"
    r"V[1-6]-[1-8]|"
    r"m2blind_v[0-9]+|"
    r"m2h2_dp[0-9]+|"
    r"qualification_candidate[0-9]+|"
    r"interaction_qualification|interaction_alternatives|"
    r"dual_regulator_mixed_loads|passive_two_level_fanout|"
    r"timer_split_filtered_gain_indicator|"
    r"corpus\.v[0-9]+"
    r")\b",
    re.IGNORECASE,
)

REFDES_LITERAL_PATTERN = re.compile(r"^(?:R|C|U|J|D|Q|RV|SW|TP)\d+[A-Z]?$")
NET_LITERAL_PATTERN = re.compile(
    r"^(?:"
    r"VREF|VCC|VPLUS|VMINUS|VBUS|FILTERED|BUFFERED|"
    r"IN_[A-Z0-9_]+|OUT_[A-Z0-9_]+|AMP_[A-Z0-9_]+"
    r")$"
)

CONTROL_NODES = (ast.If, ast.IfExp, ast.While, ast.Assert)


def _repo_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _line_at(lines: list[str], line_number: int) -> str:
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1].strip()
    return ""


def _source_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.is_file():
            files.append(resolved)
            continue
        if not resolved.exists():
            raise FileNotFoundError(path)
        for candidate in sorted(resolved.glob(PRODUCTION_GLOB)):
            parts = set(candidate.parts)
            if ".local" in parts or "legacy_openclaw" in parts:
                continue
            files.append(candidate.resolve())
    return sorted(dict.fromkeys(files))


def _string_constants(node: ast.AST) -> list[tuple[str, int]]:
    constants: list[tuple[str, int]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            constants.append((child.value, getattr(child, "lineno", getattr(node, "lineno", 0))))
    return constants


def _string_constants_in_match_pattern(pattern: ast.AST) -> list[tuple[str, int]]:
    constants: list[tuple[str, int]] = []
    for child in ast.walk(pattern):
        if isinstance(child, ast.MatchValue) and isinstance(child.value, ast.Constant):
            value = child.value.value
            if isinstance(value, str):
                constants.append((value, getattr(child, "lineno", getattr(pattern, "lineno", 0))))
    return constants


def _suspicious_literal(value: str) -> str | None:
    if REFDES_LITERAL_PATTERN.fullmatch(value):
        return "refdes_literal_control_flow"
    if NET_LITERAL_PATTERN.fullmatch(value):
        return "net_literal_control_flow"
    return None


def audit_paths(paths: Iterable[Path]) -> dict[str, Any]:
    """Return a structured structural anti-overfitting audit report."""
    findings: list[dict[str, Any]] = []
    files = _source_files(paths)
    for path in files:
        text = path.read_text()
        lines = text.splitlines()
        relative = _relative(path)
        for line_number, line in enumerate(lines, start=1):
            match = FIXTURE_LITERAL_PATTERN.search(line)
            if match:
                findings.append(
                    {
                        "kind": "fixture_specific_literal",
                        "path": relative,
                        "line": line_number,
                        "literal": match.group(0),
                        "source": line.strip(),
                    }
                )
        tree = ast.parse(text, filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, CONTROL_NODES):
                inspected = node.test if hasattr(node, "test") else node
                for value, line_number in _string_constants(inspected):
                    kind = _suspicious_literal(value)
                    if kind:
                        findings.append(
                            {
                                "kind": kind,
                                "path": relative,
                                "line": line_number,
                                "literal": value,
                                "source": _line_at(lines, line_number),
                            }
                        )
            elif isinstance(node, ast.Match):
                for case in node.cases:
                    for value, line_number in _string_constants_in_match_pattern(case.pattern):
                        kind = _suspicious_literal(value)
                        if kind:
                            findings.append(
                                {
                                    "kind": kind,
                                    "path": relative,
                                    "line": line_number,
                                    "literal": value,
                                    "source": _line_at(lines, line_number),
                                }
                            )
                    if case.guard is not None:
                        for value, line_number in _string_constants(case.guard):
                            kind = _suspicious_literal(value)
                            if kind:
                                findings.append(
                                    {
                                        "kind": kind,
                                        "path": relative,
                                        "line": line_number,
                                        "literal": value,
                                        "source": _line_at(lines, line_number),
                                    }
                                )
    return {
        "schema_version": "m2h2.structural-anti-overfitting-audit.1",
        "scope": [_relative(path) for path in files],
        "git_head": _repo_head(),
        "rules": {
            "fixture_specific_literals": FIXTURE_LITERAL_PATTERN.pattern,
            "refdes_literal_control_flow": REFDES_LITERAL_PATTERN.pattern,
            "net_literal_control_flow": NET_LITERAL_PATTERN.pattern,
        },
        "findings": findings,
        "finding_count": len(findings),
        "pass": not findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=list(PRODUCTION_ROOTS),
        help="Production files or directories to audit; defaults to active M2 modules.",
    )
    parser.add_argument("--out", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    report = audit_paths(args.paths)
    payload = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    print(payload, end="")
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
