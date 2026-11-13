"""A plain-text description of a native KiCad schematic drawing, for a text reviewer.

The plotted SVG gives every visible string and its position, but wires, symbol bodies
and power symbols are anonymous path geometry. This description says what is drawn:
each part instance with its body, pins and nets; each visible reference/value with
its distance to its own body and to the nearest other part; every wire run grouped by
net; each power symbol and flag with the direction it points; net labels and
junctions. Coordinates are millimetres on the page, y increasing downward.
"""

from __future__ import annotations

from ai_kicad.m2_geometry import point_on_segment
from ai_kicad.m2_text_layout import property_page_angle, text_extents
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.m2a_core import _nm
from ai_kicad.sexpr import children, one

from .power_symbols import FLAG_TIP, GLYPH_TIPS, _sign, _wire_segments, power_symbols

Point = tuple[int, int]
Box = tuple[int, int, int, int]
DIRECTION_NAMES = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}


def _mm(value: int) -> str:
    return f"{value / 1_000_000:.2f}"


def _point(point: Point) -> str:
    return f"({_mm(point[0])}, {_mm(point[1])})"


def _box(box: Box) -> str:
    return f"x {_mm(box[0])}..{_mm(box[2])}, y {_mm(box[1])}..{_mm(box[3])}"


def _gap(first: Box, second: Box) -> int:
    dx = max(first[0] - second[2], second[0] - first[2], 0)
    dy = max(first[1] - second[3], second[1] - first[3], 0)
    return max(dx, dy)


def _instances(tree: list) -> list[dict]:
    """Placed parts (not power symbols or flags) with their unit's pins and body box."""
    library = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    result = []
    for symbol in children(tree, "symbol"):
        lib_id = one(symbol, "lib_id")[1]
        if lib_id in GLYPH_TIPS or lib_id == "power:PWR_FLAG":
            continue
        definition = library.get(lib_id)
        properties = {p[1]: p for p in children(symbol, "property")}
        at = one(symbol, "at")
        origin, angle = (_nm(at[1]), _nm(at[2])), int(float(at[3]))
        mirrors = children(symbol, "mirror")
        mirror = mirrors[0][1] if mirrors else None
        unit = int(one(symbol, "unit")[1])
        units = set()
        pins, points = [], []
        for body in children(definition, "symbol") if definition else []:
            number = body[1].rsplit("_", 2)[-2]
            if number != "0":
                units.add(number)
            if number not in {"0", str(unit)}:
                continue
            for pin in children(body, "pin"):
                x, y = transform_library_point(
                    _nm(one(pin, "at")[1]), _nm(one(pin, "at")[2]), angle, mirror
                )
                names = children(pin, "name")
                pins.append(
                    {
                        "number": one(pin, "number")[1],
                        "name": names[0][1] if names else "",
                        "point": (origin[0] + x, origin[1] + y),
                    }
                )
            for shape in children(body, "rectangle"):
                points += [one(shape, "start"), one(shape, "end")]
            for shape in children(body, "polyline"):
                points += children(one(shape, "pts"), "xy")
        placed = [
            transform_library_point(_nm(point[1]), _nm(point[2]), angle, mirror) for point in points
        ]
        if placed:
            body = (
                origin[0] + min(x for x, _y in placed),
                origin[1] + min(y for _x, y in placed),
                origin[0] + max(x for x, _y in placed),
                origin[1] + max(y for _x, y in placed),
            )
        elif pins:
            body = (
                min(p["point"][0] for p in pins),
                min(p["point"][1] for p in pins),
                max(p["point"][0] for p in pins),
                max(p["point"][1] for p in pins),
            )
        else:
            body = (*origin, *origin)
        reference = properties["Reference"][2]
        letter = chr(ord("A") + unit - 1) if len(units) > 1 else ""
        result.append(
            {
                "name": reference + letter,
                "reference": reference,
                "unit": unit,
                "lib_id": lib_id,
                "value": properties["Value"][2] if "Value" in properties else "",
                "origin": origin,
                "angle": angle,
                "pins": pins,
                "body": body,
                "drawn_body": bool(placed),
                "symbol": symbol,
            }
        )
    return result


def _visible_fields(instance: dict) -> list[dict]:
    symbol, angle = instance["symbol"], instance["angle"]
    fields = []
    for prop in children(symbol, "property"):
        if prop[1] not in {"Reference", "Value"} or children(prop, "hide"):
            continue
        at = one(prop, "at")
        centre = (_nm(at[1]), _nm(at[2]))
        text = instance["name"] if prop[1] == "Reference" else prop[2]
        width, height = text_extents(text, property_page_angle(angle, int(float(at[3]))))
        box = (
            centre[0] - width // 2,
            centre[1] - height // 2,
            centre[0] + width // 2,
            centre[1] + height // 2,
        )
        fields.append({"field": prop[1], "text": text, "centre": centre, "box": box})
    return fields


