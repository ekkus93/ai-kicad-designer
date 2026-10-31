"""Present asserted power rails with locked KiCad global power symbols.

Brief v3 accepts a rail whose separated wire groups each carry a power symbol of that
rail, the way conventional schematics draw supplies and returns. The protected M2
observers know only the compiler's local-label form, so they inspect a label view in
which each power symbol is replaced by a same-named label at its connection point;
KiCad's ERC and netlist still run on the real schematic.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from pathlib import Path
from typing import Callable
import uuid

from ai_kicad.m2_geometry import label_text_rect, point_on_segment
from ai_kicad.m2_text_layout import text_extents
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.assets import _extract_symbol
from ai_kicad.m2a_constants import PITCH
from ai_kicad.m2a_core import _nm
from ai_kicad.m2b import pin_number_rectangles
from ai_kicad.sexpr import children, one, parse, quote

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "fixtures/pivot/power_symbols/manifest.json"
RETURN_NETS = frozenset({"REF", "GND", "AGND", "DGND", "VSS", "0"})
# Library glyph tip relative to the connection point, before rotation.
GLYPH_TIPS = {"power:VCC": (0, 2_540_000), "power:GND": (0, -2_540_000)}
DIRECTIONS = ((0, -1), (-1, 0), (1, 0), (0, 1))

Point = tuple[int, int]
Box = tuple[int, int, int, int]


def _forms(text: str) -> list[tuple[int, int, list]]:
    from .schematic_review_native import _top_level_forms

    return _top_level_forms(text)


def power_symbol_definitions() -> dict[str, str]:
    """Hash-verified library definitions keyed by lib_id, e.g. ``power:VCC``."""
    manifest = json.loads(MANIFEST.read_text())
    definitions = {}
    for lib_id, entry in manifest["symbols"].items():
        data = (ROOT / entry["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"locked power symbol {lib_id} does not match its manifest hash")
        text = data.decode()
        forms = [(start, end) for start, end, node in _forms(text) if node[0] == "symbol"]
        if len(forms) != 1:
            raise ValueError(f"locked power symbol {lib_id} must define exactly one symbol")
        start, end = forms[0]
        name = lib_id.split(":", 1)[1]
        definitions[lib_id] = text[start:end].replace(
            f"(symbol {quote(name)}", f"(symbol {quote(lib_id)}", 1
        )
    return definitions


def glyph_for_net(net: str) -> str:
    return "power:GND" if net.upper() in RETURN_NETS else "power:VCC"


def power_symbols(tree: list) -> list[dict]:
    """Every placed power symbol: reference, rail name, connection point and glyph."""
    result = []
    for symbol in children(tree, "symbol"):
        lib_id = one(symbol, "lib_id")[1]
        if lib_id not in GLYPH_TIPS:
            continue
        properties = {prop[1]: prop[2] for prop in children(symbol, "property")}
        at = one(symbol, "at")
        result.append(
            {
                "reference": properties["Reference"],
                "net": properties["Value"],
                "lib_id": lib_id,
                "point": (_nm(at[1]), _nm(at[2])),
                "angle": int(float(at[3])),
            }
        )
    return result


def label_view_text(text: str) -> str:
    """Replace each power symbol with a same-named local label at its connection point."""
    placed = {item["reference"]: item for item in power_symbols(parse(text))}
    rewritten = []
    for start, end, node in _forms(text):
        if node[0] == "lib_symbols":
            block = text[start:end]
            for inner_start, inner_end, inner in reversed(_forms(block)):
                if inner[0] == "symbol" and inner[1] in GLYPH_TIPS:
                    block = block[:inner_start] + block[inner_end:]
            rewritten.append((start, end, block))
        elif node[0] == "symbol" and one(node, "lib_id")[1] in GLYPH_TIPS:
            reference = next(p[2] for p in children(node, "property") if p[1] == "Reference")
            item = placed[reference]
            identity = uuid.uuid5(uuid.NAMESPACE_URL, "ai-kicad-label-view:" + reference)
            # The label text runs where the glyph and its value are drawn.
            tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
            text_angle = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[
                (_sign(tip[0]), _sign(tip[1]))
            ]
            rewritten.append(
                (
                    start,
                    end,
                    f"(label {quote(item['net'])} (at {_mm(item['point'])} {text_angle}) "
                    "(effects (font (size 1.27 1.27)) (justify left bottom)) "
                    f"(uuid {quote(str(identity))}))",
                )
            )
    for start, end, block in reversed(rewritten):
        text = text[:start] + block + text[end:]
    parse(text)
    return text


def _mm(point: Point) -> str:
    return f"{point[0] / 1_000_000:.6f} {point[1] / 1_000_000:.6f}"


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _glyph_boxes(lib_id: str, point: Point, angle: int, net: str) -> list[Box]:
    """Glyph and value-text boxes of one power symbol, starting just off its pin end."""
    tip_x, tip_y = transform_library_point(*GLYPH_TIPS[lib_id], angle)
    x, y = point
    direction = (_sign(tip_x), _sign(tip_y))
    start = (x + direction[0] * 500_000, y + direction[1] * 500_000)
    tip = (x + tip_x, y + tip_y)
    # The arrow or ground bar spans about 1.5 mm across the glyph axis.
    across_x = 1_020_000 if direction[1] else 250_000
    across_y = 1_020_000 if direction[0] else 250_000
    glyph = (
        min(start[0], tip[0]) - across_x,
        min(start[1], tip[1]) - across_y,
        max(start[0], tip[0]) + across_x,
        max(start[1], tip[1]) + across_y,
    )
    centre = _value_position(lib_id, point, angle, net)
    width, height = text_extents(net, 0)
    text = (
        centre[0] - width // 2 - 300_000,
        centre[1] - height // 2 - 300_000,
        centre[0] + width // 2 + 300_000,
        centre[1] + height // 2 + 300_000,
    )
    return [glyph, text]


def _value_position(lib_id: str, point: Point, angle: int, net: str) -> Point:
    """Horizontal value text centred just beyond the glyph tip, away from the pin."""
    tip_x, tip_y = transform_library_point(*GLYPH_TIPS[lib_id], angle)
    width, height = text_extents(net, 0)
    if tip_x:
        offset = abs(tip_x) + width // 2 + 600_000
        return (point[0] + _sign(tip_x) * offset, point[1])
    offset = abs(tip_y) + height // 2 + 500_000
    return (point[0], point[1] + _sign(tip_y) * offset)


def _angle_for(lib_id: str, direction: tuple[int, int]) -> int:
    for angle in (0, 90, 180, 270):
        tip = transform_library_point(*GLYPH_TIPS[lib_id], angle)
        if (_sign(tip[0]), _sign(tip[1])) == direction:
            return angle
    raise ValueError(f"no rotation points {lib_id} along {direction}")


def _overlaps(first: Box, second: Box) -> bool:
    return (
        first[0] < second[2]
        and second[0] < first[2]
        and first[1] < second[3]
        and second[1] < first[3]
    )


def _wire_segments(tree: list) -> list[tuple[Point, Point]]:
    return [
        ((_nm(first[1]), _nm(first[2])), (_nm(second[1]), _nm(second[2])))
        for wire in children(tree, "wire")
        for first, second in zip(
            children(one(wire, "pts"), "xy"), children(one(wire, "pts"), "xy")[1:]
        )
    ]


def _pin_number_boxes(text: str, tree: list) -> list[tuple[str, Box]]:
    """Visible pin-number boxes, measured as the independent layout observer does."""
    boxes = []
    for symbol in children(tree, "symbol"):
        lib_id = one(symbol, "lib_id")[1]
        if lib_id in GLYPH_TIPS:
            continue
        at = one(symbol, "at")
        mirrors = children(symbol, "mirror")
        reference = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        for bounds in pin_number_rectangles(
            _extract_symbol(text, lib_id),
            int(one(symbol, "unit")[1]),
            _nm(at[1]),
            _nm(at[2]),
            int(float(at[3])),
            mirrors[0][1] if mirrors else None,
        ):
            boxes.append((f"{reference} pin number", tuple(bounds)))
    return boxes


def _collisions(text: str, tree: list, item: dict) -> list[str]:
    """Drawn items and foreign wires touched by one power symbol's glyph or value."""
    from .schematic_review_native import _drawn_boxes, _release_endpoints

    symbol_boxes, text_boxes = _drawn_boxes(tree)
    boxes = _glyph_boxes(item["lib_id"], item["point"], item["angle"], item["net"])
    numbers = _pin_number_boxes(text, tree)
    hits = []
    # The protected observers see this symbol as a label whose text runs right of it.
    label_form = label_text_rect(item["net"], item["point"])
    hits += [
        f"label form overlaps {owner}" for owner, bounds in numbers if _overlaps(label_form, bounds)
    ]
    for owner, bounds in symbol_boxes + text_boxes + numbers:
        if owner == item.get("reference"):
            continue
        released = _release_endpoints(bounds, (item["point"],))
        if released is not None and any(_overlaps(box, released) for box in boxes):
            hits.append(owner)
    tip = transform_library_point(*GLYPH_TIPS[item["lib_id"]], item["angle"])
    glyph_direction = (_sign(tip[0]), _sign(tip[1]))
    for first, second in _wire_segments(tree):
        if point_on_segment(item["point"], first, second):
            # A wire may leave the symbol's connection point, but not along the glyph.
            ends = [end for end in (first, second) if end != item["point"]]
            leaving = {
                (_sign(end[0] - item["point"][0]), _sign(end[1] - item["point"][1])) for end in ends
            }
            if glyph_direction in leaving:
                hits.append(f"wire {_mm(first)} -> {_mm(second)}")
            continue
        bounds = (
            min(first[0], second[0]) - 100_000,
            min(first[1], second[1]) - 100_000,
            max(first[0], second[0]) + 100_000,
            max(first[1], second[1]) + 100_000,
        )
        if any(_overlaps(box, bounds) for box in boxes):
            hits.append(f"wire {_mm(first)} -> {_mm(second)}")
    return hits


