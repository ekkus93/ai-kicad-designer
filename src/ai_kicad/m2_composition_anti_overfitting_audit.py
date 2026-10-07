"""Anti-overfitting audit for M2h2 composition production sources.

This is a source-text audit helper.  It scans ordinary code and data tables for
case, fixture, refdes, literal net, topology-hash, and coordinate-map special
cases that would make composition behavior benchmark-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str


@dataclass(frozen=True)
class AuditFinding:
    path: str
    line_number: int
    category: str
    witness: str


CASE_ID_RE = re.compile(r"\b[a-z]\d+__[A-Za-z0-9_]+\b")
QUALIFICATION_GROUP_RE = re.compile(
    r"\b(?:M2H2|V3_8|DP[1-4]|I[1-6])(?:[_-][A-Z0-9]+)*\b"
)
REFDES_RE = re.compile(r"\b(?:R|C|L|U|Q|D|J|P|TP|FB)\d+[A-Za-z]?\b")
TOPOLOGY_HASH_RE = re.compile(r"\b[0-9a-f]{40,64}\b", re.IGNORECASE)
COORDINATE_PAIR_RE = re.compile(r"\(\s*-?\d+\s*,\s*-?\d+\s*\)")

_LITERAL_NET_PREFIXES = ("NET_", "N$", "/")
_LITERAL_NET_NAMES = frozenset(
    {"VIN", "VOUT", "VREF", "GND", "VCC", "VDD", "AGND"}
)


@dataclass(frozen=True)
class AuditRule:
    category: str
    pattern: re.Pattern[str]


_RULES = (
    AuditRule("fixture_or_case_id", CASE_ID_RE),
    AuditRule("qualification_group_control", QUALIFICATION_GROUP_RE),
    AuditRule("refdes_specific_control", REFDES_RE),
    AuditRule("topology_hash_special_case", TOPOLOGY_HASH_RE),
)


def audit_composition_sources(
    sources: tuple[SourceFile, ...],
) -> tuple[AuditFinding, ...]:
    """Return deterministic anti-overfitting findings from source text."""
    findings: list[AuditFinding] = []
    for source in sorted(sources, key=lambda item: item.path):
        for line_number, line in enumerate(source.text.splitlines(), start=1):
            findings.extend(_line_findings(source.path, line_number, line))
    return tuple(
        sorted(findings, key=lambda item: (item.path, item.line_number, item.category))
    )


def _line_findings(path: str, line_number: int, line: str) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    stripped = _strip_comment(line)
    for rule in _RULES:
        for match in rule.pattern.finditer(stripped):
            findings.append(AuditFinding(path, line_number, rule.category, match.group(0)))
    for witness in _literal_net_witnesses(stripped):
        findings.append(AuditFinding(path, line_number, "literal_benchmark_net_name", witness))
    if _looks_like_coordinate_map(stripped):
        findings.append(
            AuditFinding(path, line_number, "precomputed_coordinate_map", stripped.strip())
        )
    return findings


def _literal_net_witnesses(line: str) -> tuple[str, ...]:
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", line)
    witnesses: list[str] = []
    for value in quoted:
        upper = value.upper()
        if upper in _LITERAL_NET_NAMES or upper.startswith(_LITERAL_NET_PREFIXES):
            witnesses.append(value)
    return tuple(witnesses)


def _looks_like_coordinate_map(line: str) -> bool:
    if "{" not in line and "[" not in line:
        return False
    return len(COORDINATE_PAIR_RE.findall(line)) >= 2


def _strip_comment(line: str) -> str:
    before_hash = line.split("#", 1)[0]
    before_slash = before_hash.split("//", 1)[0]
    return before_slash
