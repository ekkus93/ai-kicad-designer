"""Implementation details for m2 semantics core."""

from __future__ import annotations

from dataclasses import dataclass


from typing import Literal

from .ir import InputError
from .m2_conflicts import ConflictKind
from .m2_semantics import (
    EdgeKind,
    Occurrence,
    PortRole,
    Terminal,
)


@dataclass(frozen=True)
class SemanticPort:
    id: str
    fragment: str
    net: str
    role: PortRole
    terminals: tuple[Terminal, ...]


@dataclass(frozen=True)
class BlockPlan:
    id: str
    kind: str
    relationships: tuple[str, ...]
    occurrences: frozenset[Occurrence]
    ports: tuple[SemanticPort, ...]
    function: tuple[str, str] | None = None
    unused: bool = False


@dataclass(frozen=True)
class SemanticEdge:
    kind: EdgeKind
    source: str
    target: str
    net: str
    origins: tuple[str, ...]


@dataclass(frozen=True)
class SemanticConstraint:
    id: str
    origins: tuple[str, ...]
    strength: Literal["hard", "soft"]
    kind: str
    anchors: tuple[str, ...]
    parameters: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SignalPrecedence:
    """A terminal inequality independent of route and branch presentation."""

    id: str
    source_fragment: str
    target_fragment: str
    source_terminal: Terminal
    target_terminal: Terminal
    net: str
    origins: tuple[str, ...]
    minimum_x_separation: int = 1


@dataclass(frozen=True)
class PhysicalTerminalObligation:
    terminal: Terminal
    occurrence: Occurrence
    owner: str
    asset: str
    unit: int
    pin_name: str
    pin_x: int
    pin_y: int
    net: str


@dataclass(frozen=True)
class PresentationNet:
    id: str
    terminals: tuple[Terminal, ...]
    fragments: tuple[str, ...]
    role: Literal["signal", "distributive"]
    internally_generated: bool
    explicit_geometry_required: bool = False
    producer_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalSpanObligation:
    id: str
    first: Terminal
    second: Terminal
    maximum: int
    metric: Literal["manhattan", "horizontal"]
    subtype: str
    origins: tuple[str, ...]


class PlacementConflict(InputError):
    """Typed hard conflict with the structural owners needed for repair."""

    def __init__(
        self,
        kind: Literal["precedence_violation", "local_span_violation"],
        obligation: str,
        source_fragment: str,
        target_fragment: str,
        actual: int,
        limit: int,
    ) -> None:
        self.kind = kind
        self.category = (
            ConflictKind.PRECEDENCE if kind == "precedence_violation" else ConflictKind.LOCAL_SPAN
        )
        self.obligation = obligation
        self.source_fragment = source_fragment
        self.target_fragment = target_fragment
        self.actual = actual
        self.limit = limit
        super().__init__(
            f"{kind.upper()}: {obligation} actual={actual} limit={limit} "
            f"owners={source_fragment},{target_fragment}"
        )


@dataclass(frozen=True)
class SemanticPlan:
    blocks: tuple[BlockPlan, ...]
    edges: tuple[SemanticEdge, ...]
    owners: dict[Occurrence, str]
    signal_order: tuple[str, ...]
    constraints: tuple[SemanticConstraint, ...] = ()
    precedence: tuple[SignalPrecedence, ...] = ()
    terminals: tuple[PhysicalTerminalObligation, ...] = ()
    presentation_nets: tuple[PresentationNet, ...] = ()
    local_spans: tuple[LocalSpanObligation, ...] = ()


def check_placement_constraints(plan: SemanticPlan, point) -> tuple[tuple[str, int, int], ...]:
    """Evaluate exact pin coordinates after each complete placement transform."""
    results = []
    for obligation in plan.precedence:
        source = point(*obligation.source_terminal)
        target = point(*obligation.target_terminal)
        actual = target[0] - source[0]
        if actual < obligation.minimum_x_separation:
            raise PlacementConflict(
                "precedence_violation",
                obligation.id,
                obligation.source_fragment,
                obligation.target_fragment,
                actual,
                obligation.minimum_x_separation,
            )
        results.append((obligation.id, actual, obligation.minimum_x_separation))
    for obligation in plan.local_spans:
        first, second = point(*obligation.first), point(*obligation.second)
        actual = abs(first[0] - second[0])
        if obligation.metric == "manhattan":
            actual += abs(first[1] - second[1])
        if actual > obligation.maximum:
            first_owner = next(
                (
                    block_id
                    for occurrence, block_id in plan.owners.items()
                    if occurrence[0] == obligation.first[0]
                ),
                "",
            )
            second_owner = next(
                (
                    block_id
                    for occurrence, block_id in plan.owners.items()
                    if occurrence[0] == obligation.second[0]
                ),
                "",
            )
            raise PlacementConflict(
                "local_span_violation",
                obligation.id,
                first_owner,
                second_owner,
                actual,
                obligation.maximum,
            )
        results.append((obligation.id, actual, obligation.maximum))
    return tuple(results)


def _indices(design: dict) -> tuple[dict, dict, dict, dict]:
    components = {c["id"]: c for c in design["components"]}
    nets = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    by_terminal = {member: net for net, members in nets.items() for member in members}
    relations = {r["id"]: r for r in design["relationships"]}
    return components, nets, by_terminal, relations


