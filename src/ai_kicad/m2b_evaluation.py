"""Implementation details for m2b evaluation."""

from __future__ import annotations

from .ir import InputError
from .m2a import PITCH, Asset, Scene
from .m2b import LOCKED_PIN_ROLES
from .m2b_layout import (
    Draft,
    choose_text_slots,
    measure,
    orientation_for_flow,
)
from .m2b_validation import assets


def compare(design: dict, observed: dict, resolved: dict[str, Asset] | None = None) -> dict:
    """Compare intended terminals with independent artifact/CLI inventories."""
    diagnostics = []
    resolved = resolved or assets()
    components = {c["id"]: c for c in design["components"]}
    by_ref = {c["refdes"]: c for c in design["components"]}
    expected_occurrences = {
        (c["refdes"], unit)
        for c in design["components"]
        for unit in (1, 2, 3)
        if c["asset"] == "Amplifier_Operational:NE5532"
    }
    expected_occurrences |= {
        (c["refdes"], 1)
        for c in design["components"]
        if c["asset"] != "Amplifier_Operational:NE5532"
    }
    expected_occurrences |= {(a["refdes"], 1) for a in design["power_assertions"]}
    if set(observed["occurrences"]) != expected_occurrences:
        diagnostics.append("physical occurrence inventory differs")
    for (ref, unit), item in observed["occurrences"].items():
        c = by_ref.get(ref)
        if c is None:
            if (
                ref not in {a["refdes"] for a in design["power_assertions"]}
                or item["lib"] != "power:PWR_FLAG"
                or set(item["pins"]) != {"1"}
            ):
                diagnostics.append(f"unexpected occurrence {ref}:{unit}")
            continue
        if item["lib"] != c["asset"]:
            diagnostics.append(f"{ref}:{unit} library differs")
            continue
        actual = item["pins"]
        if c["asset"] == "Amplifier_Operational:NE5532":
            f = next((f for f in c["functions"] if f["unit"] == unit), None)
            if f is None or set(actual) != set(f["pins"].values()):
                diagnostics.append(f"{ref}:{unit} physical pin inventory differs")
            elif any(
                actual[num]["name"]
                != {"plus": "+", "minus": "-", "positive": "V+", "negative": "V-"}.get(
                    role, actual[num]["name"]
                )
                for role, num in f["pins"].items()
            ):
                diagnostics.append(f"{ref}:{unit} actual pin polarity differs")
        elif c["asset"] == "Device:LED":
            if {n: p["name"] for n, p in actual.items()} != {"1": "K", "2": "A"}:
                diagnostics.append(f"{ref}: actual diode polarity differs")
        elif c["asset"] in LOCKED_PIN_ROLES:
            if {n: p["name"] for n, p in actual.items()} != LOCKED_PIN_ROLES[c["asset"]]:
                diagnostics.append(f"{ref}: actual locked physical pin roles differ")
        elif set(actual) != {p.number for p in resolved[c["asset"]].units[unit]}:
            diagnostics.append(f"{ref} actual pin inventory differs")
    if set(observed["xml_components"]) != set(by_ref):
        diagnostics.append("KiCad XML physical component inventory differs")
    for ref, c in by_ref.items():
        actual = observed["xml_components"].get(ref)
        wanted = {
            unit: set(o["pins"]) for (r, unit), o in observed["occurrences"].items() if r == ref
        }
        if actual is None or actual["lib"] != c["asset"] or actual["units"] != wanted:
            diagnostics.append(f"{ref} KiCad XML unit/pin inventory differs")
    expected = {
        frozenset((components[cid]["refdes"], pin) for cid, pin in n["members"])
        for n in design["nets"]
    }
    actual = {
        frozenset(tuple(member) for member in members) for members in observed["nets"].values()
    }
    if expected != actual:
        diagnostics.append("real KiCad connectivity differs")
    endpoint_positions = observed["pin_positions"]
    endpoints = {p for a, b in observed["wires"] for p in (a, b)} | {
        p for _, p in observed["labels"]
    }
    missing = sorted(
        (ref, pin)
        for (ref, pin), point in endpoint_positions.items()
        if ref in by_ref and point not in endpoints
    )
    if missing:
        diagnostics.append(f"actual pin endpoints unrouted: {missing}")

    def on_segment(point, start, end):
        return (
            start[0] == end[0] == point[0]
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        ) or (
            start[1] == end[1] == point[1]
            and min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        )

    def connected_to(start, destinations):
        reachable = {start}
        for _ in range(len(observed["wires"]) + 1):
            growth = {
                point
                for a, b in observed["wires"]
                if any(on_segment(known, a, b) for known in reachable)
                for point in (a, b)
            }
            if growth <= reachable:
                break
            reachable |= growth
        return bool(reachable & destinations)

    expected_nets = {
        net["id"]: {(components[cid]["refdes"], pin) for cid, pin in net["members"]}
        for net in design["nets"]
    }
    for assertion in design["power_assertions"]:
        flag = endpoint_positions.get((assertion["refdes"], "1"))
        net = assertion["net"]
        targets = {endpoint_positions.get(key) for key in expected_nets[net]}
        targets |= {point for name, point in observed["labels"] if name == net}
        if flag is None or not connected_to(flag, targets):
            diagnostics.append(f"{assertion['refdes']}: power assertion not on {net}")
    for ref, unit in expected_occurrences:
        if ref not in by_ref or (ref, unit) not in observed["occurrences"]:
            continue
        props = observed["occurrences"][(ref, unit)]["properties"]
        if (
            set(props) != {"Reference", "Value"}
            or props["Reference"]["value"] != ref
            or props["Value"]["value"] != by_ref[ref]["value"]
        ):
            diagnostics.append(f"{ref}:{unit} required reference/value differs")
    return {
        "status": "pass" if not diagnostics else "fail",
        "diagnostics": diagnostics,
        "expected_partitions": sorted([sorted(x) for x in expected]),
        "observed_partitions": sorted([sorted(x) for x in actual]),
    }


