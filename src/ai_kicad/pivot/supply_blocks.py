"""Supply and return blocks for any circuit, under brief v11 (reviewer loop spec R7.4).

* Decoupling and bypass capacitors (a capacitor from a supply pin's net, or a 555's control
  pin, to the return) move beside the pin they serve, as a unit with their local return
  symbol and private wiring.
* In a power block (a power unit, regulator or timer with its capacitors), return glyphs
  point down and positive-supply arrows point up where they fit; a sideways one is turned.
  A supply arrow never points down (the brief's power-symbol direction check), so a
  negative rail keeps its direction, and its arrows only have to agree with each other.

Each change is validated like a block move: the observer and field checks, then a full
scratch assessment in which no passing check may fail.
"""

from __future__ import annotations

from typing import Callable

from ai_kicad.m2_transform import transform_library_point
from ai_kicad.sexpr import children, parse

from .block_moves import GRID, _replace_text, _snap, _try_moves, _units
from .blocks import _pin_nets, partition
from .power_symbols import (
    GLYPH_TIPS,
    _angle_for,
    _sign,
    power_symbol_collisions,
    power_symbols,
)

# A capacitor is beside its pin when its pin is within this many millimetres of it, on a
# direct wire (the 25.4 mm reach the field-locality check uses); a moved one keeps at
# least MINIMUM_MM from the pin so it never sits on the part.
BESIDE_MM = 25.4
MINIMUM_MM = 5.08
# How far toward its pin a capacitor is tried, in grid steps.
TOWARD_REACH = range(1, 21)
OPAMP_SUPPLY = {"8": "positive", "4": "negative"}


def served_pins(design: dict, tree: list) -> list[dict]:
    """Each decoupling or bypass capacitor, the pin it serves, and its return net."""
    assets = {item["refdes"]: item["asset"] for item in design["components"]}
    pin_net = _pin_nets(design)
    units = {(i["reference"], i["unit"]): i for i in _units_tree(tree)}
    supply_pins: dict[str, list[tuple[str, str, str]]] = {}
    returns: set[str] = set()
    rails = {item["net"] for item in design.get("power_assertions", [])}
    for (reference, _unit), item in units.items():
        asset = assets.get(reference, "")
        numbers = {pin["number"] for pin in item["pins"]}
        roles: dict[str, str] = {}
        if asset.startswith("Amplifier_Operational:") and numbers >= set(OPAMP_SUPPLY):
            roles = {number: role for number, role in OPAMP_SUPPLY.items()}
        elif asset.startswith("Regulator_Linear:"):
            roles = {"1": "positive", "3": "positive"}
            returns.add(pin_net.get((reference, "2")))
        elif asset.startswith("Timer:"):
            roles = {"8": "positive", "5": "control"}
            returns.add(pin_net.get((reference, "1")))
        for number, role in roles.items():
            net = pin_net.get((reference, number))
            if net:
                supply_pins.setdefault(net, []).append((reference, number, role))
    supply_nets = set(supply_pins)
    returns |= rails - supply_nets
    returns.discard(None)
    references = reference_nets(design, supply_nets | rails)
    found = []
    for (reference, _unit), item in sorted(units.items()):
        if assets.get(reference) != "Device:C":
            continue
        nets = {pin["number"]: pin_net.get((reference, pin["number"])) for pin in item["pins"]}
        for own, net in nets.items():
            other = nets.get("2" if own == "1" else "1")
            if net in supply_pins and (other in returns or other in references):
                ic, number, role = supply_pins[net][0]
                found.append(
                    {
                        "capacitor": reference,
                        "pin": own,
                        "serves": f"{ic}.{number}",
                        "role": role,
                        "net": net,
                        "return_net": other,
                        # A divider midpoint, not a return rail: supply-to-reference.
                        "return_kind": "reference" if other in references else "rail",
                    }
                )
                break
    return found


def reference_nets(design: dict, endpoints: set[str]) -> set[str]:
    """Divider midpoints: nets joined through resistors to two different supply or rail
    nets (B12's VREF between VPLUS and VMINUS). Read from the circuit, not net names."""
    assets = {item["id"]: item["asset"] for item in design["components"]}
    pins: dict[str, dict[str, str]] = {}
    for net in design["nets"]:
        for component, pin in net["members"]:
            pins.setdefault(component, {})[pin] = net["id"]
    found = set()
    for net in design["nets"]:
        if net["id"] in endpoints:
            continue
        reached = set()
        for component, pin in net["members"]:
            if assets.get(component) != "Device:R":
                continue
            other = pins[component].get("2" if pin == "1" else "1")
            if other in endpoints:
                reached.add(other)
        if len(reached) >= 2:
            found.add(net["id"])
    return found


