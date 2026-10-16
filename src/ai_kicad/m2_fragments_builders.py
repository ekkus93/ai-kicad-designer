"""Implementation details for m2 fragments builders."""

from __future__ import annotations

from .ir import InputError
from .m2_fragments import Point
from .m2_fragments_base import (
    FragmentVariant,
    _component,
    _relationship,
    _terminal_net,
)
from .m2_fragments_geometry import _finish
from .m2_geometry import (
    label_text_width,
)
from .m2_semantics import BlockPlan
from .m2a import PITCH, Asset
from .m2b import (
    Draft,
    orientation_for_flow,
)


def _new_draft(design: dict, resolved: dict[str, Asset]) -> Draft:
    return Draft(design, resolved, {}, {}, [], [], [], [], {})


def _amplifier_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    feedback_side: str = "below",
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
    corridor_sign = 1 if feedback_side == "below" else -1
    corridor_y = minus[1] + corridor_sign * 9 * PITCH
    sense_x = minus[0] - 5 * PITCH
    branch_x = out[0] + 7 * PITCH
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
            out_net,
            minus,
            (sense_x, minus[1]),
            feedback_node,
            (branch_x, corridor_y),
            branch,
            out,
        )
    d.junctions.append(branch)
    output_end = (branch_x + 4 * PITCH, branch[1])
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
        up_left, up_right = (
            d.point(upstream["component"], "1"),
            d.point(upstream["component"], "2"),
        )
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
        cap_top, cap_bottom = (
            d.point(shunt["component"], "1"),
            d.point(shunt["component"], "2"),
        )
        d.route(shunt["node"], filter_node, cap_top)
        ref_end = (cap_bottom[0], cap_bottom[1] + 5 * PITCH)
        d.route(shunt["reference"], cap_bottom, ref_end)
        d.add(bridge["component"], ax - 9 * PITCH, plus[1] - 19 * PITCH, angle=90)
        bridge_left, bridge_right = (
            d.point(bridge["component"], "1"),
            d.point(bridge["component"], "2"),
        )
        d.route(
            bridge["first"],
            intermediate,
            (intermediate[0], bridge_left[1]),
            bridge_left,
        )
        d.route(bridge["second"], bridge_right, (branch_x, bridge_right[1]), branch)
        input_end = (up_left[0] - 5 * PITCH, up_left[1])
        d.route(upstream["input"], up_left, input_end)
        anchors.update(input=(input_end, "left"), reference=(ref_end, "down"))
    elif block.kind == "inverting_amplifier":
        input_leg = series[0]
        d.add(input_leg["component"], ax - 18 * PITCH, minus[1], angle=90)
        first, second = (
            d.point(input_leg["component"], "1"),
            d.point(input_leg["component"], "2"),
        )
        d.route(input_leg["output"], second, minus)
        d.junctions.append(minus)
        input_end = (first[0] - 4 * PITCH, first[1])
        d.route(input_leg["input"], first, input_end)
        reference_end = (plus[0] - 2 * PITCH, plus[1])
        d.route(stage["reference"], plus, reference_end)
        anchors.update(input=(input_end, "left"), reference=(reference_end, "left"))
    elif block.kind == "noninverting_amplifier":
        gain = shunts[0]
        d.add(
            gain["component"],
            sense_x,
            corridor_y + corridor_sign * 9 * PITCH,
            angle=0 if corridor_sign > 0 else 180,
        )
        top, bottom = d.point(gain["component"], "1"), d.point(gain["component"], "2")
        minus_net = gain["node"]
        d.route(minus_net, feedback_node, top)
        d.junctions.append(feedback_node)
        reference_end = (bottom[0], bottom[1] + corridor_sign * 2 * PITCH)
        d.route(gain["reference"], bottom, reference_end)
        input_end = (plus[0] - 5 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(
            input=(input_end, "left"),
            reference=(reference_end, "down" if corridor_sign > 0 else "up"),
        )
    else:
        input_end = (plus[0] - 5 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(input=(input_end, "left"), reference=(input_end, "left"))
    return _finish(design, resolved, block, d, anchors)


def _package_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    reference_side: str = "down",
    compact: bool = False,
    balanced: bool = False,
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
    d.add(
        cap_pos["component"],
        px - (10 if compact else 11) * PITCH,
        py,
        angle=180 if reference_side == "up" and not compact else 0,
    )
    d.add(
        cap_neg["component"],
        px + (10 if balanced else 11) * PITCH,
        py,
        angle=180 if reference_side == "up" and compact else 0,
    )
    cp1, cp2 = d.point(cap_pos["component"], "1"), d.point(cap_pos["component"], "2")
    cn1, cn2 = d.point(cap_neg["component"], "1"), d.point(cap_neg["component"], "2")
    pos_end = (pos[0], cp1[1])
    neg_end = (neg[0], cn2[1])
    if reference_side == "up" and compact:
        # Put both support reference pins below their bodies.  Rails can then
        # reach the opposite pins from outside the reference interval.
        d.route(rail["positive"], pos, (pos[0], cp1[1]), cp1)
        pos_end = (pos[0], pos[1] - 3 * PITCH)
        d.route(rail["positive"], pos, pos_end)
        negative_side_x = cn1[0] + (4 if balanced else 5) * PITCH
        d.route(
            rail["negative"],
            neg,
            (negative_side_x, neg[1]),
            (negative_side_x, cn2[1]),
            cn2,
        )
        neg_end = (negative_side_x, neg[1] + 3 * PITCH)
        d.route(rail["negative"], (negative_side_x, neg[1]), neg_end)
    elif reference_side == "up":
        positive_side_x = cn1[0] + 5 * PITCH
        d.route(
            rail["positive"],
            pos,
            (positive_side_x, pos[1]),
            (positive_side_x, cp1[1]),
            cp1,
        )
        pos_end = (positive_side_x, cp2[1] - 2 * PITCH)
    else:
        d.route(rail["positive"], pos, pos_end, cp1)
    if not (reference_side == "up" and compact):
        d.route(rail["negative"], neg, neg_end, cn2)
    ref1, ref2 = cp2, cn1
    # Both decoupler returns belong to the same physical reference island.
    # The right-hand capacitor's upper pin needs a side approach so the wire
    # does not pass through its body or the package power unit.
    if reference_side == "up":
        d.route(rail["reference"], cp2, cn1)
    else:
        reference_bottom = max(cp2[1], cn1[1]) + 9 * PITCH
        reference_right = cn1[0] + 5 * PITCH
        d.route(
            rail["reference"],
            cp2,
            (cp2[0], reference_bottom),
            (reference_right, reference_bottom),
            (reference_right, cn1[1]),
            cn1,
        )
    d.label(rail["reference"], ref1)
    d.label(rail["reference"], ref2)
    dividers = [
        r
        for r in design["relationships"]
        if r["kind"] == "reference_divider" and r["id"] in block.relationships
    ]
    if dividers:
        divider = dividers[0]
        # Keep the divider beside the support capacitor when measured text,
        # body and protected conductors permit it.  The shorter local
        # reference interval leaves a useful budget for global distribution.
        dx = px - (19 if compact else 34) * PITCH
        divider_offset = 8 if compact else 13
        d.add(divider["upper"], dx, py - divider_offset * PITCH)
        d.add(divider["lower"], dx, py + divider_offset * PITCH)
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
    positive_anchor = pos_end
    positive_direction = "up"
    anchors = {
        "positive": (positive_anchor, positive_direction),
        "negative": (neg_end, "down"),
        "reference": (
            ref1,
            "left"
            if dividers or (reference_side == "up" and compact)
            else ("up" if reference_side == "up" else "down"),
        ),
    }
    return _finish(
        design,
        resolved,
        block,
        d,
        anchors,
        variant_suffix=("compact_balanced_" if balanced else "compact_" if compact else "expanded_")
        + reference_side,
    )


def _reference_divider_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    compact: bool = False,
) -> FragmentVariant:
    """Local two-resistor reference producer with an exposed output island."""
    divider = next(
        relation
        for relation in design["relationships"]
        if relation["kind"] == "reference_divider" and relation["id"] in block.relationships
    )
    draft = _new_draft(design, resolved)
    x, upper_y = 35 * PITCH, 25 * PITCH
    lower_y = upper_y + (14 if compact else 18) * PITCH
    draft.add(divider["upper"], x, upper_y)
    draft.add(divider["lower"], x, lower_y)
    upper_positive = draft.point(divider["upper"], "1")
    upper_reference = draft.point(divider["upper"], "2")
    lower_reference = draft.point(divider["lower"], "1")
    lower_negative = draft.point(divider["lower"], "2")
    if upper_reference[0] != lower_reference[0]:
        raise InputError(f"FRAGMENT_DIVIDER_PIN_ALIGNMENT: {block.id}")
    reference_anchor = (
        upper_reference[0],
        (upper_reference[1] + lower_reference[1]) // (2 * PITCH) * PITCH,
    )
    draft.route(divider["local"], upper_reference, lower_reference)
    draft.junctions.append(reference_anchor)
    return _finish(
        design,
        resolved,
        block,
        draft,
        {
            "positive": (upper_positive, "up"),
            "negative": (lower_negative, "down"),
            "reference": (reference_anchor, "left"),
        },
        variant_suffix="compact" if compact else "expanded",
    )


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
    rail_nodes = {}
    for relation, x, rail in (
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["input"]),
            sx - 10 * PITCH,
            stage["input"],
        ),
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["output"]),
            sx + 10 * PITCH,
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
        d.label(stage["reference"], ref_pin)
        rail_nodes[rail] = node
    # The support branch continues beyond each regulator pin.  Its certified
    # external gateway therefore belongs at the outer junction, not midway
    # along the protected local support conductor.
    in_end = rail_nodes[stage["input"]]
    out_end = rail_nodes[stage["output"]]
    ref_end = pin_ref
    return _finish(
        design,
        resolved,
        block,
        d,
        {
            "input": (in_end, "left"),
            "output": (out_end, "right"),
            "reference": (ref_end, "down"),
        },
    )


