"""Independent interface-side and primary-flow composition observer.

The observer consumes semantic roles, directed primary-flow edges, and emitted
symbol/interface positions.  It deliberately avoids case IDs, refdes/net names,
production placement scores, and candidate rankings.
"""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[int, int]


@dataclass(frozen=True)
class CompositionNode:
    node_id: str
    role: str
    center: Point
    direction: str | None = None
    frontier: str | None = None
    stage_rank: int | None = None
    supply_group_id: str | None = None


@dataclass(frozen=True)
class CompositionEdge:
    source_id: str
    target_id: str
    role: str = "signal"


@dataclass(frozen=True)
class InterfaceSidePenalty:
    interface_id: str
    expected_frontier: str
    actual_frontier: str | None
    direction: str
    penalty: int


@dataclass(frozen=True)
class SupplyInterfacePenalty:
    interface_id: str
    nearest_supply_id: str | None
    distance: int | None
    penalty: int


@dataclass(frozen=True)
class StageOrderViolation:
    source_id: str
    target_id: str
    source_x: int
    target_x: int
    reversal_distance: int


@dataclass(frozen=True)
class PrimaryFlowMetrics:
    interface_side_penalties: tuple[InterfaceSidePenalty, ...]
    supply_interface_penalties: tuple[SupplyInterfacePenalty, ...]
    stage_order_violations: tuple[StageOrderViolation, ...]
    primary_flow_backtracking_distance: int


def measure_interface_side_composition(
    nodes: tuple[CompositionNode, ...],
    edges: tuple[CompositionEdge, ...] = (),
    *,
    supply_locality_limit: int = 30,
) -> PrimaryFlowMetrics:
    """Measure interface-side and primary-flow readability from semantic evidence."""
    by_id = {node.node_id: node for node in nodes}
    side_penalties = _interface_side_penalties(nodes)
    supply_penalties = _supply_interface_penalties(nodes, supply_locality_limit)
    order_violations = _stage_order_violations(by_id, edges)
    return PrimaryFlowMetrics(
        interface_side_penalties=side_penalties,
        supply_interface_penalties=supply_penalties,
        stage_order_violations=order_violations,
        primary_flow_backtracking_distance=sum(
            violation.reversal_distance for violation in order_violations
        ),
    )


def _interface_side_penalties(
    nodes: tuple[CompositionNode, ...],
) -> tuple[InterfaceSidePenalty, ...]:
    penalties: list[InterfaceSidePenalty] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        if node.role != "interface":
            continue
        expected = _expected_frontier(node)
        if expected is None:
            continue
        if node.frontier != expected:
            penalties.append(
                InterfaceSidePenalty(
                    node.node_id,
                    expected,
                    node.frontier,
                    node.direction or "unknown",
                    1,
                )
            )
    return tuple(penalties)


def _expected_frontier(node: CompositionNode) -> str | None:
    if node.direction == "input":
        return "left"
    if node.direction == "output":
        return "right"
    if node.direction == "power_input":
        return None
    if node.direction in {"bidirectional", "undirected", None}:
        return None
    return None


def _supply_interface_penalties(
    nodes: tuple[CompositionNode, ...], locality_limit: int
) -> tuple[SupplyInterfacePenalty, ...]:
    supply_nodes = tuple(
        node
        for node in nodes
        if node.role in {"supply", "reference"} or node.supply_group_id is not None
    )
    witnesses: list[SupplyInterfacePenalty] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        if node.role != "interface" or node.direction != "power_input":
            continue
        supply = _nearest_supply(node, supply_nodes)
        distance = None if supply is None else _manhattan(node.center, supply.center)
        if distance is None or distance > locality_limit:
            witnesses.append(
                SupplyInterfacePenalty(
                    node.node_id,
                    None if supply is None else supply.node_id,
                    distance,
                    1,
                )
            )
    return tuple(witnesses)


def _nearest_supply(
    node: CompositionNode, supply_nodes: tuple[CompositionNode, ...]
) -> CompositionNode | None:
    candidates = [
        supply
        for supply in supply_nodes
        if supply.node_id != node.node_id
        and (
            node.supply_group_id is None
            or supply.supply_group_id is None
            or node.supply_group_id == supply.supply_group_id
        )
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (_manhattan(node.center, item.center), item.node_id))


def _stage_order_violations(
    by_id: dict[str, CompositionNode], edges: tuple[CompositionEdge, ...]
) -> tuple[StageOrderViolation, ...]:
    violations: list[StageOrderViolation] = []
    for edge in sorted(edges, key=lambda item: (item.source_id, item.target_id, item.role)):
        if edge.role != "primary_signal":
            continue
        source = by_id.get(edge.source_id)
        target = by_id.get(edge.target_id)
        if source is None or target is None:
            continue
        if not _is_ordered_primary_pair(source, target):
            continue
        if target.center[0] < source.center[0]:
            violations.append(
                StageOrderViolation(
                    source.node_id,
                    target.node_id,
                    source.center[0],
                    target.center[0],
                    source.center[0] - target.center[0],
                )
            )
    return tuple(violations)


def _is_ordered_primary_pair(source: CompositionNode, target: CompositionNode) -> bool:
    if source.stage_rank is None or target.stage_rank is None:
        return False
    return source.stage_rank < target.stage_rank


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