def _units_tree(tree: list) -> list[dict]:
    from .schematic_description import _instances

    return _instances(tree)


def _point(units: dict, name: str):
    reference, number = name.split(".")
    for (ref, _unit), item in units.items():
        if ref == reference:
            for pin in item["pins"]:
                if pin["number"] == number:
                    return pin["point"]
    raise KeyError(name)


def capacitor_distances(design: dict, text: str) -> list[dict]:
    """Each decoupling or bypass capacitor's pin distance from the pin it serves (mm)."""
    tree = parse(text)
    units = _units(text)
    rows = []
    for item in served_pins(design, tree):
        here = _point(units, f"{item['capacitor']}.{item['pin']}")
        there = _point(units, item["serves"])
        rows.append(
            {
                **item,
                "distance_mm": round((abs(here[0] - there[0]) + abs(here[1] - there[1])) / 1e6, 2),
                "direct": _direct(tree, design, item),
            }
        )
    return rows


def _direct(tree: list, design: dict, item: dict) -> bool:
    """The capacitor's pin reaches the served pin by wire with at most a grid step of
    detour (a pin joined only through power symbols has no wire path and is not direct)."""
    from .net_detours import pin_pair_detours

    nets = _pin_nets(design)
    inventory = []
    for unit in _units_tree(tree):
        for pin in unit["pins"]:
            net = nets.get((unit["reference"], pin["number"]))
            if net is not None:
                inventory.append(
                    {
                        "net": net,
                        "reference": unit["reference"],
                        "pin": pin["number"],
                        "x_mm": pin["point"][0] / 1e6,
                        "y_mm": pin["point"][1] / 1e6,
                    }
                )
    pair = sorted([f"{item['capacitor']}.{item['pin']}", item["serves"]])
    for row in pin_pair_detours(tree, inventory):
        if sorted(row["pins"]) == pair:
            return row["excess_mm"] <= 2.54
    return False


def power_block_directions(design: dict, text: str) -> list[dict]:
    """Power symbols drawn within a power block's area, with their direction and role."""
    tree = parse(text)
    units = _units(text)
    pin_net = _pin_nets(design)
    positive, negative = set(), set()
    for block in partition(design, tree):
        if block["role"] not in ("power_unit", "regulator", "timer"):
            continue
        for member in block["members"]:
            for pin in units[tuple(member)]["pins"]:
                net = pin_net.get((member[0], pin["number"]))
                role = OPAMP_SUPPLY.get(pin["number"]) if block["role"] == "power_unit" else None
                if block["role"] == "timer" and pin["number"] == "8":
                    role = "positive"
                if block["role"] == "regulator" and pin["number"] in ("1", "3"):
                    role = "positive"
                if role == "positive":
                    positive.add(net)
                elif role == "negative":
                    negative.add(net)
    boxes = []
    for block in partition(design, tree):
        if block["role"] not in ("power_unit", "regulator", "timer"):
            continue
        points = []
        for member in block["members"]:
            body = units[tuple(member)]["body"]
            points += [body[:2], body[2:]]
            points += [pin["point"] for pin in units[tuple(member)]["pins"]]
        margin = 5 * GRID
        boxes.append(
            (
                min(p[0] for p in points) - margin,
                min(p[1] for p in points) - margin,
                max(p[0] for p in points) + margin,
                max(p[1] for p in points) + margin,
            )
        )
    rows = []
    for item in power_symbols(tree):
        x, y = item["point"]
        if not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes):
            continue
        tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
        direction = (_sign(tip[0]), _sign(tip[1]))
        if item["lib_id"] == "power:GND":
            role, wanted = "return", (0, 1)
        elif item["net"] in positive:
            role, wanted = "positive", (0, -1)
        elif item["net"] in negative:
            role, wanted = "negative", None
        else:
            role, wanted = "other", None
        rows.append(
            {
                "symbol": item["reference"],
                "net": item["net"],
                "role": role,
                "direction": direction,
                "consistent": wanted is None or direction == wanted,
            }
        )
    return rows


