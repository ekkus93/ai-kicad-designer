"""Deterministic composition of the qualified M2 motif contributors."""

from dataclasses import dataclass

from .ir import InputError
from .m2a import PITCH, Scene
from .m2b import (
    Draft,
    active_layout,
    choose_text_slots,
    measure,
    orientation_for_flow,
    passive_layout,
    power_stage_layout,
    timing_layout,
)


@dataclass(frozen=True)
class LayoutFragment:
    """One geometry owner set and its semantic input/output ports."""

    rule: str
    occurrences: frozenset[tuple[str, int]]
    ports: dict[str, str]


@dataclass(frozen=True)
class StageGraph:
    ports: dict[str, tuple[str, str]]
    order: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]


def stage_graph(design: dict) -> StageGraph:
    """Order declared signal stages; supplies and feedback stay distributive."""
    ports = {
        r["id"]: (r["input"], r["output"])
        for r in design["relationships"]
        if r["kind"] in ("series", "amplifier", "power_stage") and not r.get("unused")
    }
    ports.update(
        (r["id"], (r["supply"], r["output"]))
        for r in design["relationships"]
        if r["kind"] == "timer"
    )
    edges = tuple(
        sorted(
            (first, second, output)
            for first, (_, output) in ports.items()
            for second, (input_net, _) in ports.items()
            if first != second and output == input_net
        )
    )
    remaining = set(ports)
    order = []
    while remaining:
        ready = sorted(
            stage
            for stage in remaining
            if not any(a in remaining and b == stage for a, b, _ in edges)
        )
        if not ready:
            raise InputError(f"unsupported stage graph cycle: {sorted(remaining)}")
        order.extend(ready)
        remaining.difference_update(ready)
    return StageGraph(ports, tuple(order), edges)


def _draft(design, resolved, scene):
    return Draft(
        design,
        resolved,
        dict(scene.positions),
        dict(scene.angles),
        list(scene.wires),
        list(scene.wire_nets),
        list(scene.labels),
        list(scene.junctions),
        dict(scene.text_positions),
    )


def _branch_point(draft, net, point):
    for index, ((a, b), owned) in enumerate(zip(draft.wires, draft.wire_nets, strict=True)):
        if owned != net or point in (a, b):
            continue
        if (a[0] == b[0] == point[0] and min(a[1], b[1]) < point[1] < max(a[1], b[1])) or (
            a[1] == b[1] == point[1] and min(a[0], b[0]) < point[0] < max(a[0], b[0])
        ):
            draft.wires[index : index + 1] = [(a, point), (point, b)]
            draft.wire_nets[index : index + 1] = [net, net]
            break
    draft.junctions.append(point)


def _anchor(draft, net, near=None):
    segments = [
        (a, b)
        for (a, b), owned in zip(draft.wires, draft.wire_nets, strict=True)
        if owned == net and a[1] == b[1] and abs(a[0] - b[0]) >= 10 * PITCH
    ]
    if segments:
        a, b = max(segments, key=lambda pair: abs(pair[0][0] - pair[1][0]))
        if near is None:
            x = (a[0] + b[0]) // (2 * PITCH) * PITCH
        else:
            x = min(max(near[0], min(a[0], b[0]) + PITCH), max(a[0], b[0]) - PITCH)
        return x, a[1]
    labels = [point for owned, point in draft.labels if owned == net]
    if labels:
        return min(labels, key=lambda p: abs(p[0] - near[0]) if near else -p[0])
    raise InputError(f"missing compatible port for net {net}")


def _join_reference(draft, net, pin, source_y):
    candidates = [
        (a, b)
        for (a, b), owned in zip(draft.wires, draft.wire_nets, strict=True)
        if owned == net
        and a[1] == b[1]
        and min(a[0], b[0]) <= pin[0] <= max(a[0], b[0])
        and a[1] > source_y
    ]
    if candidates:
        a, _ = min(candidates, key=lambda pair: abs(pair[0][1] - pin[1]))
        node = (pin[0], a[1])
        draft.route(net, pin, node)
        _branch_point(draft, net, node)
    else:
        end = (pin[0], pin[1] + 5 * PITCH)
        draft.route(net, pin, end)
        draft.label(net, end)


def _branch(draft, relation, polarity, components):
    net = relation["input"]
    source = _anchor(draft, net)
    x, y = source
    resistor = relation["component"]
    if components[resistor]["asset"] not in ("Device:R", "Device:C"):
        raise InputError(f"relationship {relation['id']}: no branch series layout rule")
    draft.add(resistor, x, y + 12 * PITCH)
    first, second = draft.point(resistor, "1"), draft.point(resistor, "2")
    draft.route(net, source, first)
    _branch_point(draft, net, source)
    diode = polarity["component"]
    draft.add(diode, x, y + 22 * PITCH, angle=90)
    draft.text_positions[(diode, 1)] = (x + 9 * PITCH, y + 18 * PITCH)
    anode, cathode = draft.point(diode, "2"), draft.point(diode, "1")
    draft.route(relation["output"], second, anode)
    _join_reference(draft, polarity["cathode"], cathode, y)


