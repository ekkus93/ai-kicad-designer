"""Local geometry constructors for instance-based M2 schematic composition."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ir import InputError
from .m2a import Asset, PITCH, Pin
from .m2b import Draft, orientation_for_flow, _turn
from .m2_semantics import BlockPlan, Occurrence, SemanticPlan, SemanticPort


Point = tuple[int, int]
Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class PortAnchor:
    port: SemanticPort
    point: Point
    direction: str


@dataclass(frozen=True)
class FragmentVariant:
    id: str
    block: BlockPlan
    positions: dict[Occurrence, Point]
    angles: dict[Occurrence, int]
    text_positions: dict[Occurrence, Point]
    wires: tuple[tuple[Point, Point], ...]
    wire_nets: tuple[str, ...]
    labels: tuple[tuple[str, Point], ...]
    junctions: tuple[Point, ...]
    ports: tuple[PortAnchor, ...]
    envelope: Rect
    protected_wires: frozenset[int]
    rule_id: str = "m2e1.local.v1"
    origins: tuple[str, ...] = ()
    obstacles: tuple[Rect, ...] = field(default_factory=tuple)
    tap_segments: tuple[tuple[str, Point, Point], ...] = field(default_factory=tuple)


def _component(design: dict, component_id: str) -> dict:
    return next(c for c in design["components"] if c["id"] == component_id)


def _relationship(design: dict, relationship_id: str) -> dict:
    return next(r for r in design["relationships"] if r["id"] == relationship_id)


def _terminal_net(design: dict, component: str, pin: str) -> str:
    return next(net["id"] for net in design["nets"] if [component, pin] in net["members"])


def _body_rect(design: dict, resolved: dict[str, Asset], draft: Draft, key: Occurrence) -> Rect:
    component = _component(design, key[0])
    body = resolved[component["asset"]].bodies.get(key[1]) or resolved[
        component["asset"]
    ].bodies.get(0)
    x, y = draft.positions[key]
    if not body:
        return x - 3 * PITCH, y - 3 * PITCH, x + 3 * PITCH, y + 3 * PITCH
    left, top, right, bottom = body
    corners = [
        _turn(Pin("", "", "", xx, yy), draft.angles.get(key, 0))
        for xx in (left, right)
        for yy in (top, bottom)
    ]
    xs, ys = [x + point[0] for point in corners], [y + point[1] for point in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _envelope(design: dict, resolved: dict[str, Asset], draft: Draft) -> Rect:
    rects = [
        _body_rect(design, resolved, draft, key)
        for key in draft.positions
        if key[0] in {c["id"] for c in design["components"]}
    ]
    points = [point for wire in draft.wires for point in wire] + [
        point for _, point in draft.labels
    ]
    for key, (x, y) in draft.text_positions.items():
        component = _component(design, key[0])
        width = max(
            2 * PITCH, len(component["refdes"]) * 445_000, len(component["value"]) * 445_000
        )
        rects.append((x - width, y - PITCH, x + width, y + 3 * PITCH))
    if points:
        rects.append(
            (
                min(point[0] for point in points),
                min(point[1] for point in points),
                max(point[0] for point in points),
                max(point[1] for point in points),
            )
        )
    if not rects:
        raise InputError("FRAGMENT_EMPTY_ENVELOPE")
    gap = 2 * PITCH
    return (
        min(rect[0] for rect in rects) - gap,
        min(rect[1] for rect in rects) - gap,
        max(rect[2] for rect in rects) + gap,
        max(rect[3] for rect in rects) + gap,
    )


def _finish(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    draft: Draft,
    anchors: dict[str, tuple[Point, str]],
) -> FragmentVariant:
    if set(draft.positions) != set(block.occurrences):
        raise InputError(
            f"FRAGMENT_OWNER_MISMATCH: {block.id} expected={sorted(block.occurrences)} "
            f"actual={sorted(draft.positions)}"
        )
    ports = []
    for port in block.ports:
        suffix = port.id.rsplit(".", 1)[-1]
        if suffix not in anchors:
            raise InputError(f"FRAGMENT_PORT_MISSING: {port.id}")
        point, direction = anchors[suffix]
        if not any(net == port.net and label_point == point for net, label_point in draft.labels):
            draft.label(port.net, point)
        ports.append(PortAnchor(port, point, direction))
    obstacles = tuple(
        _body_rect(design, resolved, draft, key)
        for key in sorted(draft.positions)
        if key[0] in {component["id"] for component in design["components"]}
    )
    taps = tuple(
        (net, first, second)
        for net, (first, second) in zip(draft.wire_nets, draft.wires, strict=True)
        if any(port.net == net for port in block.ports)
    )
    return FragmentVariant(
        f"{block.id}.v0",
        block,
        dict(draft.positions),
        dict(draft.angles),
        dict(draft.text_positions),
        tuple(draft.wires),
        tuple(draft.wire_nets),
        tuple(draft.labels),
        tuple(draft.junctions),
        tuple(ports),
        _envelope(design, resolved, draft),
        frozenset(range(len(draft.wires))),
        origins=block.relationships,
        obstacles=obstacles,
        tap_segments=taps,
    )


def _new_draft(design: dict, resolved: dict[str, Asset]) -> Draft:
    return Draft(design, resolved, {}, {}, [], [], [], [], {})


def _amplifier_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    stage = next(
        r
        for r in design["relationships"]
        if r["kind"] == "amplifier" and r["id"] in block.relationships
    )
    feedback = next(
        r
        for r in design["relationships"]
        if r["kind"] == "feedback" and r["id"] in block.relationships
    )
    amp = _component(design, stage["component"])
    function = next(f for f in amp["functions"] if f["id"] == stage["function"])
    d = _new_draft(design, resolved)
    ax, ay = 70 * PITCH, 35 * PITCH
    d.add(amp["id"], ax, ay, function["unit"])
    plus = d.point(amp["id"], function["pins"]["plus"])
    minus = d.point(amp["id"], function["pins"]["minus"])
    out = d.point(amp["id"], function["pins"]["out"])
    out_net = stage["output"]
    corridor_y = minus[1] + 12 * PITCH
    sense_x = minus[0] - 5 * PITCH
    branch_x = out[0] + 9 * PITCH
    feedback_node = (sense_x, corridor_y)
    branch = (branch_x, out[1])
    feedback_resistor = feedback.get("resistor")
    if feedback_resistor:
        d.add(feedback_resistor, ax + 7 * PITCH, corridor_y, angle=90)
        left, right = d.point(feedback_resistor, "1"), d.point(feedback_resistor, "2")
        d.route(
            _terminal_net(design, feedback_resistor, "1"),
            minus,
            (sense_x, minus[1]),
            feedback_node,
            left,
        )
        d.route(out_net, right, (branch_x, corridor_y), branch, out)
    else:
        d.route(
            out_net, minus, (sense_x, minus[1]), feedback_node, (branch_x, corridor_y), branch, out
        )
    d.junctions.append(branch)
    output_end = (branch_x + 6 * PITCH, branch[1])
    d.route(out_net, branch, output_end)

    relationships = [_relationship(design, rid) for rid in block.relationships]
    series = [r for r in relationships if r["kind"] == "series"]
    shunts = [r for r in relationships if r["kind"] == "shunt"]
    bridges = [r for r in relationships if r["kind"] == "bridge"]
    anchors: dict[str, tuple[Point, str]] = {"output": (output_end, "right")}
    if block.kind == "sallen_key":
        bridge = bridges[0]
        upstream = next(r for r in series if r["output"] == bridge["first"])
        filter_relation = next(r for r in series if r is not upstream)
        shunt = shunts[0]
        first_x = ax - 56 * PITCH
        second_x = ax - 34 * PITCH
        d.add(upstream["component"], first_x, plus[1], angle=90)
        d.add(filter_relation["component"], second_x, plus[1], angle=90)
        up_left, up_right = d.point(upstream["component"], "1"), d.point(upstream["component"], "2")
        f_left, f_right = (
            d.point(filter_relation["component"], "1"),
            d.point(filter_relation["component"], "2"),
        )
        intermediate = (ax - 45 * PITCH, plus[1])
        filter_node = (plus[0] - 13 * PITCH, plus[1])
        d.route(upstream["output"], up_right, intermediate, f_left)
        d.route(filter_relation["output"], f_right, filter_node, plus)
        d.junctions.extend((intermediate, filter_node))
        d.add(shunt["component"], filter_node[0], plus[1] + 16 * PITCH)
        cap_top, cap_bottom = d.point(shunt["component"], "1"), d.point(shunt["component"], "2")
        d.route(shunt["node"], filter_node, cap_top)
        ref_end = (cap_bottom[0], cap_bottom[1] + 5 * PITCH)
        d.route(shunt["reference"], cap_bottom, ref_end)
        d.add(bridge["component"], ax - 9 * PITCH, plus[1] - 19 * PITCH, angle=90)
        bridge_left, bridge_right = (
            d.point(bridge["component"], "1"),
            d.point(bridge["component"], "2"),
        )
        d.route(bridge["first"], intermediate, (intermediate[0], bridge_left[1]), bridge_left)
        d.route(bridge["second"], bridge_right, (branch_x, bridge_right[1]), branch)
        input_end = (up_left[0] - 5 * PITCH, up_left[1])
        d.route(upstream["input"], up_left, input_end)
        anchors.update(input=(input_end, "left"), reference=(ref_end, "down"))
    elif block.kind == "inverting_amplifier":
        input_leg = series[0]
        d.add(input_leg["component"], ax - 25 * PITCH, minus[1], angle=90)
        first, second = d.point(input_leg["component"], "1"), d.point(input_leg["component"], "2")
        d.route(input_leg["output"], second, minus)
        d.junctions.append(minus)
        input_end = (first[0] - 5 * PITCH, first[1])
        d.route(input_leg["input"], first, input_end)
        reference_end = (plus[0] - 7 * PITCH, plus[1])
        d.route(stage["reference"], plus, reference_end)
        anchors.update(input=(input_end, "left"), reference=(reference_end, "left"))
    elif block.kind == "noninverting_amplifier":
        gain = shunts[0]
        d.add(gain["component"], sense_x, corridor_y + 9 * PITCH)
        top, bottom = d.point(gain["component"], "1"), d.point(gain["component"], "2")
        minus_net = gain["node"]
        d.route(minus_net, feedback_node, top)
        d.junctions.append(feedback_node)
        reference_end = (bottom[0], bottom[1] + 5 * PITCH)
        d.route(gain["reference"], bottom, reference_end)
        input_end = (plus[0] - 7 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(input=(input_end, "left"), reference=(reference_end, "down"))
    else:
        input_end = (plus[0] - 7 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(input=(input_end, "left"), reference=(input_end, "left"))
    return _finish(design, resolved, block, d, anchors)


def _package_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    rail = next(
        r
        for r in design["relationships"]
        if r["kind"] == "power_rails" and r["id"] in block.relationships
    )
    supports = [
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    ]
    d = _new_draft(design, resolved)
    amp = rail["component"]
    px, py = 35 * PITCH, 28 * PITCH
    d.add(amp, px, py, rail["unit"])
    pos, neg = d.point(amp, "8"), d.point(amp, "4")
    cap_pos = next(r for r in supports if r["supply"] == rail["positive"])
    cap_neg = next(r for r in supports if r["return"] == rail["negative"])
    d.add(cap_pos["component"], px - 17 * PITCH, py)
    d.add(cap_neg["component"], px + 17 * PITCH, py)
    cp1, cp2 = d.point(cap_pos["component"], "1"), d.point(cap_pos["component"], "2")
    cn1, cn2 = d.point(cap_neg["component"], "1"), d.point(cap_neg["component"], "2")
    pos_end = (pos[0], cp1[1])
    neg_end = (neg[0], cn2[1])
    d.route(rail["positive"], pos, pos_end, cp1)
    d.route(rail["negative"], neg, neg_end, cn2)
    ref1, ref2 = (cp2[0], cp2[1] + 5 * PITCH), (cn1[0], cn1[1] - 5 * PITCH)
    d.route(rail["reference"], cp2, ref1)
    d.route(rail["reference"], cn1, ref2)
    d.label(rail["reference"], ref1)
    d.label(rail["reference"], ref2)
    dividers = [
        r
        for r in design["relationships"]
        if r["kind"] == "reference_divider" and r["id"] in block.relationships
    ]
    if dividers:
        divider = dividers[0]
        dx = px - 34 * PITCH
        d.add(divider["upper"], dx, py - 13 * PITCH)
        d.add(divider["lower"], dx, py + 13 * PITCH)
        ut, ub = d.point(divider["upper"], "1"), d.point(divider["upper"], "2")
        lt, lb = d.point(divider["lower"], "1"), d.point(divider["lower"], "2")
        local = (dx, cp2[1])
        d.route(rail["reference"], ub, local, lt)
        d.route(rail["reference"], local, cp2)
        d.junctions.append(local)
        d.route(rail["positive"], ut, (ut[0], ut[1] - 5 * PITCH))
        d.label(rail["positive"], (ut[0], ut[1] - 5 * PITCH))
        d.route(rail["negative"], lb, (lb[0], lb[1] + 5 * PITCH))
        d.label(rail["negative"], (lb[0], lb[1] + 5 * PITCH))
        ref1 = local
    anchors = {
        "positive": (pos_end, "up"),
        "negative": (neg_end, "down"),
        "reference": (ref1, "down"),
    }
    return _finish(design, resolved, block, d, anchors)


def _power_stage_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    stage = next(
        r
        for r in design["relationships"]
        if r["kind"] == "power_stage" and r["id"] in block.relationships
    )
    supports = [
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    ]
    d = _new_draft(design, resolved)
    sx, sy = 35 * PITCH, 25 * PITCH
    d.add(
        stage["component"],
        sx,
        sy,
        angle=orientation_for_flow(
            resolved[_component(design, stage["component"])["asset"]],
            stage["pins"]["input"],
            stage["pins"]["output"],
            "right",
        ),
    )
    pin_in, pin_out, pin_ref = (
        d.point(stage["component"], stage["pins"][name])
        for name in ("input", "output", "reference")
    )
    for relation, x, rail in (
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["input"]),
            sx - 18 * PITCH,
            stage["input"],
        ),
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["output"]),
            sx + 18 * PITCH,
            stage["output"],
        ),
    ):
        d.add(relation["component"], x, sy + 18 * PITCH)
        rail_pin = d.point(relation["component"], "1")
        ref_pin = d.point(relation["component"], "2")
        node = (rail_pin[0], sy)
        target = pin_in if rail == stage["input"] else pin_out
        d.route(rail, target, node, rail_pin)
        d.junctions.append(node)
        ref_end = (ref_pin[0], sy + 30 * PITCH)
        d.route(stage["reference"], ref_pin, ref_end)
        d.label(stage["reference"], ref_end)
    in_end = (pin_in[0] - 12 * PITCH, pin_in[1])
    out_end = (pin_out[0] + 12 * PITCH, pin_out[1])
    ref_end = (pin_ref[0], sy + 30 * PITCH)
    d.route(stage["input"], pin_in, in_end)
    d.route(stage["output"], pin_out, out_end)
    d.route(stage["reference"], pin_ref, ref_end)
    return _finish(
        design,
        resolved,
        block,
        d,
        {"input": (in_end, "left"), "output": (out_end, "right"), "reference": (ref_end, "down")},
    )


def _timer_fragment(design: dict, resolved: dict[str, Asset], block: BlockPlan) -> FragmentVariant:
    timer = next(
        r
        for r in design["relationships"]
        if r["kind"] == "timer" and r["id"] in block.relationships
    )
    ladder = next(
        r
        for r in design["relationships"]
        if r["kind"] == "timing_ladder" and r["id"] in block.relationships
    )
    control = next(
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    )
    d = _new_draft(design, resolved)
    tx, ty, lx = 42 * PITCH, 38 * PITCH, 15 * PITCH
    d.add(timer["component"], tx, ty)
    p = {role: d.point(timer["component"], number) for role, number in timer["pins"].items()}
    d.add(ladder["upper"], lx, ty - 20 * PITCH)
    d.add(ladder["lower"], lx, ty)
    d.add(ladder["capacitor"], lx, ty + 24 * PITCH)
    # Keep the control bypass out of the timing-ladder/discharge corridor.
    d.add(control["component"], tx + 13 * PITCH, ty - 10 * PITCH)
    ut, ub = d.point(ladder["upper"], "1"), d.point(ladder["upper"], "2")
    lt, lb = d.point(ladder["lower"], "1"), d.point(ladder["lower"], "2")
    ct, cb = d.point(ladder["capacitor"], "1"), d.point(ladder["capacitor"], "2")
    cot, cob = d.point(control["component"], "1"), d.point(control["component"], "2")
    supply_end = (lx - 10 * PITCH, ut[1])
    d.route(timer["supply"], supply_end, ut)
    timer_supply_end = (p["supply"][0] + 5 * PITCH, p["supply"][1])
    d.route(timer["supply"], p["supply"], timer_supply_end)
    d.label(timer["supply"], timer_supply_end)
    d.route(timer["supply"], p["reset"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    d.label(timer["supply"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    discharge_y = (ub[1] + lt[1]) // 2
    discharge_x = p["discharge"][0] - 8 * PITCH
    d.route(timer["discharge"], ub, (lx, discharge_y), lt)
    d.route(
        timer["discharge"],
        (lx, discharge_y),
        (discharge_x, discharge_y),
        (discharge_x, p["discharge"][1]),
        p["discharge"],
    )
    timing_y = p["trigger"][1] + 6 * PITCH
    sense_x = p["trigger"][0] - 7 * PITCH
    d.route(timer["timing"], lb, (lx, timing_y), ct)
    d.route(
        timer["timing"],
        (lx, timing_y),
        (sense_x, timing_y),
        (sense_x, p["threshold"][1]),
        p["threshold"],
    )
    d.route(timer["timing"], (sense_x, p["trigger"][1]), p["trigger"])
    d.junctions.append((sense_x, p["trigger"][1]))
    output_end = (p["output"][0] + 12 * PITCH, p["output"][1])
    d.route(timer["output"], p["output"], output_end)
    reference_y = ty + 34 * PITCH
    reference_end = (tx + 12 * PITCH, reference_y)
    d.route(timer["reference"], cb, (lx, reference_y), reference_end)
    d.route(timer["reference"], p["reference"], (p["reference"][0], reference_y))
    d.junctions.append((p["reference"][0], reference_y))
    control_y = min(p["control"][1], cot[1]) - 5 * PITCH
    d.route(timer["control"], p["control"], (p["control"][0], control_y), (cot[0], control_y), cot)
    d.route(timer["reference"], cob, (cob[0], cob[1] + 3 * PITCH))
    d.label(timer["reference"], (cob[0], cob[1] + 3 * PITCH))
    return _finish(
        design,
        resolved,
        block,
        d,
        {
            "supply": (supply_end, "left"),
            "output": (output_end, "right"),
            "reference": (reference_end, "right"),
        },
    )


def _passive_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    relation = next(
        r
        for r in design["relationships"]
        if r["kind"] == "series" and r["id"] in block.relationships
    )
    d = _new_draft(design, resolved)
    anchors = {}
    if block.kind == "led_branch":
        polarity = next(
            r
            for r in design["relationships"]
            if r["kind"] == "polarity" and r["id"] in block.relationships
        )
        x, y = 20 * PITCH, 14 * PITCH
        d.add(relation["component"], x, y)
        first, second = d.point(relation["component"], "1"), d.point(relation["component"], "2")
        d.add(polarity["component"], x, y + 20 * PITCH, angle=90)
        anode, cathode = d.point(polarity["component"], "2"), d.point(polarity["component"], "1")
        d.route(relation["output"], second, anode)
        input_end = (first[0], first[1] - 5 * PITCH)
        reference_end = (cathode[0], cathode[1] + 5 * PITCH)
        d.route(relation["input"], first, input_end)
        d.route(polarity["cathode"], cathode, reference_end)
        anchors.update(
            input=(input_end, "up"), output=(anode, "down"), reference=(reference_end, "down")
        )
    else:
        x, y = 24 * PITCH, 15 * PITCH
        d.add(relation["component"], x, y, angle=90)
        first, second = d.point(relation["component"], "1"), d.point(relation["component"], "2")
        input_end, output_end = (first[0] - 7 * PITCH, first[1]), (second[0] + 7 * PITCH, second[1])
        d.route(relation["input"], input_end, first)
        d.route(relation["output"], second, output_end)
        anchors.update(input=(input_end, "left"), output=(output_end, "right"))
        if block.kind == "rc":
            shunt = next(
                r
                for r in design["relationships"]
                if r["kind"] == "shunt" and r["id"] in block.relationships
            )
            node = (second[0] + 4 * PITCH, second[1])
            d.add(shunt["component"], node[0], y + 18 * PITCH)
            top, bottom = d.point(shunt["component"], "1"), d.point(shunt["component"], "2")
            d.route(relation["output"], second, node, top)
            d.route(relation["output"], node, output_end)
            d.junctions.append(node)
            ref_end = (bottom[0], bottom[1] + 5 * PITCH)
            d.route(shunt["reference"], bottom, ref_end)
            anchors["reference"] = (ref_end, "down")
    return _finish(design, resolved, block, d, anchors)


def _interface_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    component_id = next(iter(block.occurrences))[0]
    d = _new_draft(design, resolved)
    d.add(component_id, 12 * PITCH, 16 * PITCH)
    anchors = {}
    for port in block.ports:
        pin = port.terminals[0][1]
        point = d.point(component_id, pin)
        end = (point[0] - 4 * PITCH, point[1])
        d.route(port.net, point, end)
        anchors[port.id.rsplit(".", 1)[-1]] = (end, "left")
    return _finish(design, resolved, block, d, anchors)


def fragment_variants(
    design: dict, resolved: dict[str, Asset], plan: SemanticPlan
) -> dict[str, tuple[FragmentVariant, ...]]:
    """Build finite local variants without inspecting unrelated blocks."""
    result = {}
    for block in plan.blocks:
        if block.kind in {
            "buffer",
            "unused_amplifier",
            "noninverting_amplifier",
            "inverting_amplifier",
            "sallen_key",
        }:
            variant = _amplifier_fragment(design, resolved, block)
        elif block.kind == "package_power":
            variant = _package_fragment(design, resolved, block)
        elif block.kind == "power_stage":
            variant = _power_stage_fragment(design, resolved, block)
        elif block.kind == "timer":
            variant = _timer_fragment(design, resolved, block)
        elif block.kind in {"series", "rc", "led_branch"}:
            variant = _passive_fragment(design, resolved, block)
        elif block.kind == "interface":
            variant = _interface_fragment(design, resolved, block)
        else:
            raise InputError(f"FRAGMENT_KIND_UNSUPPORTED: {block.id}:{block.kind}")
        result[block.id] = (variant,)
    return result
