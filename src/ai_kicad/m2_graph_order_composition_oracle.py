"""Independent graph-order oracle for M2h2 composition evidence.

The oracle reconstructs directed signal precedence from semantic edges, while
keeping feedback, power, reference, return, and support relationships out of the
forward primary-flow ordering relation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

Point = tuple[int, int]

FORWARD_SIGNAL_ROLES = frozenset({"signal", "primary", "interface_signal"})
NON_FORWARD_ROLES = frozenset({"feedback", "power", "reference", "return", "support"})


@dataclass(frozen=True)
class OrderNode:
    node_id: str
    role: str
    center: Point


@dataclass(frozen=True)
class OrderEdge:
    source_id: str
    target_id: str
    role: str


@dataclass(frozen=True)
class StageOrderViolation:
    source_id: str
    target_id: str
    role: str
    reversal_distance: int


@dataclass(frozen=True)
class GraphOrderMetrics:
    ordered_pairs: tuple[tuple[str, str], ...]
    incomparable_pairs: tuple[tuple[str, str], ...]
    violations: tuple[StageOrderViolation, ...]
    cumulative_reversal_distance: int
    ignored_non_forward_edges: tuple[OrderEdge, ...]


def evaluate_graph_order(
    nodes: tuple[OrderNode, ...],
    edges: tuple[OrderEdge, ...],
    *,
    reversal_tolerance: int = 0,
) -> GraphOrderMetrics:
    """Evaluate left-to-right order for semantic signal precedence only."""
    by_id = {node.node_id: node for node in nodes}
    forward_edges = tuple(edge for edge in edges if edge.role in FORWARD_SIGNAL_ROLES)
    ignored_edges = tuple(sorted((edge for edge in edges if edge.role in NON_FORWARD_ROLES), key=_edge_key))
    reachability = _transitive_forward_pairs(forward_edges, by_id)
    ordered_pairs = tuple(sorted(reachability))
    incomparable = _incomparable_signal_pairs(nodes, reachability)
    violations = _violations(forward_edges, by_id, reversal_tolerance)
    return GraphOrderMetrics(
        ordered_pairs=ordered_pairs,
        incomparable_pairs=incomparable,
        violations=violations,
        cumulative_reversal_distance=sum(item.reversal_distance for item in violations),
        ignored_non_forward_edges=ignored_edges,
    )


def _transitive_forward_pairs(
    edges: tuple[OrderEdge, ...], by_id: dict[str, OrderNode]
) -> set[tuple[str, str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.source_id in by_id and edge.target_id in by_id:
            adjacency[edge.source_id].append(edge.target_id)

    pairs: set[tuple[str, str]] = set()
    for source_id in sorted(by_id):
        queue: deque[str] = deque(sorted(adjacency[source_id]))
        seen: set[str] = set()
        while queue:
            target_id = queue.popleft()
            if target_id in seen:
                continue
            seen.add(target_id)
            pairs.add((source_id, target_id))
            queue.extend(sorted(adjacency[target_id]))
    return pairs


def _incomparable_signal_pairs(
    nodes: tuple[OrderNode, ...], reachability: set[tuple[str, str]]
) -> tuple[tuple[str, str], ...]:
    signal_ids = sorted(node.node_id for node in nodes if node.role == "signal")
    pairs: list[tuple[str, str]] = []
    for index, first in enumerate(signal_ids):
        for second in signal_ids[index + 1 :]:
            if (first, second) not in reachability and (second, first) not in reachability:
                pairs.append((first, second))
    return tuple(pairs)


def _violations(
    edges: tuple[OrderEdge, ...],
    by_id: dict[str, OrderNode],
    reversal_tolerance: int,
) -> tuple[StageOrderViolation, ...]:
    witnesses: list[StageOrderViolation] = []
    for edge in sorted(edges, key=_edge_key):
        source = by_id.get(edge.source_id)
        target = by_id.get(edge.target_id)
        if source is None or target is None:
            continue
        reversal = source.center[0] - target.center[0]
        if reversal > reversal_tolerance:
            witnesses.append(
                StageOrderViolation(edge.source_id, edge.target_id, edge.role, reversal)
            )
    return tuple(witnesses)


def _edge_key(edge: OrderEdge) -> tuple[str, str, str]:
    return (edge.source_id, edge.target_id, edge.role)
