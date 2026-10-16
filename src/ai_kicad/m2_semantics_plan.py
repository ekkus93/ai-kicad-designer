"""Implementation details for m2 semantics plan."""

from __future__ import annotations

import itertools

from .ir import InputError
from .m2_semantics import (
    EdgeKind,
    Occurrence,
)
from .m2_semantics_core import (
    BlockPlan,
    LocalSpanObligation,
    PhysicalTerminalObligation,
    PresentationNet,
    SemanticConstraint,
    SemanticEdge,
    SemanticPlan,
    SignalPrecedence,
    _amp_block,
    _function,
    _indices,
    _port,
)
from .m2a import Asset


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
            and rail["id"]
            == min(
                candidate["id"]
                for candidate in design["relationships"]
                if candidate["kind"] == "power_rails"
                and (candidate["positive"], candidate["reference"], candidate["negative"])
                == (r["positive"], r["local"], r["negative"])
            )
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

    # A generated reference may feed passive or other standalone consumers
    # without a package power unit.  Give every remaining divider its own
    # terminal-backed producer fragment instead of requiring package ownership.
    for divider in sorted(
        (r for r in design["relationships"] if r["kind"] == "reference_divider"),
        key=lambda r: r["id"],
    ):
        upper, lower = divider["upper"], divider["lower"]
        if upper in claimed_components and lower in claimed_components:
            continue
        if upper in claimed_components or lower in claimed_components:
            raise InputError(f"SEMANTIC_DIVIDER_PARTIAL_OWNER: {divider['id']}")
        fid = f"reference.{divider['id']}"
        blocks.append(
            BlockPlan(
                fid,
                "reference_divider",
                (divider["id"],),
                frozenset({(upper, 1), (lower, 1)}),
                (
                    _port(fid, "positive", divider["positive"], "power_in", [(upper, "1")]),
                    _port(fid, "negative", divider["negative"], "power_in", [(lower, "2")]),
                    _port(
                        fid,
                        "reference",
                        divider["local"],
                        "reference",
                        [(upper, "2"), (lower, "1")],
                    ),
                ),
            )
        )
        claimed_components.update((upper, lower))

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
        for first, second in itertools.pairwise(references):
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

    # External interfaces carry passive electrical pin types, but a terminal
    # feeding declared signal inputs is still the source boundary when the net
    # has no internal producer. Reference and supply distribution have no
    # invented signal direction. Keep sibling consumers incomparable.
    block_by_id = {block.id: block for block in blocks}
    signal_sources = [port for port in ports if port.role == "signal_out"]
    for net in sorted(nets):
        on_net = [port for port in ports if port.net == net]
        if not any(port.role == "signal_in" for port in on_net):
            continue
        if any(
            port.role in {"signal_out", "power_out", "power_in", "reference"} for port in on_net
        ):
            continue
        signal_sources.extend(
            port for port in on_net if block_by_id[port.fragment].kind == "interface"
        )

    precedence = tuple(
        SignalPrecedence(
            f"precedence.{source.id}.{target.id}",
            source.fragment,
            target.fragment,
            source.terminals[0],
            target.terminals[0],
            source.net,
            tuple(
                sorted(
                    set(
                        next(block for block in blocks if block.id == source.fragment).relationships
                        + next(
                            block for block in blocks if block.id == target.fragment
                        ).relationships
                    )
                )
            ),
        )
        for source in sorted(signal_sources, key=lambda port: port.id)
        for target in sorted(ports, key=lambda port: port.id)
        if target.role == "signal_in"
        and target.net == source.net
        and target.fragment != source.fragment
    )
    signal_pairs = {(p.source_fragment, p.target_fragment) for p in precedence}
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
    physical_terminals = []
    for component in sorted(design["components"], key=lambda item: item["id"]):
        asset = resolved[component["asset"]]
        for unit, pins in sorted(asset.units.items()):
            occurrence = (component["id"], unit)
            for pin in pins:
                terminal = (component["id"], pin.number)
                if terminal not in by_terminal:
                    raise InputError(f"SEMANTIC_TERMINAL_MISSING: {terminal}")
                physical_terminals.append(
                    PhysicalTerminalObligation(
                        terminal,
                        occurrence,
                        owners[occurrence],
                        component["asset"],
                        unit,
                        pin.name,
                        pin.x,
                        pin.y,
                        by_terminal[terminal],
                    )
                )
    terminal_owner = {item.terminal: item.owner for item in physical_terminals}
    connector_ids = {
        component["id"]
        for component in design["components"]
        if component["asset"].startswith("Connector_Generic:")
    }
    presentation_nets = tuple(
        PresentationNet(
            net,
            tuple(sorted(members)),
            tuple(sorted({terminal_owner[terminal] for terminal in members})),
            "distributive"
            if any(
                port.net == net and port.role in {"reference", "power_in", "power_out"}
                for port in ports
            )
            else "signal",
            not any(terminal[0] in connector_ids for terminal in members),
            not any(terminal[0] in connector_ids for terminal in members)
            and any(port.net == net and port.role == "reference" for port in ports),
            tuple(
                sorted(
                    {
                        block.id
                        for relation in design["relationships"]
                        if relation["kind"] == "reference_divider" and relation["local"] == net
                        for block in blocks
                        if relation["id"] in block.relationships
                    }
                )
            ),
        )
        for net, members in sorted(nets.items())
    )
    block_by_id = {block.id: block for block in blocks}
    local_spans = []
    passive_kinds = {"rc", "series", "led_branch"}
    for obligation in precedence:
        source_kind = block_by_id[obligation.source_fragment].kind
        target_kind = block_by_id[obligation.target_fragment].kind
        if source_kind != "interface" and (
            source_kind in passive_kinds or target_kind in passive_kinds
        ):
            local_spans.append(
                LocalSpanObligation(
                    f"span.{obligation.id}",
                    obligation.source_terminal,
                    obligation.target_terminal,
                    80_000_000,
                    "manhattan",
                    "protected_signal",
                    obligation.origins,
                )
            )
    for relation in design["relationships"]:
        if relation["kind"] == "decoupling":
            consumer = tuple(relation["consumer"])
            support_pin = next(
                (relation["component"], pin)
                for pin in ("1", "2")
                if by_terminal[(relation["component"], pin)] == by_terminal[consumer]
            )
            local_spans.append(
                LocalSpanObligation(
                    f"span.{relation['id']}",
                    consumer,
                    support_pin,
                    60_000_000,
                    "manhattan",
                    "support",
                    (relation["id"],),
                )
            )
        elif relation["kind"] == "feedback" and not any(
            item["kind"] == "amplifier"
            and item["component"] == relation["component"]
            and item["function"] == relation["function"]
            and item.get("unused")
            for item in design["relationships"]
        ):
            local_spans.append(
                LocalSpanObligation(
                    f"span.{relation['id']}",
                    (relation["component"], relation["source"]),
                    (relation["component"], relation["sense"]),
                    45_000_000,
                    "horizontal",
                    "feedback",
                    (relation["id"],),
                )
            )
    return SemanticPlan(
        tuple(sorted(blocks, key=lambda block: block.id)),
        tuple(sorted(edges, key=lambda edge: (edge.kind, edge.source, edge.target, edge.net))),
        owners,
        tuple(order),
        constraints,
        precedence,
        tuple(physical_terminals),
        presentation_nets,
        tuple(sorted(local_spans, key=lambda item: item.id)),
    )