def power_symbol_collisions(text: str) -> list[dict]:
    """Power symbols whose glyph or value touches another drawn item or a foreign wire."""
    tree = parse(text)
    return [
        {"power_symbol": item["reference"], "net": item["net"], "touches": hits}
        for item in power_symbols(tree)
        if (hits := _collisions(text, tree, item))
    ]


def _terminal_points(terminal_inventory: list[dict], net: str) -> list[Point]:
    return list(
        dict.fromkeys(
            (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000))
            for item in terminal_inventory
            if item["net"] == net
        )
    )


def _marked(marker: Point, members: set[Point], segments: list[tuple[Point, Point]]) -> bool:
    return marker in members or any(point_on_segment(marker, *segment) for segment in segments)


def rail_presentation(tree: list, terminal_inventory: list[dict], nets: list[str]) -> list[dict]:
    """Rail wire groups that are neither joined to the rail nor marked by its power symbol."""
    from .schematic_review_native import _point_group_wiring

    placed = power_symbols(tree)
    witnesses = []
    for net in nets:
        points = _terminal_points(terminal_inventory, net)
        wiring = _point_group_wiring(tree, points)
        if len(wiring) <= 1:
            continue
        markers = [item["point"] for item in placed if item["net"] == net]
        for indexes, segments in wiring:
            members = {points[index] for index in indexes}
            if any(_marked(marker, members, segments) for marker in markers):
                continue
            witnesses.append(
                {
                    "net": net,
                    "terminals": sorted(
                        f"{item['reference']}.{item['pin']}"
                        for item in terminal_inventory
                        if item["net"] == net
                        and (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6)) in members
                    ),
                    "reason": "wire group is neither joined to the rest of its rail nor "
                    f"marked by a {net} power symbol",
                }
            )
    return witnesses


