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
class TinyBranch:
    source_id: str
    target_ids: tuple[str, ...]


@dataclass(frozen=True)
class TinyPlacementScore:
    candidate_id: str
    node_positions: tuple[tuple[str, Point], ...]
    score_vector: ScoreVector
    branch_geometry_penalty: int = 0


@dataclass(frozen=True)
class TinyOracleEvidence:
    candidate_count: int
    nondominated_candidates: tuple[TinyPlacementScore, ...]
    production_candidate: TinyPlacementScore | None
    production_is_dominated: bool
    dominating_candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class TinySearchBudgetEvidence:
    """Witness that a bounded search did not encounter a better legal candidate."""

    oracle: TinyOracleEvidence
    attempted_count: int
    search_budget: int
    budget_exhausted: bool
    unvisited_optimal_candidate_ids: tuple[str, ...]


def exhaustive_tiny_grid_oracle(
    nodes: tuple[TinyNode, ...],
    grid_points: tuple[Point, ...],
    *,
    branches: tuple[TinyBranch, ...] = (),
    production_positions: tuple[tuple[str, Point], ...] | None = None,
    max_candidates: int = 5040,
) -> TinyOracleEvidence:
    """Enumerate bounded placements and report non-dominated legal candidates."""
    if not nodes:
        raise ValueError("tiny-grid oracle requires at least one node")
    node_ids = tuple(node.node_id for node in nodes)
    if len(set(node_ids)) != len(node_ids):
        raise ValueError("duplicate tiny-grid node id")
    if len(set(grid_points)) != len(grid_points):
        raise ValueError("duplicate grid point")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if any(node.side_preference not in (None, "left", "right") for node in nodes):
        raise ValueError("unknown side preference")
    if len(nodes) > len(grid_points):
        raise ValueError("grid must have at least one point per node")
    _validate_branches(branches, set(node_ids))
    candidate_count = _permutation_count(len(grid_points), len(nodes))
    if candidate_count > max_candidates:
        raise ValueError("tiny-grid oracle candidate bound exceeded")

    node_order = tuple(sorted(nodes, key=lambda item: item.node_id))
    scored: list[TinyPlacementScore] = []
    for index, placement_points in enumerate(permutations(sorted(grid_points), len(node_order))):
        positions = tuple(
            sorted(
                (
                    (node.node_id, placement_point)
                    for node, placement_point in zip(node_order, placement_points, strict=True)
                ),
                key=lambda item: item[0],
            )
        )
        score_vector, branch_penalty = _score_positions(node_order, positions, branches)
        scored.append(
            TinyPlacementScore(
                f"oracle_{index:04d}",
                positions,
                score_vector,
                branch_penalty,
            )
        )

    nondominated = _nondominated(scored)
    production = None
    dominated = False
    dominating_ids: tuple[str, ...] = ()
    if production_positions is not None:
        if sorted(node_id for node_id, _ in production_positions) != sorted(node_ids):
            raise ValueError("production positions must match node IDs exactly")
        used_points = tuple(point for _, point in production_positions)
        if len(set(used_points)) != len(used_points) or not set(used_points) <= set(grid_points):
            raise ValueError("production positions must use distinct legal grid points")
        normalized = tuple(sorted(production_positions, key=lambda item: item[0]))
        production_score, branch_penalty = _score_positions(node_order, normalized, branches)
        production = TinyPlacementScore(
            "production",
            normalized,
            production_score,
            branch_penalty,
        )
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


def verify_tiny_search_budget_witness(
    nodes: tuple[TinyNode, ...],
    grid_points: tuple[Point, ...],
    *,
    production_positions: tuple[tuple[str, Point], ...],
    attempted_placements: tuple[tuple[tuple[str, Point], ...], ...],
    search_budget: int,
    branches: tuple[TinyBranch, ...] = (),
    max_candidates: int = 5040,
) -> TinySearchBudgetEvidence:
    """Validate bounded-search provenance against the independent exhaustive oracle.

    A dominated production result is permitted only when an exhausted budget
    excludes every strictly superior candidate. All attempted legal placements
    must be disclosed, and production must be the best scored attempt.
    """
    oracle = exhaustive_tiny_grid_oracle(
        nodes,
        grid_points,
        branches=branches,
        production_positions=production_positions,
        max_candidates=max_candidates,
    )
    if search_budget < 1 or len(attempted_placements) > search_budget:
        raise ValueError("tiny search witness has invalid attempt budget")
    if not attempted_placements:
        raise ValueError("tiny search witness requires recorded attempts")

    node_ids = {node.node_id for node in nodes}
    available = set(grid_points)
    normalized_attempts: set[tuple[tuple[str, Point], ...]] = set()
    ordered_nodes = tuple(sorted(nodes, key=lambda node: node.node_id))
    for placement in attempted_placements:
        ids = [node_id for node_id, _point in placement]
        points = [point for _node_id, point in placement]
        if set(ids) != node_ids or len(ids) != len(nodes):
            raise ValueError("tiny search witness has invalid attempted node IDs")
        if len(set(points)) != len(points) or not set(points) <= available:
            raise ValueError("tiny search witness has illegal attempted grid positions")
        normalized = tuple(sorted(placement, key=lambda item: item[0]))
        if normalized in normalized_attempts:
            raise ValueError("tiny search witness repeats an attempted placement")
        normalized_attempts.add(normalized)

    production = oracle.production_candidate
    assert production is not None
    if production.node_positions not in normalized_attempts:
        raise ValueError("tiny search witness omits production placement")

    for placement in normalized_attempts:
        score, _branch_penalty = _score_positions(ordered_nodes, placement, branches)
        if score < production.score_vector:
            raise ValueError("tiny search witness skipped a better attempted candidate")

    exhausted = len(attempted_placements) == search_budget
    if oracle.production_is_dominated and (
        not exhausted or search_budget >= oracle.candidate_count
    ):
        raise ValueError("dominated tiny production requires exhausted restrictive budget")
    unvisited = tuple(
        candidate.candidate_id
        for candidate in oracle.nondominated_candidates
        if candidate.node_positions not in normalized_attempts
    )
    if oracle.production_is_dominated and not unvisited:
        raise ValueError("dominated tiny production already visited an oracle optimum")
    return TinySearchBudgetEvidence(
        oracle=oracle,
        attempted_count=len(attempted_placements),
        search_budget=search_budget,
        budget_exhausted=exhausted,
        unvisited_optimal_candidate_ids=unvisited,
    )