def _reaim(
    text: str, reference: str, direction: tuple[int, int], stub: int = 0, rise: int = 0
) -> str:
    """Redraw one power symbol at its connection point pointing along `direction`, with
    its rail name placed beyond the new glyph tip; on a horizontal stub of `stub` nm, or
    first `rise` nm straight along `direction` and then that stub."""
    from ai_kicad.sexpr import one

    from .power_symbols import _append_forms, _instance, _without_forms

    tree = parse(text)
    (item,) = [s for s in power_symbols(tree) if s["reference"] == reference]
    instances = [n for symbol in children(tree, "symbol") for n in children(symbol, "instances")]
    project_node = one(instances[0], "project")
    project = (project_node[1], one(project_node, "path")[1])
    remaining = "".join(
        _without_forms(
            text,
            lambda node: node[0] == "symbol"
            and any(p[1] == "Reference" and p[2] == reference for p in children(node, "property")),
        )
    )
    angle = _angle_for(item["lib_id"], direction)
    if not stub and not rise:
        return _append_forms(
            remaining,
            [_instance(item["lib_id"], reference, item["net"], item["point"], angle, project)],
        )
    # A short horizontal stub from the connection point (after a rise along the glyph's
    # direction, if any), with the symbol at its end.
    from .power_symbols import _wire_form

    corner = (item["point"][0] + direction[0] * rise, item["point"][1] + direction[1] * rise)
    end = (corner[0] + stub, corner[1])
    path = [item["point"], corner, end]
    return _append_forms(
        remaining,
        [
            *(_wire_form(a, b, item["net"]) for a, b in zip(path, path[1:]) if a != b),
            _instance(item["lib_id"], reference, item["net"], end, angle, project),
        ],
    )


def _redraw_capacitor(
    text: str,
    name: str,
    pin: str,
    angle: int,
    target: tuple[int, int],
    serves: tuple[int, int],
    sideways: int = 2,
    route: list[tuple[int, int]] | None = None,
) -> str:
    """Redraw a bypass capacitor: rotated to `angle`, its pin `pin` at `target`, wired
    straight to the served pin (or along `route`, its corners from the served pin to
    `target`), and a fresh return symbol on its other pin."""
    import re

    from ai_kicad.m2_geometry import point_on_segment
    from ai_kicad.sexpr import one

    from .power_symbols import _append_forms, _forms, _instance, _wire_form
    from .schematic_review_native import (
        _connect_point_groups,
        _top_level_forms,
        _translate_block,
        _wire_trees,
    )

    tree = parse(text)
    units = _units(text)
    (key,) = [k for k in units if k[0] == name]
    old_pins = {p["number"]: p["point"] for p in units[key]["pins"]}
    other = "2" if pin == "1" else "1"
    symbols = [s for s in power_symbols(tree)]
    segments, owners, roots = _wire_trees(tree)
    # The capacitor's own wiring: wire trees touching its pins that reach no other part.
    others = {p["point"] for k, u in units.items() if k[0] != name for p in u["pins"]}
    private = set()
    for point in old_pins.values():
        for segment, root in zip(segments, roots):
            if point_on_segment(point, *segment):
                touched = {
                    q
                    for q in others
                    if any(
                        point_on_segment(q, *seg) for seg, r in zip(segments, roots) if r == root
                    )
                }
                if touched == {serves} or not touched:
                    private.add(root)
    removed = {owner for owner, root in zip(owners, roots) if root in private}

    def on_private(point) -> bool:
        return any(
            point_on_segment(point, *seg) for seg, root in zip(segments, roots) if root in private
        )

    returning = [s for s in symbols if s["point"] == old_pins[other] or on_private(s["point"])]
    if not returning:
        raise ValueError(f"{name} has no return symbol to redraw")
    lib_id, net = returning[0]["lib_id"], returning[0]["net"]
    rewritten, wire_index = [], -1
    gone = {s["reference"] for s in returning}
    for start, end, node in _top_level_forms(text):
        if node[0] == "wire":
            wire_index += 1
            if wire_index in removed:
                rewritten.append((start, end, ""))
        elif node[0] == "junction":
            if on_private(
                (round(float(one(node, "at")[1]) * 1e6), round(float(one(node, "at")[2]) * 1e6))
            ):
                rewritten.append((start, end, ""))
        elif node[0] == "symbol":
            refs = [p[2] for p in children(node, "property") if p[1] == "Reference"]
            if refs and refs[0] in gone:
                rewritten.append((start, end, ""))
            elif refs and refs[0] == name:
                block = re.sub(
                    r"(\(at\s+[-+0-9.]+\s+[-+0-9.]+\s+)[-+0-9.]+\)",
                    rf"\g<1>{angle})",
                    text[start:end],
                    count=1,
                )
                rewritten.append((start, end, block))
    for start, end, block in reversed(rewritten):
        text = text[:start] + block + text[end:]
    placed = next(u for k, u in _units(text).items() if k[0] == name)
    now = {p["number"]: p["point"] for p in placed["pins"]}
    dx, dy = target[0] - now[pin][0], target[1] - now[pin][1]
    for start, end, node in _forms(text):
        if node[0] == "symbol" and any(
            p[1] == "Reference" and p[2] == name for p in children(node, "property")
        ):
            text = text[:start] + _translate_block(text[start:end], dx / 1e6, dy / 1e6) + text[end:]
            break
    return_pin = (now[other][0] + dx, now[other][1] + dy)
    if route is None:
        text = _connect_point_groups(text, sorted({target, serves}), [], "bypass capacitor")
    else:
        path = [serves, *route, target]
        text = _append_forms(
            text,
            [_wire_form(a, b, f"bypass {name}") for a, b in zip(path, path[1:]) if a != b],
        )
    instances = [
        n for symbol in children(parse(text), "symbol") for n in children(symbol, "instances")
    ]
    project_node = one(instances[0], "project")
    project = (project_node[1], one(project_node, "path")[1])
    # The return symbol points down (ground) or up (supply), on a stub when its pin faces
    # that way and the glyph would cover the capacitor.
    direction = (0, 1) if lib_id == "power:GND" else (0, -1)
    facing = (_sign(return_pin[0] - target[0]), _sign(return_pin[1] - target[1]))
    reference = sorted(gone)[0]
    forms = []
    if facing == direction:
        at = return_pin
    else:
        # Away from the capacitor first: outward along the pin, or sideways when the pin
        # faces opposite to the glyph.
        # `sideways` grid steps (signed: negative is left) for a pin facing opposite to
        # the glyph; two steps outward along any other pin.
        step = (
            (sideways * GRID, 0)
            if facing == (-direction[0], -direction[1])
            else (
                2 * GRID * facing[0],
                2 * GRID * facing[1],
            )
        )
        at = (return_pin[0] + step[0], return_pin[1] + step[1])
        forms.append(_wire_form(return_pin, at, net))
    forms.append(_instance(lib_id, reference, net, at, _angle_for(lib_id, direction), project))
    return _append_forms(text, forms)


