"""Functional blocks of a drawn schematic, from part roles and nets (reviewer loop spec R7.2).

The partition uses part types, pin roles and net membership, never per-design names:

* ``signal_interface`` / ``power_interface``: connectors. A connector is a power interface
  when every net it carries is a rail (an asserted power net, or a supply, return or
  output pin net of a regulator, timer or op-amp power unit).
* ``regulator``: a linear regulator and the capacitors on its input and output nets.
* ``timer``: a 555 with the parts on its timing pins (2, 6, 7) and control pin (5).
* ``power_unit``: an op-amp power unit with the capacitors on its supply nets.
* ``parked``: an op-amp unit whose output reaches no other part.
* ``amplifier``: an active op-amp unit with the passives on its signal nets.
* ``indicator``: an LED with the resistors in series with it.
* ``passives``: the remaining passives, grouped by shared non-rail nets.
"""

from __future__ import annotations

from .schematic_description import _instances

Part = tuple[str, int]
TIMER_TIMING_PINS = ("2", "6", "7", "5")
REGULATOR_PINS = {"input": "1", "return": "2", "output": "3"}
OPAMP_SUPPLY_PINS = ("8", "4")


def _pin_nets(design: dict) -> dict[tuple[str, str], str]:
    refs = {item["id"]: item["refdes"] for item in design["components"]}
    return {(refs[cid], pin): net["id"] for net in design["nets"] for cid, pin in net["members"]}


def partition(design: dict, tree: list) -> list[dict]:
    """Every drawn part unit assigned to exactly one functional block."""
    assets = {item["refdes"]: item["asset"] for item in design["components"]}
    pin_net = _pin_nets(design)
    units = {(item["reference"], item["unit"]): item for item in _instances(tree)}
    nets_of = {
        key: {pin_net.get((key[0], pin["number"])) for pin in item["pins"]} - {None}
        for key, item in units.items()
    }
    rails = {item["net"] for item in design.get("power_assertions", [])}
    returns = set()
    for (reference, _unit), item in units.items():
        asset = assets.get(reference, "")
        if asset.startswith("Regulator_Linear:"):
            rails |= {pin_net.get((reference, p)) for p in REGULATOR_PINS.values()}
            returns.add(pin_net.get((reference, REGULATOR_PINS["return"])))
        elif asset.startswith("Timer:"):
            rails |= {pin_net.get((reference, p)) for p in ("8", "1")}
            returns.add(pin_net.get((reference, "1")))
        elif asset.startswith("Amplifier_Operational:") and {
            p["number"] for p in item["pins"]
        } >= set(OPAMP_SUPPLY_PINS):
            rails |= {pin_net.get((reference, p)) for p in OPAMP_SUPPLY_PINS}
    rails.discard(None)
    returns.discard(None)

    def members_on(nets: set[str], *, kinds: tuple[str, ...]) -> set[Part]:
        return {
            key
            for key in units
            if assets.get(key[0], "").split(":")[0] in kinds and nets_of[key] & nets
        }

    blocks, assigned = [], set()

    def add(role: str, members: set[Part], **extra) -> None:
        fresh = sorted(members - assigned)
        if fresh:
            assigned.update(fresh)
            blocks.append({"role": role, "members": [list(m) for m in fresh], **extra})

    for key in sorted(units):
        reference, _unit = key
        asset = assets.get(reference, "")
        if asset.startswith("Regulator_Linear:"):
            io = {pin_net.get((reference, REGULATOR_PINS[k])) for k in ("input", "output")}
            add("regulator", {key} | members_on(io, kinds=("Device",)) & _capacitors(units, assets))
        elif asset.startswith("Timer:"):
            timing = {pin_net.get((reference, p)) for p in TIMER_TIMING_PINS} - {None}
            add("timer", {key} | members_on(timing, kinds=("Device",)))
    for key in sorted(units):
        reference, _unit = key
        asset = assets.get(reference, "")
        if not asset.startswith("Amplifier_Operational:"):
            continue
        numbers = {pin["number"] for pin in units[key]["pins"]}
        if numbers >= set(OPAMP_SUPPLY_PINS):
            supply = {pin_net.get((reference, p)) for p in OPAMP_SUPPLY_PINS}
            add(
                "power_unit",
                {key} | members_on(supply, kinds=("Device",)) & _capacitors(units, assets),
            )
            continue
        signal = nets_of[key] - rails
        others = {other for other in units if other[0] != reference and nets_of[other] & signal}
        # Parked: some signal net is tied only among this unit's own pins (its output fed
        # back to its input with no load), so the unit drives nothing.
        own_only = [
            net
            for net in signal
            if not any(net in nets_of[other] for other in units if other != key)
        ]
        if own_only:
            add("parked", {key})
        elif not others:
            add("parked", {key})
        else:
            add(
                "amplifier",
                {key} | {o for o in others if assets.get(o[0], "").startswith("Device:")},
            )
    for key in sorted(units):
        if assets.get(key[0], "") == "Device:LED":
            chain = {key} | {
                other
                for other in units
                if assets.get(other[0], "") == "Device:R"
                and nets_of[other] & (nets_of[key] - rails)
            }
            add("indicator", chain)
    for key in sorted(units):
        if assets.get(key[0], "").startswith("Connector"):
            role = (
                "power_interface" if nets_of[key] and nets_of[key] <= rails else "signal_interface"
            )
            add(
                role,
                {key},
                returns=sorted(nets_of[key] & returns),
                nets=sorted(nets_of[key]),
            )
    # Remaining passives, grouped through shared non-rail nets.
    rest = [key for key in sorted(units) if key not in assigned]
    groups: list[set[Part]] = []
    for key in rest:
        joined = [g for g in groups if any(nets_of[key] & nets_of[o] - rails for o in g)]
        merged = {key}.union(*joined) if joined else {key}
        groups = [g for g in groups if g not in joined] + [merged]
    for group in groups:
        add("passives", group)
    return blocks


