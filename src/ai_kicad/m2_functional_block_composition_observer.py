"""Independent functional-block and visual-ownership composition observer.

This observer consumes semantic/connectivity-derived block membership and emitted
symbol positions.  It deliberately has no dependency on production layout
scores, candidate ranks, or placement objectives.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

Point = tuple[int, int]


@dataclass(frozen=True)
class VisualMember:
    member_id: str
    block_id: str
    center: Point
    owner_id: str | None = None
    ownership: str = "block"


@dataclass(frozen=True)
class VisualRelation:
    relation_id: str
    role: str
    member_ids: tuple[str, ...]
    owner_block_id: str | None = None


@dataclass(frozen=True)
class BlockDispersion:
    block_id: str
    member_count: int
    span_x: int
    span_y: int
    manhattan_diameter: int


@dataclass(frozen=True)
class OwnershipDistance:
    member_id: str
    owner_id: str
    role: str
    distance: int


@dataclass(frozen=True)
class FeedbackWitness:
    relation_id: str
    owner_block_id: str | None
    span: int
    unrelated_block_intrusions: tuple[str, ...]


@dataclass(frozen=True)
class FunctionalBlockCompositionMetrics:
    block_dispersion: tuple[BlockDispersion, ...]
    fragmented_blocks: tuple[str, ...]
    support_to_owner: tuple[OwnershipDistance, ...]
    interface_to_owner: tuple[OwnershipDistance, ...]
    feedback: tuple[FeedbackWitness, ...]
    shared_members: tuple[str, ...]


def measure_functional_block_composition(
    members: tuple[VisualMember, ...],
    relations: tuple[VisualRelation, ...] = (),
    *,
    fragmentation_gap: int = 40,
) -> FunctionalBlockCompositionMetrics:
    """Measure grouping from independent semantic ownership and emitted positions."""
    by_id = {member.member_id: member for member in members}
    by_block: dict[str, list[VisualMember]] = defaultdict(list)
    for member in members:
        by_block[member.block_id].append(member)

    dispersion = tuple(
        _dispersion(block_id, tuple(block_members))
        for block_id, block_members in sorted(by_block.items())
    )
    fragmented = tuple(
        item.block_id
        for item in dispersion
        if item.member_count > 1
        and max(item.span_x, item.span_y) > fragmentation_gap
        and item.manhattan_diameter > fragmentation_gap
    )
    support = _ownership_distances(members, by_id, "support")
    interfaces = _ownership_distances(members, by_id, "interface")
    feedback = tuple(
        _feedback_witness(relation, by_id, members)
        for relation in sorted(relations, key=lambda item: item.relation_id)
        if relation.role == "feedback"
    )
    shared = tuple(sorted(member.member_id for member in members if member.ownership == "shared"))
    return FunctionalBlockCompositionMetrics(
        block_dispersion=dispersion,
        fragmented_blocks=fragmented,
        support_to_owner=support,
        interface_to_owner=interfaces,
        feedback=feedback,
        shared_members=shared,
    )


def _dispersion(block_id: str, members: tuple[VisualMember, ...]) -> BlockDispersion:
    xs = [member.center[0] for member in members]
    ys = [member.center[1] for member in members]
    diameter = max(
        (_manhattan(first.center, second.center) for first in members for second in members),
        default=0,
    )
    return BlockDispersion(block_id, len(members), max(xs) - min(xs), max(ys) - min(ys), diameter)


def _ownership_distances(
    members: tuple[VisualMember, ...],
    by_id: dict[str, VisualMember],
    role: str,
) -> tuple[OwnershipDistance, ...]:
    witnesses: list[OwnershipDistance] = []
    for member in sorted(members, key=lambda item: item.member_id):
        if member.ownership != role or member.owner_id is None:
            continue
        owner = by_id.get(member.owner_id)
        if owner is None:
            continue
        witnesses.append(
            OwnershipDistance(
                member.member_id,
                owner.member_id,
                role,
                _manhattan(member.center, owner.center),
            )
        )
    return tuple(witnesses)


def _feedback_witness(
    relation: VisualRelation,
    by_id: dict[str, VisualMember],
    members: tuple[VisualMember, ...],
) -> FeedbackWitness:
    related = [by_id[item] for item in relation.member_ids if item in by_id]
    if related:
        min_x = min(item.center[0] for item in related)
        max_x = max(item.center[0] for item in related)
        min_y = min(item.center[1] for item in related)
        max_y = max(item.center[1] for item in related)
        span = (max_x - min_x) + (max_y - min_y)
        intrusions = tuple(
            sorted(
                item.member_id
                for item in members
                if item.member_id not in relation.member_ids
                and item.block_id != relation.owner_block_id
                and min_x <= item.center[0] <= max_x
                and min_y <= item.center[1] <= max_y
            )
        )
    else:
        span = 0
        intrusions = ()
    return FeedbackWitness(relation.relation_id, relation.owner_block_id, span, intrusions)


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
