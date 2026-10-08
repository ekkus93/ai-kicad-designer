"""Independent functional-block composition observer."""

from __future__ import annotations
from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class Node:
    key: str
    x: float
    y: float
    role: str = "signal"


@dataclass(frozen=True)
class Edge:
    a: str
    b: str
    role: str = "signal"


@dataclass(frozen=True)
class Ownership:
    member: str
    owners: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class Metrics:
    blocks: tuple[tuple[str, ...], ...]
    block_dispersion: tuple[float, ...]
    ownership_distance: tuple[tuple[str, float], ...]
    feedback_span: float


_SHARED = frozenset({"power", "reference", "return", "shared"})
_LOCAL_EDGE = frozenset({"signal", "feedback", "support", "package_local"})


def observe(
    nodes: tuple[Node, ...], edges: tuple[Edge, ...], ownership: tuple[Ownership, ...] = ()
) -> Metrics:
    by_key = {node.key: node for node in nodes}
    local = {node.key for node in nodes if node.role not in _SHARED}
    adjacency = {key: set() for key in local}
    for edge in edges:
        if edge.role in _LOCAL_EDGE and edge.a in local and edge.b in local:
            adjacency[edge.a].add(edge.b)
            adjacency[edge.b].add(edge.a)
    blocks = _components(adjacency)
    dispersion = tuple(_dispersion(block, by_key) for block in blocks)
    owner_distance = []
    for item in sorted(ownership, key=lambda value: value.member):
        owner_nodes = [by_key[key] for key in item.owners if key in by_key]
        distance = min(
            (_distance(by_key[item.member], owner) for owner in owner_nodes), default=float("inf")
        )
        owner_distance.append((item.member, distance))
    feedback_span = sum(_distance(by_key[e.a], by_key[e.b]) for e in edges if e.role == "feedback")
    return Metrics(blocks, dispersion, tuple(owner_distance), feedback_span)


def _components(adjacency: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
    remaining = set(adjacency)
    result = []
    while remaining:
        stack = [min(remaining)]
        seen = set()
        while stack:
            key = stack.pop()
            if key in seen:
                continue
            seen.add(key)
            stack.extend(adjacency[key] - seen)
        remaining -= seen
        result.append(tuple(sorted(seen)))
    return tuple(sorted(result))


def _dispersion(block: tuple[str, ...], by_key: dict[str, Node]) -> float:
    points = [by_key[key] for key in block]
    return max(
        (_distance(a, b) for i, a in enumerate(points) for b in points[i + 1 :]), default=0.0
    )


def _distance(a: Node, b: Node) -> float:
    return hypot(a.x - b.x, a.y - b.y)
