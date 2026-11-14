"""R2 drawing-quality measures and their before/after comparison (reviewer loop spec R2).

The measures are reported, not used as gates: under brief v10 no edit is rolled back for
R2 alone. Hard failures (an actual text overlap, an owner-association failure, broken
connectivity) are still caught by the checks. The thresholds are starting hypotheses,
not validated standards (owner decision 2026-11-14, spec section 5).

Units: millimetres. KiCad page coordinates, y increasing downward.
"""

from __future__ import annotations

import math

from .power_symbols import power_symbol_collisions, power_symbols
from .readability_checks import (
    FRAME,
    _on,
    _rectilinear_spanning_length,
    _segments,
    content_extent,
    page_offset,
    wire_groups,
)
from .schematic_description import _instances

Point = tuple[int, int]
Segment = tuple[Point, Point]
Box = tuple[int, int, int, int]

# Spec R2 starting thresholds. Stored in the brief from v10 (P6-011k1).
DEFAULT_QUALITY_THRESHOLDS = {
    "wire_length_min_mm": 12.7,
    "wire_length_fraction": 0.05,
    "rail_detour_min_mm": 5.08,
    "rail_detour_fraction": 0.10,
    "bends_added": 2,
    "perimeter_min_length_mm": 50.8,
    "perimeter_envelope_distance_mm": 2.54,
    "perimeter_total_growth_mm": 25.4,
    "text_clearance_drop_mm": 0.635,
    "field_ownership_drop_mm": 1.27,
    "page_offset_growth": 0.03,
}


def _mm(value: float) -> float:
    return round(value / 1_000_000, 3)


def _length(segment: Segment) -> float:
    (x1, y1), (x2, y2) = segment
    return math.hypot(x2 - x1, y2 - y1)


def _direction(start: Point, end: Point) -> tuple[int, int]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    divisor = math.gcd(abs(dx), abs(dy)) or 1
    return dx // divisor, dy // divisor


def _straight_runs(segments: list[Segment]) -> list[Segment]:
    """Merge collinear, touching export segments into maximal straight runs."""
    runs = [tuple(sorted(segment)) for segment in segments if segment[0] != segment[1]]
    merged = True
    while merged:
        merged = False
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                a, b = runs[i], runs[j]
                if _direction(*a) != _direction(*b):
                    continue
                if not (_on(a[0], b) or _on(a[1], b) or _on(b[0], a) or _on(b[1], a)):
                    continue
                points = sorted([a[0], a[1], b[0], b[1]])
                runs[i] = (points[0], points[-1])
                del runs[j]
                merged = True
                break
            if merged:
                break
    return runs


def count_bends(segments: list[Segment]) -> int:
    """Corners: points where exactly two non-collinear wire directions meet.

    A straight continuation (two opposite directions), a T-junction (three) and a free end
    (one) are not bends; collinear export segments are merged first.
    """
    runs = _straight_runs(segments)
    ends = {point for run in runs for point in run}
    bends = 0
    for point in ends:
        directions = set()
        for start, end in runs:
            if point == start:
                directions.add(_direction(start, end))
            elif point == end:
                directions.add(_direction(end, start))
            elif _on(point, (start, end)):
                directions |= {_direction(point, end), _direction(point, start)}
        if len(directions) == 2:
            first, second = directions
            if first != (-second[0], -second[1]):
                bends += 1
    return bends


def symbol_core_box(tree: list) -> Box | None:
    """Component and connector bodies and pin anchors, without wires or text."""
    xs, ys = [], []
    for item in _instances(tree):
        left, top, right, bottom = item["body"]
        xs += [left, right]
        ys += [top, bottom]
        for pin in item["pins"]:
            xs.append(pin["point"][0])
            ys.append(pin["point"][1])
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def routing_envelope(tree: list) -> Box | None:
    """Wire and power-symbol connection geometry, without field text."""
    points = [point for segment in _segments(tree) for point in segment]
    points += [item["point"] for item in power_symbols(tree)]
    if not points:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def perimeter_paths(tree: list, thresholds: dict) -> list[dict]:
    """Long straight runs on the routing envelope's edge that lie outside the symbol core.

    A run qualifies when it is at least `perimeter_min_length_mm` long, lies within
    `perimeter_envelope_distance_mm` of one envelope edge, and sits beyond the symbol-core
    box on that side, so it skirts the parts instead of joining them. A long straight wire
    between two parts' pins stays inside the core and does not qualify.
    """
    envelope, core = routing_envelope(tree), symbol_core_box(tree)
    if envelope is None or core is None:
        return []
    minimum = thresholds["perimeter_min_length_mm"] * 1_000_000
    near = thresholds["perimeter_envelope_distance_mm"] * 1_000_000
    found = []
    for start, end in _straight_runs(_segments(tree)):
        length = _length((start, end))
        if length < minimum:
            continue
        side = None
        if start[1] == end[1]:
            y = start[1]
            if y - envelope[1] <= near and y < core[1]:
                side = "top"
            elif envelope[3] - y <= near and y > core[3]:
                side = "bottom"
        elif start[0] == end[0]:
            x = start[0]
            if x - envelope[0] <= near and x < core[0]:
                side = "left"
            elif envelope[2] - x <= near and x > core[2]:
                side = "right"
        if side:
            found.append(
                {
                    "side": side,
                    "length_mm": _mm(length),
                    "from_mm": [_mm(start[0]), _mm(start[1])],
                    "to_mm": [_mm(end[0]), _mm(end[1])],
                }
            )
    return sorted(found, key=lambda item: (item["from_mm"], item["to_mm"]))