def _pin_directions(tree: list) -> dict[Point, tuple[int, int]]:
    """Outward direction (away from the body) at every placed symbol pin end."""
    library = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    directions = {}
    for symbol in children(tree, "symbol"):
        definition = library.get(one(symbol, "lib_id")[1])
        if definition is None:
            continue
        at = one(symbol, "at")
        origin, angle = (_nm(at[1]), _nm(at[2])), int(float(at[3]))
        mirrors = children(symbol, "mirror")
        mirror = mirrors[0][1] if mirrors else None
        unit = str(one(symbol, "unit")[1])
        for body in children(definition, "symbol"):
            if body[1].rsplit("_", 2)[-2] not in {"0", unit}:
                continue
            for pin in children(body, "pin"):
                pin_at, length = one(pin, "at"), _nm(one(pin, "length")[1])
                step = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}.get(
                    int(float(pin_at[3])) % 360
                )
                if step is None or length <= 0:
                    continue
                end = transform_library_point(_nm(pin_at[1]), _nm(pin_at[2]), angle, mirror)
                inner = transform_library_point(
                    _nm(pin_at[1]) + step[0] * length,
                    _nm(pin_at[2]) + step[1] * length,
                    angle,
                    mirror,
                )
                directions[(origin[0] + end[0], origin[1] + end[1])] = (
                    _sign(end[0] - inner[0]),
                    _sign(end[1] - inner[1]),
                )
    return directions


def _instance(
    lib_id: str, reference: str, net: str, point: Point, angle: int, project: tuple[str, str]
) -> str:
    identity = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-kicad-power:{reference}:{net}:{_mm(point)}")
    pin = uuid.uuid5(identity, "pin-1")
    value = _value_position(lib_id, point, angle, net)
    # KiCad field angles are 0 (horizontal) or 90 relative to the symbol; 180/270 would
    # draw the rail name upside down.
    field_angle = angle % 180
    return (
        f"(symbol (lib_id {quote(lib_id)}) (at {_mm(point)} {angle}) (unit 1) "
        f"(in_bom yes) (on_board yes) (dnp no) (uuid {quote(str(identity))})\n"
        f'    (property "Reference" {quote(reference)} (at {_mm(point)} {field_angle}) (hide yes) '
        "(effects (font (size 1.27 1.27))))\n"
        f'    (property "Value" {quote(net)} (at {_mm(value)} {field_angle}) '
        "(effects (font (size 1.27 1.27))))\n"
        f'    (pin "1" (uuid {quote(str(pin))}))\n'
        f"    (instances (project {quote(project[0])} (path {quote(project[1])} "
        f"(reference {quote(reference)}) (unit 1)))) )"
    )