def _serial_shunt(draft, relation, shunt, components, prepend):
    cid = relation["component"]
    asset = components[cid]["asset"]
    if asset not in ("Device:R", "Device:C"):
        raise InputError(f"relationship {relation['id']}: no passive series layout rule")
    if prepend:
        consumers = [
            r
            for r in draft.design["relationships"]
            if r["kind"] == "series"
            and r["input"] == relation["output"]
            and (r["component"], 1) in draft.positions
        ]
        if len(consumers) != 1:
            raise InputError(f"relationship {relation['id']}: missing downstream input port")
        target = draft.point(consumers[0]["component"], "1")
        x, y = target[0] - 27 * PITCH, target[1]
        node_x = target[0] - 13 * PITCH
    else:
        output_ports = [point for net, point in draft.labels if net == relation["input"]]
        source = (
            max(output_ports, key=lambda point: point[0])
            if output_ports
            else _anchor(draft, relation["input"])
        )
        left = min(
            point[0]
            for point in (
                list(draft.positions.values())
                + [p for _, p in draft.labels]
                + [p for wire in draft.wires for p in wire]
            )
        )
        right_limit = min(182 * PITCH, left + 138 * PITCH)
        x, y = min(max(p[0] for p in draft.positions.values()) + 8 * PITCH, right_limit), source[1]
        node_x = x + 17 * PITCH
    draft.add(cid, x, y, angle=orientation_for_flow(draft.resolved[asset], "1", "2", "right"))
    first, second = draft.point(cid, "1"), draft.point(cid, "2")
    if prepend:
        draft.route(relation["output"], second, (node_x, y), target)
        draft.route(relation["input"], first, (first[0] - 5 * PITCH, y))
        draft.label(relation["input"], (first[0] - 5 * PITCH, y))
    else:
        draft.route(relation["input"], source, (first[0], source[1]), first)
        _branch_point(draft, relation["input"], source)
    draft.add(shunt["component"], node_x, y + 17 * PITCH)
    top, bottom = draft.point(shunt["component"], "1"), draft.point(shunt["component"], "2")
    draft.route(relation["output"], second, (node_x, y), top)
    draft.junctions.append((node_x, y))
    if not prepend:
        end = (node_x + 10 * PITCH, y)
        draft.route(relation["output"], (node_x, y), end)
        draft.label(relation["output"], end)
    _join_reference(draft, shunt["reference"], bottom, y)


def compose_layout(design: dict, resolved: dict) -> Scene:
    relations = design["relationships"]
    graph = stage_graph(design)
    components = {c["id"]: c for c in design["components"]}
    kinds = {r["kind"] for r in relations}
    contributors = (
        ("timer", timing_layout),
        ("power_stage", power_stage_layout),
        ("amplifier", active_layout),
    )
    recognized = [(rule, contributor) for rule, contributor in contributors if rule in kinds]
    if len(recognized) > 1:
        raise InputError(
            f"incompatible local core contributors: {[rule for rule, _ in recognized]}"
        )
    rule, primary = recognized[0] if recognized else ("passive", passive_layout)
    scene = primary(design, resolved, partial=True)
    draft = _draft(design, resolved, scene)
    primary_ids = {r["id"] for r in relations if r["kind"] == rule and not r.get("unused")}
    ordered_core = [stage for stage in graph.order if stage in primary_ids]
    core_ports = (
        {"input": graph.ports[ordered_core[0]][0], "output": graph.ports[ordered_core[-1]][1]}
        if ordered_core
        else {}
    )
    core = LayoutFragment(rule, frozenset(draft.positions), core_ports)
    fragments = [core]
    remaining = [
        r for r in relations if r["kind"] == "series" and (r["component"], 1) not in draft.positions
    ]
    remaining.sort(key=lambda relation: graph.order.index(relation["id"]))
    while remaining:
        progressed = False
        for relation in list(remaining):
            polarities = [
                r for r in relations if r["kind"] == "polarity" and r["anode"] == relation["output"]
            ]
            shunts = [
                r for r in relations if r["kind"] == "shunt" and r["node"] == relation["output"]
            ]
            if len(polarities) + len(shunts) != 1:
                raise InputError(
                    f"relationship {relation['id']}: no unique downstream branch/shunt rule"
                )
            owned_nets = {
                n["id"]
                for n in design["nets"]
                if any((cid, 1) in draft.positions for cid, _ in n["members"])
            }
            prepend = any(
                r["kind"] == "series"
                and r["input"] == relation["output"]
                and (r["component"], 1) in draft.positions
                for r in relations
            )
            if not prepend and relation["input"] not in owned_nets:
                continue
            before = frozenset(draft.positions)
            if polarities:
                _branch(draft, relation, polarities[0], components)
            else:
                _serial_shunt(draft, relation, shunts[0], components, prepend)
            fragments.append(
                LayoutFragment(
                    relation["id"],
                    frozenset(draft.positions) - before,
                    {"input": relation["input"], "output": relation["output"]},
                )
            )
            remaining.remove(relation)
            progressed = True
        if not progressed:
            raise InputError(
                f"stage graph cycle or missing input port: {[r['id'] for r in remaining]}"
            )
    owners = {}
    for fragment in fragments:
        for occurrence in fragment.occurrences:
            if occurrence in owners:
                raise InputError(
                    f"component {occurrence[0]}: incompatible geometry owners {owners[occurrence]}, {fragment.rule}"
                )
            owners[occurrence] = fragment.rule
    absent = sorted(
        (c["id"], unit)
        for c in design["components"]
        for unit in resolved[c["asset"]].units
        if (c["id"], unit) not in owners
    )
    if absent:
        raise InputError(f"components with no geometry owner: {absent}")
    choose_text_slots(design, draft)
    metrics = measure(design, resolved, draft)
    metrics.update(scene.metrics)
    return Scene(
        draft.positions,
        draft.wires,
        draft.wire_nets,
        draft.labels,
        draft.junctions,
        metrics,
        draft.angles,
        draft.text_positions,
        {key: angle for key, angle in draft.angles.items() if angle in (90, 270)},
    )
