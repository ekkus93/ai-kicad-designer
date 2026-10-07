"""Independent branch, fanout, and feedback readability observer."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

Point = tuple[int, int]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class FlowNode:
    node_id: str
    block_id: str
    center: Point


@dataclass(frozen=True)
class BranchRelation:
    relation_id: str
    source_id: str
    output_ids: tuple[str, ...]
    branch_point: Point | None = None
    route_segments: tuple[Segment, ...] = ()


@dataclass(frozen=True)
class FeedbackRelation:
    relation_id: str
    owner_id: str
    member_ids: tuple[str, ...]
    route_segments: tuple[Segment, ...] = ()


@dataclass(frozen=True)
class BranchWitness:
    relation_id: str
    source_distance: int
    sibling_geometry_variance: int
    crossing_count: int
    detour_distance: int


@dataclass(frozen=True)
class FeedbackReadabilityWitness:
    relation_id: str
    owner_distance: int
    span: int
    unrelated_block_intrusions: tuple[str, ...]
    crossing_count: int


@dataclass(frozen=True)
class BranchFeedbackMetrics:
    branch_witnesses: tuple[BranchWitness, ...]
    feedback_witnesses: tuple[FeedbackReadabilityWitness, ...]


def measure_branch_feedback_composition(
    nodes: tuple[FlowNode, ...],
    branches: tuple[BranchRelation, ...] = (),
    feedback: tuple[FeedbackRelation, ...] = (),
) -> BranchFeedbackMetrics:
    by_id = {node.node_id: node for node in nodes}
    return BranchFeedbackMetrics(
        branch_witnesses=tuple(
            _branch_witness(branch, by_id)
            for branch in sorted(branches, key=lambda item: item.relation_id)
        ),
        feedback_witnesses=tuple(
            _feedback_witness(relation, by_id, nodes)
            for relation in sorted(feedback, key=lambda item: item.relation_id)
        ),
    )


def _branch_witness(branch: BranchRelation, by_id: dict[str, FlowNode]) -> BranchWitness:
    source = by_id[branch.source_id]
    outputs = tuple(by_id[item] for item in branch.output_ids if item in by_id)
    point = source.center if branch.branch_point is None else branch.branch_point
    source_distance = _manhattan(source.center, point)
    output_distances = tuple(_manhattan(point, output.center) for output in outputs)
    variance = _range(output_distances)
    crossings = _crossing_count(branch.route_segments)
    output_points = tuple(output.center for output in outputs)
    detour = _detour_distance(point, output_points, branch.route_segments)
    return BranchWitness(branch.relation_id, source_distance, variance, crossings, detour)


def _feedback_witness(
    relation: FeedbackRelation,
    by_id: dict[str, FlowNode],
    nodes: tuple[FlowNode, ...],
) -> FeedbackReadabilityWitness:
    owner = by_id[relation.owner_id]
    members = tuple(by_id[item] for item in relation.member_ids if item in by_id)
    all_points = (owner.center,) + tuple(member.center for member in members)
    owner_distance = max((_manhattan(owner.center, member.center) for member in members), default=0)
    span = _span(all_points)
    intrusions = _unrelated_intrusions(owner, members, nodes)
    crossings = _crossing_count(relation.route_segments)
    return FeedbackReadabilityWitness(
        relation.relation_id,
        owner_distance,
        span,
        intrusions,
        crossings,
    )


def _detour_distance(
    origin: Point, destinations: tuple[Point, ...], segments: tuple[Segment, ...]
) -> int:
    if not segments:
        return 0
    routed = sum(_manhattan(start, end) for start, end in segments)
    direct = sum(_manhattan(origin, destination) for destination in destinations)
    return max(0, routed - direct)


def _unrelated_intrusions(
    owner: FlowNode, members: tuple[FlowNode, ...], nodes: tuple[FlowNode, ...]
) -> tuple[str, ...]:
    if not members:
        return ()
    xs = [owner.center[0], *(member.center[0] for member in members)]
    ys = [owner.center[1], *(member.center[1] for member in members)]
    related_ids = {owner.node_id, *(member.node_id for member in members)}
    return tuple(
        sorted(
            node.node_id
            for node in nodes
            if node.node_id not in related_ids
            and node.block_id != owner.block_id
            and min(xs) <= node.center[0] <= max(xs)
            and min(ys) <= node.center[1] <= max(ys)
        )
    )


def _crossing_count(segments: tuple[Segment, ...]) -> int:
    return sum(1 for left, right in combinations(segments, 2) if _segments_cross(left, right))


def _segments_cross(left: Segment, right: Segment) -> bool:
    (a1, a2), (b1, b2) = left, right
    if a1 in right or a2 in right or b1 in left or b2 in left:
        return False
    return _ccw(a1, b1, b2) != _ccw(a2, b1, b2) and _ccw(a1, a2, b1) != _ccw(a1, a2, b2)


def _ccw(first: Point, second: Point, third: Point) -> bool:
    return (third[1] - first[1]) * (second[0] - first[0]) > (second[1] - first[1]) * (
        third[0] - first[0]
    )


def _span(points: tuple[Point, ...]) -> int:
    if not points:
        return 0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return max(xs) - min(xs) + max(ys) - min(ys)


def _range(values: tuple[int, ...]) -> int:
    if not values:
        return 0
    return max(values) - min(values)


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