def _flag_paths(
    segments: list[tuple[Point, Point]], flag: Point, terminals: set[Point]
) -> list[tuple[Point, Point]]:
    """Shortest wire path from a power flag to the nearest rail terminal in its tree."""
    stops = {point for segment in segments for point in segment} | terminals | {flag}
    graph: dict[Point, list[tuple[Point, int]]] = {}
    for first, second in segments:
        on = sorted(
            (point for point in stops if point_on_segment(point, first, second)),
            key=lambda point: (point[0], point[1]),
        )
        for a, b in zip(on, on[1:]):
            length = abs(a[0] - b[0]) + abs(a[1] - b[1])
            graph.setdefault(a, []).append((b, length))
            graph.setdefault(b, []).append((a, length))
    distances, previous, queue = {flag: 0}, {}, [(0, flag)]
    while queue:
        distance, point = heapq.heappop(queue)
        if distance != distances[point]:
            continue
        for neighbour, length in graph.get(point, []):
            if distance + length < distances.get(neighbour, float("inf")):
                distances[neighbour] = distance + length
                previous[neighbour] = point
                heapq.heappush(queue, (distance + length, neighbour))
    reached = [point for point in terminals if point in distances and point != flag]
    if not reached:
        return []
    point = min(reached, key=lambda item: (distances[item], item))
    path = []
    while point != flag:
        path.append((previous[point], point))
        point = previous[point]
    return path


def _rail_runs(
    segments: list[tuple[Point, Point]],
    roots: list[int],
    terminals: list[Point],
    flag_points: list[Point],
    local_pairs: list[tuple[Point, Point]],
) -> tuple[set[int], list[tuple[Point, Point]]]:
    """Wire trees joining two or more rail terminals, and the paths within them to keep.

    A single pin's stub to its label is not a run. Kept are the shortest existing paths
    from each power flag to its nearest terminal and between declared local pairs.
    """
    rail_roots = {
        root
        for root in set(roots)
        if sum(
            any(
                point_on_segment(point, *segment)
                for segment, other in zip(segments, roots)
                if other == root
            )
            for point in terminals
        )
        >= 2
    }
    kept: list[tuple[Point, Point]] = []
    for root in rail_roots:
        tree_segments = [segment for segment, other in zip(segments, roots) if other == root]
        for flag in flag_points:
            if any(point_on_segment(flag, *segment) for segment in tree_segments):
                kept.extend(_flag_paths(tree_segments, flag, set(terminals)))
        for first, second in local_pairs:
            if all(
                any(point_on_segment(point, *segment) for segment in tree_segments)
                for point in (first, second)
            ):
                kept.extend(_flag_paths(tree_segments, first, {second}))
    return rail_roots, sorted({tuple(sorted(edge)) for edge in kept})


def remove_rail_runs_text(
    text: str,
    net: str,
    terminal_inventory: list[dict],
    flag_points: list[Point],
    local_pairs: list[tuple[Point, Point]] = (),
) -> str:
    """Remove one rail's terminal-to-terminal wiring so it can be rerouted.

    Power-flag paths and declared local pairs (such as decoupling) stay wired, and
    labels are untouched, so connectivity is unchanged.
    """
    from .schematic_review_native import _wire_trees

    tree = parse(text)
    terminals = _terminal_points(terminal_inventory, net)
    segments, owners, roots = _wire_trees(tree)
    rail_roots, kept = _rail_runs(segments, roots, terminals, flag_points, local_pairs)
    if not rail_roots:
        return text
    removed = {owner for owner, root in zip(owners, roots) if root in rail_roots}
    run_points = {
        point for segment, root in zip(segments, roots) if root in rail_roots for point in segment
    }
    position = -1

    def drop(node: list) -> bool:
        nonlocal position
        if node[0] == "wire":
            position += 1
            return position in removed
        return (
            node[0] == "junction"
            and (_nm(one(node, "at")[1]), _nm(one(node, "at")[2])) in run_points
        )

    text = "".join(_without_forms(text, drop))
    degree: dict[Point, int] = {}
    for edge in kept:
        for point in edge:
            degree[point] = degree.get(point, 0) + 1
    junctions = [
        f"(junction (at {_mm(point)}) (diameter 0) (color 0 0 0 0) "
        f"(uuid {quote(str(uuid.uuid5(uuid.NAMESPACE_URL, f'ai-kicad-kept-junction:{net}:{_mm(point)}')))}))"
        for point, count in sorted(degree.items())
        if count >= 3
    ]
    return _append_forms(text, junctions + [_wire_form(a, b, net) for a, b in kept])


