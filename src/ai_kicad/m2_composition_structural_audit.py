"""Structural anti-overfitting audit for M2h2 composition modules.

The audit works on a small, language-independent structural model so production
source adapters can expose condition predicates, lookup tables, and numeric
layout constants without making this checker depend on Python AST details.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StructuralFact:
    path: str
    line_number: int
    kind: str
    key: str
    value: str


@dataclass(frozen=True)
class StructuralFinding:
    path: str
    line_number: int
    category: str
    witness: str


_FORBIDDEN_CONTROL_KEYS = frozenset(
    {
        "fixture_id",
        "case_id",
        "qualification_group",
        "refdes",
        "net_name",
        "topology_hash",
        "inventory_signature",
    }
)
_TARGET_KEYS = frozenset(
    {
        "target_x",
        "target_y",
        "target_width",
        "target_height",
        "image_width",
        "image_height",
    }
)


def audit_structural_facts(
    facts: tuple[StructuralFact, ...],
) -> tuple[StructuralFinding, ...]:
    """Return deterministic findings for benchmark-specific structure."""
    findings: list[StructuralFinding] = []
    coordinate_tables: dict[tuple[str, str], list[StructuralFact]] = {}

    for fact in facts:
        if fact.kind == "condition" and fact.key in _FORBIDDEN_CONTROL_KEYS:
            findings.append(
                StructuralFinding(
                    fact.path,
                    fact.line_number,
                    "benchmark_specific_control",
                    f"{fact.key}={fact.value}",
                )
            )
        if fact.kind == "constant" and fact.key in _TARGET_KEYS:
            findings.append(
                StructuralFinding(
                    fact.path,
                    fact.line_number,
                    "precomputed_target_geometry",
                    f"{fact.key}={fact.value}",
                )
            )
        if fact.kind == "inventory_lookup":
            findings.append(
                StructuralFinding(
                    fact.path,
                    fact.line_number,
                    "exact_inventory_special_case",
                    f"{fact.key}={fact.value}",
                )
            )
        if fact.kind == "coordinate_table":
            coordinate_tables.setdefault((fact.path, fact.key), []).append(fact)

    for (path, key), entries in coordinate_tables.items():
        if len(entries) >= 2:
            first = min(entries, key=lambda item: item.line_number)
            findings.append(
                StructuralFinding(
                    path,
                    first.line_number,
                    "per_case_coordinate_map",
                    f"{key}:{len(entries)} entries",
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.path,
                item.line_number,
                item.category,
                item.witness,
            ),
        )
    )
