"""Functional-block and visual-ownership observer for M2h2 composition evidence.

The production placer may optimize grouping, but acceptance needs an observer
that derives block membership, ownership, and dispersion from semantic records
plus externally observed coordinates. This module does not consume production
layout scores as proof.
"""

from __future__ import annotations

from dataclasses import dataclass

from .m2_semantics import Occurrence, SemanticPlan

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class FunctionalBlockWitness:
    block: str
    kind: str
    relationship_ids: tuple[str, ...]
    occurrences: tuple[Occurrence, ...]
    port_ids: tuple[str, ...]
    shared: bool


@dataclass(frozen=True)
class VisualOwnershipWitness:
    occurrence: Occurrence
    owner: str
    owner_kind: str


@dataclass(frozen=True)
class BlockDispersionWitness:
    block: str
    occurrence_count: int
    observed_occurrence_count: int
    bbox: Rect | None
    manhattan_span: int
    missing_occurrences: tuple[Occurrence, ...]
    fragmented: bool


def derive_functional_blocks(plan: SemanticPlan) -> tuple[FunctionalBlockWitness, ...]:
    """Return deterministic functional-block evidence from plan semantics."""
    witnesses: list[FunctionalBlockWitness] = []
    for block in plan.blocks:
        witnesses.append(
            FunctionalBlockWitness(
                block=block.id,
                kind=block.kind,
                relationship_ids=tuple(sorted(block.relationships)),
                occurrences=tuple(sorted(block.occurrences)),
                port_ids=tuple(sorted(port.id for port in block.ports)),
                shared=_is_shared_block(plan, block.id),
            )
        )
    return tuple(sorted(witnesses, key=lambda witness: witness.block))


def visual_ownership_witnesses(plan: SemanticPlan) -> tuple[VisualOwnershipWitness, ...]:
    """Report occurrence ownership independently of any placement score."""
    kind_by_block = {block.id: block.kind for block in plan.blocks}
    witnesses = [
        VisualOwnershipWitness(
            occurrence=occurrence,
            owner=owner,
            owner_kind=kind_by_block.get(owner, "unknown"),
        )
        for occurrence, owner in plan.owners.items()
    ]
    return tuple(sorted(witnesses, key=lambda witness: (witness.occurrence, witness.owner)))


def functional_block_dispersion(
    plan: SemanticPlan,
    point_by_occurrence: dict[Occurrence, Point],
) -> tuple[BlockDispersionWitness, ...]:
    """Measure block dispersion from observed occurrence coordinates.

    Missing coordinates are retained as witnesses instead of being treated as
    zero-distance evidence.
    """
    witnesses: list[BlockDispersionWitness] = []
    for block in plan.blocks:
        occurrences = tuple(sorted(block.occurrences))
        observed = [
            (occurrence, point_by_occurrence[occurrence])
            for occurrence in occurrences
            if occurrence in point_by_occurrence
        ]
        missing = tuple(
            occurrence for occurrence in occurrences if occurrence not in point_by_occurrence
        )
        if observed:
            xs = [point[0] for _, point in observed]
            ys = [point[1] for _, point in observed]
            bbox: Rect | None = (min(xs), min(ys), max(xs), max(ys))
            manhattan_span = (bbox[2] - bbox[0]) + (bbox[3] - bbox[1])
        else:
            bbox = None
            manhattan_span = 0
        witnesses.append(
            BlockDispersionWitness(
                block=block.id,
                occurrence_count=len(occurrences),
                observed_occurrence_count=len(observed),
                bbox=bbox,
                manhattan_span=manhattan_span,
                missing_occurrences=missing,
                fragmented=len(observed) > 1 and manhattan_span > 0,
            )
        )
    return tuple(sorted(witnesses, key=lambda witness: witness.block))


def support_to_owner_distances(
    plan: SemanticPlan,
    point_by_occurrence: dict[Occurrence, Point],
) -> tuple[tuple[Occurrence, str, int], ...]:
    """Report distance from each owned occurrence to its owner centroid.

    This is intentionally a raw witness vector; later acceptance thresholds can
    freeze policy without changing the underlying observer evidence.
    """
    owner_points: dict[str, list[Point]] = {}
    for occurrence, owner in plan.owners.items():
        if occurrence in point_by_occurrence:
            owner_points.setdefault(owner, []).append(point_by_occurrence[occurrence])

    centroids: dict[str, Point] = {}
    for owner, points in owner_points.items():
        centroids[owner] = (
            sum(point[0] for point in points) // len(points),
            sum(point[1] for point in points) // len(points),
        )

    distances: list[tuple[Occurrence, str, int]] = []
    for occurrence, owner in sorted(plan.owners.items()):
        if occurrence not in point_by_occurrence or owner not in centroids:
            continue
        point = point_by_occurrence[occurrence]
        centroid = centroids[owner]
        distance = abs(point[0] - centroid[0]) + abs(point[1] - centroid[1])
        distances.append((occurrence, owner, distance))
    return tuple(distances)


def _is_shared_block(plan: SemanticPlan, block_id: str) -> bool:
    for net in plan.presentation_nets:
        if net.role == "distributive" and block_id in net.fragments:
            return True
    return False
