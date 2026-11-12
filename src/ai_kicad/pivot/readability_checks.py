"""Brief-v4 readability measurements that ERC, netlist and field checks do not cover.

Each check targets a defect class the owner or an outside review found in drawings that
passed every brief-v3 check and the model review
(``review_qualification_v3_2026-11-12_qwen35_256k_run1``):

* rail wiring that detours far beyond the shortest route joining its terminals;
* power symbols drawn against convention (supply arrow down, ground glyph up).

Brief v5 adds page balance, and brief v6 adds reference/value text that sits nearer
another part than its own (``fields_nearer_another_part``).

Wires through a bodyless unit's pin-name column are measured by
``schematic_review_native.wires_through_bodyless_units``.
"""

from __future__ import annotations

from ai_kicad.m2_transform import transform_library_point
from ai_kicad.sexpr import children, one

from .power_symbols import GLYPH_TIPS, power_symbols

Point = tuple[int, int]
Segment = tuple[Point, Point]

# A rail wire group fails only when it is both proportionally and absolutely long: short
# stubs to a power symbol bend once and reach 2-2.5x their direct distance, but only a few
# millimetres; real detours measured 1.10-2.35x over 12.7-122 mm (owner choice 2026-11-12).
MAXIMUM_RAIL_ROUTE_RATIO = 1.15
MINIMUM_RAIL_DETOUR_NM = 7_620_000
# Page directions (KiCad Y grows downward) that a glyph must never point.
FORBIDDEN_DIRECTIONS = {"power:VCC": (0, 1), "power:GND": (0, -1)}


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def _nm(value) -> int:
    return round(float(value) * 1_000_000)


def _segments(tree: list) -> list[Segment]:
    result = []
    for wire in children(tree, "wire"):
        first, second = children(one(wire, "pts"), "xy")[:2]
        result.append(((_nm(first[1]), _nm(first[2])), (_nm(second[1]), _nm(second[2]))))
    return result


def _on(point: Point, segment: Segment) -> bool:
    (x1, y1), (x2, y2) = segment
    return (
        min(x1, x2) <= point[0] <= max(x1, x2)
        and min(y1, y2) <= point[1] <= max(y1, y2)
        and (x2 - x1) * (point[1] - y1) == (y2 - y1) * (point[0] - x1)
    )