def active_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Construct functional stage, feedback corridor and support islands from relations."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    relations = design["relationships"]
    stages = [r for r in relations if r["kind"] == "amplifier"]
    rails = [r for r in relations if r["kind"] == "power_rails"]
    feedbacks = [r for r in relations if r["kind"] == "feedback"]
    decouplers = [r for r in relations if r["kind"] == "decoupling"]
    if len(stages) != 2 or len(rails) != 1 or len(feedbacks) != 2 or len(decouplers) != 2:
        raise InputError("unsupported active-stage relation inventory")
    active_stages = [r for r in stages if not r.get("unused")]
    active = next(
        (r for r in active_stages if r["input"] not in {s["output"] for s in active_stages}),
        active_stages[0] if active_stages else None,
    )
    parked = next((r for r in stages if r is not active), None)
    if (
        active is None
        or parked is None
        or active["component"] != parked["component"]
        or active["component"] != rails[0]["component"]
    ):
        raise InputError("unsupported active-stage function composition")
    amp = active["component"]
    component = next(c for c in design["components"] if c["id"] == amp)
    functions = {f["id"]: f for f in component["functions"]}
    af, pf = functions[active["function"]], functions[parked["function"]]
    if {af["unit"], pf["unit"]} != {1, 2} or rails[0]["unit"] != 3:
        raise InputError("unsupported function unit assignment")
    net_members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    by_pin = {member: net for net, members in net_members.items() for member in members}
    fb = next(
        (r for r in feedbacks if r["function"] == af["id"] and r["component"] == amp),
        None,
    )
    parked_fb = next(
        (r for r in feedbacks if r["function"] == pf["id"] and r["component"] == amp),
        None,
    )
    if (
        fb is None
        or parked_fb is None
        or fb["source"] != af["pins"]["out"]
        or fb["sense"] != af["pins"]["minus"]
        or parked_fb["source"] != pf["pins"]["out"]
        or parked_fb["sense"] != pf["pins"]["minus"]
    ):
        raise InputError("feedback pin roles mismatch")
    if fb["polarity"] != "negative" or parked_fb["polarity"] != "negative":
        raise InputError("positive feedback unsupported")
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    ax, ay = 100 * PITCH, 59 * PITCH
    bx, by = (ax, ay + 57 * PITCH) if parked.get("unused") else (ax + 70 * PITCH, ay)
    px, py = ax + 64 * PITCH, ay + 33 * PITCH
    d.add(amp, ax, ay, af["unit"])
    d.add(amp, bx, by, pf["unit"])
    d.add(amp, px, py, rails[0]["unit"])
    d.text_positions[(amp, rails[0]["unit"])] = (px, py - 16 * PITCH)
    plus = d.point(amp, af["pins"]["plus"])
    minus = d.point(amp, af["pins"]["minus"])
    out = d.point(amp, af["pins"]["out"])
    plus_net = by_pin[(amp, af["pins"]["plus"])]
    minus_net = by_pin[(amp, af["pins"]["minus"])]
    out_net = by_pin[(amp, af["pins"]["out"])]
    if fb["net"] != out_net:
        raise InputError("feedback source net mismatch")
    if active["output"] != out_net:
        raise InputError("amplifier output relation differs from physical output net")
    # A horizontal resistor has pin 1 to the left and pin 2 to the right.
    feedback_resistor = fb.get("resistor")
    corridor_y = minus[1] + 12 * PITCH
    sense_x = minus[0] - 5 * PITCH
    branch_x = out[0] + 9 * PITCH
    feedback_node = (sense_x, corridor_y)
    branch = (branch_x, out[1])
    if feedback_resistor:
        d.add(
            feedback_resistor,
            ax + 7 * PITCH,
            corridor_y,
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        rleft, rright = d.point(feedback_resistor, "1"), d.point(feedback_resistor, "2")
        if (
            by_pin[(feedback_resistor, "1")] != minus_net
            or by_pin[(feedback_resistor, "2")] != out_net
        ):
            raise InputError("feedback resistor terminal/net mismatch")
        d.route(minus_net, minus, (sense_x, minus[1]), feedback_node, rleft)
        d.route(out_net, rright, (branch_x, corridor_y), branch, out)
    else:
        if minus_net != out_net:
            raise InputError("direct feedback requires same source and sense net")
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
    d.route(out_net, branch, (branch_x + 7 * PITCH, branch[1]))
    d.label(out_net, (branch_x + 7 * PITCH, branch[1]))
    # Gain-reference resistor or inverting input resistor may share the sense net.
    series = [r for r in relations if r["kind"] == "series"]
    shunts = [r for r in relations if r["kind"] == "shunt"]
    gain_leg = next(
        (r for r in shunts if r["node"] == minus_net and r["component"] != feedback_resistor),
        None,
    )
    input_leg = next((r for r in series if r["output"] == minus_net), None)
    input_filter = next((r for r in series if r["output"] == plus_net), None)
    upstream = (
        next((r for r in series if r["output"] == input_filter["input"]), None)
        if input_filter
        else None
    )
    bridges = [r for r in relations if r["kind"] == "bridge"]
    if bridges and (
        len(bridges) != 1
        or upstream is None
        or bridges[0]["first"] != upstream["output"]
        or bridges[0]["second"] != out_net
    ):
        raise InputError("bridge does not compose with the signal path and output")
    accepted_input = (
        input_leg["input"] if input_leg else input_filter["output"] if input_filter else plus_net
    )
    if active["input"] != accepted_input:
        raise InputError("amplifier input relation does not match semantic stage port")
    if gain_leg and input_leg:
        raise InputError("unsupported simultaneous gain and inverting input legs")
    if gain_leg:
        d.add(
            gain_leg["component"],
            sense_x,
            corridor_y + 9 * PITCH,
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "down"),
        )
        d.text_positions[(gain_leg["component"], 1)] = (
            sense_x - 8 * PITCH,
            corridor_y + 5 * PITCH,
        )
        top, bottom = (
            d.point(gain_leg["component"], "1"),
            d.point(gain_leg["component"], "2"),
        )
        d.route(minus_net, feedback_node, top)
        d.junctions.append(feedback_node)
        d.route(gain_leg["reference"], bottom, (bottom[0], bottom[1] + 5 * PITCH))
        d.label(gain_leg["reference"], (bottom[0], bottom[1] + 5 * PITCH))
    if input_leg:
        d.add(
            input_leg["component"],
            ax - 25 * PITCH,
            minus[1],
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        pin1, pin2 = (
            d.point(input_leg["component"], "1"),
            d.point(input_leg["component"], "2"),
        )
        d.route(minus_net, pin2, minus)
        d.junctions.append(minus)
        d.route(input_leg["input"], pin1, (pin1[0] - 5 * PITCH, pin1[1]))
        d.label(input_leg["input"], (pin1[0] - 5 * PITCH, pin1[1]))
    if input_filter:
        d.add(
            input_filter["component"],
            ax - 34 * PITCH,
            plus[1],
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        rin, rout = (
            d.point(input_filter["component"], "1"),
            d.point(input_filter["component"], "2"),
        )
        cap_relation = next((r for r in shunts if r["node"] == plus_net), None)
        if cap_relation is None:
            raise InputError("input filter lacks shunt relation")
        node = (plus[0] - 13 * PITCH, plus[1])
        d.add(cap_relation["component"], node[0], plus[1] + 16 * PITCH)
        cap_top, cap_bottom = (
            d.point(cap_relation["component"], "1"),
            d.point(cap_relation["component"], "2"),
        )
        d.route(plus_net, rout, node, plus)
        d.route(plus_net, node, cap_top)
        d.junctions.append(node)
        d.route(
            cap_relation["reference"],
            cap_bottom,
            (cap_bottom[0], cap_bottom[1] + 5 * PITCH),
        )
        d.label(cap_relation["reference"], (cap_bottom[0], cap_bottom[1] + 5 * PITCH))
        if upstream:
            up_component = upstream["component"]
            up_asset = resolved[
                next(c for c in design["components"] if c["id"] == up_component)["asset"]
            ]
            d.add(
                up_component,
                ax - 56 * PITCH,
                plus[1],
                angle=orientation_for_flow(up_asset, "1", "2", "right"),
            )
            upstream_left, upstream_right = (
                d.point(up_component, "1"),
                d.point(up_component, "2"),
            )
            bridge_node = (ax - 45 * PITCH, plus[1])
            d.route(input_filter["input"], upstream_right, bridge_node, rin)
            d.junctions.append(bridge_node)
            d.route(
                upstream["input"],
                upstream_left,
                (upstream_left[0] - 5 * PITCH, upstream_left[1]),
            )
            d.label(upstream["input"], (upstream_left[0] - 5 * PITCH, upstream_left[1]))
            if bridges:
                bridge = bridges[0]
                bridge_id = bridge["component"]
                bridge_asset = resolved[
                    next(c for c in design["components"] if c["id"] == bridge_id)["asset"]
                ]
                bridge_y = plus[1] - 19 * PITCH
                d.add(
                    bridge_id,
                    ax - 9 * PITCH,
                    bridge_y,
                    angle=orientation_for_flow(bridge_asset, "1", "2", "right"),
                )
                bridge_left, bridge_right = (
                    d.point(bridge_id, "1"),
                    d.point(bridge_id, "2"),
                )
                d.route(
                    bridge["first"],
                    bridge_node,
                    (bridge_node[0], bridge_y),
                    bridge_left,
                )
                d.route(bridge["second"], bridge_right, (branch_x, bridge_y), branch)
        else:
            d.route(input_filter["input"], rin, (rin[0] - 5 * PITCH, rin[1]))
            d.label(input_filter["input"], (rin[0] - 5 * PITCH, rin[1]))
    elif not input_leg:
        d.route(plus_net, plus, (plus[0] - 7 * PITCH, plus[1]))
        d.label(plus_net, (plus[0] - 7 * PITCH, plus[1]))
    if input_leg:
        d.route(plus_net, plus, (plus[0] - 7 * PITCH, plus[1]))
        d.label(plus_net, (plus[0] - 7 * PITCH, plus[1]))
    # The other function may be parked or a second active stage in the same package.
    pout = d.point(amp, pf["pins"]["out"])
    pminus = d.point(amp, pf["pins"]["minus"])
    pplus = d.point(amp, pf["pins"]["plus"])
    parked_net = by_pin[(amp, pf["pins"]["out"])]
    if parked_net != by_pin[(amp, pf["pins"]["minus"])]:
        raise InputError("parked unit feedback disconnected")
    pcorridor = pminus[1] + 9 * PITCH
    pbranch = (pout[0] + 7 * PITCH, pout[1])
    d.route(
        parked_net,
        pminus,
        (pminus[0] - 5 * PITCH, pminus[1]),
        (pminus[0] - 5 * PITCH, pcorridor),
        (pbranch[0], pcorridor),
        pbranch,
        pout,
    )
    if parked.get("unused"):
        d.route(by_pin[(amp, pf["pins"]["plus"])], pplus, (pplus[0] - 5 * PITCH, pplus[1]))
        d.label(by_pin[(amp, pf["pins"]["plus"])], (pplus[0] - 5 * PITCH, pplus[1]))
    else:
        if parked["input"] != out_net or parked["output"] != parked_net:
            raise InputError(f"stages {active['id']}, {parked['id']}: incompatible ports")
        first_out = (branch_x + 7 * PITCH, branch[1])
        second_in = (pplus[0] - 5 * PITCH, pplus[1])
        d.route(out_net, first_out, (second_in[0], first_out[1]), second_in, pplus)
        second_out = (pbranch[0] + 7 * PITCH, pbranch[1])
        d.route(parked_net, pbranch, second_out)
        d.label(parked_net, second_out)
    # Power unit and split-rail decoupling are separate owned occurrences.
    pospin = d.point(amp, "8")
    negpin = d.point(amp, "4")
    positive, negative, reference = (
        rails[0]["positive"],
        rails[0]["negative"],
        rails[0]["reference"],
    )
    if by_pin[(amp, "8")] != positive or by_pin[(amp, "4")] != negative:
        raise InputError("power rail physical pin mismatch")
    cap_pos = next(
        (r for r in decouplers if r["supply"] == positive and r["return"] == reference),
        None,
    )
    cap_neg = next(
        (r for r in decouplers if r["supply"] == reference and r["return"] == negative),
        None,
    )
    if cap_pos is None or cap_neg is None:
        raise InputError("unsupported split-rail decoupling")
    d.add(cap_pos["component"], px - 17 * PITCH, py)
    d.add(cap_neg["component"], px + 17 * PITCH, py)
    cp1, cp2 = d.point(cap_pos["component"], "1"), d.point(cap_pos["component"], "2")
    cn1, cn2 = d.point(cap_neg["component"], "1"), d.point(cap_neg["component"], "2")
    pos_flag = (((cp1[0] + pospin[0]) // (2 * PITCH)) * PITCH, cp1[1])
    neg_flag = (((cn2[0] + negpin[0]) // (2 * PITCH)) * PITCH, cn2[1])
    d.route(positive, pospin, (pospin[0], cp1[1]), pos_flag, cp1)
    d.route(negative, negpin, (negpin[0], cn2[1]), neg_flag, cn2)
    d.label(positive, pospin)
    d.label(negative, negpin)
    d.route(reference, cp2, (cp2[0], cp2[1] + 5 * PITCH))
    d.label(reference, (cp2[0], cp2[1] + 5 * PITCH))
    d.route(reference, cn1, (cn1[0], cn1[1] - 5 * PITCH))
    d.label(reference, (cn1[0], cn1[1] - 5 * PITCH))
    dividers = [r for r in relations if r["kind"] == "reference_divider"]
    if dividers:
        if len(dividers) != 1 or any(
            dividers[0][role] != net
            for role, net in (
                ("positive", positive),
                ("local", reference),
                ("negative", negative),
            )
        ):
            raise InputError("reference divider and split rails disagree")
        divider = dividers[0]
        divider_x = px - 37 * PITCH
        d.add(divider["upper"], divider_x, py - 13 * PITCH)
        d.add(divider["lower"], divider_x, py + 13 * PITCH)
        upper_top, upper_bottom = (
            d.point(divider["upper"], "1"),
            d.point(divider["upper"], "2"),
        )
        lower_top, lower_bottom = (
            d.point(divider["lower"], "1"),
            d.point(divider["lower"], "2"),
        )
        local_node = (divider_x, cp2[1])
        d.route(reference, upper_bottom, local_node, lower_top)
        d.route(reference, local_node, cp2)
        d.junctions.append(local_node)
        d.route(positive, upper_top, (divider_x, upper_top[1] - 5 * PITCH))
        d.label(positive, (divider_x, upper_top[1] - 5 * PITCH))
        d.route(negative, lower_bottom, (divider_x, lower_bottom[1] + 5 * PITCH))
        d.label(negative, (divider_x, lower_bottom[1] + 5 * PITCH))
        d.label(reference, local_node)
    # Mixed connector is a lookup island; each terminal carries its semantic net.
    connectors = [c for c in design["components"] if c["asset"].startswith("Connector_Generic:")]
    if len(connectors) != 1:
        raise InputError("active stage requires one mixed interface")
    interface = connectors[0]
    d.add(interface["id"], ax - 58 * PITCH, ay + 25 * PITCH)
    for pin in resolved[interface["asset"]].units[1]:
        net = by_pin[(interface["id"], pin.number)]
        point = d.point(interface["id"], pin.number)
        end = (point[0] - 4 * PITCH, point[1])
        d.route(net, point, end)
        d.label(net, end)
    flags = {a["net"]: a for a in design["power_assertions"]}
    required_flags = {positive, negative} if dividers else {positive, negative, reference}
    if set(flags) != required_flags:
        raise InputError("missing external supply assertions")
    for net, point in (
        (positive, pos_flag),
        (negative, neg_flag),
        (reference, (cp2[0], cp2[1] + 5 * PITCH)),
    ):
        if net in flags:
            d.positions[(flags[net]["id"], 1)] = point
            d.angles[(flags[net]["id"], 1)] = 0
    # Each component is placed once even when it belongs to several relations.
    placed = {cid for cid, _ in d.positions if cid in {c["id"] for c in design["components"]}}
    if not partial and placed != {c["id"] for c in design["components"]}:
        raise InputError(
            f"components without geometry owner: {sorted({c['id'] for c in design['components']} - placed)}"
        )
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    metrics.update(
        {
            "feedback_local_span_mm": (branch_x - sense_x) / 1_000_000,
            "input_left_of_output": plus[0] < out[0],
        }
    )
    if metrics["feedback_local_span_mm"] > 40 or not metrics["input_left_of_output"]:
        raise InputError("active motif feedback span or flow violation")
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
        {key: angle for key, angle in d.angles.items() if angle in (90, 270)},
        mirrors=d.mirrors,
    )