def use_power_symbols_text(
    text: str,
    net: str,
    terminal_inventory: list[dict],
    flag_points: list[Point],
    local_pairs: list[tuple[Point, Point]] = (),
    layout_check: Callable[[str], str | None] | None = None,
    prune_rail_wiring: bool = True,
) -> str:
    """Present one rail conventionally: a power symbol at each terminal, no rail wiring.

    The rail's labels and the wires joining its terminals are removed. Kept are the
    shortest existing wire from each power flag to its nearest rail terminal, and between
    each pair of terminals the design wires locally (such as a decoupling capacitor and
    the supply pin it serves). Each resulting wire
    group then receives one power symbol, placed where it touches no other drawing item
    when such a position exists (otherwise the clearance check reports the conflict).
    ``layout_check`` returns the independent observer's objection to a candidate sheet,
    if any; a group keeps its labels until its own symbol replaces them, so every
    intermediate sheet is a valid label-form drawing for that observer.
    """
    from .schematic_review_native import _wire_trees

    tree = parse(text)
    lib_id = glyph_for_net(net)
    terminals = _terminal_points(terminal_inventory, net)
    if not terminals:
        raise ValueError(f"use_power_symbols found no observed terminals on {net}")
    label_points = {
        (_nm(one(label, "at")[1]), _nm(one(label, "at")[2]))
        for label in children(tree, "label")
        if label[1] == net
    }
    segments, owners, roots = _wire_trees(tree)
    rail_roots, kept = (
        _rail_runs(segments, roots, terminals, flag_points, local_pairs)
        if prune_rail_wiring
        else (set(), [])
    )
    removed_wires = {owner for owner, root in zip(owners, roots) if root in rail_roots}
    rail_segment_points = {
        point for segment, root in zip(segments, roots) if root in rail_roots for point in segment
    }
    instances = [
        node for symbol in children(tree, "symbol") for node in children(symbol, "instances")
    ]
    if not instances:
        raise ValueError("use_power_symbols requires a native KiCad sheet with symbol instances")
    project_node = one(instances[0], "project")
    project = (project_node[1], one(project_node, "path")[1])
    existing = [item for item in power_symbols(tree) if item["net"] == net]
    if existing:
        # Repeating the edit re-places this rail's symbols that touch other drawing items.
        colliding = {item["reference"] for item in existing if _collisions(text, tree, item)}
        if not colliding:
            raise ValueError(
                f"use_power_symbols made no change; {net} already uses power symbols and "
                "none of them touches another drawing item"
            )
        text = "".join(
            _without_forms(
                text,
                lambda node: node[0] == "symbol"
                and any(
                    prop[1] == "Reference" and prop[2] in colliding
                    for prop in children(node, "property")
                ),
            )
        )
        text = _prune_dangling(text)
        return _place_rail_symbols(
            text,
            net,
            lib_id,
            terminals,
            flag_points,
            set(),
            layout_check,
            project,
            terminal_inventory,
        )
    if not removed_wires and not label_points:
        raise ValueError(f"use_power_symbols made no change; {net} has no rail wiring or labels")

    remaining = [
        segment for segment, root in zip(segments, roots) if root not in rail_roots
    ] + list(kept)

    def anchored(point: Point) -> bool:
        return point in terminals or any(point_on_segment(point, *item) for item in remaining)

    wire_index = -1
    pieces, cursor = [], 0
    for start, end, node in _forms(text):
        drop = False
        if node[0] == "wire":
            wire_index += 1
            drop = wire_index in removed_wires
        elif node[0] == "label":
            # Labels left on removed rail runs go now; the rest go with their group.
            drop = node[1] == net and not anchored(
                (_nm(one(node, "at")[1]), _nm(one(node, "at")[2]))
            )
        elif node[0] == "junction":
            drop = (_nm(one(node, "at")[1]), _nm(one(node, "at")[2])) in rail_segment_points
        if drop:
            pieces.append(text[cursor:start].rstrip(" "))
            cursor = end
    pieces.append(text[cursor:])
    text = "".join(pieces)
    degree: dict[Point, int] = {}
    for edge in kept:
        for point in edge:
            degree[point] = degree.get(point, 0) + 1
    junctions = [
        f"(junction (at {_mm(point)}) (diameter 0) (color 0 0 0 0) "
        f"(uuid {quote(str(uuid.uuid5(uuid.NAMESPACE_URL, f'ai-kicad-kept-junction:{net}:{_mm(point)}')))}))"
        for point, count in sorted(degree.items())
        if count >= 3
    ]
    additions = junctions + [
        f"(wire (pts (xy {_mm(first)}) (xy {_mm(second)})) (stroke (width 0) (type default)) "
        f"(uuid {quote(str(uuid.uuid5(uuid.NAMESPACE_URL, f'ai-kicad-flag-path:{net}:{_mm(first)}:{_mm(second)}')))}))"
        for first, second in kept
    ]
    if lib_id not in {node[1] for node in children(one(parse(text), "lib_symbols"), "symbol")}:
        _start, end, _node = next(item for item in _forms(text) if item[2][0] == "lib_symbols")
        text = text[: end - 1] + power_symbol_definitions()[lib_id] + "\n  " + text[end - 1 :]
    text = _append_forms(text, additions)

    return _place_rail_symbols(
        text,
        net,
        lib_id,
        terminals,
        flag_points,
        label_points,
        layout_check,
        project,
        terminal_inventory,
    )