def wire_groups(segments: list[Segment]) -> list[list[Segment]]:
    """Wires joined end-to-end or by an end landing on another wire (a T-junction)."""
    parent = list(range(len(segments)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i, first in enumerate(segments):
        for j in range(i + 1, len(segments)):
            second = segments[j]
            if any(_on(end, second) for end in first) or any(_on(end, first) for end in second):
                parent[find(i)] = find(j)
    groups: dict[int, list[Segment]] = {}
    for index, segment in enumerate(segments):
        groups.setdefault(find(index), []).append(segment)
    return list(groups.values())


def _rectilinear_spanning_length(points: set[Point]) -> int:
    """Length of the minimum spanning tree of ``points`` under Manhattan distance."""
    remaining = list(points)
    if len(remaining) < 2:
        return 0
    start = remaining.pop()
    best = {point: abs(point[0] - start[0]) + abs(point[1] - start[1]) for point in remaining}
    total = 0
    while best:
        nearest = min(best, key=lambda point: (best[point], point))
        total += best.pop(nearest)
        for point in best:
            distance = abs(point[0] - nearest[0]) + abs(point[1] - nearest[1])
            best[point] = min(best[point], distance)
    return total


def rail_route_detours(tree: list, terminal_inventory: list[dict], rails: list[str]) -> list[dict]:
    """Rail wire groups much longer than the shortest rectilinear tree of their terminals.

    A group is measured when every terminal and power symbol it touches belongs to one
    asserted rail. The spanning tree over Manhattan distance is an upper bound on the
    shortest rectilinear wiring, so the ratio never overstates a detour.
    """
    terminals: dict[Point, str] = {
        (_nm(item["x_mm"]), _nm(item["y_mm"])): item["net"] for item in terminal_inventory
    }
    terminals.update({item["point"]: item["net"] for item in power_symbols(tree)})
    witnesses = []
    for group in wire_groups(_segments(tree)):
        touched = {
            (point, net)
            for point, net in terminals.items()
            if any(_on(point, segment) for segment in group)
        }
        nets = {net for _point, net in touched}
        if len(nets) != 1 or next(iter(nets)) not in rails:
            continue
        length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in group)
        shortest = _rectilinear_spanning_length({point for point, _net in touched})
        if not shortest:
            continue
        ratio = length / shortest
        if ratio > MAXIMUM_RAIL_ROUTE_RATIO and length - shortest > MINIMUM_RAIL_DETOUR_NM:
            witnesses.append(
                {
                    "net": next(iter(nets)),
                    "wire_length_mm": round(length / 1e6, 2),
                    "shortest_route_mm": round(shortest / 1e6, 2),
                    "ratio": round(ratio, 3),
                    "terminals_mm": sorted(
                        [round(x / 1e6, 2), round(y / 1e6, 2)] for (x, y), _net in touched
                    ),
                }
            )
    return witnesses


def power_symbols_against_convention(tree: list) -> list[dict]:
    """Supply arrows pointing down and ground glyphs pointing up on the page."""
    witnesses = []
    for item in power_symbols(tree):
        tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
        direction = (_sign(tip[0]), _sign(tip[1]))
        if direction == FORBIDDEN_DIRECTIONS[item["lib_id"]]:
            witnesses.append(
                {
                    "power_symbol": item["reference"],
                    "net": item["net"],
                    "glyph": item["lib_id"],
                    "points": "down" if direction == (0, 1) else "up",
                    "at_mm": [item["point"][0] / 1e6, item["point"][1] / 1e6],
                }
            )
    return witnesses


# Usable A4 frame and title block, as the protected observer defines them (nm).
FRAME = (20_320_000, 25_400_000, 276_680_000, 184_600_000)
TITLE_BLOCK = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
# Brief v5: the drawing's centre may sit at most this fraction of the frame's half-width
# (half-height) from the frame centre (owner choice 2026-11-12: centre the drawing).
MAXIMUM_PAGE_OFFSET = 0.25


def content_extent(tree: list) -> tuple[int, int, int, int]:
    """Box around every wire, symbol body/pin stub and visible field or label text."""
    from .schematic_review_native import _drawn_boxes

    symbol_boxes, text_boxes = _drawn_boxes(tree)
    xs, ys = [], []
    for _owner, (left, top, right, bottom) in symbol_boxes + text_boxes:
        xs += [left, right]
        ys += [top, bottom]
    for start, end in _segments(tree):
        xs += [start[0], end[0]]
        ys += [start[1], end[1]]
    return min(xs), min(ys), max(xs), max(ys)


def _overlap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return (
        first[0] < second[2]
        and second[0] < first[2]
        and first[1] < second[3]
        and second[1] < first[3]
    )


def page_offset(extent: tuple[int, int, int, int]) -> tuple[float, float]:
    """Centre of ``extent`` from the frame centre, in half-widths and half-heights."""
    left, top, right, bottom = FRAME
    return (
        ((extent[0] + extent[2]) / 2 - (left + right) / 2) / ((right - left) / 2),
        ((extent[1] + extent[3]) / 2 - (top + bottom) / 2) / ((bottom - top) / 2),
    )


def placement_fits(extent: tuple[int, int, int, int]) -> bool:
    """Whether a drawing's extent lies inside the usable frame and clear of the title block."""
    left, top, right, bottom = FRAME
    inside = extent[0] >= left and extent[1] >= top and extent[2] <= right and extent[3] <= bottom
    return inside and not _overlap(extent, TITLE_BLOCK)


def page_balance_witnesses(tree: list) -> list[dict]:
    """A drawing outside the frame, over the title block, or off the frame centre."""
    extent = content_extent(tree)
    offset = page_offset(extent)
    witnesses = []
    if not placement_fits(extent):
        witnesses.append(
            {
                "reason": "drawing extends outside the usable frame or over the title block",
                "extent_mm": [round(value / 1e6, 2) for value in extent],
                "frame_mm": [value / 1e6 for value in FRAME],
            }
        )
    if max(abs(offset[0]), abs(offset[1])) > MAXIMUM_PAGE_OFFSET:
        witnesses.append(
            {
                "reason": "drawing is off the page centre",
                "offset_fraction": [round(offset[0], 3), round(offset[1], 3)],
                "limit": MAXIMUM_PAGE_OFFSET,
            }
        )
    return witnesses


# A visible reference or value fails when another part's drawing is nearer to it than its
# own unit's drawing and it is more than four drafting pitches from its own drawing. The
# accepted drawings' nearest-other cases sit 3.72 mm from their own part; the historical
# R1/R2 text measured 5.34-8.04 mm and led_series's detached value 6.93 mm (owner choice
# 2026-11-12). Units drawn without a body, such as U1C, are exempt: their label stays
# beside the pin column by owner decision and has no body to sit against.
MINIMUM_FIELD_OWNER_GAP_NM = 5_080_000


def _gap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    dx = max(0, second[0] - first[2], first[0] - second[2])
    dy = max(0, second[1] - first[3], first[1] - second[3])
    return (dx * dx + dy * dy) ** 0.5


def _placed_parts(tree: list) -> list[tuple[str, int, list, bool, list, set]]:
    """Each placed unit: reference, unit, drawn boxes, drawn without a body, fields and
    pin connection points."""
    from ai_kicad.m2_text_layout import property_page_angle, text_extents

    from .power_symbols import _pin_points

    from .schematic_review_native import _drawn_boxes

    head = [tree[0], one(tree, "lib_symbols")]
    placed = []
    for symbol in children(tree, "symbol"):
        properties = {prop[1]: prop for prop in children(symbol, "property")}
        reference = properties["Reference"][2]
        if reference.startswith("#"):
            continue
        bodyless: list = []
        boxes = [box for _owner, box in _drawn_boxes(head + [symbol], bodyless)[0]]
        angle = int(float(one(symbol, "at")[3]))
        fields = []
        for name in ("Reference", "Value"):
            prop = properties.get(name)
            if prop is None or children(prop, "hide"):
                continue
            effects = children(prop, "effects")
            if effects and (children(effects[0], "hide") or "hide" in effects[0]):
                continue
            size = one(one(effects[0], "font"), "size") if effects else None
            scale = max(_nm(size[1]), _nm(size[2])) / 1_270_000 if size else 1.0
            at = one(prop, "at")
            width, height = text_extents(prop[2], property_page_angle(angle, int(float(at[3]))))
            half_width, half_height = round(width * scale / 2), round(height * scale / 2)
            x, y = _nm(at[1]), _nm(at[2])
            fields.append(
                (name, prop[2], (x - half_width, y - half_height, x + half_width, y + half_height))
            )
        placed.append(
            (
                reference,
                int(one(symbol, "unit")[1]),
                boxes,
                bool(bodyless),
                fields,
                _pin_points(head + [symbol]),
            )
        )
    return placed


def fields_nearer_another_part(tree: list, include_bodyless: bool = False) -> list[dict]:
    """Visible reference/value text that reads as belonging to a different part.

    Brief v6 exempts units drawn without a body; brief v7 measures their text against
    their pin column (``include_bodyless``).
    """
    placed = _placed_parts(tree)
    witnesses = []
    for reference, unit, boxes, bodyless, fields, _pins in placed:
        if (bodyless and not include_bodyless) or not boxes:
            continue
        for name, text, box in fields:
            own = min(_gap(box, other) for other in boxes)
            nearest = min(
                (
                    (_gap(box, other), other_reference, other_unit)
                    for other_reference, other_unit, other_boxes, *_rest in placed
                    if (other_reference, other_unit) != (reference, unit)
                    for other in other_boxes
                ),
                default=None,
            )
            if nearest and nearest[0] < own and own > MINIMUM_FIELD_OWNER_GAP_NM:
                witnesses.append(
                    {
                        "reference": reference,
                        "unit": unit,
                        "field": name,
                        "text": text,
                        "own_part_gap_mm": round(own / 1e6, 2),
                        "nearest_part": f"{nearest[1]}:{nearest[2]}",
                        "nearest_part_gap_mm": round(nearest[0] / 1e6, 2),
                    }
                )
    return witnesses


def _closest_points(first: tuple, second: tuple) -> tuple[Point, Point]:
    """The nearest pair of points of two axis-aligned boxes."""
    points = []
    for low_a, high_a, low_b, high_b in (
        (first[0], first[2], second[0], second[2]),
        (first[1], first[3], second[1], second[3]),
    ):
        if high_a < low_b:
            points.append((high_a, low_b))
        elif high_b < low_a:
            points.append((low_a, high_b))
        else:
            middle = (max(low_a, low_b) + min(high_a, high_b)) // 2
            points.append((middle, middle))
    return (points[0][0], points[1][0]), (points[0][1], points[1][1])


def _crosses(start: Point, end: Point, wire: Segment) -> bool:
    """Whether an axis-aligned wire meets the straight line from ``start`` to ``end``."""
    (x1, y1), (x2, y2) = wire

    def side(point: Point, a: Point, b: Point) -> int:
        return _sign((b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0]))

    if start == end:
        return False
    first, second = side(wire[0], start, end), side(wire[1], start, end)
    third, fourth = side(start, wire[0], wire[1]), side(end, wire[0], wire[1])
    if first * second < 0 and third * fourth < 0:
        return True
    # A wire lying along the line counts when the two overlap.
    if first == second == 0:
        lo_x, hi_x = sorted((x1, x2))
        lo_y, hi_y = sorted((y1, y2))
        s_lo_x, s_hi_x = sorted((start[0], end[0]))
        s_lo_y, s_hi_y = sorted((start[1], end[1]))
        return lo_x <= s_hi_x and s_lo_x <= hi_x and lo_y <= s_hi_y and s_lo_y <= hi_y
    return False