def _wire_groups(segments: list[tuple[Point, Point]]) -> list[list[tuple[Point, Point]]]:
    """Wire segments joined at an end or at a T (an end lying on another segment)."""
    parent = list(range(len(segments)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i, first in enumerate(segments):
        for j in range(i + 1, len(segments)):
            second = segments[j]
            if any(point_on_segment(p, *second) for p in first) or any(
                point_on_segment(p, *first) for p in second
            ):
                parent[find(i)] = find(j)
    groups: dict[int, list] = {}
    for index, segment in enumerate(segments):
        groups.setdefault(find(index), []).append(segment)
    return list(groups.values())


def describe_schematic(tree: list, terminal_inventory: list[dict]) -> str:
    """Plain-text description of what the sheet draws, for a text reviewer."""
    instances = _instances(tree)
    net_of_pin = {(item["reference"], item["pin"]): item["net"] for item in terminal_inventory}
    terminals = {
        (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000)): (
            f"{item['reference']}.{item['pin']}",
            item["net"],
        )
        for item in terminal_inventory
    }
    symbols = power_symbols(tree)
    labels = [
        (label[1], (_nm(one(label, "at")[1]), _nm(one(label, "at")[2])))
        for label in children(tree, "label")
    ]
    flags = []
    for symbol in children(tree, "symbol"):
        if one(symbol, "lib_id")[1] == "power:PWR_FLAG":
            at = one(symbol, "at")
            tip = transform_library_point(*FLAG_TIP, int(float(at[3])))
            flags.append(
                ((_nm(at[1]), _nm(at[2])), DIRECTION_NAMES[(_sign(tip[0]), _sign(tip[1]))])
            )
    lines = [
        "SCHEMATIC DRAWING (millimetres, A4 page 297 x 210, y increases downward)",
        "",
        "PARTS (body box; pins as number name at (x, y) -> net):",
    ]
    for item in sorted(instances, key=lambda i: i["name"]):
        kind = "" if item["drawn_body"] else " (drawn without a body: only its pin stubs)"
        lines.append(
            f"- {item['name']} {item['value']} [{item['lib_id']}] rotation {item['angle']}, "
            f"body {_box(item['body'])}{kind}"
        )
        for pin in sorted(item["pins"], key=lambda p: (len(p["number"]), p["number"])):
            net = net_of_pin.get((item["reference"], pin["number"]), "unconnected")
            name = f" {pin['name']}" if pin["name"] and pin["name"] != "~" else ""
            lines.append(f"    pin {pin['number']}{name} at {_point(pin['point'])} -> {net}")
    lines += ["", "VISIBLE PART TEXT (gap to its own body; nearest other part and gap):"]
    for item in sorted(instances, key=lambda i: i["name"]):
        for field in _visible_fields(item):
            others = [
                (_gap(field["box"], other["body"]), other["name"])
                for other in instances
                if other is not item
            ]
            nearest = min(others) if others else (0, "none")
            lines.append(
                f'- "{field["text"]}" ({item["name"]} {field["field"]}) centred at '
                f"{_point(field['centre'])}, box {_box(field['box'])}; "
                f"{_mm(_gap(field['box'], item['body']))} mm from {item['name']}'s body; "
                f"nearest other part {nearest[1]} at {_mm(nearest[0])} mm"
            )
    lines += ["", "WIRES (grouped by connected run; each segment from -> to):"]
    segments = _wire_segments(tree)
    for group in _wire_groups(segments):
        touched = sorted(
            {
                name
                for point, (name, _net) in terminals.items()
                if any(point_on_segment(point, *segment) for segment in group)
            }
        )
        nets = {
            net
            for point, (_name, net) in terminals.items()
            if any(point_on_segment(point, *segment) for segment in group)
        }
        nets |= {
            item["net"]
            for item in symbols
            if any(point_on_segment(item["point"], *segment) for segment in group)
        }
        nets |= {
            name
            for name, point in labels
            if any(point_on_segment(point, *segment) for segment in group)
        }
        length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in group)
        lines.append(
            f"- net {'/'.join(sorted(nets)) or 'unnamed'}: {len(group)} segment(s), "
            f"{_mm(length)} mm, joins {', '.join(touched) or 'no pins'}"
        )
        for first, second in group:
            lines.append(f"    {_point(first)} -> {_point(second)}")
    lines += ["", "POWER SYMBOLS (rail name; glyph points from its connection point):"]
    for item in sorted(symbols, key=lambda s: (s["net"], s["point"])):
        tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
        direction = DIRECTION_NAMES[(_sign(tip[0]), _sign(tip[1]))]
        glyph = "ground glyph" if item["lib_id"] == "power:GND" else "supply arrow"
        on = terminals.get(item["point"], (None,))[0]
        where = f"on pin {on}" if on else "on a wire"
        lines.append(
            f"- {item['net']} {glyph} at {_point(item['point'])} {where}, pointing "
            f'{direction}; its text "{item["net"]}" centred at {_point(item["value"])}'
        )
    lines += ["", "POWER FLAGS (PWR_FLAG diamonds; the flag points from its connection point):"]
    for point, direction in sorted(flags):
        on = terminals.get(point, (None,))[0]
        lines.append(
            f"- at {_point(point)} {'on pin ' + on if on else 'on a wire'}, pointing {direction}"
        )
    lines += ["", "NET LABELS:"]
    lines += [f'- "{name}" at {_point(point)}' for name, point in sorted(labels)] or ["- none"]
    junctions = [
        (_nm(one(node, "at")[1]), _nm(one(node, "at")[2])) for node in children(tree, "junction")
    ]
    lines += ["", "JUNCTION DOTS:"]
    lines += [f"- {_point(point)}" for point in sorted(junctions)] or ["- none"]
    return "\n".join(lines) + "\n"