def _outward(units: dict, name: str) -> tuple[int, int]:
    """The direction a pin leaves its part's body."""
    reference, number = name.split(".")
    for (ref, _unit), item in units.items():
        if ref != reference:
            continue
        for pin in item["pins"]:
            if pin["number"] != number:
                continue
            x, y = pin["point"]
            left, top, right, bottom = item["body"]
            if y < top:
                return (0, -1)
            if y > bottom:
                return (0, 1)
            return (-1, 0) if x < left else (1, 0)
    raise KeyError(name)


def _try_redraw(text, design, row, layout_check, fields_ok, native_ok, skip):
    """Redraw a bypass capacitor straight out from the pin it serves (spec R7.4).

    Spots run along the direction the served pin points, nearest first; at each, the
    capacitor is turned so the right pin faces the served pin, and its return symbol sits
    on its other pin, or on a stub to either side when that pin faces away from where the
    glyph must point. The first spot that every check accepts is used.
    """
    units = _units(text)
    there = _point(units, row["serves"])
    out = _outward(units, row["serves"])
    tried = 0
    for steps in range(4, 11):
        spot = (there[0] + out[0] * steps * GRID, there[1] + out[1] * steps * GRID)
        for angle in (180, 0, 90, 270):
            for sideways in (-2, 2, -3, 3, -4, 4):
                label = (
                    f"redraw at {spot[0] / 1e6:.2f},{spot[1] / 1e6:.2f} turned {angle}, "
                    f"return stub {sideways * 1.27:+.2f} mm"
                )
                if f"{row['capacitor']}|{label}" in skip:
                    continue
                try:
                    candidate = _redraw_capacitor(
                        text, row["capacitor"], row["pin"], angle, spot, there, sideways
                    )
                except (ValueError, KeyError):
                    continue
                # Cheap geometry first: the observer, the capacitor's text placed again,
                # every field check and power-symbol clearance; then a full assessment.
                if layout_check(candidate):
                    continue
                key = next(k for k in _units(candidate) if k[0] == row["capacitor"])
                candidate = _replace_text(candidate, key, layout_check, fields_ok)
                if candidate is None or power_symbol_collisions(candidate):
                    continue
                check = next(
                    r
                    for r in capacitor_distances(design, candidate)
                    if r["capacitor"] == row["capacitor"]
                )
                if not check["direct"]:
                    continue
                tried += 1
                if tried > 12:
                    return None
                if native_ok and native_ok(candidate):
                    continue
                return candidate, label
    return None


