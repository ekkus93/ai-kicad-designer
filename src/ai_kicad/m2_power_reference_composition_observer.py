"""Independent power/reference composition observer for M2h2 readability.

The observer consumes semantic roles plus emitted positions.  It intentionally
stays independent of production layout scores and fixture names.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

Point = tuple[int, int]


@dataclass(frozen=True)
class PowerReferenceNode:
    node_id: str
    role: str
    center: Point
    owner_id: str | None = None
    source_id: str | None = None
    external: bool = False
    semantic_evidence: bool = True


@dataclass(frozen=True)
class PowerReferenceEdge:
    source_id: str
    consumer_id: str
    role: str


@dataclass(frozen=True)
class InfrastructureDispersion:
    role: str
    node_count: int
    span_x: int
    span_y: int
    manhattan_diameter: int


@dataclass(frozen=True)
class LocalSupportDistance:
    support_id: str
    owner_id: str
    role: str
    distance: int


@dataclass(frozen=True)
class ProducerCoherence:
    source_id: str
    role: str
    consumer_count: int
    distribution_span: int


@dataclass(frozen=True)
class PrimaryRowIntrusion:
    node_id: str
    role: str
    distance_to_primary_row: int


@dataclass(frozen=True)
class PowerReferenceCompositionMetrics:
    infrastructure_dispersion: tuple[InfrastructureDispersion, ...]
    local_support_distances: tuple[LocalSupportDistance, ...]
    producer_coherence: tuple[ProducerCoherence, ...]
    primary_row_intrusions: tuple[PrimaryRowIntrusion, ...]
    fake_external_references: tuple[str, ...]


def measure_power_reference_composition(
    nodes: tuple[PowerReferenceNode, ...],
    edges: tuple[PowerReferenceEdge, ...] = (),
    *,
    primary_row_y: int = 0,
    primary_row_tolerance: int = 10,
) -> PowerReferenceCompositionMetrics:
    """Measure supply/reference visual coherence from independent semantics."""
    by_id = {node.node_id: node for node in nodes}
    infrastructure = _infrastructure_dispersion(nodes)
    support = _local_support_distances(nodes, by_id)
    producer = _producer_coherence(edges, by_id)
    intrusion = _primary_row_intrusions(nodes, primary_row_y, primary_row_tolerance)
    fake_refs = tuple(
        sorted(
            node.node_id
            for node in nodes
            if node.role == "reference" and node.external and not node.semantic_evidence
        )
    )
    return PowerReferenceCompositionMetrics(
        infrastructure_dispersion=infrastructure,
        local_support_distances=support,
        producer_coherence=producer,
        primary_row_intrusions=intrusion,
        fake_external_references=fake_refs,
    )


def _infrastructure_dispersion(
    nodes: tuple[PowerReferenceNode, ...]
) -> tuple[InfrastructureDispersion, ...]:
    by_role: dict[str, list[PowerReferenceNode]] = defaultdict(list)
    for node in nodes:
        if node.role in {"supply", "reference", "power_interface"}:
            by_role[node.role].append(node)
    return tuple(_dispersion(role, tuple(items)) for role, items in sorted(by_role.items()))


def _dispersion(role: str, nodes: tuple[PowerReferenceNode, ...]) -> InfrastructureDispersion:
    xs = [node.center[0] for node in nodes]
    ys = [node.center[1] for node in nodes]
    diameter = max(
        (_manhattan(first.center, second.center) for first in nodes for second in nodes),
        default=0,
    )
    return InfrastructureDispersion(role, len(nodes), max(xs) - min(xs), max(ys) - min(ys), diameter)


def _local_support_distances(
    nodes: tuple[PowerReferenceNode, ...],
    by_id: dict[str, PowerReferenceNode],
) -> tuple[LocalSupportDistance, ...]:
    witnesses: list[LocalSupportDistance] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        if node.role != "decoupling" or node.owner_id is None:
            continue
        owner = by_id.get(node.owner_id)
        if owner is None:
            continue
        witnesses.append(
            LocalSupportDistance(
                node.node_id,
                owner.node_id,
                node.role,
                _manhattan(node.center, owner.center),
            )
        )
    return tuple(witnesses)


def _producer_coherence(
    edges: tuple[PowerReferenceEdge, ...],
    by_id: dict[str, PowerReferenceNode],
) -> tuple[ProducerCoherence, ...]:
    by_source_role: dict[tuple[str, str], list[PowerReferenceNode]] = defaultdict(list)
    for edge in edges:
        consumer = by_id.get(edge.consumer_id)
        if edge.role in {"supply", "reference"} and consumer is not None:
            by_source_role[(edge.source_id, edge.role)].append(consumer)
    witnesses: list[ProducerCoherence] = []
    for (source_id, role), consumers in sorted(by_source_role.items()):
        source = by_id.get(source_id)
        participants = ([source] if source is not None else []) + consumers
        diameter = max(
            (
                _manhattan(first.center, second.center)
                for first in participants
                for second in participants
            ),
            default=0,
        )
        witnesses.append(ProducerCoherence(source_id, role, len(consumers), diameter))
    return tuple(witnesses)


def _primary_row_intrusions(
    nodes: tuple[PowerReferenceNode, ...], row_y: int, tolerance: int
) -> tuple[PrimaryRowIntrusion, ...]:
    intrusions: list[PrimaryRowIntrusion] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        if node.role not in {"supply", "reference", "power_interface"}:
            continue
        distance = abs(node.center[1] - row_y)
        if distance <= tolerance:
            intrusions.append(PrimaryRowIntrusion(node.node_id, node.role, distance))
    return tuple(intrusions)


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
