"""Instance-based semantic planning for the qualified M2 schematic profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ir import InputError
from .m2a import Asset


Occurrence = tuple[str, int]
Terminal = tuple[str, str]
PortRole = Literal[
    "signal_in",
    "signal_out",
    "power_in",
    "power_out",
    "reference",
    "passive",
]
EdgeKind = Literal[
    "signal",
    "power",
    "reference",
    "support",
    "feedback",
    "branch",
    "package",
]


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
class SemanticPlan:
    blocks: tuple[BlockPlan, ...]
    edges: tuple[SemanticEdge, ...]
    owners: dict[Occurrence, str]
    signal_order: tuple[str, ...]
    constraints: tuple[SemanticConstraint, ...] = ()


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


def semantic_plan(design: dict, resolved: dict[str, Asset]) -> SemanticPlan:
    """Recognize local instances, allocate occurrences, and derive typed projections."""
    components, nets, by_terminal, _ = _indices(design)
    blocks: list[BlockPlan] = []
    claimed_components: set[str] = set()

    amplifier_stages = sorted(
        (r for r in design["relationships"] if r["kind"] == "amplifier"),
        key=lambda r: (r["component"], r["function"]),
    )
    for stage in amplifier_stages:
        blocks.append(_amp_block(stage, design, components, by_terminal, claimed_components))

    for rail in sorted(
        (r for r in design["relationships"] if r["kind"] == "power_rails"),
        key=lambda r: r["id"],
    ):
        component = components[rail["component"]]
        function = next((f for f in component["functions"] if f["unit"] == rail["unit"]), None)
        if function is None:
            raise InputError(f"SEMANTIC_PACKAGE_POWER_UNIT_MISSING: {rail['id']}")
        supports = [
            r
            for r in design["relationships"]
            if r["kind"] == "decoupling" and r["consumer"][0] == component["id"]
        ]
        supported_pins = {r["consumer"][1] for r in supports}
        if supported_pins != {function["pins"]["positive"], function["pins"]["negative"]}:
            raise InputError(
                f"SEMANTIC_PACKAGE_SUPPORT_CONFLICT: {rail['id']} consumers "
                f"{sorted(supported_pins)}"
            )
        fid = f"package.{component['id']}.power"
        occurrences = {(component["id"], function["unit"])}
        occurrences.update((r["component"], 1) for r in supports)
        claimed_components.update(r["component"] for r in supports)
        dividers = [
            r
            for r in design["relationships"]
            if r["kind"] == "reference_divider"
            and (r["positive"], r["local"], r["negative"])
            == (rail["positive"], rail["reference"], rail["negative"])
        ]
        for divider in dividers:
            occurrences.update(((divider["upper"], 1), (divider["lower"], 1)))
            claimed_components.update((divider["upper"], divider["lower"]))
        ports = (
            _port(fid, "positive", rail["positive"], "power_in", [(component["id"], "8")]),
            _port(fid, "negative", rail["negative"], "power_in", [(component["id"], "4")]),
            _port(
                fid,
                "reference",
                rail["reference"],
                "reference",
                [
                    (support["component"], pin)
                    for support in supports
                    for pin in ("1", "2")
                    if by_terminal[(support["component"], pin)] == rail["reference"]
                ],
            ),
        )
        blocks.append(
            BlockPlan(
                fid,
                "package_power",
                tuple(
                    sorted([rail["id"], *[r["id"] for r in supports], *[r["id"] for r in dividers]])
                ),
                frozenset(occurrences),
                ports,
            )
        )

    for stage in sorted(
        (r for r in design["relationships"] if r["kind"] == "power_stage"),
        key=lambda r: r["id"],
    ):
        supports = [
            r
            for r in design["relationships"]
            if r["kind"] == "decoupling" and r["consumer"][0] == stage["component"]
        ]
        expected = {stage["pins"]["input"], stage["pins"]["output"]}
        actual = {r["consumer"][1] for r in supports}
        if actual != expected:
            raise InputError(
                f"SEMANTIC_POWER_SUPPORT_CONFLICT: {stage['id']} expected {sorted(expected)}, "
                f"got {sorted(actual)} from {[r['id'] for r in supports]}"
            )
        fid = f"power_stage.{stage['component']}"
        occurrences = {(stage["component"], 1), *((r["component"], 1) for r in supports)}
        claimed_components.update(r["component"] for r in supports)
        blocks.append(
            BlockPlan(
                fid,
                "power_stage",
                tuple(sorted([stage["id"], *[r["id"] for r in supports]])),
                frozenset(occurrences),
                (
                    _port(
                        fid,
                        "input",
                        stage["input"],
                        "power_in",
                        [(stage["component"], stage["pins"]["input"])],
                    ),
                    _port(
                        fid,
                        "output",
                        stage["output"],
                        "power_out",
                        [(stage["component"], stage["pins"]["output"])],
                    ),
                    _port(
                        fid,
                        "reference",
                        stage["reference"],
                        "reference",
                        [(stage["component"], stage["pins"]["reference"])],
                    ),
                ),
            )
        )
        claimed_components.add(stage["component"])

    for timer in sorted(
        (r for r in design["relationships"] if r["kind"] == "timer"), key=lambda r: r["id"]
    ):
        ladders = [
            r
            for r in design["relationships"]
            if r["kind"] == "timing_ladder"
            and all(
                r[name] == timer[name] for name in ("supply", "reference", "timing", "discharge")
            )
        ]
        controls = [
            r
            for r in design["relationships"]
            if r["kind"] == "decoupling"
            and r["consumer"] == [timer["component"], timer["pins"]["control"]]
        ]
        if len(ladders) != 1 or len(controls) != 1:
            raise InputError(
                f"SEMANTIC_TIMER_SUPPORT_CONFLICT: {timer['id']} ladders="
                f"{[r['id'] for r in ladders]} controls={[r['id'] for r in controls]}"
            )
        ladder, control = ladders[0], controls[0]
        fid = f"timer.{timer['component']}"
        owned = {
            timer["component"],
            ladder["upper"],
            ladder["lower"],
            ladder["capacitor"],
            control["component"],
        }
        claimed_components.update(owned)
        blocks.append(
            BlockPlan(
                fid,
                "timer",
                tuple(sorted((timer["id"], ladder["id"], control["id"]))),
                frozenset((cid, 1) for cid in owned),
                (
                    _port(
                        fid,
                        "supply",
                        timer["supply"],
                        "power_in",
                        [(timer["component"], timer["pins"]["supply"])],
                    ),
                    _port(
                        fid,
                        "output",
                        timer["output"],
                        "signal_out",
                        [(timer["component"], timer["pins"]["output"])],
                    ),
                    _port(
                        fid,
                        "reference",
                        timer["reference"],
                        "reference",
                        [(timer["component"], timer["pins"]["reference"])],
                    ),
                ),
            )
        )

    series = sorted(
        (r for r in design["relationships"] if r["kind"] == "series"), key=lambda r: r["id"]
    )
    for relation in series:
        if relation["component"] in claimed_components:
            continue
        shunts = [
            r
            for r in design["relationships"]
            if r["kind"] == "shunt"
            and r["node"] == relation["output"]
            and r["component"] not in claimed_components
        ]
        polarities = [
            r
            for r in design["relationships"]
            if r["kind"] == "polarity"
            and r["anode"] == relation["output"]
            and r["component"] not in claimed_components
        ]
        if len(shunts) + len(polarities) > 1:
            raise InputError(
                f"SEMANTIC_PASSIVE_MATCH_CONFLICT: {relation['id']} candidates "
                f"{sorted(r['id'] for r in shunts + polarities)}"
            )
        companion = (shunts + polarities)[0] if shunts or polarities else None
        fid = f"passive.{relation['id']}"
        occurrences = {(relation["component"], 1)}
        origins = [relation["id"]]
        kind = "series"
        ports = [
            _port(fid, "input", relation["input"], "signal_in", [(relation["component"], "1")]),
            _port(fid, "output", relation["output"], "signal_out", [(relation["component"], "2")]),
        ]
        if companion:
            occurrences.add((companion["component"], 1))
            origins.append(companion["id"])
            claimed_components.add(companion["component"])
            reference = (
                companion["reference"] if companion["kind"] == "shunt" else companion["cathode"]
            )
            terminal = "2" if companion["kind"] == "shunt" else "1"
            ports.append(
                _port(
                    fid, "reference", reference, "reference", [(companion["component"], terminal)]
                )
            )
            kind = "rc" if companion["kind"] == "shunt" else "led_branch"
        claimed_components.add(relation["component"])
        blocks.append(
            BlockPlan(fid, kind, tuple(sorted(origins)), frozenset(occurrences), tuple(ports))
        )

    for connector in sorted(
        (c for c in design["components"] if c["asset"].startswith("Connector_Generic:")),
        key=lambda c: c["id"],
    ):
        fid = f"interface.{connector['id']}"
        ports = tuple(
            _port(
                fid,
                f"pin{pin.number}",
                by_terminal[(connector["id"], pin.number)],
                "passive",
                [(connector["id"], pin.number)],
            )
            for pin in resolved[connector["asset"]].units[1]
        )
        blocks.append(BlockPlan(fid, "interface", (), frozenset({(connector["id"], 1)}), ports))
        claimed_components.add(connector["id"])

    expected = {
        (component["id"], unit)
        for component in design["components"]
        for unit in resolved[component["asset"]].units
    }
    owners: dict[Occurrence, str] = {}
    for block in sorted(blocks, key=lambda b: b.id):
        for occurrence in block.occurrences:
            if occurrence in owners:
                raise InputError(
                    f"SEMANTIC_GEOMETRY_OWNER_CONFLICT: {occurrence} claimed by "
                    f"{owners[occurrence]} and {block.id}"
                )
            owners[occurrence] = block.id
    if set(owners) != expected:
        missing = sorted(expected - set(owners))
        extra = sorted(set(owners) - expected)
        raise InputError(f"SEMANTIC_OWNER_INCOMPLETE: missing={missing} extra={extra}")

    ports = [p for block in blocks for p in block.ports]
    edges: set[SemanticEdge] = set()
    for net in sorted(nets):
        on_net = [p for p in ports if p.net == net]
        signal_outputs = [p for p in on_net if p.role == "signal_out"]
        signal_inputs = [p for p in on_net if p.role == "signal_in"]
        power_outputs = [p for p in on_net if p.role == "power_out"]
        power_inputs = [p for p in on_net if p.role == "power_in"]
        for source in signal_outputs:
            for target in signal_inputs:
                if source.fragment != target.fragment:
                    kind: EdgeKind = (
                        "branch" if target.fragment.startswith("passive.") else "signal"
                    )
                    edges.add(SemanticEdge(kind, source.fragment, target.fragment, net, ()))
        for source in power_outputs:
            for target in power_inputs + signal_inputs:
                if source.fragment != target.fragment:
                    kind = (
                        "branch"
                        if target.fragment.startswith("passive.")
                        and next(block for block in blocks if block.id == target.fragment).kind
                        == "led_branch"
                        else "power"
                    )
                    edges.add(SemanticEdge(kind, source.fragment, target.fragment, net, ()))
        references = [p for p in on_net if p.role == "reference"]
        for first, second in zip(references, references[1:]):
            if first.fragment != second.fragment:
                edges.add(SemanticEdge("reference", first.fragment, second.fragment, net, ()))

    for relation in design["relationships"]:
        if relation["kind"] == "decoupling":
            owner = owners[(relation["component"], 1)]
            consumer_occurrence = next(
                occurrence for occurrence in owners if occurrence[0] == relation["consumer"][0]
            )
            edges.add(
                SemanticEdge(
                    "support",
                    owner,
                    owners[consumer_occurrence],
                    relation["supply"],
                    (relation["id"],),
                )
            )
        elif relation["kind"] == "feedback":
            owner = owners[
                (
                    relation["component"],
                    _function(components[relation["component"]], relation["function"])["unit"],
                )
            ]
            edges.add(SemanticEdge("feedback", owner, owner, relation["net"], (relation["id"],)))
    for block in blocks:
        if block.function:
            package = f"package.{block.function[0]}.power"
            if any(candidate.id == package for candidate in blocks):
                edges.add(SemanticEdge("package", block.id, package, "", block.relationships))

    signal_pairs = {(e.source, e.target) for e in edges if e.kind == "signal"}
    remaining = {b.id for b in blocks if b.kind not in {"interface", "package_power"}}
    order: list[str] = []
    while remaining:
        ready = sorted(
            node
            for node in remaining
            if not any(a in remaining and b == node for a, b in signal_pairs)
        )
        if not ready:
            raise InputError(f"SEMANTIC_SIGNAL_CYCLE: {sorted(remaining)}")
        order.extend(ready)
        remaining.difference_update(ready)
    constraints = tuple(
        SemanticConstraint(
            f"edge.{index}",
            edge.origins,
            "hard",
            edge.kind,
            (edge.source, edge.target),
            (("net", edge.net),),
        )
        for index, edge in enumerate(
            sorted(edges, key=lambda edge: (edge.kind, edge.source, edge.target, edge.net))
        )
    )
    return SemanticPlan(
        tuple(sorted(blocks, key=lambda block: block.id)),
        tuple(sorted(edges, key=lambda edge: (edge.kind, edge.source, edge.target, edge.net))),
        owners,
        tuple(order),
        constraints,
    )
