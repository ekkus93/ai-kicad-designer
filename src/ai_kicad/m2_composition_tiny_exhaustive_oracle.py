"""Independent bounded exhaustive oracle for tiny schematic composition graphs.

This module intentionally does not import the production placer or its scoring
function. It enumerates distinct grid placements and checks semantic relations
directly, so small counterexamples can falsify production ranking decisions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import permutations
from math import perm


@dataclass(frozen=True)
class TinyNode:
    id: str
    role: str = "stage"  # stage, input, output, support, shared, bidirectional


@dataclass(frozen=True)
class TinyEdge:
    source: str
    target: str
    kind: str = "signal"  # signal, branch, feedback, support, power, reference


@dataclass(frozen=True)
class TinyOracleResult:
    best_score: tuple[int, ...]
    best_placements: tuple[tuple[tuple[str, tuple[int, int]], ...], ...]
    pareto_scores: tuple[tuple[int, ...], ...]
    evaluated: int
    legal: int


def tiny_composition_metrics(
    nodes: Sequence[TinyNode],
    edges: Sequence[TinyEdge],
    positions: Mapping[str, tuple[int, int]],
) -> tuple[int, int, int, int, int, int, int]:
    """Compute independent side, reversal, ownership and compactness witnesses."""
    roles = {node.id: node.role for node in nodes}
    if len(roles) != len(nodes) or set(positions) != set(roles):
        raise ValueError("node inventory and placement must match uniquely")
    if len(set(positions.values())) != len(positions):
        raise ValueError("tiny oracle requires non-overlapping grid cells")
    if any(edge.source not in roles or edge.target not in roles for edge in edges):
        raise ValueError("edge references an unknown node")

    side = reversal_count = reversal_distance = owner_distance = support = 0
    for edge in edges:
        sx, sy = positions[edge.source]
        tx, ty = positions[edge.target]
        distance = abs(sx - tx) + abs(sy - ty)
        if edge.kind in {"signal", "branch"}:
            backward = max(0, sx - tx)
            reversal_count += int(backward > 0)
            reversal_distance += backward
            if roles[edge.source] == "input":
                side += backward
                owner_distance += distance
            if roles[edge.target] == "output":
                side += backward
                owner_distance += distance
        elif edge.kind == "support":
            support += distance
        # Feedback and shared power/reference/return do not impose forward order.
    xs = [point[0] for point in positions.values()]
    ys = [point[1] for point in positions.values()]
    width = max(xs) - min(xs) + 1
    height = max(ys) - min(ys) + 1
    return (
        side,
        reversal_count,
        reversal_distance,
        owner_distance,
        support,
        width * height,
        width + height,
    )


def _dominates(left: tuple[int, ...], right: tuple[int, ...]) -> bool:
    return all(a <= b for a, b in zip(left, right, strict=True)) and any(
        a < b for a, b in zip(left, right, strict=True)
    )


def exhaustive_tiny_composition(
    nodes: Sequence[TinyNode],
    edges: Sequence[TinyEdge],
    slots: Sequence[tuple[int, int]],
    *,
    hard_gate: Callable[[Mapping[str, tuple[int, int]]], bool] | None = None,
    max_enumerations: int = 100_000,
) -> TinyOracleResult:
    """Exhaustively enumerate bounded distinct placements, with no solver.

    The optional hard gate models immutable constraints. It is evaluated before
    aesthetic ranking and cannot be compensated by any score improvement.
    """
    ordered = tuple(sorted(nodes, key=lambda node: node.id))
    unique_slots = tuple(sorted(set(slots)))
    if not ordered or len(ordered) > 6 or len(unique_slots) < len(ordered):
        raise ValueError("tiny oracle needs 1..6 nodes and enough unique slots")
    if len({node.id for node in ordered}) != len(ordered):
        raise ValueError("duplicate node ID")
    evaluated = perm(len(unique_slots), len(ordered))
    if evaluated > max_enumerations:
        raise ValueError("tiny exhaustive enumeration exceeds fixed budget")
    best_score: tuple[int, ...] | None = None
    best: list[tuple[tuple[str, tuple[int, int]], ...]] = []
    pareto: set[tuple[int, ...]] = set()
    legal = 0
    for assignment in permutations(unique_slots, len(ordered)):
        placement = {node.id: point for node, point in zip(ordered, assignment, strict=True)}
        if hard_gate is not None and not hard_gate(placement):
            continue
        legal += 1
        score = tiny_composition_metrics(ordered, edges, placement)
        if best_score is None or score < best_score:
            best_score = score
            best = [tuple(sorted(placement.items()))]
        elif score == best_score:
            best.append(tuple(sorted(placement.items())))
        if not any(_dominates(existing, score) for existing in pareto):
            pareto = {existing for existing in pareto if not _dominates(score, existing)}
            pareto.add(score)
    if best_score is None:
        raise ValueError("no placement satisfies the independent hard gate")
    return TinyOracleResult(
        best_score,
        tuple(sorted(best)),
        tuple(sorted(pareto)),
        evaluated,
        legal,
    )