def _pin_points(tree: list) -> set[Point]:
    """Connection points of every placed symbol pin, including zero-length power pins."""
    library = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    points = set()
    for symbol in children(tree, "symbol"):
        definition = library.get(one(symbol, "lib_id")[1])
        if definition is None:
            continue
        at = one(symbol, "at")
        mirrors = children(symbol, "mirror")
        unit = str(one(symbol, "unit")[1])
        for body in children(definition, "symbol"):
            if body[1].rsplit("_", 2)[-2] not in {"0", unit}:
                continue
            for pin in children(body, "pin"):
                pin_at = one(pin, "at")
                dx, dy = transform_library_point(
                    _nm(pin_at[1]),
                    _nm(pin_at[2]),
                    int(float(at[3])),
                    mirrors[0][1] if mirrors else None,
                )
                points.add((_nm(at[1]) + dx, _nm(at[2]) + dy))
    return points


def _prune_dangling(text: str) -> str:
    """Remove wires left with an end that touches no other wire, pin or label."""
    while True:
        tree = parse(text)
        anchors = _pin_points(tree) | {
            (_nm(one(label, "at")[1]), _nm(one(label, "at")[2]))
            for label in children(tree, "label")
        }
        wires = [
            tuple((_nm(xy[1]), _nm(xy[2])) for xy in children(one(wire, "pts"), "xy"))
            for wire in children(tree, "wire")
        ]
        dangling = {
            index
            for index, ends in enumerate(wires)
            if any(
                end not in anchors
                and not any(
                    point_on_segment(end, *other)
                    for other_index, other in enumerate(wires)
                    if other_index != index
                )
                for end in ends
            )
        }
        if not dangling:
            return text
        position = -1

        def drop(node: list) -> bool:
            nonlocal position
            if node[0] != "wire":
                return False
            position += 1
            return position in dangling

        text = "".join(_without_forms(text, drop))