def _score_positions(
    nodes: tuple[TinyNode, ...],
    positions: tuple[tuple[str, Point], ...],
    branches: tuple[TinyBranch, ...],
) -> tuple[ScoreVector, int]:
    by_id = dict(positions)
    xs = [point[0] for point in by_id.values()]
    ys = [point[1] for point in by_id.values()]
    min_x = min(xs)
    max_x = max(xs)
    side_penalty = _side_penalty(nodes, by_id, min_x, max_x)
    stage_penalty = _stage_order_penalty(nodes, by_id)
    grouping_penalty = _grouping_penalty(nodes, by_id)
    branch_penalty = _branch_geometry_penalty(branches, by_id)
    repeated_penalty = _repeated_alignment_penalty(nodes, by_id)
    whitespace_penalty = (max_x - min_x) * (max(ys) - min(ys))
    return (
        side_penalty,
        stage_penalty,
        grouping_penalty + branch_penalty,
        repeated_penalty,
        whitespace_penalty,
    ), branch_penalty


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
    penalty = 0
    channels = {node.channel_id for node in nodes}
    for channel in channels:
        staged = sorted(
            (node for node in nodes if node.stage_index is not None and node.channel_id == channel),
            key=lambda item: (item.stage_index, item.node_id),
        )
        for first, second in zip(staged, staged[1:]):
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
    # A repeated stage may use a shared row or a shared column. Penalize
    # off-axis drift in the better of those two legal visual grammars; never
    # require horizontal rows for a vertically composed repeated structure.
    penalty = 0
    roles = sorted({node.repeated_role for node in nodes if node.repeated_role is not None})
    for role in roles:
        role_nodes = [node for node in nodes if node.repeated_role == role]
        if len(role_nodes) < 2:
            continue
        xs = [by_id[node.node_id][0] for node in role_nodes]
        ys = [by_id[node.node_id][1] for node in role_nodes]
        penalty += min(max(xs) - min(xs), max(ys) - min(ys))
    return penalty


def _validate_branches(branches: tuple[TinyBranch, ...], node_ids: set[str]) -> None:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for branch in branches:
        if branch.source_id not in node_ids:
            raise ValueError("tiny branch source must match a node ID")
        if len(branch.target_ids) < 2 or len(set(branch.target_ids)) != len(branch.target_ids):
            raise ValueError("tiny branch requires at least two distinct targets")
        if branch.source_id in branch.target_ids or not set(branch.target_ids) <= node_ids:
            raise ValueError("tiny branch targets must be distinct existing non-source nodes")
        identity = (branch.source_id, tuple(sorted(branch.target_ids)))
        if identity in seen:
            raise ValueError("duplicate tiny branch")
        seen.add(identity)


def _branch_geometry_penalty(
    branches: tuple[TinyBranch, ...],
    by_id: dict[str, Point],
) -> int:
    """Prefer a centered source and consistent forward sibling depth."""
    penalty = 0
    for branch in branches:
        source = by_id[branch.source_id]
        targets = [by_id[target_id] for target_id in branch.target_ids]
        target_ys = [point[1] for point in targets]
        target_dx = [point[0] - source[0] for point in targets]
        vertical_midpoint = (min(target_ys) + max(target_ys)) // 2
        penalty += abs(source[1] - vertical_midpoint)
        penalty += max(target_dx) - min(target_dx)
        penalty += sum(max(0, -distance) for distance in target_dx)
    return penalty


def _nondominated(candidates: list[TinyPlacementScore]) -> tuple[TinyPlacementScore, ...]:
    # The governed objective is lexicographic, not a Pareto/weighted trade-off.
    best_score = min(candidate.score_vector for candidate in candidates)
    return tuple(
        sorted(
            (candidate for candidate in candidates if candidate.score_vector == best_score),
            key=lambda item: item.candidate_id,
        )
    )


def _dominates(first: ScoreVector, second: ScoreVector) -> bool:
    return first < second


def _permutation_count(total: int, selected: int) -> int:
    count = 1
    for value in range(total, total - selected, -1):
        count *= value
    return count


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
