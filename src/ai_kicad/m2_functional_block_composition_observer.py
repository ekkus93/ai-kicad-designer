"""Functional-block composition observer for M2h2 human-readability evidence.

This module consumes independently reconstructed semantic ownership and emitted
geometry. It intentionally has no production layout score input: every metric is
computed from semantic block identity, visual ownership, and drawing geometry.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

Point = tuple[int, int]
Rect = tuple[int, int, int, int]

PRIMARY_ROLE = "primary"
SUPPORT_ROLE = "support"
FEEDBACK_ROLE = "feedback"
INTERFACE_ROLE = "interface"
SHARED_ROLE = "shared"


@dataclass(frozen=True)
class VisualBlockMember:
    ref: str
    block_id: str
    role: str
    center: Point
    bbox: Rect
    owner_block_id: str | None = None


@dataclass(frozen=True)
class OwnershipDistanceWitness:
    ref: str
    owner_block_id: str
    distance: int


@dataclass(frozen=True)
class FeedbackSpanWitness:
    ref: str
    owner_block_id: str
    span_width: int
    span_height: int
    intrusion_refs: tuple[str, ...]


@dataclass(frozen=True)
class BlockIntrusionWitness:
    ref: str
    intruded_block_id: str
    intruded_refs: tuple[str, ...]


@dataclass(frozen=True)
class FunctionalBlockCompositionMetrics:
    block_dispersion: dict[str, int]
    block_fragmentation: dict[str, int]
    support_to_owner_distance: tuple[OwnershipDistanceWitness, ...]
    interface_to_owner_distance: tuple[OwnershipDistanceWitness, ...]
    feedback_loop_span: tuple[FeedbackSpanWitness, ...]
    unrelated_block_intrusions: tuple[BlockIntrusionWitness, ...]


def measure_functional_block_composition(
    members: tuple[VisualBlockMember, ...], *, adjacency_gap: int = 0
) -> FunctionalBlockCompositionMetrics:
    """Compute independent functional-block and ownership readability metrics."""
    members_by_block = _members_by_block(members)
    block_bboxes = {
        block_id: _union_rect(tuple(member.bbox for member in block_members))
        for block_id, block_members in members_by_block.items()
    }
    return FunctionalBlockCompositionMetrics(
        block_dispersion={
            block_id: _dispersion(tuple(member.center for member in block_members))
            for block_id, block_members in sorted(members_by_block.items())
        },
        block_fragmentation={
            block_id: _fragment_count(tuple(member.bbox for member in block_members), adjacency_gap)
            for block_id, block_members in sorted(members_by_block.items())
        },
        support_to_owner_distance=_ownership_distances(members, block_bboxes, role=SUPPORT_ROLE),
        interface_to_owner_distance=_ownership_distances(
            members, block_bboxes, role=INTERFACE_ROLE
        ),
        feedback_loop_span=_feedback_spans(members, block_bboxes),
        unrelated_block_intrusions=_unrelated_intrusions(members, members_by_block),
    )


def _members_by_block(
    members: tuple[VisualBlockMember, ...],
) -> dict[str, tuple[VisualBlockMember, ...]]:
    grouped: dict[str, list[VisualBlockMember]] = defaultdict(list)
    for member in members:
        grouped[member.block_id].append(member)
    return {block_id: tuple(items) for block_id, items in grouped.items()}


def _dispersion(points: tuple[Point, ...]) -> int:
    if len(points) < 2:
        return 0
    return max(_manhattan(first, second) for first in points for second in points)


def _fragment_count(rects: tuple[Rect, ...], adjacency_gap: int) -> int:
    if not rects:
        return 0
    remaining = set(range(len(rects)))
    fragments = 0
    while remaining:
        fragments += 1
        start = remaining.pop()
        queue: deque[int] = deque((start,))
        while queue:
            current = queue.popleft()
            for candidate in tuple(remaining):
                if _rects_adjacent(rects[current], rects[candidate], adjacency_gap):
                    remaining.remove(candidate)
                    queue.append(candidate)
    return fragments


def _ownership_distances(
    members: tuple[VisualBlockMember, ...], block_bboxes: dict[str, Rect], *, role: str
) -> tuple[OwnershipDistanceWitness, ...]:
    witnesses = []
    for member in sorted(members, key=lambda item: item.ref):
        if member.role != role or member.owner_block_id is None:
            continue
        owner_bbox = block_bboxes.get(member.owner_block_id)
        if owner_bbox is None:
            continue
        witnesses.append(
            OwnershipDistanceWitness(
                ref=member.ref,
                owner_block_id=member.owner_block_id,
                distance=_rect_distance(member.bbox, owner_bbox),
            )
        )
    return tuple(witnesses)


def _feedback_spans(
    members: tuple[VisualBlockMember, ...], block_bboxes: dict[str, Rect]
) -> tuple[FeedbackSpanWitness, ...]:
    spans = []
    for member in sorted(members, key=lambda item: item.ref):
        if member.role != FEEDBACK_ROLE or member.owner_block_id is None:
            continue
        owner_bbox = block_bboxes.get(member.owner_block_id)
        if owner_bbox is None:
            continue
        span = _union_rect((member.bbox, owner_bbox))
        intrusions = tuple(
            other.ref
            for other in sorted(members, key=lambda item: item.ref)
            if other.block_id not in {member.block_id, member.owner_block_id}
            and _rects_intersect(other.bbox, span)
        )
        spans.append(
            FeedbackSpanWitness(
                ref=member.ref,
                owner_block_id=member.owner_block_id,
                span_width=span[2] - span[0],
                span_height=span[3] - span[1],
                intrusion_refs=intrusions,
            )
        )
    return tuple(spans)


def _unrelated_intrusions(
    members: tuple[VisualBlockMember, ...],
    members_by_block: dict[str, tuple[VisualBlockMember, ...]],
) -> tuple[BlockIntrusionWitness, ...]:
    witnesses = []
    for member in sorted(members, key=lambda item: item.ref):
        allowed_blocks = {member.block_id}
        if member.owner_block_id is not None:
            allowed_blocks.add(member.owner_block_id)
        for block_id, block_members in sorted(members_by_block.items()):
            if block_id in allowed_blocks:
                continue
            intruded_refs = tuple(
                other.ref
                for other in sorted(block_members, key=lambda item: item.ref)
                if _rects_intersect(member.bbox, other.bbox)
            )
            if intruded_refs:
                witnesses.append(
                    BlockIntrusionWitness(
                        ref=member.ref,
                        intruded_block_id=block_id,
                        intruded_refs=intruded_refs,
                    )
                )
    return tuple(witnesses)


def _union_rect(rects: tuple[Rect, ...]) -> Rect:
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _rects_adjacent(first: Rect, second: Rect, gap: int) -> bool:
    return not (
        first[2] + gap < second[0]
        or second[2] + gap < first[0]
        or first[3] + gap < second[1]
        or second[3] + gap < first[1]
    )


def _rects_intersect(first: Rect, second: Rect) -> bool:
    return not (
        first[2] <= second[0]
        or second[2] <= first[0]
        or first[3] <= second[1]
        or second[3] <= first[1]
    )


def _rect_distance(first: Rect, second: Rect) -> int:
    dx = max(second[0] - first[2], first[0] - second[2], 0)
    dy = max(second[1] - first[3], first[1] - second[3], 0)
    return dx + dy


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