def _place_rail_symbols(
    text: str,
    net: str,
    lib_id: str,
    terminals: list[Point],
    flag_points: list[Point],
    label_points: set[Point],
    layout_check: Callable[[str], str | None] | None,
    project: tuple[str, str],
    terminal_inventory: list[dict] = (),
) -> str:
    """Give every unmarked wire group of one rail a clear power symbol.

    A group with no clear position is refused with the nets whose wiring blocks it,
    rather than drawn overlapping another item.
    """
    tree = parse(text)
    points = list(dict.fromkeys(terminals + list(flag_points)))
    # Drafting convention: ground glyphs point up, and supply glyphs down, only as a
    # last resort.
    forbidden = (0, -1) if lib_id == "power:GND" else (0, 1)
    used = {item["reference"] for item in power_symbols(tree)}
    serial = 1
    for indexes, group_segments in _point_group_wiring_of(tree, points):
        members = [points[index] for index in indexes]
        group_points = set(members) | {p for segment in group_segments for p in segment}
        markers = [item["point"] for item in power_symbols(parse(text)) if item["net"] == net]
        if any(_marked(marker, set(members), group_segments) for marker in markers):
            continue
        text = "".join(
            _without_forms(
                text,
                lambda node: node[0] == "label"
                and node[1] == net
                and any(
                    (_nm(one(node, "at")[1]), _nm(one(node, "at")[2])) == point
                    or any(
                        point_on_segment((_nm(one(node, "at")[1]), _nm(one(node, "at")[2])), *seg)
                        for seg in group_segments
                    )
                    for point in group_points
                ),
            )
        )
        tree = parse(text)
        baseline_ok = layout_check is None or layout_check(text) is None
        while f"#PWR{serial:02d}" in used:
            serial += 1
        reference = f"#PWR{serial:02d}"
        used.add(reference)
        pin_directions = _pin_directions(tree)
        candidates = sorted(set(members) | {p for s in group_segments for p in s})
        # The compiler's own label points are known-clear for the label-form observers.
        candidates.sort(
            key=lambda point: (point not in label_points, point not in pin_directions, point)
        )
        options = []
        for order, point in enumerate(candidates):
            outward = pin_directions.get(point)
            inward = (-outward[0], -outward[1]) if outward else None
            # A stub leaves the point outward from its pin first, sideways second.
            stub_ways = [way for way in ([outward] if outward else []) + list(DIRECTIONS)]
            stub_ways = [way for way in dict.fromkeys(stub_ways) if way != inward]
            ordered = ([outward] if outward else []) + [d for d in DIRECTIONS if d != outward]
            options.extend(
                (direction == forbidden, 0, order, 0, 0, point, None, direction)
                for direction in ordered
                if direction != inward
            )
            for rank, way in enumerate(stub_ways):
                for steps in (1, 2, 3, 4):
                    options.extend(
                        (
                            direction == forbidden,
                            1 + (way != outward),
                            order,
                            rank,
                            steps,
                            point,
                            way,
                            direction,
                        )
                        for direction in DIRECTIONS
                        if direction != (-way[0], -way[1])
                    )
        if not options:
            raise ValueError(f"use_power_symbols found no placement for a {net} wire group")
        options.sort()
        chosen, trials = None, {}
        for *_rank, steps, point, way, direction in options:
            stub = None
            if steps:
                end = (point[0] + way[0] * steps * PITCH, point[1] + way[1] * steps * PITCH)
                stub = (point, end)
                if stub not in trials:
                    clear = not _segment_collisions(text, tree, point, end)
                    trial = _append_forms(text, [_wire_form(point, end, net)]) if clear else None
                    trials[stub] = (trial, parse(trial) if trial else None)
                trial_text, trial_tree = trials[stub]
                if trial_text is None:
                    continue
                point = end
            else:
                trial_text, trial_tree = text, tree
            item = {
                "lib_id": lib_id,
                "point": point,
                "angle": _angle_for(lib_id, direction),
                "net": net,
                "reference": reference,
            }
            if _collisions(trial_text, trial_tree, item):
                continue
            if layout_check is not None and baseline_ok:
                instance = _instance(lib_id, reference, net, point, item["angle"], project)
                if layout_check(_append_forms(trial_text, [instance])) is not None:
                    continue
            chosen = (point, direction, stub)
            break
        if chosen is None:
            blockers = _blocking_nets(tree, members, terminal_inventory, net)
            names = sorted(
                f"{item['reference']}.{item['pin']}"
                for item in terminal_inventory
                if item["net"] == net
                and (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6)) in set(members)
            )
            advice = (
                f"; if {', '.join(blockers)} is an asserted rail, request use_power_symbols "
                "for it first so its wiring is replaced by power symbols, then repeat this edit"
                if blockers
                else "; move a nearby symbol with move_symbols, then repeat this edit"
            )
            raise ValueError(
                f"no clear position for a {net} power symbol at {names or 'its flag'}; "
                f"wiring of {blockers or 'no other net'} and nearby drawing items block it" + advice
            )
        point, direction, stub = chosen
        forms = [_wire_form(*stub, net)] if stub else []
        forms.append(
            _instance(lib_id, reference, net, point, _angle_for(lib_id, direction), project)
        )
        text = _append_forms(text, forms)
    text = "".join(_without_forms(text, lambda node: node[0] == "label" and node[1] == net))
    text = _prune_dangling(text)
    text = _reaim_colliding(text, project, layout_check)
    parse(text)
    return text


def _blocking_nets(
    tree: list, members: list[Point], terminal_inventory: list[dict], net: str
) -> list[str]:
    """Other nets with wiring within reach of a power symbol at any of these points."""
    from .schematic_review_native import _wire_trees

    reach = 2 * GLYPH_TIPS["power:VCC"][1]
    segments, _owners, roots = _wire_trees(tree)
    net_of_root = {}
    for item in terminal_inventory:
        point = (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6))
        for segment, root in zip(segments, roots):
            if point_on_segment(point, *segment):
                net_of_root.setdefault(root, item["net"])
    blockers = set()
    for (first, second), root in zip(segments, roots):
        other = net_of_root.get(root)
        if other is None or other == net:
            continue
        bounds = (
            min(first[0], second[0]),
            min(first[1], second[1]),
            max(first[0], second[0]),
            max(first[1], second[1]),
        )
        if any(_overlaps((x - reach, y - reach, x + reach, y + reach), bounds) for x, y in members):
            blockers.add(other)
    return sorted(blockers)


