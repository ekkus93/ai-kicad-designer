"""Brief-v4 readability measurements that ERC, netlist and field checks do not cover.

Each check targets a defect class the owner or an outside review found in drawings that
passed every brief-v3 check and the model review
(``review_qualification_v3_2026-11-12_qwen35_256k_run1``):

* rail wiring that detours far beyond the shortest route joining its terminals;
* power symbols drawn against convention (supply arrow down, ground glyph up).

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