def fields_across_a_wire(tree: list) -> list[dict]:
    """Visible reference/value text with a wire drawn between it and its own part.

    The line joining the text box to the nearest point of its own unit's drawing (body,
    pin stubs or, for a unit drawn without a body, its pin column) must not meet a wire;
    otherwise a wire of another net separates the text from the part it names. Wiring
    joined to one of the part's own pins is its own net and does not count.
    """
    groups = wire_groups(_segments(tree))
    witnesses = []
    for reference, unit, boxes, _bodyless, fields, pins in _placed_parts(tree):
        if not boxes:
            continue
        foreign = [
            wire
            for group in groups
            if not any(_on(pin, segment) for pin in pins for segment in group)
            for wire in group
        ]
        for name, text, box in fields:
            nearest = min(boxes, key=lambda other: _gap(box, other))
            if _gap(box, nearest) == 0:
                continue
            start, end = _closest_points(box, nearest)
            crossing = [wire for wire in foreign if _crosses(start, end, wire)]
            if crossing:
                witnesses.append(
                    {
                        "reference": reference,
                        "unit": unit,
                        "field": name,
                        "text": text,
                        "own_part_gap_mm": round(_gap(box, nearest) / 1e6, 2),
                        "wires_between": [
                            [[x / 1e6 for x in point] for point in wire] for wire in crossing
                        ],
                    }
                )
    return witnesses


