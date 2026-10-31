"""Place reference/value text of vertical two-pin parts next to their bodies.

The protected compiler centres these fields about 10 mm right of the part. This pivot
presentation step moves each pair to the nearest clear position just right of the
body. Field boxes use the independent layout observer's text-size estimate, and a
position is accepted only when it touches no wire, body, pin, label, pin number or
other field.
"""

from __future__ import annotations

import re

from ai_kicad.m2_text_layout import text_extents
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.m2a_core import _nm
from ai_kicad.sexpr import children, one, parse

from .power_symbols import GLYPH_TIPS, _forms, _overlaps, _pin_number_boxes, _wire_segments

Box = tuple[int, int, int, int]
# Clearance between the part body and the nearest edge of its text.
BODY_GAP = 1_270_000
STEP = 635_000
# The layout observer's conservative field half-height and per-character half-width.
FIELD_HALF_HEIGHT = 850_000
FIELD_CHARACTER_HALF_WIDTH = 445_000
MINIMUM_FIELD_HALF_WIDTH = 635_000
# Margin the router keeps around visible text; labels keep the same clearance from wires.
TEXT_PADDING = 500_000


def _field_box(center: tuple[int, int], text: str) -> Box:
    """Conservative text box: the wider of the observer's and the router's estimates."""
    width, height = text_extents(text, 0)
    half = max(
        MINIMUM_FIELD_HALF_WIDTH,
        len(text) * FIELD_CHARACTER_HALF_WIDTH,
        width // 2 + TEXT_PADDING,
    )
    half_height = max(FIELD_HALF_HEIGHT, height // 2 + TEXT_PADDING)
    return (center[0] - half, center[1] - half_height, center[0] + half, center[1] + half_height)


def _vertical_bodies(tree: list) -> dict[str, Box]:
    """Body boxes of two-pin vertical parts (kept for callers that need only those)."""
    return {
        reference: box
        for reference, (box, kind) in _label_bodies(tree).items()
        if kind == "vertical"
    }


def _label_bodies(tree: list) -> dict[str, tuple[Box, str]]:
    """Parts whose text belongs right of the body: two-pin vertical parts and connectors.

    ``vertical``: exactly two pins on one vertical line. ``connector``: every pin leaves
    the body on its left, so the right side is free for the reference and value.
    """
    library = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    bodies = {}
    for symbol in children(tree, "symbol"):
        lib_id = one(symbol, "lib_id")[1]
        definition = library.get(lib_id)
        if definition is None or lib_id in GLYPH_TIPS or lib_id == "power:PWR_FLAG":
            continue
        at = one(symbol, "at")
        origin, angle = (_nm(at[1]), _nm(at[2])), int(float(at[3]))
        mirrors = children(symbol, "mirror")
        mirror = mirrors[0][1] if mirrors else None
        unit = str(one(symbol, "unit")[1])
        pins, points = [], []
        for body in children(definition, "symbol"):
            if body[1].rsplit("_", 2)[-2] not in {"0", unit}:
                continue
            pins += [
                transform_library_point(
                    _nm(one(pin, "at")[1]), _nm(one(pin, "at")[2]), angle, mirror
                )
                for pin in children(body, "pin")
            ]
            for shape in children(body, "rectangle"):
                points += [one(shape, "start"), one(shape, "end")]
            for shape in children(body, "polyline"):
                points += children(one(shape, "pts"), "xy")
        if not pins or not points:
            continue
        placed = [
            transform_library_point(_nm(point[1]), _nm(point[2]), angle, mirror) for point in points
        ]
        box = (
            origin[0] + min(x for x, _y in placed),
            origin[1] + min(y for _x, y in placed),
            origin[0] + max(x for x, _y in placed),
            origin[1] + max(y for _x, y in placed),
        )
        if len(pins) == 2 and pins[0][0] == pins[1][0]:
            kind = "vertical"
        elif all(origin[0] + x < box[0] for x, _y in pins):
            kind = "connector"
        else:
            continue
        reference = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        bodies[reference] = (box, kind)
    return bodies


def _obstacles(text: str, tree: list, reference: str) -> list[Box]:
    from .schematic_review_native import _drawn_boxes

    symbol_boxes, text_boxes = _drawn_boxes(tree)
    boxes = [bounds for _owner, bounds in symbol_boxes]
    boxes += [bounds for owner, bounds in text_boxes if owner != reference]
    boxes += [bounds for _owner, bounds in _pin_number_boxes(text, tree)]
    boxes += [
        (
            min(first[0], second[0]) - 100_000,
            min(first[1], second[1]) - 100_000,
            max(first[0], second[0]) + 100_000,
            max(first[1], second[1]) + 100_000,
        )
        for first, second in _wire_segments(tree)
    ]
    return boxes


# Reach of the search for a clear position right of the body.
SEARCH_REACH = 25_400_000
# Vertical offset of a connector's reference (above) and value (below) from its centre.
CONNECTOR_ROW_OFFSET = 1_350_000


def tighten_vertical_fields_text(text: str) -> tuple[str, list[dict]]:
    """Move reference/value pairs of vertical parts and connectors next to the body.

    Vertical parts keep each field's height; connector text is centred on the body,
    reference above value. A move is kept only when it brings the text closer to the body.
    """
    moves = []
    for reference, (body, kind) in sorted(_label_bodies(parse(text)).items()):
        tree = parse(text)
        symbol = next(
            item
            for item in children(tree, "symbol")
            if any(p[1] == "Reference" and p[2] == reference for p in children(item, "property"))
        )
        fields = {
            prop[1]: prop
            for prop in children(symbol, "property")
            if prop[1] in {"Reference", "Value"} and not children(prop, "hide")
        }
        if set(fields) != {"Reference", "Value"}:
            continue
        positions = {
            name: (_nm(one(prop, "at")[1]), _nm(one(prop, "at")[2]))
            for name, prop in fields.items()
        }
        if kind == "vertical" and (
            positions["Value"][0] != positions["Reference"][0]
            or positions["Reference"][0] <= body[2]
        ):
            continue
        centre = ((body[0] + body[2]) // 2, (body[1] + body[3]) // 2)

        def distance(points: dict[str, tuple[int, int]]) -> int:
            return sum(abs(x - centre[0]) + abs(y - centre[1]) for x, y in points.values())

        half = max((_field_box((0, 0), prop[2])[2]) for prop in fields.values())
        first = body[2] + BODY_GAP + half
        if kind == "vertical":
            # Right of the body, each field at its own height.
            proposals = [
                {name: (x, positions[name][1]) for name in fields}
                for x in range(first, first + SEARCH_REACH, STEP)
            ]
        else:
            # Right of the body centred on it, or centred above it; reference on top.
            proposals = [
                {
                    "Reference": (x, centre[1] - CONNECTOR_ROW_OFFSET),
                    "Value": (x, centre[1] + CONNECTOR_ROW_OFFSET),
                }
                for x in range(first, first + SEARCH_REACH, STEP)
            ]
            lowest = body[1] - BODY_GAP - FIELD_HALF_HEIGHT
            proposals += [
                {
                    "Reference": (centre[0], y - 2 * CONNECTOR_ROW_OFFSET),
                    "Value": (centre[0], y),
                }
                for y in range(lowest, lowest - SEARCH_REACH, -STEP)
            ]
        obstacles = _obstacles(text, tree, reference)
        clear = [
            proposed
            for proposed in proposals
            if distance(proposed) < distance(positions)
            and not any(
                _overlaps(_field_box(proposed[name], prop[2]), obstacle)
                for name, prop in fields.items()
                for obstacle in obstacles
            )
        ]
        chosen = min(clear, key=distance) if clear else None
        if chosen is None:
            continue
        text = _move_fields(text, reference, chosen)
        moves.append(
            {
                "reference": reference,
                "kind": kind,
                "from_mm": {
                    name: [v / 1_000_000 for v in point] for name, point in positions.items()
                },
                "to_mm": {name: [v / 1_000_000 for v in point] for name, point in chosen.items()},
            }
        )
    parse(text)
    return text, moves


def _move_fields(text: str, reference: str, points: dict[str, tuple[int, int]]) -> str:
    for start, end, node in _forms(text):
        if node[0] != "symbol" or not any(
            p[1] == "Reference" and p[2] == reference for p in children(node, "property")
        ):
            continue
        block = text[start:end]
        for name, (x, y) in points.items():
            block = re.sub(
                r'(\(property\s+"' + name + r'"\s+"(?:\\.|[^"\\])*"\s+\(at\s+)'
                r"([-+0-9.eE]+)\s+([-+0-9.eE]+)",
                lambda match: match[1] + f"{x / 1_000_000:.6f} {y / 1_000_000:.6f}",
                block,
            )
        return text[:start] + block + text[end:]
    raise ValueError(f"symbol {reference} not found")