def rail_detours(tree: list, terminal_inventory: list[dict], rails: list[str]) -> list[dict]:
    """Per single-rail wire group: drawn length over the shortest rectilinear tree."""
    terminals: dict[Point, str] = {
        (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6)): item["net"]
        for item in terminal_inventory
    }
    terminals.update({item["point"]: item["net"] for item in power_symbols(tree)})
    result = []
    for group in wire_groups(_segments(tree)):
        touched = {
            (point, net)
            for point, net in terminals.items()
            if any(_on(point, segment) for segment in group)
        }
        nets = {net for _point, net in touched}
        if len(nets) != 1 or next(iter(nets)) not in rails:
            continue
        length = sum(_length(segment) for segment in group)
        shortest = _rectilinear_spanning_length({point for point, _net in touched})
        result.append(
            {
                "net": next(iter(nets)),
                "wire_length_mm": _mm(length),
                "shortest_route_mm": _mm(shortest),
                "excess_mm": _mm(max(0.0, length - shortest)),
                "path_mm": sorted(
                    [[_mm(a[0]), _mm(a[1])], [_mm(b[0]), _mm(b[1])]] for a, b in group
                ),
            }
        )
    return sorted(result, key=lambda item: (item["net"], item["path_mm"]))


def power_symbol_flags(tree: list, text: str) -> dict:
    """Per-rail counts, and symbols that are orphaned, ambiguous, redundant or colliding."""
    symbols = power_symbols(tree)
    groups = wire_groups(_segments(tree))
    counts: dict[str, int] = {}
    orphaned, ambiguous, redundant = [], [], []
    on_group: dict[tuple[int, str], list[str]] = {}
    for item in symbols:
        counts[item["net"]] = counts.get(item["net"], 0) + 1
        joined = [
            index
            for index, group in enumerate(groups)
            if any(_on(item["point"], segment) for segment in group)
        ]
        if not joined:
            # A symbol placed straight on a pin has no wire; it is not orphaned.
            continue
        for index in joined:
            on_group.setdefault((index, item["net"]), []).append(item["reference"])
            other_nets = {
                other["net"]
                for other in symbols
                if any(_on(other["point"], segment) for segment in groups[index])
            } - {item["net"]}
            if other_nets:
                ambiguous.append(item["reference"])
    for (_index, _net), references in on_group.items():
        if len(references) > 1:
            redundant.extend(sorted(references))
    pin_points = {pin["point"] for instance in _instances(tree) for pin in instance["pins"]}
    for item in symbols:
        on_wire = any(_on(item["point"], segment) for group in groups for segment in group)
        if not on_wire and item["point"] not in pin_points:
            orphaned.append(item["reference"])
    colliding = sorted(item["power_symbol"] for item in power_symbol_collisions(text))
    return {
        "per_rail": dict(sorted(counts.items())),
        "orphaned": sorted(orphaned),
        "ambiguous": sorted(set(ambiguous)),
        "redundant": sorted(set(redundant)),
        "colliding": colliding,
    }