def _timer_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    compact: bool = False,
    narrow: bool = False,
) -> FragmentVariant:
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
    # The compact construction keeps the same ordered ladder terminals while
    # using separate measured body/text clearances for a shorter support band.
    d.add(ladder["upper"], lx, ty - (14 if compact else 20) * PITCH)
    d.add(ladder["lower"], lx, ty)
    d.add(ladder["capacitor"], lx, ty + (17 if compact else 24) * PITCH)
    # Keep the control bypass out of the timing-ladder/discharge corridor.
    d.add(control["component"], tx - 14 * PITCH, ty - (14 if compact else 18) * PITCH)
    ut, ub = d.point(ladder["upper"], "1"), d.point(ladder["upper"], "2")
    lt, lb = d.point(ladder["lower"], "1"), d.point(ladder["lower"], "2")
    ct, cb = d.point(ladder["capacitor"], "1"), d.point(ladder["capacitor"], "2")
    cot, cob = d.point(control["component"], "1"), d.point(control["component"], "2")
    supply_end = ut
    d.label(timer["supply"], supply_end)
    timer_supply_end = p["supply"]
    # Keep the local terminal label when the final gateway has no label.
    # _finish removes it only when it emits the redundant same-net gateway label.
    d.label(timer["supply"], timer_supply_end)
    reset_clearance = ((label_text_width(timer["supply"]) + PITCH - 1) // PITCH) * PITCH
    reset_label = (p["reset"][0] - reset_clearance, p["reset"][1])
    d.route(timer["supply"], p["reset"], reset_label)
    d.label(timer["supply"], reset_label)
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
    output_end = (p["output"][0] + (6 if narrow else 12) * PITCH, p["output"][1])
    d.route(timer["output"], p["output"], output_end)
    # Reference support terminals are typed rail contacts, not part of the
    # protected timing/discharge path.  Keep the timer terminal's gateway
    # explicit and avoid a long cosmetic bottom bus between independent
    # support returns.
    d.label(timer["reference"], cb)
    reference_end = p["reference"]
    control_y = min(p["control"][1], cot[1]) - 5 * PITCH
    d.route(
        timer["control"],
        p["control"],
        (p["control"][0], control_y),
        (cot[0], control_y),
        cot,
    )
    d.label(timer["reference"], cob)
    return _finish(
        design,
        resolved,
        block,
        d,
        {
            "supply": (timer_supply_end, "up"),
            "output": (output_end, "right"),
            "reference": (reference_end, "right"),
        },
    )


def _passive_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan, *, compact: bool = False
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
        first, second = (
            d.point(relation["component"], "1"),
            d.point(relation["component"], "2"),
        )
        d.add(polarity["component"], x, y + (9 if compact else 12) * PITCH, angle=90)
        anode, cathode = (
            d.point(polarity["component"], "2"),
            d.point(polarity["component"], "1"),
        )
        d.route(relation["output"], second, anode)
        input_end = (first[0], first[1] - (4 if compact else 5) * PITCH)
        reference_end = cathode
        d.route(relation["input"], first, input_end)
        anchors.update(
            input=(input_end, "up"),
            output=(anode, "left"),
            reference=(reference_end, "down"),
        )
    else:
        x, y = 24 * PITCH, 15 * PITCH
        d.add(relation["component"], x, y, angle=90)
        first, second = (
            d.point(relation["component"], "1"),
            d.point(relation["component"], "2"),
        )
        input_end, output_end = (
            (first[0] - 7 * PITCH, first[1]),
            (second[0] + 7 * PITCH, second[1]),
        )
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
            d.add(shunt["component"], node[0], y + (8 if compact else 18) * PITCH)
            top, bottom = (
                d.point(shunt["component"], "1"),
                d.point(shunt["component"], "2"),
            )
            d.route(relation["output"], second, node, top)
            d.route(relation["output"], node, output_end)
            d.junctions.append(node)
            ref_end = (bottom[0], bottom[1] + (2 if compact else 5) * PITCH)
            d.route(shunt["reference"], bottom, ref_end)
            anchors["reference"] = (ref_end, "down")
    return _finish(design, resolved, block, d, anchors)


def _interface_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    mirrored: bool = False,
) -> FragmentVariant:
    """Build a measured connector motif with an outward horizontal gateway.

    The mirrored family gives passive signal interfaces a generic inward-facing
    alternative when a direct visible route is legal. Both orientations remain
    independently certified and participate in the same bounded local-variant
    budget; no remote topology or fixture identity is inspected here.
    """
    component_id = next(iter(block.occurrences))[0]
    d = _new_draft(design, resolved)
    d.add(component_id, 12 * PITCH, 16 * PITCH, angle=180 if mirrored else 0)
    anchors = {}
    direction = "right" if mirrored else "left"
    offset = 2 * PITCH if mirrored else -2 * PITCH
    for port in block.ports:
        pin = port.terminals[0][1]
        point = d.point(component_id, pin)
        end = (point[0] + offset, point[1])
        d.route(port.net, point, end)
        anchors[port.id.rsplit(".", 1)[-1]] = (end, direction)
    return _finish(design, resolved, block, d, anchors)
