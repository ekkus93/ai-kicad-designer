"""Independent tiny-grid exhaustive placement oracle for composition evidence."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

Point = tuple[int, int]
ScoreVector = tuple[int, int, int, int, int]


@dataclass(frozen=True)
class TinyNode:
    node_id: str
    role: str
    side_preference: str | None = None
    group_id: str | None = None
    stage_index: int | None = None
    channel_id: str | None = None
    repeated_role: str | None = None


@dataclass(frozen=True)
class TinyPlacementScore:
    candidate_id: str
    node_positions: tuple[tuple[str, Point], ...]
    score_vector: ScoreVector


@dataclass(frozen=True)
class TinyOracleEvidence:
    candidate_count: int
    nondominated_candidates: tuple[TinyPlacementScore, ...]
    production_candidate: TinyPlacementScore | None
    production_is_dominated: bool
    dominating_candidate_ids: tuple[str, ...]


def exhaustive_tiny_grid_oracle(
    nodes: tuple[TinyNode, ...],
    grid_points: tuple[Point, ...],
    *,
    production_positions: tuple[tuple[str, Point], ...] | None = None,
    max_candidates: int = 5040,
) -> TinyOracleEvidence:
    """Enumerate bounded placements and report non-dominated legal candidates."""
    if len(nodes) > len(grid_points):
        raise ValueError("grid must have at least one point per node")
    candidate_count = _permutation_count(len(grid_points), len(nodes))
    if candidate_count > max_candidates:
        raise ValueError("tiny-grid oracle candidate bound exceeded")

    node_order = tuple(sorted(nodes, key=lambda item: item.node_id))
    scored: list[TinyPlacementScore] = []
    for index, placement_points in enumerate(permutations(grid_points, len(node_order))):
        positions = tuple(
            sorted(
                (
                    (node.node_id, placement_point)
                    for node, placement_point in zip(node_order, placement_points, strict=True)
                ),
                key=lambda item: item[0],
            )
        )
        scored.append(
            TinyPlacementScore(f"oracle_{index:04d}", positions, _score_positions(node_order, positions))
        )

    nondominated = _nondominated(scored)
    production = None
    dominated = False
    dominating_ids: tuple[str, ...] = ()
    if production_positions is not None:
        normalized = tuple(sorted(production_positions, key=lambda item: item[0]))
        production = TinyPlacementScore("production", normalized, _score_positions(node_order, normalized))
        dominating_ids = tuple(
            candidate.candidate_id
            for candidate in nondominated
            if _dominates(candidate.score_vector, production.score_vector)
        )
        dominated = bool(dominating_ids)

    return TinyOracleEvidence(
        len(scored),
        nondominated,
        production,
        dominated,
        dominating_ids,
    )


def _score_positions(nodes: tuple[TinyNode, ...], positions: tuple[tuple[str, Point], ...]) -> ScoreVector:
    by_id = dict(positions)
    xs = [point[0] for point in by_id.values()]
    ys = [point[1] for point in by_id.values()]
    min_x = min(xs)
    max_x = max(xs)
    side_penalty = _side_penalty(nodes, by_id, min_x, max_x)
    stage_penalty = _stage_order_penalty(nodes, by_id)
    grouping_penalty = _grouping_penalty(nodes, by_id)
    repeated_penalty = _repeated_alignment_penalty(nodes, by_id)
    whitespace_penalty = (max_x - min_x) * (max(ys) - min(ys))
    return (side_penalty, stage_penalty, grouping_penalty, repeated_penalty, whitespace_penalty)


def _side_penalty(
    nodes: tuple[TinyNode, ...], by_id: dict[str, Point], min_x: int, max_x: int
) -> int:
    penalty = 0
    for node in nodes:
        point = by_id[node.node_id]
        if node.side_preference == "left":
            penalty += point[0] - min_x
        elif node.side_preference == "right":
            penalty += max_x - point[0]
    return penalty


def _stage_order_penalty(nodes: tuple[TinyNode, ...], by_id: dict[str, Point]) -> int:
    staged = sorted(
        (node for node in nodes if node.stage_index is not None),
        key=lambda item: (item.stage_index, item.node_id),
    )
    penalty = 0
    for first, second in zip(staged, staged[1:], strict=True):
        if first.stage_index == second.stage_index:
            continue
        penalty += max(0, by_id[first.node_id][0] - by_id[second.node_id][0])
    return penalty


def _grouping_penalty(nodes: tuple[TinyNode, ...], by_id: dict[str, Point]) -> int:
    penalty = 0
    groups = sorted({node.group_id for node in nodes if node.group_id is not None})
    for group in groups:
        group_nodes = [node for node in nodes if node.group_id == group]
        group_points = [by_id[node.node_id] for node in group_nodes]
        penalty += max(
            (_manhattan(first, second) for first in group_points for second in group_points),
            default=0,
        )
    return penalty


def _repeated_alignment_penalty(nodes: tuple[TinyNode, ...], by_id: dict[str, Point]) -> int:
    penalty = 0
    roles = sorted({node.repeated_role for node in nodes if node.repeated_role is not None})
    for role in roles:
        role_nodes = [node for node in nodes if node.repeated_role == role]
        if len(role_nodes) < 2:
            continue
        ys = [by_id[node.node_id][1] for node in role_nodes]
        penalty += max(ys) - min(ys)
    return penalty


def _nondominated(candidates: list[TinyPlacementScore]) -> tuple[TinyPlacementScore, ...]:
    output: list[TinyPlacementScore] = []
    for candidate in candidates:
        if any(_dominates(other.score_vector, candidate.score_vector) for other in candidates):
            continue
        output.append(candidate)
    return tuple(sorted(output, key=lambda item: (item.score_vector, item.candidate_id)))


def _dominates(first: ScoreVector, second: ScoreVector) -> bool:
    return all(left <= right for left, right in zip(first, second, strict=True)) and any(
        left < right for left, right in zip(first, second, strict=True)
    )


def _permutation_count(total: int, selected: int) -> int:
    count = 1
    for value in range(total, total - selected, -1):
        count *= value
    return count


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
