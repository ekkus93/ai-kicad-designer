"""Close parallel runs of different nets in a drawing (reviewer loop spec R7.4).

A schematic reads badly where a wire of one net runs alongside a wire, pin or power
glyph of another at a small gap: the eye cannot tell which line goes where. For every
pair of parallel conductors of different nets at a perpendicular gap of at most
`GAP_MM`, the length over which they run side by side is their exposure. Pins of one
symbol lying side by side are the library's doing and are not counted, and neither is
the first `PIN_EXIT_MM` of a wire leaving a pin, which neighbouring pins make
unavoidable. A net pair is `sustained` when one run alone is at least `SUSTAINED_MM`.
Report-only: it changes no check.
"""

from __future__ import annotations

from ai_kicad.m2_transform import transform_library_point

from .power_symbols import GLYPH_TIPS, power_symbols
from .readability_checks import _on, _segments, wire_groups
from .schematic_description import _instances

Point = tuple[int, int]
Segment = tuple[Point, Point]

GRID = 1_270_000
# Two grid steps (the closest pin spacing of common symbols) plus a coordinate tolerance.
GAP_MM = 2.54
GAP = 2_540_000 + 10_000
# A wire's first grid step from a pin end runs beside the neighbouring pins by necessity.
PIN_EXIT_MM = 1.27
PIN_EXIT = 1_270_000
# A single side-by-side run this long is sustained: what a reader notices.
SUSTAINED_MM = 2.54
SUSTAINED = 2_540_000


def _conductors(tree: list, terminal_inventory: list[dict]) -> list[dict]:
    """Wires, pin lines and power glyphs, each with its net and kind."""
    pins = {
        (round(t["x_mm"] * 1e6), round(t["y_mm"] * 1e6)): (t["net"], f"{t['reference']}.{t['pin']}")
        for t in terminal_inventory
    }
    symbols = power_symbols(tree)
    marks = {item["point"]: item["net"] for item in symbols}
    result = []
    for group in wire_groups(_segments(tree)):
        net = next(
            (
                found
                for segment in group
                for point, found in [
                    *((p, n) for p, (n, _name) in pins.items()),
                    *marks.items(),
                ]
                if _on(point, segment)
            ),
            None,
        )
        for segment in group:
            exits = [p for p in pins if p in segment]
            result.append({"kind": "wire", "net": net, "segment": segment, "exits": exits})
    for item in _instances(tree):
        body = item["body"]
        for pin in item["pins"]:
            point = pin["point"]
            if point not in pins:
                continue
            x, y = point
            edge = (
                (x, body[1])
                if y < body[1]
                else (x, body[3])
                if y > body[3]
                else (body[0], y)
                if x < body[0]
                else (body[2], y)
            )
            result.append(
                {
                    "kind": "pin",
                    "net": pins[point][0],
                    "segment": (point, edge),
                    "owner": item["reference"],
                    "name": pins[point][1],
                    "exits": [],
                }
            )
    for item in symbols:
        tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
        x, y = item["point"]
        result.append(
            {
                "kind": "glyph",
                "net": item["net"],
                "segment": ((x, y), (x + tip[0], y + tip[1])),
                "name": item["reference"],
                "exits": [],
            }
        )
    return result


def _runs(segment: Segment, axis: int) -> bool:
    """The segment runs along `axis` (0: x, 1: y) with a length."""
    other = 1 - axis
    return segment[0][other] == segment[1][other] and segment[0][axis] != segment[1][axis]


def _span(segment: Segment, axis: int) -> tuple[int, int]:
    return min(segment[0][axis], segment[1][axis]), max(segment[0][axis], segment[1][axis])


def _exempt(item: dict, axis: int) -> list[tuple[int, int]]:
    """The first PIN_EXIT of a wire from each pin end it starts at, along its run."""
    spans = []
    for point in item["exits"]:
        low, high = _span(item["segment"], axis)
        if point[axis] == low:
            spans.append((low, low + PIN_EXIT))
        elif point[axis] == high:
            spans.append((high - PIN_EXIT, high))
    return spans


def _length(low: int, high: int, holes: list[tuple[int, int]]) -> int:
    """Length of [low, high] outside the holes."""
    covered = 0
    edge = low
    for start, end in sorted(holes):
        start, end = max(start, edge), min(end, high)
        if end > start:
            covered += end - start
            edge = end
    return max(high - low - covered, 0)


def parallel_exposure(tree: list, terminal_inventory: list[dict]) -> list[dict]:
    """Every net pair with a close parallel run, with its exposed length and witnesses."""
    items = [i for i in _conductors(tree, terminal_inventory) if i["net"]]
    pairs: dict[tuple[str, str], dict] = {}
    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            if first["net"] == second["net"] or "wire" not in (first["kind"], second["kind"]):
                continue
            a, b = first["segment"], second["segment"]
            if _runs(a, 1) and _runs(b, 1):
                axis, gap = 1, abs(a[0][0] - b[0][0])
            elif _runs(a, 0) and _runs(b, 0):
                axis, gap = 0, abs(a[0][1] - b[0][1])
            else:
                continue
            if not 0 < gap <= GAP:
                continue
            (a_low, a_high), (b_low, b_high) = _span(a, axis), _span(b, axis)
            low, high = max(a_low, b_low), min(a_high, b_high)
            if high <= low:
                continue
            exposed = _length(low, high, _exempt(first, axis) + _exempt(second, axis))
            if not exposed:
                continue
            key = tuple(sorted((first["net"], second["net"])))
            row = pairs.setdefault(
                key, {"nets": list(key), "exposure_mm": 0.0, "sustained": False, "witnesses": []}
            )
            row["sustained"] = row["sustained"] or exposed >= SUSTAINED
            row["exposure_mm"] = round(row["exposure_mm"] + exposed / 1e6, 3)
            row["witnesses"].append(
                {
                    "kinds": [first["kind"], second["kind"]],
                    "parts": [n for n in (first.get("name"), second.get("name")) if n],
                    "gap_mm": round(gap / 1e6, 3),
                    "from_mm": [round(v / 1e6, 3) for v in (low, high)],
                    "along": "y" if axis == 1 else "x",
                    "at_mm": round((a[0][0] if axis == 1 else a[0][1]) / 1e6, 3),
                    "exposed_mm": round(exposed / 1e6, 3),
                }
            )
    return sorted(pairs.values(), key=lambda r: (-r["exposure_mm"], r["nets"]))
