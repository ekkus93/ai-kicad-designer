"""Independent semantic-flow observer for M2h2 composition evidence.

This module deliberately consumes semantic plans and externally supplied block
positions instead of production placement scores. It is the first small slice of
the human-readable composition observer: it reconstructs semantic flow roles,
preserves incomparable siblings, excludes feedback from forward-flow ordering,
and emits exact witnesses for left-to-right stage-order violations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from .m2_semantics import EdgeKind, PortRole, SemanticEdge, SemanticPlan

CompositionRole = Literal["signal", "support", "power", "reference", "return", "interface"]

PRIMARY_FORWARD_KINDS: frozenset[EdgeKind] = frozenset({"signal", "branch"})
ROLE_BY_EDGE_KIND: dict[EdgeKind, CompositionRole] = {
    "signal": "signal",
    "branch": "signal",
    "feedback": "return",
    "support": "support",
    "package": "support",
    "power": "power",
    "reference": "reference",
}
ROLE_BY_PORT_ROLE: dict[PortRole, CompositionRole] = {
    "signal_in": "interface",
    "signal_out": "interface",
    "power_in": "power",
    "power_out": "power",
    "reference": "reference",
    "passive": "support",
}


@dataclass(frozen=True)
class FlowEdge:
    kind: EdgeKind
    role: CompositionRole
    source: str
    target: str
    net: str
    origins: tuple[str, ...]


@dataclass(frozen=True)
class PortRoleWitness:
    block: str
    port: str
    net: str
    port_role: PortRole
    composition_role: CompositionRole
    terminals: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SemanticFlowGraph:
    nodes: tuple[str, ...]
    edges: tuple[FlowEdge, ...]
    port_roles: tuple[PortRoleWitness, ...]


@dataclass(frozen=True)
class StageOrderWitness:
    source: str
    target: str
    kind: EdgeKind
    net: str
    source_x: int
    target_x: int
    minimum_x_separation: int
    reversal_distance: int
    origins: tuple[str, ...]


def reconstruct_semantic_flow(plan: SemanticPlan) -> SemanticFlowGraph:
    """Reconstruct composition flow roles without consulting placement state."""
    nodes = {block.id for block in plan.blocks}
    edges: list[FlowEdge] = []
    for edge in plan.edges:
        nodes.add(edge.source)
        nodes.add(edge.target)
        edges.append(_flow_edge(edge))

    port_roles: list[PortRoleWitness] = []
    for block in plan.blocks:
        for port in block.ports:
            port_roles.append(
                PortRoleWitness(
                    block=block.id,
                    port=port.id,
                    net=port.net,
                    port_role=port.role,
                    composition_role=ROLE_BY_PORT_ROLE[port.role],
                    terminals=port.terminals,
                )
            )

    return SemanticFlowGraph(
        nodes=tuple(sorted(nodes)),
        edges=tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.kind, edge.net))),
        port_roles=tuple(sorted(port_roles, key=lambda role: (role.block, role.port, role.net))),
    )


def primary_precedence_pairs(graph: SemanticFlowGraph) -> tuple[tuple[str, str], ...]:
    """Return transitive forward-flow precedence while preserving sibling incomparability."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.kind in PRIMARY_FORWARD_KINDS and edge.source != edge.target:
            adjacency[edge.source].add(edge.target)

    pairs: set[tuple[str, str]] = set()
    for start in graph.nodes:
        pending = list(sorted(adjacency.get(start, ())))
        seen: set[str] = set()
        while pending:
            target = pending.pop(0)
            if target in seen:
                continue
            seen.add(target)
            pairs.add((start, target))
            for next_target in sorted(adjacency.get(target, ())):
                if next_target != start:
                    pending.append(next_target)
    return tuple(sorted(pairs))


def stage_order_witnesses(
    graph: SemanticFlowGraph,
    x_by_block: dict[str, int],
    *,
    minimum_x_separation: int = 1,
) -> tuple[StageOrderWitness, ...]:
    """Emit exact direct-edge witnesses for forward-flow x-order violations."""
    witnesses: list[StageOrderWitness] = []
    for edge in graph.edges:
        if edge.kind not in PRIMARY_FORWARD_KINDS:
            continue
        if edge.source not in x_by_block or edge.target not in x_by_block:
            continue
        source_x = x_by_block[edge.source]
        target_x = x_by_block[edge.target]
        actual = target_x - source_x
        if actual < minimum_x_separation:
            witnesses.append(
                StageOrderWitness(
                    source=edge.source,
                    target=edge.target,
                    kind=edge.kind,
                    net=edge.net,
                    source_x=source_x,
                    target_x=target_x,
                    minimum_x_separation=minimum_x_separation,
                    reversal_distance=minimum_x_separation - actual,
                    origins=edge.origins,
                )
            )
    return tuple(witnesses)


def cumulative_primary_flow_reversal_distance(witnesses: tuple[StageOrderWitness, ...]) -> int:
    return sum(witness.reversal_distance for witness in witnesses)


def final_signal_output_blocks(graph: SemanticFlowGraph) -> tuple[str, ...]:
    """Return blocks exposing signal outputs that do not feed another forward block."""
    forward_sources = {
        edge.source
        for edge in graph.edges
        if edge.kind in PRIMARY_FORWARD_KINDS and edge.source != edge.target
    }
    outputs = {
        role.block
        for role in graph.port_roles
        if role.port_role == "signal_out" and role.block not in forward_sources
    }
    return tuple(sorted(outputs))


def _flow_edge(edge: SemanticEdge) -> FlowEdge:
    return FlowEdge(
        kind=edge.kind,
        role=ROLE_BY_EDGE_KIND[edge.kind],
        source=edge.source,
        target=edge.target,
        net=edge.net,
        origins=tuple(sorted(edge.origins)),
    )