def measure_quality(tree: list, text: str, report: dict, thresholds: dict | None = None) -> dict:
    """Every R2 measure for one candidate, from its native schematic and assessment."""
    thresholds = thresholds or DEFAULT_QUALITY_THRESHOLDS
    segments = _segments(tree)
    rails = sorted(
        {item["net"] for item in report.get("intended_circuit", {}).get("power_assertions", [])}
    )
    detours = rail_detours(tree, report.get("terminal_inventory", []), rails)
    perimeter = perimeter_paths(tree, thresholds)
    margins = [
        -item["owner_advantage_mm"]
        for item in report.get("field_owner_association", {}).get("fields", [])
        if math.isfinite(item["owner_advantage_mm"])
    ]
    extent = content_extent(tree) if segments or _instances(tree) else None
    offset = page_offset(extent) if extent else None
    frame_area = (FRAME[2] - FRAME[0]) * (FRAME[3] - FRAME[1])
    core, envelope = symbol_core_box(tree), routing_envelope(tree)
    return {
        # Overlapping collinear wires are drawn once, so measure the merged runs.
        "wire_length_mm": _mm(sum(_length(run) for run in _straight_runs(segments))),
        "rail_detour_mm": round(sum(item["excess_mm"] for item in detours), 3),
        "rail_detours": detours,
        "bends": count_bends(segments),
        "perimeter_paths": perimeter,
        "perimeter_length_mm": round(sum(item["length_mm"] for item in perimeter), 3),
        "text_clearance_mm": report.get("layout", {}).get("observed_text_wire_clearance_mm"),
        "field_ownership_mm": round(min(margins), 3) if margins else None,
        "page_offset": round(max(abs(offset[0]), abs(offset[1])), 4) if offset else None,
        "occupied_area_fraction": (
            round((extent[2] - extent[0]) * (extent[3] - extent[1]) / frame_area, 4)
            if extent
            else None
        ),
        "power_symbols": power_symbol_flags(tree, text),
        "symbol_core_box_mm": [_mm(value) for value in core] if core else None,
        "routing_envelope_mm": [_mm(value) for value in envelope] if envelope else None,
    }


def _grew(before: float, after: float, minimum: float, fraction: float) -> bool:
    return after - before > max(minimum, fraction * before)


def compare_quality(before: dict, after: dict, thresholds: dict | None = None) -> dict:
    """Per-measure deltas and worse flags from `before` to `after` (spec R2 table)."""
    thresholds = thresholds or DEFAULT_QUALITY_THRESHOLDS
    worse: dict[str, dict] = {}
    deltas: dict[str, float | None] = {}

    def numeric(name: str) -> tuple[float, float] | None:
        first, second = before.get(name), after.get(name)
        if first is None or second is None:
            deltas[name] = None
            return None
        deltas[name] = round(second - first, 4)
        return first, second

    if pair := numeric("wire_length_mm"):
        if _grew(*pair, thresholds["wire_length_min_mm"], thresholds["wire_length_fraction"]):
            worse["wire_length_mm"] = {"before": pair[0], "after": pair[1]}
    if pair := numeric("rail_detour_mm"):
        if _grew(*pair, thresholds["rail_detour_min_mm"], thresholds["rail_detour_fraction"]):
            worse["rail_detour_mm"] = {"before": pair[0], "after": pair[1]}
    if pair := numeric("bends"):
        if pair[1] - pair[0] > thresholds["bends_added"]:
            worse["bends"] = {"before": pair[0], "after": pair[1]}
    if pair := numeric("perimeter_length_mm"):
        old = {(tuple(p["from_mm"]), tuple(p["to_mm"])) for p in before["perimeter_paths"]}
        new = [
            p
            for p in after["perimeter_paths"]
            if (tuple(p["from_mm"]), tuple(p["to_mm"])) not in old
        ]
        if new or pair[1] - pair[0] > thresholds["perimeter_total_growth_mm"]:
            worse["perimeter_paths"] = {"before": pair[0], "after": pair[1], "new": new}
    if pair := numeric("text_clearance_mm"):
        if pair[0] - pair[1] > thresholds["text_clearance_drop_mm"]:
            worse["text_clearance_mm"] = {"before": pair[0], "after": pair[1]}
    if pair := numeric("field_ownership_mm"):
        if pair[0] - pair[1] > thresholds["field_ownership_drop_mm"]:
            worse["field_ownership_mm"] = {"before": pair[0], "after": pair[1]}
    if pair := numeric("page_offset"):
        if pair[1] - pair[0] > thresholds["page_offset_growth"]:
            worse["page_offset"] = {"before": pair[0], "after": pair[1]}
    numeric("occupied_area_fraction")
    flags_before, flags_after = before.get("power_symbols", {}), after.get("power_symbols", {})
    for flag in ("orphaned", "ambiguous", "redundant", "colliding"):
        added = sorted(set(flags_after.get(flag, [])) - set(flags_before.get(flag, [])))
        if added:
            worse[f"power_symbols_{flag}"] = {"added": added}
    return {"deltas": deltas, "worse": worse, "not_worse": not worse}


def quality_overlay(primary_effect: str | None, comparison: dict | None) -> str | None:
    """LOCAL_FIX_ONLY for a fix that makes R2 worse; QUALITY_REGRESSION for a neutral one."""
    if not comparison or comparison["not_worse"] or primary_effect is None:
        return None
    return "QUALITY_REGRESSION" if primary_effect == "LAYOUT_CHANGE" else "LOCAL_FIX_ONLY"