def _reaim_colliding(
    text: str,
    project: tuple[str, str],
    layout_check: Callable[[str], str | None] | None = None,
) -> str:
    """Turn any colliding power symbol, of any rail, to a clear direction at its own point."""
    for _round in range(4):
        tree = parse(text)
        changed = False
        for item in power_symbols(tree):
            if not _collisions(text, tree, item):
                continue
            forbidden = (0, -1) if item["lib_id"] == "power:GND" else (0, 1)
            outward = _pin_directions(tree).get(item["point"])
            for direction in sorted(DIRECTIONS, key=lambda direction: direction == forbidden):
                if outward and direction == (-outward[0], -outward[1]):
                    continue
                trial = dict(item, angle=_angle_for(item["lib_id"], direction))
                if trial["angle"] == item["angle"] or _collisions(text, tree, trial):
                    continue
                candidate = "".join(
                    _without_forms(
                        text,
                        lambda node, reference=item["reference"]: node[0] == "symbol"
                        and any(
                            prop[1] == "Reference" and prop[2] == reference
                            for prop in children(node, "property")
                        ),
                    )
                )
                candidate = _append_forms(
                    candidate,
                    [
                        _instance(
                            item["lib_id"],
                            item["reference"],
                            item["net"],
                            item["point"],
                            trial["angle"],
                            project,
                        )
                    ],
                )
                if layout_check is not None and layout_check(candidate) is not None:
                    continue
                text = candidate
                changed = True
                break
            if changed:
                break
        if not changed:
            return text
    return text


def _wire_form(first: Point, second: Point, net: str) -> str:
    identity = uuid.uuid5(
        uuid.NAMESPACE_URL, f"ai-kicad-power-wire:{net}:{_mm(first)}:{_mm(second)}"
    )
    return (
        f"(wire (pts (xy {_mm(first)}) (xy {_mm(second)})) (stroke (width 0) (type default)) "
        f"(uuid {quote(str(identity))}))"
    )


def _segment_collisions(text: str, tree: list, start: Point, end: Point) -> list[str]:
    """Items a new stub from a pin end would touch, other than the pin it leaves."""
    from .schematic_review_native import _drawn_boxes, _release_endpoints

    symbol_boxes, text_boxes = _drawn_boxes(tree)
    bounds = (
        min(start[0], end[0]) - 100_000,
        min(start[1], end[1]) - 100_000,
        max(start[0], end[0]) + 100_000,
        max(start[1], end[1]) + 100_000,
    )
    hits = [
        owner
        for owner, box in symbol_boxes + text_boxes + _pin_number_boxes(text, tree)
        if (released := _release_endpoints(box, (start,))) is not None
        and _overlaps(bounds, released)
    ]
    for first, second in _wire_segments(tree):
        contact = _contact(start, end, first, second)
        if contact is not None and contact != {start}:
            hits.append(f"wire {_mm(first)} -> {_mm(second)}")
        elif contact is None:
            wire = (
                min(first[0], second[0]) - 100_000,
                min(first[1], second[1]) - 100_000,
                max(first[0], second[0]) + 100_000,
                max(first[1], second[1]) + 100_000,
            )
            if _overlaps(bounds, wire):
                hits.append(f"wire {_mm(first)} -> {_mm(second)}")
    return hits


def _contact(start: Point, end: Point, first: Point, second: Point) -> set[Point] | None:
    """Shared points of two axis-aligned segments (endpoints if collinear), or None."""
    horizontal = start[1] == end[1]
    other_horizontal = first[1] == second[1]
    if horizontal != other_horizontal:
        vertical_x = first[0] if horizontal else start[0]
        horizontal_y = start[1] if horizontal else first[1]
        point = (vertical_x, horizontal_y)
        if point_on_segment(point, start, end) and point_on_segment(point, first, second):
            return {point}
        return None
    axis = 0 if horizontal else 1
    if start[1 - axis] != first[1 - axis]:
        return None
    low = max(min(start[axis], end[axis]), min(first[axis], second[axis]))
    high = min(max(start[axis], end[axis]), max(first[axis], second[axis]))
    if low > high:
        return None
    points = set()
    for value in (low, high):
        point = [0, 0]
        point[axis], point[1 - axis] = value, start[1 - axis]
        points.add(tuple(point))
    return points


def _without_forms(text: str, drop) -> list[str]:
    pieces, cursor = [], 0
    for start, end, node in _forms(text):
        if drop(node):
            pieces.append(text[cursor:start].rstrip(" "))
            cursor = end
    pieces.append(text[cursor:])
    return pieces


def _point_group_wiring_of(tree: list, points: list[Point]):
    from .schematic_review_native import _point_group_wiring

    return _point_group_wiring(tree, points)


def _append_forms(text: str, forms: list[str]) -> str:
    """Insert native forms after the last drawn item of the sheet."""
    if not forms:
        return text
    _start, end, _node = next(
        item
        for item in reversed(_forms(text))
        if item[2][0] in {"symbol", "wire", "label", "junction"}
    )
    return text[:end] + "".join("\n  " + form for form in forms) + text[end:]