# Bounded search for a route that turns away from a neighbouring pin (spec R7.4).
DOGLEG_GEOMETRIC_BUDGET = 12
DOGLEG_NATIVE_BUDGET = 3


# Close runs this near the served pin are the capacitor's to fix.
NEAR_MM = 10.16


def _served_exposure(text: str, nets: dict, net: str, near: tuple[int, int]) -> float:
    """Close parallel runs of a net beside other nets within NEAR_MM of a point, in mm,
    counted only for a net pair with a sustained run there."""
    from .connector_flow import current_inventory
    from .parallel_exposure import parallel_exposure

    total = 0.0
    for r in parallel_exposure(parse(text), current_inventory(text, nets)):
        if net not in r["nets"]:
            continue
        local = []
        for w in r["witnesses"]:
            at, (low, high) = w["at_mm"] * 1e6, (v * 1e6 for v in w["from_mm"])
            x_span, y_span = (
                ((at, at), (low, high)) if w["along"] == "y" else ((low, high), (at, at))
            )
            if (
                x_span[0] - NEAR_MM * 1e6 <= near[0] <= x_span[1] + NEAR_MM * 1e6
                and y_span[0] - NEAR_MM * 1e6 <= near[1] <= y_span[1] + NEAR_MM * 1e6
            ):
                local.append(w["exposed_mm"])
        if local and max(local) >= 2.54:
            total += sum(local)
    return round(total, 3)


