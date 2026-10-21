"""Implementation details for m2b observation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .assets import _extract_symbol
from .ir import InputError
from .m2_geometry import (
    ConductorSegment,
    canonical_conductor_tree,
    conductor_reachable,
    label_text_rect,
    label_text_width,
)
from .m2a import Pin, _nm
from .m2b_layout import _turn
from .sexpr import children, one, parse


@lru_cache(maxsize=64)
def _local_pin_number_rectangles(definition: str, unit: int) -> tuple:
    """Conservative visible-number keepouts from actual embedded pin geometry."""
    tree = parse(definition)
    if any(children(item, "hide") or "hide" in item[1:] for item in children(tree, "pin_numbers")):
        return ()
    rectangles = []
    for body in children(tree, "symbol"):
        if int(body[1].rsplit("_", 2)[-2]) not in (0, unit):
            continue
        for pin in children(body, "pin"):
            number = one(pin, "number")
            effects = one(number, "effects")
            if children(effects, "hide") or "hide" in effects[1:]:
                continue
            at = one(pin, "at")
            dx, dy = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[int(at[3])]
            half_length = _nm(one(pin, "length")[1]) // 2
            x, y = _nm(at[1]) + dx * half_length, _nm(at[2]) + dy * half_length
            size = one(one(effects, "font"), "size")
            scale = max(_nm(size[1]), _nm(size[2]))
            width = (label_text_width(number[1]) * scale + 1_269_999) // 1_270_000
            height = (2_000_000 * scale + 1_269_999) // 1_270_000
            rectangles.append((x, y, dx, dy, width, height))
    return tuple(rectangles)


def pin_number_rectangles(definition: str, unit: int, x: int, y: int, angle: int) -> tuple:
    rectangles = []
    for px, py, dx, dy, width, height in _local_pin_number_rectangles(definition, unit):
        cx, cy = _turn(Pin("", "", "", px, py), angle)
        _vx, vy = _turn(Pin("", "", "", dx, dy), angle)
        cx, cy = x + cx, y + cy
        half = (width + 1) // 2
        # Native horizontal pin numbers are above the pin midpoint;
        # vertical pin numbers are to its left, independent of direction.
        rectangles.append(
            (cx - half, cy - height, cx + half, cy)
            if vy == 0
            else (cx - height, cy - half, cx, cy + half)
        )
    return tuple(rectangles)


def check_observed_layout(schematic: Path, observed: dict, design: dict) -> dict:
    """Measure actual emitted geometry using embedded definitions and KiCad's netlist."""
    tree = parse(schematic.read_text())
    bodies = {}
    definitions = {}
    for definition in children(one(tree, "lib_symbols"), "symbol"):
        definitions[definition[1]] = _extract_symbol(schematic.read_text(), definition[1])
        for unit in children(definition, "symbol"):
            unit_no = int(unit[1].rsplit("_", 2)[-2])
            points = []
            for shape in unit[2:]:
                if not isinstance(shape, list):
                    continue
                if shape[0] == "rectangle":
                    points += [one(shape, "start"), one(shape, "end")]
                elif shape[0] == "polyline":
                    points += [xy for pts in children(shape, "pts") for xy in children(pts, "xy")]
            if points:
                xs, ys = [_nm(p[1]) for p in points], [_nm(p[2]) for p in points]
                bodies[(definition[1], unit_no)] = (min(xs), max(ys), max(xs), min(ys))
    instances = {}
    rectangles = []
    required_fields = []
    worksheet_fields = []
    visible_pin_numbers = []
    source_refs = set()
    for symbol in children(tree, "symbol"):
        ref = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        lib = one(symbol, "lib_id")[1]
        if lib != "power:PWR_FLAG" and any(
            children(prop, "hide")
            for prop in children(symbol, "property")
            if prop[1] in ("Reference", "Value")
        ):
            raise InputError("observed required reference/value hidden")
        unit = int(one(symbol, "unit")[1])
        at = one(symbol, "at")
        x, y, angle = _nm(at[1]), _nm(at[2]), int(at[3])
        instances[(ref, unit)] = (x, y, angle)
        if lib == "power:PWR_FLAG":
            source_refs.add(ref)
        if lib in definitions:
            visible_pin_numbers.extend(
                (ref, rectangle)
                for rectangle in pin_number_rectangles(definitions[lib], unit, x, y, angle)
            )
        if lib != "power:PWR_FLAG":
            for prop in children(symbol, "property"):
                if prop[1] not in {"Reference", "Value"}:
                    continue
                field_at = one(prop, "at")
                fx, fy = _nm(field_at[1]), _nm(field_at[2])
                displayed_length = len(prop[2]) + (
                    1
                    if prop[1] == "Reference"
                    and any(key[0] == lib and key[1] > 1 for key in bodies)
                    else 0
                )
                half = max(635_000, displayed_length * 445_000)
                native_angle = int(field_at[3]) - (angle if lib in {"Device:R", "Device:C"} else 0)
                dx, dy = (850_000, half) if native_angle % 180 else (half, 850_000)
                worksheet_fields.append((fx - dx, fy - dy, fx + dx, fy + dy))
        long_passive = lib in {"Device:R", "Device:C"} and any(
            len(prop[2]) > 4
            for prop in children(symbol, "property")
            if prop[1] in {"Reference", "Value"}
        )
        if lib not in {"Device:R", "Device:C", "power:PWR_FLAG"} or long_passive:
            for prop in children(symbol, "property"):
                if prop[1] not in {"Reference", "Value"}:
                    continue
                field_at = one(prop, "at")
                fx, fy = _nm(field_at[1]), _nm(field_at[2])
                text = prop[2]
                # KiCad appends the function letter when rendering multi-unit references.
                displayed_length = len(text) + (
                    1
                    if prop[1] == "Reference"
                    and any(key[0] == lib and key[1] > 1 for key in bodies)
                    else 0
                )
                half = max(635_000, displayed_length * 445_000)
                # KiCad rotates passive property glyphs relative to their symbol.
                native_angle = int(field_at[3]) - (angle if long_passive else 0)
                dx, dy = (850_000, half) if native_angle % 180 else (half, 850_000)
                required_fields.append((ref, prop[1], (fx - dx, fy - dy, fx + dx, fy + dy)))
        boxes = [box for key, box in bodies.items() if key[0] == lib and key[1] in (0, unit)]
        if boxes:
            left, top, right, bottom = (
                min(z[0] for z in boxes),
                max(z[1] for z in boxes),
                max(z[2] for z in boxes),
                min(z[3] for z in boxes),
            )
            corners = [
                _turn(Pin("", "", "", xx, yy), angle)
                for xx in (left, right)
                for yy in (top, bottom)
            ]
            xs, ys = [x + z[0] for z in corners], [y + z[1] for z in corners]
            rectangles.append((ref, (min(xs), min(ys), max(xs), max(ys))))
    for i, (ref, a) in enumerate(rectangles):
        for other, b in rectangles[i + 1 :]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise InputError(f"observed body overlap: {ref}, {other}")
    # This is an independent emitted-byte check, not a certificate assertion.
    label_boxes = [
        (
            net,
            label_text_rect(net, point),
        )
        for net, point in observed["labels"]
    ]
    for ref, field_name, box in required_fields:
        for owner, obstacle in rectangles + label_boxes:
            if max(box[0], obstacle[0]) < min(box[2], obstacle[2]) and max(
                box[1], obstacle[1]
            ) < min(box[3], obstacle[3]):
                raise InputError(
                    f"observed required field overlaps body/label: {ref} {field_name}, {owner}"
                )
    wires = observed["wires"]
    labels = observed["labels"]
    pin_positions = observed["pin_positions"]
    pin_to_net = {
        (ref, pin): name for name, members in observed["nets"].items() for ref, pin in members
    }

    def on_segment(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        )

    wire_net = [set() for _ in wires]
    for i, (a, b) in enumerate(wires):
        if a[0] != b[0] and a[1] != b[1]:
            raise InputError("observed diagonal wire")
        for key, point in pin_positions.items():
            if on_segment(point, a, b) and key in pin_to_net:
                wire_net[i].add(pin_to_net[key])
        for name, point in labels:
            if on_segment(point, a, b):
                wire_net[i].add(name)
    for _ in range(len(wires)):
        changed = False
        for i, (a, b) in enumerate(wires):
            for j, (c, e) in enumerate(wires):
                if i == j or not any(on_segment(p, c, e) for p in (a, b)):
                    continue
                combined = wire_net[i] | wire_net[j]
                if combined != wire_net[i] or combined != wire_net[j]:
                    wire_net[i] = wire_net[j] = combined
                    changed = True
        if not changed:
            break
    if any(len(names) != 1 for names in wire_net):
        raise InputError("observed wire net attribution ambiguous")
    names = [next(iter(x)) for x in wire_net]
    observed_junctions = set(observed.get("junctions", ()))
    conductor_trees = {}
    for net in sorted(set(names)):
        indexed = [
            (index, wire)
            for index, (name, wire) in enumerate(zip(names, wires, strict=True))
            if name == net
        ]
        conductor_trees[net] = canonical_conductor_tree(
            (
                ConductorSegment(a, b, net, "independent-observer", (f"wire.{index}",))
                for index, (a, b) in indexed
            ),
            junctions=observed_junctions,
            pins=(
                point
                for terminal, point in pin_positions.items()
                if pin_to_net.get(terminal) == net
            ),
        )
    if "junctions" in observed:
        missing_junctions = sorted(
            point
            for tree in conductor_trees.values()
            for point in tree.junctions
            if point not in observed_junctions
        )
        if missing_junctions:
            raise InputError(f"observed branch junction missing: {missing_junctions}")
    for i, (a, b) in enumerate(wires):
        for ref, rect in rectangles:
            if a in {point for (r, _), point in pin_positions.items() if r == ref} or b in {
                point for (r, _), point in pin_positions.items() if r == ref
            }:
                continue
            left, top, right, bottom = rect
            if (
                a[0] == b[0]
                and left < a[0] < right
                and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
            ):
                raise InputError(f"observed wire through body: {ref}")
            if (
                a[1] == b[1]
                and top < a[1] < bottom
                and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
            ):
                raise InputError(f"observed wire through body: {ref}")
        for key, point in pin_positions.items():
            if key in pin_to_net and pin_to_net[key] != names[i] and on_segment(point, a, b):
                raise InputError("wire touches unrelated physical pin")
        for j, (c, e) in enumerate(wires[i + 1 :], i + 1):
            if names[i] == names[j]:
                continue
            if (
                a[0] == b[0]
                and c[1] == e[1]
                and on_segment((a[0], c[1]), a, b)
                and on_segment((a[0], c[1]), c, e)
            ):
                raise InputError("observed unrelated wire crossing")
            if (
                a[1] == b[1]
                and c[0] == e[0]
                and on_segment((c[0], a[1]), a, b)
                and on_segment((c[0], a[1]), c, e)
            ):
                raise InputError("observed unrelated wire crossing")
            if a[0] == b[0] == c[0] == e[0] and max(min(a[1], b[1]), min(c[1], e[1])) <= min(
                max(a[1], b[1]), max(c[1], e[1])
            ):
                raise InputError("observed unrelated wire overlap")
            if a[1] == b[1] == c[1] == e[1] and max(min(a[0], b[0]), min(c[0], e[0])) <= min(
                max(a[0], b[0]), max(c[0], e[0])
            ):
                raise InputError("observed unrelated wire overlap")
    minimum_text_clearance = None
    for (ref, unit), item in observed["occurrences"].items():
        if item["lib"] == "power:PWR_FLAG":
            continue
        props = item["properties"]
        if set(props) != {"Reference", "Value"}:
            raise InputError("observed required text missing")
        for prop in props.values():
            x, y = prop["position"]
            half = max(635_000, len(prop["value"]) * 445_000)
            box = (x - half, y - 850_000, x + half, y + 850_000)
            for a, b in wires:
                wire_box = (
                    min(a[0], b[0]),
                    min(a[1], b[1]),
                    max(a[0], b[0]),
                    max(a[1], b[1]),
                )
                clearance = max(box[0] - wire_box[2], wire_box[0] - box[2], 0) + max(
                    box[1] - wire_box[3], wire_box[1] - box[3], 0
                )
                minimum_text_clearance = (
                    clearance
                    if minimum_text_clearance is None
                    else min(minimum_text_clearance, clearance)
                )
                if (
                    a[0] == b[0]
                    and box[0] < a[0] < box[2]
                    and max(min(a[1], b[1]), box[1]) < min(max(a[1], b[1]), box[3])
                ):
                    raise InputError("observed wire through text")
                if (
                    a[1] == b[1]
                    and box[1] < a[1] < box[3]
                    and max(min(a[0], b[0]), box[0]) < min(max(a[0], b[0]), box[2])
                ):
                    raise InputError("observed wire through text")
    all_points = (
        [p for a, b in wires for p in (a, b)]
        + [p for _, p in labels]
        + [
            v["position"]
            for item in observed["occurrences"].values()
            for v in item["properties"].values()
        ]
    )
    if any(
        not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000)
        for x, y in all_points
    ):
        raise InputError("observed content outside A4 margin")
    extent_points = all_points + list(pin_positions.values())
    width_mm = (max(p[0] for p in extent_points) - min(p[0] for p in extent_points)) / 1_000_000
    height_mm = (max(p[1] for p in extent_points) - min(p[1] for p in extent_points)) / 1_000_000
    if width_mm > 210 or height_mm > 140:
        raise InputError("observed layout spreads unnecessarily across the page")
    by_ref = {c["id"]: c["refdes"] for c in design["components"]}
    series_relations = [r for r in design["relationships"] if r["kind"] == "series"]
    for upstream in series_relations:
        for downstream in series_relations:
            if upstream is downstream or upstream["output"] != downstream["input"]:
                continue
            left = pin_positions[(by_ref[upstream["component"]], "2")]
            right = pin_positions[(by_ref[downstream["component"]], "1")]
            if left[0] >= right[0]:
                raise InputError("observed functional stage order reversal")
    spans = []
    for relation in design["relationships"]:
        if relation["kind"] == "feedback" and not any(
            r["kind"] == "amplifier"
            and r["component"] == relation["component"]
            and r["function"] == relation["function"]
            and r.get("unused")
            for r in design["relationships"]
        ):
            ref = by_ref[relation["component"]]
            source = pin_positions[(ref, relation["source"])]
            sense = pin_positions[(ref, relation["sense"])]
            span = abs(source[0] - sense[0]) / 1_000_000
            spans.append(span)
            if span > 45:
                raise InputError("excessive local feedback span")
    length_by_net = {net: tree.length for net, tree in conductor_trees.items()}
    if any(length > 250_000_000 for length in length_by_net.values()):
        raise InputError("obvious excessive net detour")
    endpoints = {p for a, b in wires for p in (a, b)} | {p for _, p in labels}
    missing = [
        (ref, pin)
        for (ref, pin), point in pin_positions.items()
        if (ref, pin) in pin_to_net and point not in endpoints
    ]
    if missing:
        raise InputError(f"observed pin endpoint mismatch: {missing}")
    reversals = 0
    for relation in design["relationships"]:
        kind = relation["kind"]
        if kind == "series":
            ref = by_ref[relation["component"]]
            start, end = pin_positions[(ref, "1")], pin_positions[(ref, "2")]
            reversals += not (start[0] < end[0] or start[1] < end[1])
        elif kind == "polarity":
            ref = by_ref[relation["component"]]
            start, end = pin_positions[(ref, "2")], pin_positions[(ref, "1")]
            reversals += not (start[0] < end[0] or start[1] < end[1])
        elif kind == "amplifier" and not relation.get("unused"):
            component = next(c for c in design["components"] if c["id"] == relation["component"])
            function = next(f for f in component["functions"] if f["id"] == relation["function"])
            ref = component["refdes"]
            reversals += (
                pin_positions[(ref, function["pins"]["plus"])][0]
                >= pin_positions[(ref, function["pins"]["out"])][0]
            )
    if reversals:
        raise InputError("observed functional flow reversal")
    relation_by_kind = {}
    for relation in design["relationships"]:
        relation_by_kind.setdefault(relation["kind"], []).append(relation)

    def pin(component, number):
        return by_ref[component], number

    def wired_path(first, second):
        net = pin_to_net.get(first)
        if net is None or pin_to_net.get(second) != net:
            return False
        if net not in conductor_trees:
            return False
        return conductor_reachable(
            conductor_trees[net], pin_positions[first], pin_positions[second]
        )

    local_paths = []

    def require_path(first, second, relation):
        if not wired_path(first, second):
            raise InputError(f"observed local motif lacks explicit wire path: {relation}")
        a, b = pin_positions[first], pin_positions[second]
        local_paths.append((relation, (abs(a[0] - b[0]) + abs(a[1] - b[1])) / 1_000_000))

    for first in relation_by_kind.get("series", []):
        for second in relation_by_kind.get("series", []):
            if first is not second and first["output"] == second["input"]:
                a, b = pin(first["component"], "2"), pin(second["component"], "1")
                require_path(a, b, "ordered series")
                if pin_positions[a][0] >= pin_positions[b][0]:
                    raise InputError("observed functional stage order reversal")
        for second in relation_by_kind.get("polarity", []):
            if first["output"] == second["anode"]:
                require_path(
                    pin(first["component"], "2"),
                    pin(second["component"], "2"),
                    "series/polarity",
                )
        for second in relation_by_kind.get("shunt", []):
            if first["output"] == second["node"]:
                require_path(
                    pin(first["component"], "2"),
                    pin(second["component"], "1"),
                    "series/shunt",
                )
        for second in relation_by_kind.get("amplifier", []):
            if second.get("unused") or first["output"] != second["input"]:
                continue
            component = next(c for c in design["components"] if c["id"] == second["component"])
            function = next(f for f in component["functions"] if f["id"] == second["function"])
            source = pin(first["component"], "2")
            input_leg = next(
                (
                    r
                    for r in relation_by_kind.get("series", [])
                    if r["input"] == first["output"]
                    and pin_to_net.get(pin(r["component"], "2"))
                    == pin_to_net.get(pin(second["component"], function["pins"]["minus"]))
                ),
                None,
            )
            target = (
                pin(input_leg["component"], "1")
                if input_leg
                else pin(second["component"], function["pins"]["plus"])
            )
            require_path(source, target, "series/amplifier")
            if pin_positions[source][0] >= pin_positions[target][0]:
                raise InputError("observed functional stage order reversal")
    for relation in relation_by_kind.get("feedback", []):
        if any(
            stage["component"] == relation["component"]
            and stage["function"] == relation["function"]
            and stage.get("unused")
            for stage in relation_by_kind.get("amplifier", [])
        ):
            continue
        source = pin(relation["component"], relation["source"])
        sense = pin(relation["component"], relation["sense"])
        if "resistor" in relation:
            require_path(source, pin(relation["resistor"], "2"), "feedback source")
            require_path(sense, pin(relation["resistor"], "1"), "feedback sense")
        else:
            require_path(source, sense, "direct feedback")
    for relation in relation_by_kind.get("bridge", []):
        peers = [
            pin(cid, number)
            for net in design["nets"]
            if net["id"] == relation["first"]
            for cid, number in net["members"]
            if cid != relation["component"]
            and not next(c for c in design["components"] if c["id"] == cid)["asset"].startswith(
                "Connector_Generic:"
            )
        ]
        if peers and not any(wired_path(peer, pin(relation["component"], "1")) for peer in peers):
            raise InputError("observed bridge is visually detached")
        for stage in relation_by_kind.get("amplifier", []):
            if stage.get("unused") or stage["output"] != relation["second"]:
                continue
            component = next(c for c in design["components"] if c["id"] == stage["component"])
            function = next(f for f in component["functions"] if f["id"] == stage["function"])
            require_path(
                pin(relation["component"], "2"),
                pin(stage["component"], function["pins"]["out"]),
                "bridge feedback",
            )
    for relation in relation_by_kind.get("decoupling", []):
        consumer = pin(*relation["consumer"])
        cap = next(
            pin(relation["component"], number)
            for number in ("1", "2")
            if pin_to_net.get(pin(relation["component"], number)) == pin_to_net.get(consumer)
        )
        require_path(consumer, cap, "decoupling")
    for relation in relation_by_kind.get("timing_ladder", []):
        require_path(pin(relation["upper"], "2"), pin(relation["lower"], "1"), "timing discharge")
        require_path(pin(relation["lower"], "2"), pin(relation["capacitor"], "1"), "timing node")
        if not (
            pin_positions[pin(relation["upper"], "1")][1]
            < pin_positions[pin(relation["lower"], "1")][1]
            < pin_positions[pin(relation["capacitor"], "1")][1]
        ):
            raise InputError("observed timing ladder order reversal")
    for relation in relation_by_kind.get("reference_divider", []):
        require_path(
            pin(relation["upper"], "2"),
            pin(relation["lower"], "1"),
            "local reference divider",
        )
    excessive_local_paths = [item for item in local_paths if item[1] > 80]
    if excessive_local_paths:
        raise InputError(
            "observed local motif is excessively fragmented: "
            f"paths={excessive_local_paths} threshold_mm=80"
        )
    local_spans = []
    support_spans = []
    for relation in design["relationships"]:
        kind = relation["kind"]
        if kind == "polarity":
            diode_ref = by_ref[relation["component"]]
            anode = pin_positions[(diode_ref, "2")]
            peers = [
                pin_positions[(by_ref[cid], pin)]
                for net in design["nets"]
                if net["id"] == relation["anode"]
                for cid, pin in net["members"]
                if cid != relation["component"]
            ]
            if peers:
                local_spans.append(
                    min(abs(anode[0] - p[0]) + abs(anode[1] - p[1]) for p in peers) / 1_000_000
                )
        elif kind == "shunt":
            shunt_ref = by_ref[relation["component"]]
            terminal = pin_positions[(shunt_ref, "1")]
            peers = [
                pin_positions[(by_ref[cid], pin)]
                for net in design["nets"]
                if net["id"] == relation["node"]
                for cid, pin in net["members"]
                if cid != relation["component"]
                and not next(c for c in design["components"] if c["id"] == cid)["asset"].startswith(
                    "Connector_Generic:"
                )
            ]
            if peers:
                local_spans.append(
                    min(abs(terminal[0] - p[0]) + abs(terminal[1] - p[1]) for p in peers)
                    / 1_000_000
                )
        elif kind == "feedback" and "resistor" in relation:
            amp_ref = by_ref[relation["component"]]
            resistor_ref = by_ref[relation["resistor"]]
            for amp_pin, resistor_pin in (
                (relation["sense"], "1"),
                (relation["source"], "2"),
            ):
                a = pin_positions[(amp_ref, amp_pin)]
                b = pin_positions[(resistor_ref, resistor_pin)]
                local_spans.append((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 1_000_000)
        elif kind == "decoupling":
            consumer_ref = by_ref[relation["consumer"][0]]
            cap_ref = by_ref[relation["component"]]
            consumer = pin_positions[(consumer_ref, relation["consumer"][1])]
            member = next(
                p
                for p in ("1", "2")
                if (cap_ref, p)
                in observed["nets"].get(pin_to_net[(consumer_ref, relation["consumer"][1])], [])
            )
            cap = pin_positions[(cap_ref, member)]
            span = (abs(consumer[0] - cap[0]) + abs(consumer[1] - cap[1])) / 1_000_000
            local_spans.append(span)
            support_spans.append(span)
    if any(span > 80 for span in local_spans):
        raise InputError("observed motif fragmentation")
    if any(span > 60 for span in support_spans):
        raise InputError("observed support component detached from consumer")
    # Keep electrical falsification diagnostics ahead of source readability failures.
    for ref, box in rectangles:
        if ref not in source_refs:
            continue
        for net, obstacle in label_boxes:
            if max(box[0], obstacle[0]) < min(box[2], obstacle[2]) and max(
                box[1], obstacle[1]
            ) < min(box[3], obstacle[3]):
                raise InputError(f"observed source glyph overlaps label: {ref}, {net}")
        for first, second in wires:
            if (
                first[0] == second[0]
                and box[0] < first[0] < box[2]
                and max(min(first[1], second[1]), box[1]) < min(max(first[1], second[1]), box[3])
            ) or (
                first[1] == second[1]
                and box[1] < first[1] < box[3]
                and max(min(first[0], second[0]), box[0]) < min(max(first[0], second[0]), box[2])
            ):
                raise InputError(f"observed wire through source glyph: {ref}")
    # Independently measured native A4 worksheet corner, including border stroke.
    worksheet = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
    page_geometry = (
        worksheet_fields
        + [box for _, box in rectangles + label_boxes]
        + [box for _, _, box in required_fields]
        + [(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])) for a, b in wires]
    )
    for box in page_geometry:
        if (
            box[0] < worksheet[2]
            and box[2] > worksheet[0]
            and box[1] < worksheet[3]
            and box[3] > worksheet[1]
        ):
            raise InputError(f"observed content overlaps worksheet title block: {box}")
    for index, (net, box) in enumerate(label_boxes):
        for owner, obstacle in visible_pin_numbers:
            if max(box[0], obstacle[0]) < min(box[2], obstacle[2]) and max(
                box[1], obstacle[1]
            ) < min(box[3], obstacle[3]):
                raise InputError(f"observed net label overlaps visible pin number: {net}, {owner}")
        for owner, obstacle in rectangles + label_boxes[index + 1 :]:
            if max(box[0], obstacle[0]) < min(box[2], obstacle[2]) and max(
                box[1], obstacle[1]
            ) < min(box[3], obstacle[3]):
                raise InputError(f"observed net label overlaps body/label: {net}, {owner}")
    bends = sum(tree.bends for tree in conductor_trees.values())
    if bends > max(16, len(wires) * 3):
        raise InputError("observed excessive bends")
    return {
        "observed_body_overlap_count": 0,
        "observed_wire_through_body_count": 0,
        "observed_wire_through_text_count": 0,
        "observed_unrelated_wire_crossing_count": 0,
        "observed_unrelated_pin_contact_count": 0,
        "observed_pin_endpoint_mismatch_count": 0,
        "observed_flow_reversal_count": 0,
        "observed_motif_fragmentation_mm": max(local_spans, default=0),
        "observed_bend_count": bends,
        "observed_required_visible_fields": 2
        * sum(item["lib"] != "power:PWR_FLAG" for item in observed["occurrences"].values()),
        "observed_page_margin_pass": True,
        "observed_feedback_span_mm": max(spans, default=0),
        "observed_wire_length_mm": sum(tree.length for tree in conductor_trees.values())
        / 1_000_000,
        "observed_wire_count": sum(
            len(tree.geometry_signature) for tree in conductor_trees.values()
        ),
        "observed_raw_wire_count": len(wires),
        "observed_actual_junction_count": sum(
            len(tree.junctions) for tree in conductor_trees.values()
        ),
        "observed_stage_order_reversal_count": 0,
        "observed_local_wire_span_mm": max((span for _, span in local_paths), default=0),
        "observed_local_wire_span_witness": max(
            local_paths, key=lambda item: item[1], default=None
        ),
        "observed_support_locality_mm": max(support_spans, default=0),
        "observed_content_width_mm": width_mm,
        "observed_content_height_mm": height_mm,
        "observed_page_utilization": round(width_mm * height_mm / (256.36 * 159.2), 6),
        "observed_text_wire_clearance_mm": (
            None if minimum_text_clearance is None else minimum_text_clearance / 1_000_000
        ),
    }