def _capacitors(units, assets) -> set[Part]:
    return {key for key in units if assets.get(key[0], "") == "Device:C"}


def _centre(item: dict) -> tuple[int, int]:
    body = item["body"]
    return (body[0] + body[2]) // 2, (body[1] + body[3]) // 2


def return_connector_distances(design: dict, tree: list) -> list[dict]:
    """Each return connector's distance from its power-interface block (R7.2 measure).

    The power-interface block is the supply connectors plus the regulator, timer or
    op-amp power unit their rails feed; the distance is from the return connector's body
    centre to the nearest body of that block, in millimetres. Report-only.
    """
    blocks = partition(design, tree)
    units = {(item["reference"], item["unit"]): item for item in _instances(tree)}
    interface = [
        tuple(member)
        for block in blocks
        if block["role"] in ("power_interface", "regulator", "timer", "power_unit")
        for member in block["members"]
    ]
    result = []
    for block in blocks:
        if not block.get("returns") or not block["role"].endswith("interface"):
            continue
        (member,) = block["members"]
        here = _centre(units[tuple(member)])
        others = [key for key in interface if key != tuple(member)]
        if not others:
            continue
        nearest = min(
            others,
            key=lambda key: abs(_centre(units[key])[0] - here[0])
            + abs(_centre(units[key])[1] - here[1]),
        )
        there = _centre(units[nearest])
        result.append(
            {
                "connector": member[0],
                "returns": block["returns"],
                "nearest_interface_part": nearest[0],
                "distance_mm": round((abs(there[0] - here[0]) + abs(there[1] - here[1])) / 1e6, 2),
            }
        )
    return result


def block_layout(design: dict, tree: list, slack_mm: float = 2.54) -> dict:
    """Signal order and containment of the drawn blocks (R7.2), report-only.

    Signal order: blocks are ranked by their distance, over non-rail nets, from the
    leftmost signal connector; a block further along the signal path must not sit left of
    one before it by more than `slack_mm`. Only the starting connector is ranked; the
    others are placed by the connector-flow step. Containment: no part of one block lies inside
    another block's box. Rails do not order blocks, so power units, power interfaces and
    parked units are not ranked.
    """
    blocks = partition(design, tree)
    units = {(item["reference"], item["unit"]): item for item in _instances(tree)}
    pin_net = _pin_nets(design)
    rails = {item["net"] for item in design.get("power_assertions", [])}
    for block in blocks:
        if block["role"] in ("power_unit", "power_interface", "regulator", "timer"):
            for member in block["members"]:
                for pin in units[tuple(member)]["pins"]:
                    if block["role"] in ("power_unit",):
                        rails.add(pin_net.get((member[0], pin["number"])))
    boxes = {}
    for index, block in enumerate(blocks):
        points = []
        for member in block["members"]:
            item = units[tuple(member)]
            points += [item["body"][:2], item["body"][2:]]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        boxes[index] = (min(xs), min(ys), max(xs), max(ys))
    nets_of = {
        index: {
            pin_net.get((m[0], pin["number"]))
            for m in block["members"]
            for pin in units[tuple(m)]["pins"]
        }
        - rails
        - {None}
        for index, block in enumerate(blocks)
    }
    ranked = [
        i
        for i, block in enumerate(blocks)
        if block["role"] not in ("power_unit", "power_interface", "parked")
    ]
    starts = [i for i in ranked if blocks[i]["role"] == "signal_interface"]
    depth: dict[int, int] = {}
    if starts:
        first = min(starts, key=lambda i: boxes[i][0])
        # Other connectors are placed by the connector-flow step (R7.1); a return
        # connector belongs beside the input, not after the parts it returns from.
        ranked = [i for i in ranked if blocks[i]["role"] != "signal_interface" or i == first]
        depth[first] = 0
        frontier = [first]
        while frontier:
            following = []
            for i in frontier:
                for j in ranked:
                    if j not in depth and nets_of[i] & nets_of[j]:
                        depth[j] = depth[i] + 1
                        following.append(j)
            frontier = following
    order_witnesses = []
    slack = slack_mm * 1e6
    for i in depth:
        for j in depth:
            centre_i = (boxes[i][0] + boxes[i][2]) / 2
            centre_j = (boxes[j][0] + boxes[j][2]) / 2
            if (
                depth[i] < depth[j]
                and centre_j < centre_i - slack
                and blocks[i]["role"] != "signal_interface"
            ):
                order_witnesses.append(
                    {
                        "before": [m[0] for m in blocks[i]["members"]],
                        "after": [m[0] for m in blocks[j]["members"]],
                        "left_by_mm": round((centre_i - centre_j) / 1e6, 2),
                    }
                )
    intrusions = []
    for i, box in boxes.items():
        for j, block in enumerate(blocks):
            if i == j:
                continue
            for member in block["members"]:
                body = units[tuple(member)]["body"]
                centre = ((body[0] + body[2]) // 2, (body[1] + body[3]) // 2)
                if box[0] < centre[0] < box[2] and box[1] < centre[1] < box[3]:
                    intrusions.append(
                        {
                            "part": member[0],
                            "unit": member[1],
                            "inside": [m[0] for m in blocks[i]["members"]],
                            "role": blocks[i]["role"],
                        }
                    )
    return {
        "blocks": [
            {**block, "depth": depth.get(i), "box_mm": [round(v / 1e6, 2) for v in boxes[i]]}
            for i, block in enumerate(blocks)
        ],
        "signal_order_witnesses": order_witnesses,
        "intrusions": intrusions,
    }