def _port(
    block: str,
    name: str,
    net: str,
    role: PortRole,
    terminals: list[Terminal] | tuple[Terminal, ...],
) -> SemanticPort:
    return SemanticPort(f"{block}.{name}", block, net, role, tuple(sorted(terminals)))


def _function(component: dict, function_id: str) -> dict:
    try:
        return next(f for f in component.get("functions", []) if f["id"] == function_id)
    except StopIteration as exc:
        raise InputError(f"SEMANTIC_FUNCTION_MISSING: {component['id']}:{function_id}") from exc


def _amp_block(
    stage: dict,
    design: dict,
    components: dict,
    by_terminal: dict,
    claimed: set[str],
) -> BlockPlan:
    amp = components[stage["component"]]
    function = _function(amp, stage["function"])
    feedbacks = [
        r
        for r in design["relationships"]
        if r["kind"] == "feedback"
        and r["component"] == amp["id"]
        and r["function"] == function["id"]
    ]
    if len(feedbacks) != 1:
        raise InputError(
            f"SEMANTIC_FEEDBACK_MATCH: {stage['id']} expected one feedback, "
            f"got {[r['id'] for r in feedbacks]}"
        )
    feedback = feedbacks[0]
    if (
        feedback["source"] != function["pins"]["out"]
        or feedback["sense"] != function["pins"]["minus"]
    ):
        raise InputError(f"SEMANTIC_FEEDBACK_PIN_CONFLICT: {feedback['id']}")
    out_terminal = (amp["id"], function["pins"]["out"])
    minus_terminal = (amp["id"], function["pins"]["minus"])
    plus_terminal = (amp["id"], function["pins"]["plus"])
    out_net, minus_net, plus_net = (
        by_terminal[out_terminal],
        by_terminal[minus_terminal],
        by_terminal[plus_terminal],
    )
    if feedback["net"] != out_net or stage["output"] != out_net:
        raise InputError(f"SEMANTIC_FEEDBACK_NET_CONFLICT: {stage['id']}, {feedback['id']}")

    owned = {amp["id"]}
    relationship_ids = {stage["id"], feedback["id"]}
    if feedback.get("resistor"):
        owned.add(feedback["resistor"])
    series = [r for r in design["relationships"] if r["kind"] == "series"]
    shunts = [r for r in design["relationships"] if r["kind"] == "shunt"]
    bridges = [
        r for r in design["relationships"] if r["kind"] == "bridge" and r["second"] == out_net
    ]
    input_leg = next((r for r in series if r["output"] == minus_net), None)
    gain_leg = next(
        (
            r
            for r in shunts
            if r["node"] == minus_net and r["component"] != feedback.get("resistor")
        ),
        None,
    )
    input_filter = next((r for r in series if r["output"] == plus_net), None)
    upstream = (
        next((r for r in series if r["output"] == input_filter["input"]), None)
        if input_filter
        else None
    )
    bridge = next(
        (r for r in bridges if upstream is not None and r["first"] == upstream["output"]),
        None,
    )
    sallen = bool(bridge and input_filter and upstream)
    if input_leg and gain_leg:
        raise InputError(
            f"SEMANTIC_AMPLIFIER_INPUT_CONFLICT: {stage['id']} has inverting and gain legs"
        )
    if sallen:
        shunt = next((r for r in shunts if r["node"] == plus_net), None)
        if shunt is None:
            raise InputError(f"SEMANTIC_SALLEN_KEY_SHUNT_MISSING: {stage['id']}")
        local = (upstream, input_filter, shunt, bridge)
        owned.update(r["component"] for r in local)
        relationship_ids.update(r["id"] for r in local)
        input_net = upstream["input"]
        input_terminal = (upstream["component"], "1")
        kind = "sallen_key"
    elif input_leg:
        owned.add(input_leg["component"])
        relationship_ids.add(input_leg["id"])
        input_net = input_leg["input"]
        input_terminal = (input_leg["component"], "1")
        kind = "inverting_amplifier"
    elif gain_leg:
        owned.add(gain_leg["component"])
        relationship_ids.add(gain_leg["id"])
        input_net = plus_net
        input_terminal = plus_terminal
        kind = "noninverting_amplifier"
    else:
        input_net = plus_net
        input_terminal = plus_terminal
        kind = "unused_amplifier" if stage.get("unused") else "buffer"

    fragment_id = f"function.{amp['id']}.{function['id']}"
    ports = [
        _port(fragment_id, "input", input_net, "signal_in", [input_terminal]),
        _port(fragment_id, "output", out_net, "signal_out", [out_terminal]),
    ]
    if kind not in {"buffer", "unused_amplifier"}:
        if kind == "sallen_key":
            reference_terminals = [(shunt["component"], "2")]
        elif kind == "noninverting_amplifier":
            reference_terminals = [(gain_leg["component"], "2")]
        else:
            reference_terminals = [plus_terminal]
        ports.append(
            _port(
                fragment_id,
                "reference",
                stage.get("reference", plus_net),
                "reference",
                reference_terminals,
            )
        )
    claimed.update(owned - {amp["id"]})
    return BlockPlan(
        fragment_id,
        kind,
        tuple(sorted(relationship_ids)),
        frozenset({(amp["id"], function["unit"])} | {(cid, 1) for cid in owned - {amp["id"]}}),
        tuple(ports),
        (amp["id"], function["id"]),
        bool(stage.get("unused")),
    )
