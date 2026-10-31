"""Place reference/value text of vertical two-pin parts next to their bodies.

The protected compiler centres these fields about 10 mm right of the part. This pivot
presentation step moves each pair to the nearest clear position just right of the
body. Field boxes use the independent layout observer's text-size estimate, and a
position is accepted only when it touches no wire, body, pin, label, pin number or
other field.
"""

from __future__ import annotations

import re

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


def _field_box(center: tuple[int, int], text: str) -> Box:
    half = max(MINIMUM_FIELD_HALF_WIDTH, len(text) * FIELD_CHARACTER_HALF_WIDTH)
    return (
        center[0] - half,
        center[1] - FIELD_HALF_HEIGHT,
        center[0] + half,
        center[1] + FIELD_HALF_HEIGHT,
    )


def _vertical_bodies(tree: list) -> dict[str, Box]:
    """Body box (without pins) of each placed two-pin part whose pins are vertically aligned."""
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
        if len(pins) != 2 or not points or pins[0][0] != pins[1][0]:
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
        reference = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        bodies[reference] = box
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


def tighten_vertical_fields_text(text: str) -> tuple[str, list[dict]]:
    """Move vertical parts' right-hand reference/value pairs next to the body."""
    moves = []
    for reference, body in sorted(_vertical_bodies(parse(text)).items()):
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
        current_x = positions["Reference"][0]
        if positions["Value"][0] != current_x or current_x <= body[2]:
            continue
        half = max(
            max(MINIMUM_FIELD_HALF_WIDTH, len(prop[2]) * FIELD_CHARACTER_HALF_WIDTH)
            for prop in fields.values()
        )
        obstacles = _obstacles(text, tree, reference)
        target = body[2] + BODY_GAP + half
        chosen = None
        while target < current_x:
            if not any(
                _overlaps(_field_box((target, positions[name][1]), prop[2]), obstacle)
                for name, prop in fields.items()
                for obstacle in obstacles
            ):
                chosen = target
                break
            target += STEP
        if chosen is None:
            continue
        text = _move_fields(text, reference, chosen)
        moves.append(
            {
                "reference": reference,
                "from_x_mm": current_x / 1_000_000,
                "to_x_mm": chosen / 1_000_000,
            }
        )
    parse(text)
    return text, moves


def _move_fields(text: str, reference: str, x: int) -> str:
    for start, end, node in _forms(text):
        if node[0] != "symbol" or not any(
            p[1] == "Reference" and p[2] == reference for p in children(node, "property")
        ):
            continue
        block = re.sub(
            r'(\(property\s+"(?:Reference|Value)"\s+"(?:\\.|[^"\\])*"\s+\(at\s+)([-+0-9.eE]+)',
            lambda match: match[1] + f"{x / 1_000_000:.6f}",
            text[start:end],
        )
        return text[:start] + block + text[end:]
    raise ValueError(f"symbol {reference} not found")
