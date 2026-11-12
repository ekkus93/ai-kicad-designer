"""Place reference/value text of two-pin parts next to their bodies.

The protected compiler centres these fields about 10 mm right of a vertical part and
about 10 mm above a horizontal one. This pivot presentation step moves each pair to the
nearest clear position just right of a vertical body, or just above or below a
horizontal one. Connectors and body-less power units (an op-amp's V+/V- unit) get the same
treatment. Parts are keyed by reference and unit, because every unit of a
multi-unit part shares one reference. Field boxes use the independent layout observer's text-size estimate, and a
position is accepted only when it touches no wire, body, pin, label, pin number or
other field.
"""

from __future__ import annotations

import re

from ai_kicad.m2_text_layout import text_extents
from ai_kicad.pivot.schematic_fields import measure_field_association
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.m2a_core import _nm
from ai_kicad.sexpr import children, one, parse

from ai_kicad.m2_geometry import label_text_rect

from ai_kicad.m2a_constants import PITCH

from .power_symbols import (
    GLYPH_TIPS,
    _forms,
    _glyph_boxes,
    _overlaps,
    _pin_number_boxes,
    _wire_segments,
    power_symbols,
)

Box = tuple[int, int, int, int]
Part = tuple[str, int]
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


def _vertical_bodies(tree: list) -> dict[Part, Box]:
    """Body boxes of two-pin vertical parts (kept for callers that need only those)."""
    return {part: box for part, (box, kind) in _label_bodies(tree).items() if kind == "vertical"}


