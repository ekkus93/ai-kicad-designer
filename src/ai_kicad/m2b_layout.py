"""Implementation details for m2b layout."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .ir import InputError
from .m2_geometry import label_text_rect
from .m2a import PITCH, Asset, Pin, Scene
from .m2_text_layout import (
    candidate_text_anchors,
    first_clear_text_anchor,
    property_envelopes,
)


def _turn(pin: Pin, angle: int) -> tuple[int, int]:
    """KiCad library Y is upward; sheet Y is downward."""
    x, y = pin.x, -pin.y
    return {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[angle]


def orientation_for_flow(asset: Asset, first: str, second: str, axis: str) -> int:
    """Select a legal quarter turn from resolved physical pin endpoints."""
    pins = {p.number: p for unit in asset.units.values() for p in unit}
    if first not in pins or second not in pins:
        raise InputError("orientation terminals absent from locked asset")
    for angle in (0, 90, 180, 270):
        a, b = _turn(pins[first], angle), _turn(pins[second], angle)
        if axis == "right" and a[1] == b[1] and a[0] < b[0]:
            return angle
        if axis == "down" and a[0] == b[0] and a[1] < b[1]:
            return angle
    raise InputError("resolved pin geometry cannot satisfy semantic flow")


@dataclass
class Draft:
    design: dict
    resolved: dict[str, Asset]
    positions: dict[tuple[str, int], tuple[int, int]]
    angles: dict[tuple[str, int], int]
    wires: list
    wire_nets: list[str]
    labels: list
    junctions: list
    text_positions: dict

    def point(self, component: str, number: str) -> tuple[int, int]:
        c = next(c for c in self.design["components"] if c["id"] == component)
        unit, pin = next(
            (u, p)
            for u, pins in self.resolved[c["asset"]].units.items()
            for p in pins
            if p.number == number
        )
        x, y = self.positions[(component, unit)]
        dx, dy = _turn(pin, self.angles.get((component, unit), 0))
        return x + dx, y + dy

    def route(self, net: str, *points):
        for a, b in itertools.pairwise(points):
            if a != b:
                if a[0] != b[0] and a[1] != b[1]:
                    raise InputError("internal non-orthogonal routing request")
                self.wires.append((a, b))
                self.wire_nets.append(net)

    def label(self, net: str, point):
        self.labels.append((net, point))

    def add(self, component: str, x: int, y: int, unit: int = 1, angle: int = 0):
        key = (component, unit)
        if key in self.positions:
            raise InputError("duplicate geometry owner")
        self.positions[key] = (x, y)
        self.angles[key] = angle
        asset = next(c for c in self.design["components"] if c["id"] == component)["asset"]
        self.text_positions[key] = (
            (x + 8 * PITCH, y - 2 * PITCH) if asset == "Device:C" else (x, y - 8 * PITCH)
        )


def passive_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Compose series, shunt and diode relations through net anchors."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    relations = design["relationships"]
    series = [r for r in relations if r["kind"] == "series"]
    shunts = [r for r in relations if r["kind"] == "shunt"]
    polarities = [r for r in relations if r["kind"] == "polarity"]
    if not series or not shunts and not polarities:
        raise InputError("unsupported passive composition")
    flows = [r for r in relations if r["kind"] == "signal_flow"]
    s = next((r for r in series if flows and r["input"] == flows[0]["input"]), series[0])
    shunts = [r for r in shunts if r["node"] == s["output"]]
    polarities = [r for r in polarities if r["anode"] == s["output"]]
    if len(shunts) + len(polarities) != 1:
        raise InputError(f"series {s['id']}: no unique downstream shunt/polarity rule")
    final_net = polarities[0]["cathode"] if polarities else s["output"]
    if len(flows) != 1 or flows[0]["input"] != s["input"] or flows[0]["output"] != final_net:
        raise InputError("signal flow relation does not match passive path")
    components = {c["id"]: c for c in design["components"]}
    if components[s["component"]]["asset"] not in ("Device:R", "Device:C"):
        raise InputError("passive series requires a two-terminal passive")
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    anchor_x, anchor_y = 96 * PITCH, 64 * PITCH
    d.add(
        s["component"],
        anchor_x,
        anchor_y,
        angle=orientation_for_flow(
            resolved[components[s["component"]]["asset"]], "1", "2", "right"
        ),
    )
    left = d.point(s["component"], "1")
    right = d.point(s["component"], "2")
    net_members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {
        net: next(
            (
                cid
                for cid, pin in members
                if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
            ),
            None,
        )
        for net, members in net_members.items()
    }
    if ports.get(s["input"]) is None:
        raise InputError("missing signal input interface")
    d.add(ports[s["input"]], anchor_x - 31 * PITCH, anchor_y, angle=180)
    source = d.point(ports[s["input"]], "1")
    d.route(s["input"], source, left)
    d.label(s["input"], source)
    if polarities:
        p = polarities[0]
        if s["output"] != p["anode"]:
            raise InputError("series and polarity relations do not compose")
        d.add(
            p["component"],
            anchor_x + 30 * PITCH,
            anchor_y,
            angle=orientation_for_flow(
                resolved[components[p["component"]]["asset"]], "2", "1", "right"
            ),
        )
        anode = d.point(p["component"], "2")
        cathode = d.point(p["component"], "1")
        d.route(s["output"], right, anode)
        if ports.get(p["cathode"]) is None:
            raise InputError("missing return interface")
        d.add(ports[p["cathode"]], anchor_x + 61 * PITCH, anchor_y)
        return_pin = d.point(ports[p["cathode"]], "1")
        d.route(p["cathode"], cathode, return_pin)
        d.label(p["cathode"], return_pin)
    else:
        sh = shunts[0]
        if s["output"] != sh["node"]:
            raise InputError("series and shunt relations do not compose")
        d.add(sh["component"], anchor_x + 30 * PITCH, anchor_y + 22 * PITCH)
        node = (d.positions[(sh["component"], 1)][0], right[1])
        shunt_top, shunt_bottom = (
            d.point(sh["component"], "1"),
            d.point(sh["component"], "2"),
        )
        d.route(s["output"], right, node, shunt_top)
        if ports.get(s["output"]) is None or ports.get(sh["reference"]) is None:
            raise InputError("missing output/reference interface")
        d.add(ports[s["output"]], anchor_x + 65 * PITCH, anchor_y)
        out = d.point(ports[s["output"]], "1")
        d.route(s["output"], node, out)
        d.junctions.append(node)
        d.label(s["output"], out)
        d.add(ports[sh["reference"]], anchor_x + 65 * PITCH, anchor_y + 40 * PITCH)
        ref = d.point(ports[sh["reference"]], "1")
        d.route(sh["reference"], shunt_bottom, (shunt_bottom[0], ref[1]), ref)
        d.label(sh["reference"], ref)
    if not partial and len(d.positions) != len(design["components"]):
        raise InputError("unsupported passive component occurrence")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    text_angles = {key: angle for key, angle in d.angles.items() if angle in (90, 270)}
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
        text_angles,
    )


def power_stage_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Place a three-terminal power stage between its interfaces and local support."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    stages = [r for r in design["relationships"] if r["kind"] == "power_stage"]
    supports = [r for r in design["relationships"] if r["kind"] == "decoupling"]
    if len(stages) != 1 or len(supports) != 2:
        raise InputError("unsupported power-stage relation inventory")
    stage = stages[0]
    stage_id = stage["component"]
    support_by_pin = {tuple(r["consumer"]): r for r in supports}
    if set(support_by_pin) != {
        (stage_id, stage["pins"]["input"]),
        (stage_id, stage["pins"]["output"]),
    } or any(
        {r["supply"], r["return"]} != {stage["reference"], stage[role]}
        for role in ("input", "output")
        for r in (support_by_pin[(stage_id, stage["pins"][role])],)
    ):
        raise InputError("support relationships do not attach to power-stage rails")
    components = {c["id"]: c for c in design["components"]}
    members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {}
    for net in (stage["input"], stage["output"], stage["reference"]):
        matches = [
            cid
            for cid, pin in members[net]
            if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
        ]
        if len(matches) != 1:
            raise InputError("power stage requires one interface per rail")
        ports[net] = matches[0]
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    sx, sy = 116 * PITCH, 67 * PITCH
    stage_asset = resolved[components[stage_id]["asset"]]
    d.add(
        stage_id,
        sx,
        sy,
        angle=orientation_for_flow(
            stage_asset, stage["pins"]["input"], stage["pins"]["output"], "right"
        ),
    )
    input_pin = d.point(stage_id, stage["pins"]["input"])
    output_pin = d.point(stage_id, stage["pins"]["output"])
    reference_pin = d.point(stage_id, stage["pins"]["reference"])
    in_relation = support_by_pin[(stage_id, stage["pins"]["input"])]
    out_relation = support_by_pin[(stage_id, stage["pins"]["output"])]
    cap_y = sy + 22 * PITCH if reference_pin[1] > sy else sy - 22 * PITCH

    def support_endpoints(relation, rail, x):
        rail_pin = "1" if relation["supply"] == rail else "2"
        reference_pin_number = "2" if rail_pin == "1" else "1"
        rail_above = cap_y > sy
        angle = (
            0 if (rail_above and rail_pin == "1") or (not rail_above and rail_pin == "2") else 180
        )
        d.add(relation["component"], x, cap_y, angle=angle)
        return d.point(relation["component"], rail_pin), d.point(
            relation["component"], reference_pin_number
        )

    left_rail, left_reference = support_endpoints(in_relation, stage["input"], sx - 24 * PITCH)
    right_rail, right_reference = support_endpoints(out_relation, stage["output"], sx + 24 * PITCH)
    d.add(ports[stage["input"]], sx - 55 * PITCH, sy, angle=180)
    d.add(ports[stage["output"]], sx + 55 * PITCH, sy)
    reference_y = cap_y + (19 * PITCH if cap_y > sy else -19 * PITCH)
    d.add(ports[stage["reference"]], sx + 55 * PITCH, reference_y)
    source = d.point(ports[stage["input"]], "1")
    load = d.point(ports[stage["output"]], "1")
    return_port = d.point(ports[stage["reference"]], "1")
    left_node = (left_rail[0], sy)
    right_node = (right_rail[0], sy)
    d.route(stage["input"], source, left_node, input_pin)
    d.route(stage["input"], left_node, left_rail)
    d.route(stage["output"], output_pin, right_node, load)
    d.route(stage["output"], right_node, right_rail)
    d.junctions.extend((left_node, right_node))
    return_y = return_port[1]
    d.route(stage["reference"], left_reference, (left_reference[0], return_y), return_port)
    d.route(stage["reference"], right_reference, (right_reference[0], return_y))
    d.route(stage["reference"], reference_pin, (reference_pin[0], return_y))
    d.junctions.extend(((right_reference[0], return_y), (reference_pin[0], return_y)))
    for net, point in (
        (stage["input"], source),
        (stage["output"], load),
        (stage["reference"], return_port),
    ):
        d.label(net, point)
    flags = {a["net"]: a for a in design["power_assertions"]}
    if not {stage["input"], stage["reference"]} <= set(flags):
        raise InputError("power stage lacks external source assertions")
    for net, point in (
        (stage["input"], left_node),
        (stage["reference"], (reference_pin[0], return_y)),
    ):
        d.positions[(flags[net]["id"], 1)] = point
    if not partial and {cid for cid, _ in d.positions if cid in components} != set(components):
        raise InputError("unplaced power-stage component")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
    )


def timing_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Compose a vertical timing ladder beside a physical timer symbol."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    timers = [r for r in design["relationships"] if r["kind"] == "timer"]
    ladders = [r for r in design["relationships"] if r["kind"] == "timing_ladder"]
    controls = [r for r in design["relationships"] if r["kind"] == "decoupling"]
    if len(timers) != 1 or len(ladders) != 1 or len(controls) != 1:
        raise InputError("unsupported timing relation inventory")
    timer, ladder, control = timers[0], ladders[0], controls[0]
    if any(timer[k] != ladder[k] for k in ("supply", "reference", "timing", "discharge")):
        raise InputError("timer and timing ladder nets disagree")
    if control["consumer"] != [timer["component"], timer["pins"]["control"]] or (
        control["supply"],
        control["return"],
    ) != (timer["control"], timer["reference"]):
        raise InputError("timer control bypass relation disagrees")
    components = {c["id"]: c for c in design["components"]}
    nets = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {}
    for net in (timer["supply"], timer["output"], timer["reference"]):
        matches = [
            cid
            for cid, pin in nets[net]
            if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
        ]
        if len(matches) != 1:
            raise InputError("timer requires supply, output and reference interfaces")
        ports[net] = matches[0]
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    tx, ty = 143 * PITCH, 75 * PITCH
    lx = tx - 43 * PITCH
    d.add(timer["component"], tx, ty)
    d.text_positions[(timer["component"], 1)] = (tx + 18 * PITCH, ty - 12 * PITCH)
    p = {role: d.point(timer["component"], number) for role, number in timer["pins"].items()}
    d.add(ladder["upper"], lx, ty - 25 * PITCH)
    d.add(ladder["lower"], lx, ty - 5 * PITCH)
    d.add(ladder["capacitor"], lx, ty + 21 * PITCH)
    d.add(control["component"], tx - 16 * PITCH, ty - 10 * PITCH)
    upper_top, upper_bottom = (
        d.point(ladder["upper"], "1"),
        d.point(ladder["upper"], "2"),
    )
    lower_top, lower_bottom = (
        d.point(ladder["lower"], "1"),
        d.point(ladder["lower"], "2"),
    )
    timing_top, timing_bottom = (
        d.point(ladder["capacitor"], "1"),
        d.point(ladder["capacitor"], "2"),
    )
    control_top, control_bottom = (
        d.point(control["component"], "1"),
        d.point(control["component"], "2"),
    )
    d.add(ports[timer["supply"]], lx - 28 * PITCH, ty - 35 * PITCH, angle=180)
    d.add(ports[timer["output"]], tx + 36 * PITCH, p["output"][1])
    d.add(ports[timer["reference"]], tx + 36 * PITCH, ty + 32 * PITCH)
    source = d.point(ports[timer["supply"]], "1")
    load = d.point(ports[timer["output"]], "1")
    return_port = d.point(ports[timer["reference"]], "1")
    supply_y = source[1]
    d.route(timer["supply"], source, (lx, supply_y), upper_top)
    d.route(timer["supply"], (lx, supply_y), (p["supply"][0], supply_y), p["supply"])
    d.junctions.append((lx, supply_y))
    d.route(timer["supply"], p["reset"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    d.label(timer["supply"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    discharge_y = (upper_bottom[1] + lower_top[1]) // 2
    discharge_x = p["discharge"][0] - 10 * PITCH
    d.route(timer["discharge"], upper_bottom, (lx, discharge_y), lower_top)
    d.route(
        timer["discharge"],
        (lx, discharge_y),
        (discharge_x, discharge_y),
        (discharge_x, p["discharge"][1]),
        p["discharge"],
    )
    d.junctions.append((lx, discharge_y))
    timing_y = p["trigger"][1] + 6 * PITCH
    sense_x = p["trigger"][0] - 7 * PITCH
    d.route(timer["timing"], lower_bottom, (lx, timing_y), timing_top)
    d.route(
        timer["timing"],
        (lx, timing_y),
        (sense_x, timing_y),
        (sense_x, p["threshold"][1]),
        p["threshold"],
    )
    d.route(timer["timing"], (sense_x, p["trigger"][1]), p["trigger"])
    d.junctions.extend(((lx, timing_y), (sense_x, p["trigger"][1])))
    d.route(timer["output"], p["output"], load)
    d.route(timer["reference"], timing_bottom, (lx, return_port[1]), return_port)
    d.route(timer["reference"], p["reference"], (p["reference"][0], return_port[1]))
    d.junctions.append((p["reference"][0], return_port[1]))
    control_y = min(p["control"][1], control_top[1]) - 5 * PITCH
    d.route(
        timer["control"],
        p["control"],
        (p["control"][0], control_y),
        (control_top[0], control_y),
        control_top,
    )
    d.route(
        timer["reference"],
        control_bottom,
        (control_bottom[0], control_bottom[1] + 3 * PITCH),
    )
    d.label(timer["reference"], (control_bottom[0], control_bottom[1] + 3 * PITCH))
    for net, point in (
        (timer["supply"], source),
        (timer["output"], load),
        (timer["reference"], return_port),
    ):
        d.label(net, point)
    flags = {a["net"]: a for a in design["power_assertions"]}
    if not {timer["supply"], timer["reference"]} <= set(flags):
        raise InputError("timer lacks external supply assertions")
    for net, point in (
        (timer["supply"], (lx, supply_y)),
        (timer["reference"], (p["reference"][0], return_port[1])),
    ):
        d.positions[(flags[net]["id"], 1)] = point
    if not partial and {cid for cid, _ in d.positions if cid in components} != set(components):
        raise InputError("unplaced timer component")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
    )


def measure(design: dict, resolved: dict[str, Asset], draft: Draft) -> dict:
    """Conservative independent-of-render preflight; observed gates run after KiCad."""
    rectangles = []
    for (cid, unit), (x, y) in draft.positions.items():
        c = next((c for c in design["components"] if c["id"] == cid), None)
        if c is None:
            continue
        body = resolved[c["asset"]].bodies.get(unit) or resolved[c["asset"]].bodies.get(0)
        if body:
            left, top, right, bottom = body
            corners = [
                _turn(Pin("", "", "", xx, yy), draft.angles.get((cid, unit), 0))
                for xx in (left, right)
                for yy in (top, bottom)
            ]
            xs, ys = [x + z[0] for z in corners], [y + z[1] for z in corners]
            rectangles.append((cid, (min(xs), min(ys), max(xs), max(ys))))
    for i, (cid, a) in enumerate(rectangles):
        for other, b in rectangles[i + 1 :]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise InputError(f"symbol body overlap: {cid}, {other}")
    for net, (a, b) in zip(draft.wire_nets, draft.wires, strict=True):
        if a[0] != b[0] and a[1] != b[1]:
            raise InputError("diagonal wire")
        for cid, rect in rectangles:
            if a in {
                draft.point(cid, p.number)
                for pins in resolved[
                    next(c for c in design["components"] if c["id"] == cid)["asset"]
                ].units.values()
                for p in pins
            } or b in {
                draft.point(cid, p.number)
                for pins in resolved[
                    next(c for c in design["components"] if c["id"] == cid)["asset"]
                ].units.values()
                for p in pins
            }:
                continue
            left, top, right, bottom = rect
            if (
                a[0] == b[0]
                and left < a[0] < right
                and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
            ):
                raise InputError(f"wire through body: {net}, {cid}")
            if (
                a[1] == b[1]
                and top < a[1] < bottom
                and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
            ):
                raise InputError(f"wire through body: {net}, {cid}")

    def on_segment(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        )

    for i, (a, b) in enumerate(draft.wires):
        for j in range(i + 1, len(draft.wires)):
            if draft.wire_nets[i] == draft.wire_nets[j]:
                continue
            c, e = draft.wires[j]
            if (
                a[0] == b[0]
                and c[1] == e[1]
                and on_segment((a[0], c[1]), a, b)
                and on_segment((a[0], c[1]), c, e)
            ):
                raise InputError(
                    f"unrelated wire crossing: {draft.wire_nets[i]} {a}->{b}, {draft.wire_nets[j]} {c}->{e}"
                )
            if (
                a[1] == b[1]
                and c[0] == e[0]
                and on_segment((c[0], a[1]), a, b)
                and on_segment((c[0], a[1]), c, e)
            ):
                raise InputError(
                    f"unrelated wire crossing: {draft.wire_nets[i]} {a}->{b}, {draft.wire_nets[j]} {c}->{e}"
                )
            if a[0] == b[0] == c[0] == e[0] and max(min(a[1], b[1]), min(c[1], e[1])) <= min(
                max(a[1], b[1]), max(c[1], e[1])
            ):
                raise InputError("unrelated wire overlap")
            if a[1] == b[1] == c[1] == e[1] and max(min(a[0], b[0]), min(c[0], e[0])) <= min(
                max(a[0], b[0]), max(c[0], e[0])
            ):
                raise InputError("unrelated wire overlap")
    for c in design["components"]:
        key_units = resolved[c["asset"]].units
        for unit in key_units:
            x, y = draft.text_positions[(c["id"], unit)]
            for value, py in ((c["refdes"], y), (c["value"], y + 2 * PITCH)):
                width = max(635_000, len(value) * 445_000)
                box = (x - width, py - 850_000, x + width, py + 850_000)
                for a, b in draft.wires:
                    if (
                        a[0] == b[0]
                        and box[0] < a[0] < box[2]
                        and max(min(a[1], b[1]), box[1]) < min(max(a[1], b[1]), box[3])
                    ):
                        raise InputError(f"wire through text: {c['id']}")
                    if (
                        a[1] == b[1]
                        and box[1] < a[1] < box[3]
                        and max(min(a[0], b[0]), box[0]) < min(max(a[0], b[0]), box[2])
                    ):
                        raise InputError(f"wire through text: {c['id']}")
    endpoints = {p for a, b in draft.wires for p in (a, b)} | {p for _, p in draft.labels}
    for c in design["components"]:
        for pins in resolved[c["asset"]].units.values():
            for p in pins:
                if draft.point(c["id"], p.number) not in endpoints:
                    raise InputError(f"unrouted pin: {c['id']}:{p.number}")
    points = endpoints | set(draft.positions.values()) | set(draft.text_positions.values())
    if any(
        not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000) for x, y in points
    ):
        raise InputError("content exceeds A4 margin")
    bends = sum(
        1
        for i, (_, b) in enumerate(draft.wires)
        for c, e in draft.wires[i + 1 :]
        if b == c and ((draft.wires[i][0][0] == b[0]) != (c[0] == e[0]))
    )
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in draft.wires)
    if bends > max(16, 3 * len(draft.wires)):
        raise InputError("excessive wire bends")
    return {
        "body_overlap_count": 0,
        "wire_through_body_count": 0,
        "wire_through_text_count": 0,
        "unrelated_wire_crossing_count": 0,
        "unrouted_pin_count": 0,
        "page_margin_pass": True,
        "wire_count": len(draft.wires),
        "label_count": len(draft.labels),
        "bend_count": bends,
        "wire_length_mm": length / 1_000_000,
        "symbol_occurrences": len(draft.positions),
    }


def choose_text_slots(design: dict, draft: Draft, *, alternate: bool = False) -> None:
    """Choose a finite outside slot from actual text length and routed segments.

    Alternate search tries other legal slots first, retaining the original
    as fallback. The default ordering and existing callers are unchanged.
    """
    for c in design["components"]:
        if c["asset"] not in ("Device:C", "Device:R"):
            continue
        key = (c["id"], 1)
        if key not in draft.positions:
            continue
        sx, sy = draft.positions[key]
        horizontal = draft.angles.get(key, 0) in (90, 270)
        slots = [draft.text_positions[key]]
        slots += (
            [
                (sx, sy - 8 * PITCH),
                (sx, sy + 5 * PITCH),
                (sx, sy - 12 * PITCH),
                (sx, sy + 9 * PITCH),
                (sx, sy - 16 * PITCH),
            ]
            if horizontal
            else [
                (sx + 8 * PITCH, sy - 2 * PITCH),
                (sx - 8 * PITCH, sy - 2 * PITCH),
                (sx + 12 * PITCH, sy - 2 * PITCH),
                (sx - 12 * PITCH, sy - 2 * PITCH),
                (sx + 16 * PITCH, sy - 2 * PITCH),
                (sx - 16 * PITCH, sy - 2 * PITCH),
                (sx + 12 * PITCH, sy - 10 * PITCH),
                (sx - 12 * PITCH, sy - 10 * PITCH),
                (sx + 20 * PITCH, sy - 2 * PITCH),
                (sx - 20 * PITCH, sy - 2 * PITCH),
            ]
        )
        if alternate:
            original = slots[0]
            slots = [point for point in slots[1:] if point != original] + [original]
        for x, y in slots:
            clear = True
            for value, py in ((c["refdes"], y), (c["value"], y + 2 * PITCH)):
                half = max(635_000, len(value) * 445_000)
                clearance = 1_000_000
                for a, b in draft.wires:
                    if (
                        a[0] == b[0]
                        and x - half - clearance < a[0] < x + half + clearance
                        and max(min(a[1], b[1]), py - 850_000 - clearance)
                        < min(max(a[1], b[1]), py + 850_000 + clearance)
                    ):
                        clear = False
                    if (
                        a[1] == b[1]
                        and py - 850_000 - clearance < a[1] < py + 850_000 + clearance
                        and max(min(a[0], b[0]), x - half - clearance)
                        < min(max(a[0], b[0]), x + half + clearance)
                    ):
                        clear = False
            if clear:
                draft.text_positions[key] = (x, y)
                break
        else:
            raise InputError(f"no clear value/reference slot for {c['id']}")
    _place_all_component_text_slots(design, draft)


def _place_all_component_text_slots(design: dict, draft: Draft) -> None:
    """Validate every component field against transformed symbol geometry."""
    components = {component["id"]: component for component in design["components"]}
    body_rects = {}
    pin_obstacles = []
    for key, (sx, sy) in draft.positions.items():
        component = components[key[0]]
        asset = draft.resolved.get(component["asset"])
        if asset is None:
            continue
        body = asset.bodies.get(key[1]) or asset.bodies.get(0)
        if body is None:
            body_rects[key] = (sx - 3 * PITCH, sy - 3 * PITCH, sx + 3 * PITCH, sy + 3 * PITCH)
        else:
            left, top, right, bottom = body
            corners = [
                _turn(Pin("", "", "", x, y), draft.angles.get(key, 0))
                for x in (left, right)
                for y in (top, bottom)
            ]
            xs = [sx + point[0] for point in corners]
            ys = [sy + point[1] for point in corners]
            body_rects[key] = (min(xs), min(ys), max(xs), max(ys))
        for pin in asset.units.get(key[1], asset.units.get(0, ())):
            px, py = draft.point(key[0], pin.number)
            pin_obstacles.append((px - 500_000, py - 500_000, px + 500_000, py + 500_000))

    label_obstacles = [label_text_rect(net, point) for net, point in draft.labels]
    for key in sorted(draft.text_positions):
        component = components[key[0]]
        origin = draft.positions[key]
        preferred = draft.text_positions[key]
        body = body_rects.get(key)
        candidates = candidate_text_anchors(
            origin,
            preferred,
            body=body,
            longest_field=max(component["refdes"], component["value"], key=len),
        )
        obstacles = list(pin_obstacles)
        obstacles.extend(label_obstacles)
        obstacles.extend(body_rects.values())
        for other, (x, y) in draft.text_positions.items():
            if other == key:
                continue
            other_component = components[other[0]]
            obstacles.extend(
                property_envelopes(other_component["refdes"], other_component["value"], (x, y))
            )
        selected = first_clear_text_anchor(
            candidates,
            lambda anchor: property_envelopes(component["refdes"], component["value"], anchor),
            obstacles=obstacles,
            wires=draft.wires,
        )
        if selected is None:
            raise InputError(f"TEXT_SLOT_INFEASIBLE: {component['id']} unit {key[1]}")
        draft.text_positions[key] = selected


def _place_nonpassive_text_slots(design: dict, draft: Draft) -> None:
    """Compatibility wrapper retained for focused geometry tests."""
    _place_all_component_text_slots(design, draft)