def _try_dogleg(text, design, row, nets, layout_check, fields_ok, native_ok, skip):
    """Re-route a near, direct bypass capacitor whose wire runs beside another net.

    The wire leaves the served pin one to five grid steps, then turns away from the
    neighbouring pin of the same part; the capacitor hangs back beside the wire (its
    return symbol then needs no stub) or stands at its end. At most
    DOGLEG_GEOMETRIC_BUDGET candidates get the cheap checks and DOGLEG_NATIVE_BUDGET the
    full assessment; one is kept only if it lowers the exposure. Returns the text (or
    None), its label, and the record of the search.
    """
    import time

    started = time.monotonic()
    units = _units(text)
    name = row["capacitor"]
    there = _point(units, row["serves"])
    out = _outward(units, row["serves"])
    before = _served_exposure(text, nets, row["net"], there)
    record = {
        "exposure_mm_before": before,
        "structural": 0,
        "geometric": 0,
        "native": 0,
        "refused": [],
    }
    own_pins = [p["point"] for k, u in units.items() if k[0] == name for p in u["pins"]]
    # Stage 1 needs only points: other parts' pins and power symbols with their glyphs.
    occupied = [p["point"] for k, u in units.items() if k[0] != name for p in u["pins"]] + [
        point
        for item in power_symbols(parse(text))
        for tip in [transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])]
        for point in (item["point"], (item["point"][0] + tip[0], item["point"][1] + tip[1]))
        if item["point"] != there
        # The capacitor's own return symbol is redrawn with it.
        and not (
            item["net"] == row["return_net"]
            and any(
                abs(item["point"][0] - q[0]) + abs(item["point"][1] - q[1]) <= 6 * GRID
                for q in own_pins
            )
        )
    ]

    def crowded(exit_point, corner, facing) -> bool:
        """Something already stands where the route or the capacitor would go."""
        far = (corner[0] + facing[0] * 6 * GRID, corner[1] + facing[1] * 6 * GRID)
        boxes = [
            (exit_point, corner, GRID),
            (corner, far, 2 * GRID),
            ((there[0] + out[0] * GRID, there[1] + out[1] * GRID), exit_point, GRID // 2),
        ]
        for a, b, pad in boxes:
            low = (min(a[0], b[0]) - pad, min(a[1], b[1]) - pad)
            high = (max(a[0], b[0]) + pad, max(a[1], b[1]) + pad)
            if any(low[0] <= x <= high[0] and low[1] <= y <= high[1] for x, y in occupied):
                return True
        return False

    owner = row["serves"].split(".")[0]
    pins = {p["point"] for k, u in units.items() if k[0] == owner for p in u["pins"]}
    sides = [(out[1], out[0]), (-out[1], -out[0])]
    # Away from a neighbouring pin first.
    sides.sort(key=lambda d: (there[0] + d[0] * 2 * GRID, there[1] + d[1] * 2 * GRID) in pins)
    # The part's body, across the pin's direction: a capacitor hanging back must clear it.
    body = next(u["body"] for k, u in units.items() if k[0] == owner)
    axis = 0 if out[0] == 0 else 1
    edge = body[2] if sides[0][axis] > 0 else body[0]
    if axis == 1:
        edge = body[3] if sides[0][axis] > 0 else body[1]
    clear_steps = abs(edge - there[axis]) // GRID + 3
    plans = []
    for exit_steps in (1, 2, 3, 4, 5):
        for across in range(2, clear_steps + 3):
            for hang in (True, False):
                # Stage 1, structure only: hanging back over the body is impossible.
                if hang and across < clear_steps:
                    continue
                if not hang and across > 5:
                    continue
                exit_point = (
                    there[0] + out[0] * exit_steps * GRID,
                    there[1] + out[1] * exit_steps * GRID,
                )
                corner = (
                    exit_point[0] + sides[0][0] * across * GRID,
                    exit_point[1] + sides[0][1] * across * GRID,
                )
                # Hanging back: the capacitor runs from the corner towards the part;
                # standing: away from it. Its return pin faces that way.
                facing = (-out[0], -out[1]) if hang else out
                plans.append((hang, exit_steps, across, exit_point, corner, facing))
    # Shortest route first; a hanging capacitor (no return stub) before a standing one.
    plans.sort(key=lambda plan: (plan[1] + plan[2], not plan[0]))
    chosen = None
    for hang, exit_steps, across, exit_point, corner, facing in plans:
        if record["geometric"] >= DOGLEG_GEOMETRIC_BUDGET:
            record["refused"].append("geometric budget spent")
            break
        label = (
            f"route out {exit_steps * 1.27:.2f} mm, across {across * 1.27:.2f} mm, "
            f"{'hanging back' if hang else 'standing'}"
        )
        if f"{name}|{label}" in skip:
            continue
        if crowded(exit_point, corner, facing):
            record["structural"] += 1
            continue
        candidate = None
        for angle in (0, 90, 180, 270):
            for sideways in (2,) if hang else (side_sign(sides[0]) * 2, -side_sign(sides[0]) * 2):
                try:
                    drawn = _redraw_capacitor(
                        text,
                        name,
                        row["pin"],
                        angle,
                        corner,
                        there,
                        sideways,
                        route=[exit_point],
                    )
                except (ValueError, KeyError):
                    continue
                placed = next(u for k, u in _units(drawn).items() if k[0] == name)
                other = next(p["point"] for p in placed["pins"] if p["number"] != row["pin"])
                if (_sign(other[0] - corner[0]), _sign(other[1] - corner[1])) != facing:
                    break
                candidate = drawn
                break
            if candidate is not None:
                break
        if candidate is None:
            continue
        record["geometric"] += 1
        objection = layout_check(candidate)
        if objection:
            record["refused"].append(f"{label}: layout check: {objection[:80]}")
            continue
        key = next(k for k in _units(candidate) if k[0] == name)
        candidate = _replace_text(candidate, key, layout_check, fields_ok)
        if candidate is None or power_symbol_collisions(candidate):
            record["refused"].append(f"{label}: no clear spot for its text or symbols")
            continue
        check = next(r for r in capacitor_distances(design, candidate) if r["capacitor"] == name)
        if not check["direct"]:
            record["refused"].append(f"{label}: not joined by a direct wire")
            continue
        after = _served_exposure(candidate, nets, row["net"], there)
        if after >= before:
            record["refused"].append(f"{label}: exposure {after} mm, not lower")
            continue
        if record["native"] >= DOGLEG_NATIVE_BUDGET:
            record["refused"].append("native budget spent")
            break
        record["native"] += 1
        failure = native_ok(candidate) if native_ok else None
        if failure:
            record["refused"].append(f"{label}: native check: {failure[:80]}")
            continue
        chosen = (candidate, label)
        record["exposure_mm_after"] = after
        break
    record["seconds"] = round(time.monotonic() - started, 1)
    record["refused"] = record["refused"][:8]
    if chosen is None:
        return None, None, record
    return chosen[0], chosen[1], record


def side_sign(direction: tuple[int, int]) -> int:
    """-1 for a direction to the left or up, 1 otherwise."""
    return -1 if direction[0] < 0 or direction[1] < 0 else 1


def place_supply_blocks_text(
    text: str,
    design: dict,
    inventory: list[dict],
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
    native_ok: Callable[[str], str | None] | None,
    skip: frozenset[str] = frozenset(),
) -> tuple[str, list[dict]]:
    """Move decoupling and bypass capacitors beside their pins, then re-aim power-block
    symbols. Returns the text and a record of every change and refusal."""
    nets = {(item["reference"], item["pin"]): item["net"] for item in inventory}
    moves = []
    for row in capacitor_distances(design, text):
        if row["distance_mm"] <= BESIDE_MM and row["direct"]:
            continue
        name = row["capacitor"]
        if name in skip:
            moves.append(
                {"connector": name, "block": "supply", "change": None, "kept_because": ["skipped"]}
            )
            continue
        units = _units(text)
        here = _point(units, f"{name}.{row['pin']}")
        there = _point(units, row["serves"])
        # Positions around the served pin, at least MINIMUM_MM from it, nearest first.
        deltas = set()
        for dx_steps in range(-10, 11):
            for dy_steps in range(-10, 11):
                spot = (there[0] + dx_steps * GRID, there[1] + dy_steps * GRID)
                reach = abs(spot[0] - there[0]) + abs(spot[1] - there[1])
                if MINIMUM_MM * 1e6 <= reach <= BESIDE_MM * 1e6:
                    deltas.add((_snap(spot[0] - here[0]), _snap(spot[1] - here[1])))
        # Skip spots where the moved capacitor's body would overlap another part's body.
        own = next(u for k, u in units.items() if k[0] == name)["body"]
        others = [u["body"] for k, u in units.items() if k[0] != name]

        def clear(delta) -> bool:
            moved = (own[0] + delta[0], own[1] + delta[1], own[2] + delta[0], own[3] + delta[1])
            return not any(
                moved[0] < b[2] + GRID
                and b[0] - GRID < moved[2]
                and moved[1] < b[3] + GRID
                and b[1] - GRID < moved[3]
                for b in others
            )

        ordered = sorted(
            (d for d in deltas if d != (0, 0) and clear(d)),
            key=lambda d: (
                abs(there[0] - here[0] - d[0]) + abs(there[1] - here[1] - d[1]),
                abs(d[0]) + abs(d[1]),
                d,
            ),
        )
        key = next(k for k in units if k[0] == name)
        candidate, label, reasons = _try_moves(
            text, key, ordered, nets, layout_check, fields_ok, skip, native_ok
        )
        if candidate is not None and not next(
            r["direct"] for r in capacitor_distances(design, candidate) if r["capacitor"] == name
        ):
            # Moved, but still not joined by a direct wire: try redrawing it instead.
            reasons.insert(0, f"{label}: moved but its wire to the pin still detours")
            candidate = None
        if candidate is not None:
            text = candidate
            after = next(
                r["distance_mm"]
                for r in capacitor_distances(design, text)
                if r["capacitor"] == name
            )
            moves.append(
                {
                    "connector": name,
                    "block": "supply",
                    "change": label,
                    "serves": row["serves"],
                    "distance_mm": {"before": row["distance_mm"], "after": after},
                }
            )
        else:
            redrawn = _try_redraw(text, design, row, layout_check, fields_ok, native_ok, skip)
            if redrawn is not None:
                text, label = redrawn
                after = next(r for r in capacitor_distances(design, text) if r["capacitor"] == name)
                moves.append(
                    {
                        "connector": name,
                        "block": "supply",
                        "change": label,
                        "serves": row["serves"],
                        "distance_mm": {
                            "before": row["distance_mm"],
                            "after": after["distance_mm"],
                        },
                        "direct": after["direct"],
                    }
                )
                continue
            moves.append(
                {
                    "connector": name,
                    "block": "supply",
                    "change": None,
                    "serves": row["serves"],
                    "kept_because": reasons[:6],
                }
            )
    # A near, direct capacitor whose wire still runs beside another net: route it away.
    for row in capacitor_distances(design, text):
        name = row["capacitor"]
        if not row["direct"] or name in skip:
            continue
        if not _served_exposure(text, nets, row["net"], _point(_units(text), row["serves"])):
            continue
        candidate, label, record = _try_dogleg(
            text, design, row, nets, layout_check, fields_ok, native_ok, skip
        )
        if candidate is not None:
            text = candidate
        moves.append(
            {
                "connector": name,
                "block": "supply",
                "change": label,
                "serves": row["serves"],
                "parallel_exposure": record,
            }
        )
    for row in power_block_directions(design, text):
        if row["consistent"]:
            continue
        wanted = (0, 1) if row["role"] == "return" else (0, -1)
        name = row["symbol"]
        # Turn it in place, or draw a short stub to either side with the symbol at its end.
        reasons, chosen = [], None
        for stub in (0, 2 * GRID, -2 * GRID, 3 * GRID, -3 * GRID, 4 * GRID, -4 * GRID):
            label = "re-aim" if not stub else f"re-aim on a {stub / 1e6:+.2f} mm stub"
            if f"{name}|{label}" in skip:
                continue
            try:
                candidate = _reaim(text, name, wanted, stub)
            except (ValueError, KeyError) as error:
                reasons.append(f"{label}: {error}")
                continue
            objection = layout_check(candidate)
            if objection:
                reasons.append(f"{label}: layout check: {objection[:100]}")
                continue
            if not fields_ok(candidate):
                reasons.append(f"{label}: a field check would report something new")
                continue
            # The native power-symbol clearance check is this same geometry: a collision
            # would fail it, so it is refused before the full assessment.
            if power_symbol_collisions(candidate):
                reasons.append(f"{label}: power-symbol clearance: touches another item")
                continue
            failure = native_ok(candidate) if native_ok else None
            if failure:
                reasons.append(f"{label}: native check: {failure[:100]}")
                continue
            chosen = (candidate, label)
            break
        search = None
        if chosen is None:
            found, label, search = _try_block_reaim(
                text, name, wanted, layout_check, fields_ok, native_ok, skip
            )
            if found is not None:
                chosen = (found, label)
        if chosen is None:
            moves.append(
                {
                    "connector": name,
                    "block": "supply",
                    "change": None,
                    "kept_because": [f"re-aim {row['role']} symbol: {r}" for r in reasons[:6]],
                    "block_search": search,
                }
            )
            continue
        text = chosen[0]
        move = {"connector": name, "block": "supply", "change": chosen[1], "net": row["net"]}
        if search is not None:
            move["block_search"] = search
        moves.append(move)
    return text, moves


# Whole-block re-aim (spec R7.4, reviewed solution §E): bounded, and never more than this
# much added wire to turn one glyph its conventional way.
BLOCK_REAIM_MAX_WIRE = 5 * GRID
BLOCK_REAIM_GEOMETRIC_BUDGET = 12
BLOCK_REAIM_NATIVE_BUDGET = 3


def _try_block_reaim(text, name, wanted, layout_check, fields_ok, native_ok, skip):
    """Re-aim a power symbol with its power block: out along the glyph's direction, a short
    jog, and the text of the unit whose pin it marks placed again. Shortest added wire
    first, within the budgets; returns the text (or None), its label and the record."""
    import time

    started = time.monotonic()
    record = {"geometric": 0, "native": 0, "refused": []}
    (item,) = [s for s in power_symbols(parse(text)) if s["reference"] == name]
    owner = next(
        (k for k, u in _units(text).items() if any(p["point"] == item["point"] for p in u["pins"])),
        None,
    )
    shapes = sorted(
        (
            (rise, stub)
            for rise in (2, 3, 4)
            for stub in (0, -2, 2, -3, 3, -4, 4)
            if rise + abs(stub) <= BLOCK_REAIM_MAX_WIRE // GRID
        ),
        key=lambda shape: (shape[0] + abs(shape[1]), shape),
    )
    chosen = None
    for rise, stub in shapes:
        if record["geometric"] >= BLOCK_REAIM_GEOMETRIC_BUDGET:
            record["refused"].append("geometric budget spent")
            break
        label = f"re-aim with its block: out {rise * 1.27:.2f} mm, across {stub * 1.27:+.2f} mm"
        if f"{name}|{label}" in skip:
            continue
        try:
            candidate = _reaim(text, name, wanted, stub * GRID, rise * GRID)
        except (ValueError, KeyError) as error:
            record["refused"].append(f"{label}: {error}")
            continue
        record["geometric"] += 1
        if (power_symbol_collisions(candidate) or layout_check(candidate)) and owner:
            # The unit's own text is in the way: place it again, clear of the glyph.
            candidate = _replace_text(
                candidate,
                owner,
                lambda c: "power symbol" if power_symbol_collisions(c) else layout_check(c),
                fields_ok,
            )
        if candidate is None or power_symbol_collisions(candidate):
            record["refused"].append(f"{label}: no clear spot for the glyph and the unit's text")
            continue
        objection = layout_check(candidate)
        if objection:
            record["refused"].append(f"{label}: layout check: {objection[:80]}")
            continue
        if not fields_ok(candidate):
            record["refused"].append(f"{label}: a field check would report something new")
            continue
        if record["native"] >= BLOCK_REAIM_NATIVE_BUDGET:
            record["refused"].append("native budget spent")
            break
        record["native"] += 1
        failure = native_ok(candidate) if native_ok else None
        if failure:
            record["refused"].append(f"{label}: native check: {failure[:80]}")
            continue
        chosen = (candidate, label)
        break
    record["seconds"] = round(time.monotonic() - started, 1)
    record["refused"] = record["refused"][:8]
    if chosen is None:
        return None, None, record
    return chosen[0], chosen[1], record
