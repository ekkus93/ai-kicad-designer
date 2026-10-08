"""Independent tiny-grid composition oracle for M2h2 readability evidence."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Literal

Point = tuple[int, int]
Role = Literal["input", "output", "stage", "support", "power", "reference"]


@dataclass(frozen=True)
class TinyNode:
    id: str
    role: Role
    owner: str | None = None


@dataclass(frozen=True)
class TinyEdge:
    source: str
    target: str
    kind: Literal["signal", "support", "power", "reference", "feedback"] = "signal"


@dataclass(frozen=True)
class TinyPlacement:
    positions: tuple[tuple[str, Point], ...]
    score: tuple[int, int, int, int, int]
    witnesses: tuple[str, ...]


def exhaustive_tiny_grid_oracle(
    nodes: tuple[TinyNode, ...],
    edges: tuple[TinyEdge, ...],
    *,
    width: int,
    height: int,
    max_candidates: int = 12,
) -> tuple[TinyPlacement, ...]:
    """Enumerate legal tiny placements and return non-dominated readable candidates.

    The score is lexicographic: interface side, signal order, grouping, repeated-row
    consistency, then compactness. This oracle is intentionally small and exact;
    production search may not use it as a coordinate lookup table.
    """
    if width <= 0 or height <= 0:
        raise ValueError("tiny grid dimensions must be positive")
    if len(nodes) > width * height:
        raise ValueError("tiny grid cannot hold all nodes")

    grid = tuple((x, y) for y in range(height) for x in range(width))
    scored: list[TinyPlacement] = []
    for chosen in permutations(grid, len(nodes)):
        positions = dict(zip((node.id for node in nodes), chosen, strict=True))
        score, witnesses = _score(nodes, edges, positions, width)
        scored.append(
            TinyPlacement(
                positions=tuple(sorted(positions.items())),
                score=score,
                witnesses=witnesses,
            )
        )
    scored.sort(key=lambda candidate: (candidate.score, candidate.positions))
    return tuple(_non_dominated(scored)[:max_candidates])


def production_dominated_by_oracle(
    production_score: tuple[int, int, int, int, int],
    oracle_candidates: tuple[TinyPlacement, ...],
) -> bool:
    """Return true when an exact oracle candidate strictly beats production."""
    return any(candidate.score < production_score for candidate in oracle_candidates)


def _score(
    nodes: tuple[TinyNode, ...],
    edges: tuple[TinyEdge, ...],
    positions: dict[str, Point],
    width: int,
) -> tuple[tuple[int, int, int, int, int], tuple[str, ...]]:
    witnesses: list[str] = []
    interface_penalty = _interface_side_penalty(nodes, positions, width, witnesses)
    order_penalty = _signal_order_penalty(edges, positions, witnesses)
    grouping_penalty = _grouping_penalty(nodes, positions, witnesses)
    row_penalty = _repeated_row_penalty(nodes, positions, witnesses)
    compactness_penalty = _compactness_penalty(tuple(positions.values()))
    return (
        interface_penalty,
        order_penalty,
        grouping_penalty,
        row_penalty,
        compactness_penalty,
    ), tuple(witnesses)


def _interface_side_penalty(
    nodes: tuple[TinyNode, ...], positions: dict[str, Point], width: int, witnesses: list[str]
) -> int:
    penalty = 0
    for node in nodes:
        x = positions[node.id][0]
        if node.role == "input" and x != 0:
            penalty += x
            witnesses.append(f"input-side:{node.id}:x={x}")
        if node.role == "output" and x != width - 1:
            distance = width - 1 - x
            penalty += distance
            witnesses.append(f"output-side:{node.id}:distance={distance}")
    return penalty


def _signal_order_penalty(
    edges: tuple[TinyEdge, ...], positions: dict[str, Point], witnesses: list[str]
) -> int:
    penalty = 0
    for edge in edges:
        if edge.kind != "signal":
            continue
        delta = positions[edge.target][0] - positions[edge.source][0]
        if delta < 0:
            penalty += abs(delta)
            witnesses.append(f"signal-reversal:{edge.source}->{edge.target}:dx={delta}")
    return penalty


def _grouping_penalty(
    nodes: tuple[TinyNode, ...], positions: dict[str, Point], witnesses: list[str]
) -> int:
    by_owner: dict[str, list[str]] = {}
    for node in nodes:
        if node.owner is not None:
            by_owner.setdefault(node.owner, []).append(node.id)
    penalty = 0
    for owner, owned_nodes in by_owner.items():
        owner_position = positions.get(owner)
        if owner_position is None:
            continue
        for node_id in owned_nodes:
            distance = _manhattan(owner_position, positions[node_id])
            penalty += distance
            if distance > 1:
                witnesses.append(f"owner-distance:{node_id}->{owner}:distance={distance}")
    return penalty


def _repeated_row_penalty(
    nodes: tuple[TinyNode, ...], positions: dict[str, Point], witnesses: list[str]
) -> int:
    rows_by_role: dict[tuple[Role, str], list[int]] = {}
    for node in nodes:
        if node.role in {"stage", "support"} and node.owner is not None:
            rows_by_role.setdefault((node.role, node.owner), []).append(positions[node.id][1])
    penalty = 0
    for role, rows in rows_by_role.items():
        if len(rows) < 2:
            continue
        spread = max(rows) - min(rows)
        penalty += spread
        if spread:
            witnesses.append(f"row-variance:{role[0]}:{role[1]}:spread={spread}")
    return penalty


def _compactness_penalty(points: tuple[Point, ...]) -> int:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _non_dominated(scored: list[TinyPlacement]) -> list[TinyPlacement]:
    non_dominated: list[TinyPlacement] = []
    for candidate in scored:
        if not any(other.score < candidate.score for other in non_dominated):
            non_dominated.append(candidate)
    return non_dominated


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