# A ground glyph may point sideways only where pointing down is impossible: into its own
# pin, or onto another drawn item for every value-text spot the compiler tries (owner
# request 2026-11-12). Supply arrows may point sideways (VPLUS on pin 8, owner decision).
def grounds_that_could_point_down(text: str) -> list[dict]:
    """Sideways ground glyphs with a clear spot to point down at the same connection."""
    from ai_kicad.sexpr import parse

    from .power_symbols import (
        _angle_for,
        _collisions,
        _pin_directions,
        _value_position,
        _value_sides,
    )

    tree = parse(text)
    outward = _pin_directions(tree)
    witnesses = []
    for item in power_symbols(tree):
        if item["lib_id"] != "power:GND":
            continue
        tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
        if _sign(tip[0]) == 0:
            continue
        pin = outward.get(item["point"])
        if pin and (0, 1) == (-pin[0], -pin[1]):
            continue
        angle = _angle_for(item["lib_id"], (0, 1))
        for side in _value_sides((0, 1), (0, 1)):
            value = _value_position(item["lib_id"], item["point"], angle, item["net"], side)
            if not _collisions(text, tree, dict(item, angle=angle, value=value)):
                witnesses.append(
                    {
                        "power_symbol": item["reference"],
                        "net": item["net"],
                        "points": "right" if tip[0] > 0 else "left",
                        "at_mm": [item["point"][0] / 1e6, item["point"][1] / 1e6],
                        "clear_downward_value_side": side,
                    }
                )
                break
    return witnesses
