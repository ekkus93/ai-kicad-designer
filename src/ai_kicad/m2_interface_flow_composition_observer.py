"""Interface-side and primary-flow observer for M2h2 composition evidence.

The observer consumes independently reconstructed interface roles, semantic stage
centers, and directed flow precedence. It emits deterministic witnesses for
human-readability defects without trusting production placement scores.
"""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[int, int]

SIGNAL_INPUT_ROLE = "signal_input"
SIGNAL_OUTPUT_ROLE = "signal_output"
POWER_INPUT_ROLE = "power_input"
BIDIRECTIONAL_ROLE = "bidirectional"
UNDIRECTED_ROLE = "undirected"
PRIMARY_FLOW_ROLE = "primary"
SIGNAL_FLOW_ROLE = "signal"


@dataclass(frozen=True)
class ExternalInterface:
    interface_id: str
    role: str
    center: Point
    owner_stage_id: str | None = None
    side_justification: str | None = None


@dataclass(frozen=True)
class FlowStage:
    stage_id: str
    center: Point


@dataclass(frozen=True)
class FlowPrecedence:
    before_stage_id: str
    after_stage_id: str
    role: str = PRIMARY_FLOW_ROLE


@dataclass(frozen=True)
class InterfaceSideViolation:
    interface_id: str
    expected_side: str
    owner_stage_id: str
    distance: int
    reason: str


@dataclass(frozen=True)
class PowerInterfaceDistance:
    interface_id: str
    owner_stage_id: str
    distance: int


@dataclass(frozen=True)
class StageOrderViolation:
    before_stage_id: str
    after_stage_id: str
    role: str
    reversal_distance: int


@dataclass(frozen=True)
class InterfaceFlowCompositionMetrics:
    interface_side_violations: tuple[InterfaceSideViolation, ...]
    justified_side_exemptions: tuple[str, ...]
    power_interface_distances: tuple[PowerInterfaceDistance, ...]
    stage_order_violations: tuple[StageOrderViolation, ...]
    primary_flow_backtracking_distance: int
    checked_precedence_count: int


def measure_interface_flow_composition(
    interfaces: tuple[ExternalInterface, ...],
    stages: tuple[FlowStage, ...],
    precedence: tuple[FlowPrecedence, ...],
) -> InterfaceFlowCompositionMetrics:
    """Measure interface-side and left-to-right flow readability.

    Only explicit precedence constraints are ordered. Sibling stages with no
    semantic order relation therefore remain incomparable and produce no order
    witness solely because their x-coordinates differ.
    """
    stage_by_id = {stage.stage_id: stage for stage in stages}
    side_violations = _interface_side_violations(interfaces, stage_by_id)
    stage_order_violations = _stage_order_violations(precedence, stage_by_id)
    return InterfaceFlowCompositionMetrics(
        interface_side_violations=side_violations,
        justified_side_exemptions=tuple(
            sorted(
                interface.interface_id
                for interface in interfaces
                if interface.side_justification is not None
            )
        ),
        power_interface_distances=_power_interface_distances(interfaces, stage_by_id),
        stage_order_violations=stage_order_violations,
        primary_flow_backtracking_distance=sum(
            violation.reversal_distance
            for violation in stage_order_violations
            if violation.role in {PRIMARY_FLOW_ROLE, SIGNAL_FLOW_ROLE}
        ),
        checked_precedence_count=sum(
            1
            for relation in precedence
            if relation.before_stage_id in stage_by_id and relation.after_stage_id in stage_by_id
        ),
    )


def _interface_side_violations(
    interfaces: tuple[ExternalInterface, ...], stage_by_id: dict[str, FlowStage]
) -> tuple[InterfaceSideViolation, ...]:
    violations: list[InterfaceSideViolation] = []
    for interface in sorted(interfaces, key=lambda item: item.interface_id):
        if interface.role in {BIDIRECTIONAL_ROLE, UNDIRECTED_ROLE, POWER_INPUT_ROLE}:
            continue
        if interface.side_justification is not None or interface.owner_stage_id is None:
            continue
        owner = stage_by_id.get(interface.owner_stage_id)
        if owner is None:
            continue
        if interface.role == SIGNAL_INPUT_ROLE and interface.center[0] > owner.center[0]:
            violations.append(
                InterfaceSideViolation(
                    interface_id=interface.interface_id,
                    expected_side="left",
                    owner_stage_id=owner.stage_id,
                    distance=interface.center[0] - owner.center[0],
                    reason="directed signal input is right of first consuming stage",
                )
            )
        if interface.role == SIGNAL_OUTPUT_ROLE and interface.center[0] < owner.center[0]:
            violations.append(
                InterfaceSideViolation(
                    interface_id=interface.interface_id,
                    expected_side="right",
                    owner_stage_id=owner.stage_id,
                    distance=owner.center[0] - interface.center[0],
                    reason="directed signal output is left of final producing stage",
                )
            )
    return tuple(violations)


def _power_interface_distances(
    interfaces: tuple[ExternalInterface, ...], stage_by_id: dict[str, FlowStage]
) -> tuple[PowerInterfaceDistance, ...]:
    distances: list[PowerInterfaceDistance] = []
    for interface in sorted(interfaces, key=lambda item: item.interface_id):
        if interface.role != POWER_INPUT_ROLE or interface.owner_stage_id is None:
            continue
        owner = stage_by_id.get(interface.owner_stage_id)
        if owner is None:
            continue
        distances.append(
            PowerInterfaceDistance(
                interface_id=interface.interface_id,
                owner_stage_id=owner.stage_id,
                distance=_manhattan(interface.center, owner.center),
            )
        )
    return tuple(distances)


def _stage_order_violations(
    precedence: tuple[FlowPrecedence, ...], stage_by_id: dict[str, FlowStage]
) -> tuple[StageOrderViolation, ...]:
    violations: list[StageOrderViolation] = []
    for relation in sorted(
        precedence,
        key=lambda item: (item.before_stage_id, item.after_stage_id, item.role),
    ):
        before = stage_by_id.get(relation.before_stage_id)
        after = stage_by_id.get(relation.after_stage_id)
        if before is None or after is None:
            continue
        if before.center[0] > after.center[0]:
            violations.append(
                StageOrderViolation(
                    before_stage_id=before.stage_id,
                    after_stage_id=after.stage_id,
                    role=relation.role,
                    reversal_distance=before.center[0] - after.center[0],
                )
            )
    return tuple(violations)


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