def _label_bodies(tree: list) -> dict[Part, tuple[Box, str]]:
    """Parts whose text belongs right of the body, keyed by (reference, unit).

    ``vertical``: exactly two pins on one vertical line. ``horizontal``: exactly two
    pins on one horizontal line; its text belongs above or below the body. ``connector``: every pin leaves
    the body on its left, so the right side is free for the reference and value.
    ``power_unit``: a unit with no drawn body whose pins all lie on one vertical line
    (such as an op-amp's supply unit); its body spans that line and the symbol anchor.
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
        reference = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        if not pins:
            continue
        if not points:
            if len({x for x, _y in pins}) != 1 or len(pins) < 2:
                continue
            line = origin[0] + pins[0][0]
            box = (
                min(line - BODY_GAP, origin[0]),
                origin[1] + min(y for _x, y in pins),
                max(line + BODY_GAP, origin[0]),
                origin[1] + max(y for _x, y in pins),
            )
            bodies[(reference, int(unit))] = (box, "power_unit")
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
        elif len(pins) == 2 and pins[0][1] == pins[1][1]:
            kind = "horizontal"
        elif all(origin[0] + x < box[0] for x, _y in pins):
            kind = "connector"
        else:
            continue
        bodies[(reference, int(unit))] = (box, kind)
    return bodies


def _symbol(tree: list, part: Part) -> list:
    reference, unit = part
    return next(
        item
        for item in children(tree, "symbol")
        if int(one(item, "unit")[1]) == unit
        and any(p[1] == "Reference" and p[2] == reference for p in children(item, "property"))
    )


def _association_witnesses(tree: list, part: Part) -> int:
    return sum(
        1
        for item in measure_field_association(tree)["witnesses"]
        if (item["reference"], item["unit"]) == part
    )


def _nearer_witnesses(tree: list, part: Part) -> int:
    from .readability_checks import fields_nearer_another_part

    return sum(
        1
        for item in fields_nearer_another_part(tree, include_bodyless=True)
        if (item["reference"], item["unit"]) == part
    )


def _obstacles(text: str, tree: list, part: Part) -> list[Box]:
    """Everything the part's text must stay clear of, except that text itself.

    Other units of the same part share its reference, so the part's own field boxes
    are recognised by their centres (its current field positions), not by owner name.
    """
    from .schematic_review_native import _drawn_boxes

    own = {
        (_nm(one(prop, "at")[1]), _nm(one(prop, "at")[2]))
        for prop in children(_symbol(tree, part), "property")
        if prop[1] in {"Reference", "Value"}
    }
    symbol_boxes, text_boxes = _drawn_boxes(tree)
    boxes = [bounds for _owner, bounds in symbol_boxes]
    boxes += [
        bounds
        for owner, bounds in text_boxes
        if owner != part[0]
        or ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2) not in own
    ]
    boxes += [bounds for _owner, bounds in _pin_number_boxes(text, tree)]
    # The protected observers read each power symbol as a label whose text runs right.
    boxes += [label_text_rect(item["net"], item["point"]) for item in power_symbols(tree)]
    # A power symbol's rail name keeps a grid step clear of other text (power-symbol
    # clearance), so part text keeps the same distance from it.
    for item in power_symbols(tree):
        left, top, right, bottom = _glyph_boxes(
            item["lib_id"], item["point"], item["angle"], item["net"], item["value"]
        )[1]
        boxes.append((left - PITCH, top - PITCH, right + PITCH, bottom + PITCH))
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


# The protected layout observer rejects any field position outside this A4 content area.
PAGE_CONTENT: Box = (20_320_000, 25_400_000, 276_680_000, 184_600_000)


def _on_page(points: dict[str, tuple[int, int]]) -> bool:
    return all(
        PAGE_CONTENT[0] <= x <= PAGE_CONTENT[2] and PAGE_CONTENT[1] <= y <= PAGE_CONTENT[3]
        for x, y in points.values()
    )


# Reach of the search for a clear position right of the body.
SEARCH_REACH = 25_400_000
# Vertical offset of a connector's reference (above) and value (below) from its centre.
CONNECTOR_ROW_OFFSET = 1_350_000
# How far above a power unit's top pin its text may be, before it goes beside the unit.
POWER_UNIT_REACH = 4 * 1_270_000
# How far off the pin column's centre line a power unit's text written beside it may sit.
POWER_UNIT_BESIDE_SLACK = 2 * 1_270_000


def power_unit_text_spots(tree: list) -> list[tuple[str, Box]]:
    """Text boxes of the reference and value centred just above each power unit.

    That is where tighten_vertical_fields_text puts a power unit's text first; a power
    symbol drawn there would push the text beside the unit's pin names.
    """
    spots = []
    for part, (body, kind) in sorted(_label_bodies(tree).items()):
        if kind != "power_unit":
            continue
        fields = {
            prop[1]: prop[2]
            for prop in children(_symbol(tree, part), "property")
            if prop[1] in {"Reference", "Value"} and not children(prop, "hide")
        }
        if set(fields) != {"Reference", "Value"}:
            continue
        centre = (body[0] + body[2]) // 2
        value_y = body[1] - BODY_GAP - FIELD_HALF_HEIGHT
        for name, y in (("Reference", value_y - 2 * CONNECTOR_ROW_OFFSET), ("Value", value_y)):
            # The drawn text itself; the placement step's padding would also rule out a
            # symbol drawn sideways at the pin.
            width, height = text_extents(fields[name], 0)
            spots.append(
                (
                    part[0],
                    (centre - width // 2, y - height // 2, centre + width // 2, y + height // 2),
                )
            )
    return spots


def tighten_vertical_fields_text(
    text: str, power_unit_both_sides: bool = False
) -> tuple[str, list[dict]]:
    """Move reference/value pairs of two-pin parts, connectors and power units nearer.

    Vertical parts keep each field's height; horizontal parts' text is centred above or
    below the body; connector text is centred beside the body (or above it), and
    power-unit text centred above it, reference above value. A move is kept only when it
    brings the text closer to the body and does not make the part's text read as
    belonging to another symbol (the independent owner-association measurement).

    With ``power_unit_both_sides`` (brief v7), power-unit text that cannot sit above the
    unit may be written on either side of its pin column, up to two grid steps off the
    column's centre line; otherwise only on its right, level with the centre. It also
    rejects a move that leaves the text nearer another part's drawing than its own.
    """
    moves = []
    for part, (body, kind) in sorted(_label_bodies(parse(text)).items()):
        reference, unit = part
        tree = parse(text)
        fields = {
            prop[1]: prop
            for prop in children(_symbol(tree, part), "property")
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
        if kind == "horizontal" and positions["Value"][0] != positions["Reference"][0]:
            continue
        centre = ((body[0] + body[2]) // 2, (body[1] + body[3]) // 2)

        def distance(points: dict[str, tuple[int, int]]) -> int:
            return sum(abs(x - centre[0]) + abs(y - centre[1]) for x, y in points.values())

        half = max((_field_box((0, 0), prop[2])[2]) for prop in fields.values())
        first = body[2] + BODY_GAP + half
        if kind == "horizontal":
            # Centred above the body or centred below it; reference on top.
            above = body[1] - BODY_GAP - FIELD_HALF_HEIGHT
            below = body[3] + BODY_GAP + FIELD_HALF_HEIGHT
            proposals = [
                {"Reference": (centre[0], y - 2 * CONNECTOR_ROW_OFFSET), "Value": (centre[0], y)}
                for y in range(above, above - SEARCH_REACH, -STEP)
            ] + [
                {"Reference": (centre[0], y), "Value": (centre[0], y + 2 * CONNECTOR_ROW_OFFSET)}
                for y in range(below, below + SEARCH_REACH, STEP)
            ]
        elif kind == "vertical":
            # Right of the body, each field at its own height.
            proposals = [
                {name: (x, positions[name][1]) for name in fields}
                for x in range(first, first + SEARCH_REACH, STEP)
            ]
        elif kind == "power_unit":
            # Just above the top pin, centred or shifted sideways past a wire that leaves
            # the pin upward, clear of the pin names beside it; beside the unit only when
            # nothing above fits.
            lowest = body[1] - BODY_GAP - FIELD_HALF_HEIGHT
            shift = half + BODY_GAP
            proposals = [
                {
                    "Reference": (centre[0] + dx, y - 2 * CONNECTOR_ROW_OFFSET),
                    "Value": (centre[0] + dx, y),
                }
                for y in range(lowest, lowest - POWER_UNIT_REACH, -STEP)
                for step in range(0, shift + 1, STEP)
                for dx in dict.fromkeys((-step, step))
            ] + [
                # Beside the pin column on either side, up to two grid steps off its
                # centre line, so the text stays next to the pins it names.
                {
                    "Reference": (x, y - CONNECTOR_ROW_OFFSET),
                    "Value": (x, y + CONNECTOR_ROW_OFFSET),
                    "beside": True,
                }
                for offset in range(0, SEARCH_REACH, STEP)
                for x in (
                    (first + offset, body[0] - BODY_GAP - half - offset)
                    if power_unit_both_sides
                    else (first + offset,)
                )
                for y in (
                    range(
                        centre[1] - POWER_UNIT_BESIDE_SLACK,
                        centre[1] + POWER_UNIT_BESIDE_SLACK + 1,
                        STEP,
                    )
                    if power_unit_both_sides
                    else (centre[1],)
                )
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
        fallback = [proposed for proposed in proposals if proposed.pop("beside", False)]
        obstacles = _obstacles(text, tree, part)
        clear = sorted(
            (
                proposed
                for proposed in proposals
                if distance(proposed) < distance(positions)
                and _on_page(proposed)
                and not any(
                    _overlaps(_field_box(proposed[name], prop[2]), obstacle)
                    for name, prop in fields.items()
                    for obstacle in obstacles
                )
            ),
            key=lambda proposed: (proposed in fallback, distance(proposed)),
        )
        before = _association_witnesses(tree, part)
        nearer_before = _nearer_witnesses(tree, part) if power_unit_both_sides else 0
        for chosen in clear:
            moved = _move_fields(text, part, chosen)
            if _association_witnesses(parse(moved), part) > before:
                continue
            # Brief v7 also measures whether the text sits nearer another part's drawing.
            if power_unit_both_sides and _nearer_witnesses(parse(moved), part) > nearer_before:
                continue
            text = moved
            moves.append(
                {
                    "reference": reference,
                    "unit": unit,
                    "kind": kind,
                    "from_mm": {
                        name: [v / 1_000_000 for v in point] for name, point in positions.items()
                    },
                    "to_mm": {
                        name: [v / 1_000_000 for v in point] for name, point in chosen.items()
                    },
                }
            )
            break
    parse(text)
    return text, moves


def _move_fields(text: str, part: Part, points: dict[str, tuple[int, int]]) -> str:
    reference, unit = part
    for start, end, node in _forms(text):
        if (
            node[0] != "symbol"
            or not children(node, "unit")
            or int(one(node, "unit")[1]) != unit
            or not any(
                p[1] == "Reference" and p[2] == reference for p in children(node, "property")
            )
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
    raise ValueError(f"symbol {reference} unit {unit} not found")


# A net label's text closer than this to a pin number or field reads as touching it.
LABEL_CLEARANCE = 635_000
# Furthest a label's stub is lengthened to make that room.
LABEL_REACH = 4 * 1_270_000


def _gap(first: Box, second: Box) -> int:
    """Separation of two boxes; negative when they overlap."""
    gap = max(
        first[0] - second[2], second[0] - first[2], first[1] - second[3], second[1] - first[3]
    )
    return gap if gap >= 0 else -1


def _label_text_box(name: str, point: tuple[int, int], angle: int) -> Box:
    from ai_kicad.m2_geometry import label_text_width

    width = label_text_width(name)
    if angle == 0:
        return (point[0], point[1] - 2_000_000, point[0] + width, point[1])
    return (point[0] - width, point[1] - 2_000_000, point[0], point[1])


def _relocate(block: str, old: tuple[int, int], new: tuple[int, int]) -> str:
    """Move the first ``(at x y ...)`` of a form from ``old`` to ``new``."""

    def number(value: int) -> str:
        return f"{value / 1_000_000:.6f}"

    pattern = re.compile(r"\(at\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)")
    match = pattern.search(block)
    if match is None or (_nm(match[1]), _nm(match[2])) != old:
        raise ValueError("form is not at the expected point")
    return block[: match.start()] + f"(at {number(new[0])} {number(new[1])}" + block[match.end() :]


def clear_label_pin_numbers_text(text: str) -> tuple[str, list[dict]]:
    """Give a net label crowding a pin number room by lengthening its free stub end.

    A horizontal label whose text comes within ``LABEL_CLEARANCE`` of a pin number or
    other text is moved outward along its stub, one grid step at a time, when its
    anchor is a free wire end (one wire, no pin, no other wire through it). The wire
    is extended to the new anchor and PWR_FLAGs on that end move with the label, so
    the netlist is unchanged. The first step at which the text is clear and the
    lengthened stub, label and flags touch nothing else is kept.
    """
    from .power_symbols import _append_forms, _pin_points, _wire_form, _wire_segments
    from .schematic_review_native import _drawn_boxes

    moves = []
    names = [
        (label[1], (_nm(one(label, "at")[1]), _nm(one(label, "at")[2])))
        for label in children(parse(text), "label")
        if int(float(one(label, "at")[3])) % 360 in {0, 180}
    ]
    for name, anchor in names:
        tree = parse(text)
        label = next(
            item
            for item in children(tree, "label")
            if item[1] == name and (_nm(one(item, "at")[1]), _nm(one(item, "at")[2])) == anchor
        )
        angle = int(float(one(label, "at")[3])) % 360
        outward = -1 if angle == 0 else 1
        box = _label_text_box(name, anchor, angle)
        numbers = [bounds for _owner, bounds in _pin_number_boxes(text, tree)]
        symbol_boxes, text_boxes = _drawn_boxes(tree)
        # Stacked connector labels sit a pitch apart by design: they must not overlap,
        # but only pin numbers and symbol fields need the full clearance.
        fields = [bounds for owner, bounds in text_boxes if not owner.startswith("label-")]
        labels = [
            bounds
            for owner, bounds in text_boxes
            if owner.startswith("label-") and not (owner == f"label-{name}" and bounds == box)
        ]

        def crowding(candidate: Box) -> int:
            if any(_overlaps(candidate, bounds) for bounds in labels):
                return -1
            return min(
                (_gap(candidate, bounds) for bounds in numbers + fields), default=LABEL_CLEARANCE
            )

        before = crowding(box)
        if before >= LABEL_CLEARANCE:
            continue
        segments = _wire_segments(tree)
        touching = [segment for segment in segments if anchor in segment]
        through = [
            segment
            for segment in segments
            if anchor not in segment and _on_segment(anchor, segment)
        ]
        flag_pins = {
            (_nm(one(symbol, "at")[1]), _nm(one(symbol, "at")[2]))
            for symbol in children(tree, "symbol")
            if one(symbol, "lib_id")[1] == "power:PWR_FLAG"
        }
        points = _pin_points(tree) - flag_pins
        if len(touching) != 1 or through or anchor in points:
            continue
        other_end = next(end for end in touching[0] if end != anchor)
        if other_end[1] != anchor[1] or (other_end[0] - anchor[0]) * outward > 0:
            continue
        flags = [
            symbol
            for symbol in children(tree, "symbol")
            if one(symbol, "lib_id")[1] == "power:PWR_FLAG"
            and (_nm(one(symbol, "at")[1]), _nm(one(symbol, "at")[2])) == anchor
        ]
        flag_names = {
            next(p[2] for p in children(flag, "property") if p[1] == "Reference") for flag in flags
        }
        bodies = [
            bounds
            for owner, bounds in symbol_boxes
            if owner not in flag_names and not _overlaps(box, bounds)
        ]
        for step in range(1_270_000, LABEL_REACH + 1, 1_270_000):
            new = (anchor[0] + outward * step, anchor[1])
            moved = _label_text_box(name, new, angle)
            stub = (min(new[0], anchor[0]), anchor[1], max(new[0], anchor[0]), anchor[1])
            # The text sits above its own wire: test it against wires a hair above that line.
            lifted = (moved[0], moved[1], moved[2], moved[3] - 100_000)
            if (
                crowding(moved) < LABEL_CLEARANCE
                or not _on_page({"anchor": new, "text": (moved[0], moved[1])})
                or not _on_page({"end": (moved[2], moved[3])})
                or any(_overlaps(moved, bounds) or _overlaps(stub, bounds) for bounds in bodies)
                or any(
                    _overlaps(lifted, _segment_box(segment))
                    or _touches(stub, _segment_box(segment))
                    for segment in segments
                    if segment != touching[0]
                )
                or any(stub[0] <= x <= stub[2] and y == anchor[1] for x, y in points)
            ):
                continue
            text = _move_label(text, name, anchor, new)
            for reference in sorted(flag_names):
                text = _move_symbol(text, reference, anchor, new)
            text = _append_forms(text, [_wire_form(new, anchor, name)])
            moves.append(
                {
                    "label": name,
                    "from_mm": [v / 1_000_000 for v in anchor],
                    "to_mm": [v / 1_000_000 for v in new],
                    "flags": sorted(flag_names),
                    "clearance_mm": [before / 1_000_000, crowding(moved) / 1_000_000],
                }
            )
            break
    parse(text)
    return text, moves


def _touches(first: Box, second: Box) -> bool:
    """Closed-box intersection: shared edges and end points count."""
    return (
        first[0] <= second[2]
        and second[0] <= first[2]
        and first[1] <= second[3]
        and second[1] <= first[3]
    )


def _segment_box(segment: tuple[tuple[int, int], tuple[int, int]]) -> Box:
    first, second = segment
    return (
        min(first[0], second[0]),
        min(first[1], second[1]),
        max(first[0], second[0]),
        max(first[1], second[1]),
    )


def _on_segment(point: tuple[int, int], segment) -> bool:
    from ai_kicad.m2_geometry import point_on_segment

    return point_on_segment(point, *segment)


def _move_label(text: str, name: str, old: tuple[int, int], new: tuple[int, int]) -> str:
    for start, end, node in _forms(text):
        if (
            node[0] == "label"
            and node[1] == name
            and (_nm(one(node, "at")[1]), _nm(one(node, "at")[2])) == old
        ):
            return text[:start] + _relocate(text[start:end], old, new) + text[end:]
    raise ValueError(f"label {name} not found")


def _move_symbol(text: str, reference: str, old: tuple[int, int], new: tuple[int, int]) -> str:
    for start, end, node in _forms(text):
        if node[0] == "symbol" and any(
            p[1] == "Reference" and p[2] == reference for p in children(node, "property")
        ):
            return text[:start] + _relocate(text[start:end], old, new) + text[end:]
    raise ValueError(f"symbol {reference} not found")
