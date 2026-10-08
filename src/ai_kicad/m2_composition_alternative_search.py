"""Bounded deterministic search over semantic composition alternatives."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class AlternativeAxis:
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class CompositionAlternative:
    choices: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SearchEvidence:
    alternatives: tuple[CompositionAlternative, ...]
    theoretical_count: int
    attempted_count: int
    emitted_count: int
    duplicate_count: int
    budget_exhausted: bool


_ALLOWED_AXES = frozenset(
    {
        "interface_frontier",
        "semantic_block_order",
        "repeated_channel_grammar",
        "support_placement",
        "field_slot",
        "branch_route",
    }
)


def enumerate_alternatives(
    axes: tuple[AlternativeAxis, ...],
    *,
    budget: int,
) -> SearchEvidence:
    """Enumerate a bounded, deterministic, deduplicated alternative space."""
    if budget < 1:
        raise ValueError("budget must be positive")
    normalized = _normalize_axes(axes)
    theoretical_count = 1
    for axis in normalized:
        theoretical_count *= len(axis.values)

    emitted: list[CompositionAlternative] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    attempted = 0
    duplicates = 0

    for values in product(*(axis.values for axis in normalized)):
        if attempted >= budget:
            break
        attempted += 1
        choices = tuple((axis.name, value) for axis, value in zip(normalized, values, strict=True))
        if choices in seen:
            duplicates += 1
            continue
        seen.add(choices)
        emitted.append(CompositionAlternative(choices))

    return SearchEvidence(
        alternatives=tuple(emitted),
        theoretical_count=theoretical_count,
        attempted_count=attempted,
        emitted_count=len(emitted),
        duplicate_count=duplicates,
        budget_exhausted=attempted < theoretical_count,
    )


def _normalize_axes(
    axes: tuple[AlternativeAxis, ...],
) -> tuple[AlternativeAxis, ...]:
    by_name: dict[str, tuple[str, ...]] = {}
    for axis in axes:
        if axis.name not in _ALLOWED_AXES:
            raise ValueError(f"unsupported composition axis: {axis.name}")
        if not axis.values:
            raise ValueError(f"composition axis has no values: {axis.name}")
        if axis.name in by_name:
            raise ValueError(f"duplicate composition axis: {axis.name}")
        by_name[axis.name] = tuple(sorted(set(axis.values)))
    return tuple(AlternativeAxis(name, by_name[name]) for name in sorted(by_name))
