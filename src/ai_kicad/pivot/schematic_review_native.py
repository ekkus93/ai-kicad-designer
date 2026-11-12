"""Native KiCad adapter for image review of a pinned M2b circuit."""

from __future__ import annotations

import json
import heapq
import itertools
from itertools import count
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4

from ai_kicad.ir import InputError
from ai_kicad.kicad import ToolFailure, run_headless
from ai_kicad.m2_text_layout import overlaps, property_page_angle, text_extents
from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a_artifacts import emit, observe, verify_serialized_scene
from ai_kicad.m2b import assets, check_observed_layout, compare, validate
from ai_kicad.m2_geometry import (
    Reservation,
    label_text_width,
    point_on_segment,
)
from ai_kicad.m2_fragments_types import Point
from ai_kicad.m2_route_core import _connect
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.m2a_core import _nm
from ai_kicad.m2a_constants import PITCH
from ai_kicad.sexpr import children, one, parse, quote

from .schematic_review import (
    MoveField,
    AddWirePath,
    ConnectRail,
    MoveSymbols,
    RegenerateSchematic,
    SchematicAction,
    SchematicAssessment,
    TranslateSheet,
    UsePowerSymbols,
    WirePoint,
    file_hash,
    write_json,
)
from .field_layout import clear_label_pin_numbers_text, tighten_vertical_fields_text
from .power_symbols import (
    _flag_paths,
    _pin_directions,
    aim_power_flags_text,
    _wire_segments,
    glyph_for_net,
    label_view_text,
    remove_rail_runs_text,
    use_power_symbols_text,
    power_symbol_collisions,
    power_symbol_definitions,
    power_symbols,
    rail_presentation,
)
from .readability_checks import (
    FRAME,
    content_extent,
    page_balance_witnesses,
    page_offset,
    placement_fits,
    power_symbols_against_convention,
    rail_route_detours,
)
from .schematic_fields import measure_field_association, measure_field_locality


def _top_level_forms(text: str) -> list[tuple[int, int, list]]:
    """Locate native forms without rewriting embedded library definitions."""
    parse(text)
    depth, quoted, escaped, start = 0, False, False, None
    result = []
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            if depth == 1:
                start = index
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and start is not None:
                result.append((start, index + 1, parse(text[start : index + 1])))
                start = None
    return result


def edit_schematic_text(
    text: str,
    actions: list[SchematicAction],
    terminal_inventory: list[dict] | None = None,
    rail_context: dict[str, dict] | None = None,
) -> str:
    """Apply bounded visual edits without changing symbols or electrical net assignments."""
    for action in actions:
        forms = _top_level_forms(text)
        replacements = []
        if isinstance(action, MoveField):
            matches = []
            for start, end, node in forms:
                if node[0] != "symbol":
                    continue
                refs = [p for p in children(node, "property") if p[1] == "Reference"]
                if (
                    len(refs) == 1
                    and refs[0][2] == action.reference
                    and int(one(node, "unit")[1]) == action.unit
                ):
                    matches.append((start, end, node))
            if len(matches) != 1:
                raise ValueError("move_field must identify one existing reference/unit")
            start, end, node = matches[0]
            properties = {prop[1]: prop for prop in children(node, "property")}
            current = one(properties[action.field], "at")
            if (
                abs(float(current[1]) - action.x_mm) < 0.000001
                and abs(float(current[2]) - action.y_mm) < 0.000001
                and int(float(current[3])) == action.angle
            ):
                raise ValueError(
                    f"move_field for {action.reference}.{action.field} made no change; "
                    "choose a different position"
                )
            block = text[start:end]
            pattern = re.compile(
                r'(\(property\s+"' + action.field + r'"\s+"(?:\\.|[^"\\])*"\s+\(at\s+)[^()]+(?=\))'
            )
            block, count = pattern.subn(
                lambda m: m[1] + f"{action.x_mm:.6f} {action.y_mm:.6f} {action.angle}",
                block,
            )
            if count != 1:
                raise ValueError("move_field requires exactly one native property position")
            replacements.append((start, end, block))
        elif isinstance(action, AddWirePath):
            if terminal_inventory is None:
                raise ValueError("add_wire_path requires independently observed terminal positions")
            route = resolve_wire_path_points(action, terminal_inventory)
            text = _insert_wire_route(text, route_around_existing_wires(text, route))
        elif isinstance(action, ConnectRail):
            if terminal_inventory is None:
                raise ValueError("connect_rail requires independently observed terminal positions")
            text = connect_rail_text(
                text,
                action.net,
                terminal_inventory,
                power_symbols_allowed=rail_context is not None,
                rail=(rail_context or {}).get(action.net),
                replace_existing=action.replace_existing,
            )
        elif isinstance(action, MoveSymbols):
            if terminal_inventory is None:
                raise ValueError("move_symbols requires independently observed terminal positions")
            text = move_symbols_text(text, action, terminal_inventory)
        elif isinstance(action, UsePowerSymbols):
            if terminal_inventory is None or rail_context is None:
                raise ValueError(
                    "use_power_symbols requires independently observed terminal positions"
                )
            context = rail_context.get(action.net, {})
            text = use_power_symbols_text(
                text,
                action.net,
                terminal_inventory,
                context.get("flags", []),
                context.get("local_pairs", []),
                context.get("layout_check"),
            )
        elif isinstance(action, TranslateSheet):
            if action.dx_mm == 0 and action.dy_mm == 0:
                raise ValueError("translate_sheet made no change; choose nonzero movement")
            for start, end, node in forms:
                if node[0] not in {"symbol", "wire", "junction", "label", "no_connect", "text"}:
                    continue
                block = _translate_block(text[start:end], action.dx_mm, action.dy_mm)
                replacements.append((start, end, block))
        else:
            raise ValueError("regeneration is handled by the compiler adapter")
        for start, end, block in reversed(replacements):
            text = text[:start] + block + text[end:]
    parse(text)
    return text


def resolve_wire_path_points(
    action: AddWirePath, terminal_inventory: list[dict]
) -> list[WirePoint]:
    """Resolve named route endpoints to exact observed positions on the declared net."""
    terminals = {
        (item["reference"], item["pin"]): item
        for item in terminal_inventory
        if item["net"] == action.net
    }
    resolved = []
    for reference, pin in ((action.from_ref, action.from_pin), (action.to_ref, action.to_pin)):
        terminal = terminals.get((reference, pin))
        if terminal is None:
            raise ValueError(
                f"{reference}.{pin} is not an intended terminal on {action.net}; "
                f"valid terminals are {sorted(terminals)}"
            )
        resolved.append(WirePoint(x_mm=terminal["x_mm"], y_mm=terminal["y_mm"]))
    route = [resolved[0], *action.waypoints, resolved[1]]
    for first, second in zip(route, route[1:]):
        if first == second:
            raise ValueError(
                f"wire route repeats waypoint {first.x_mm, first.y_mm}; omit points matching "
                "either named terminal"
            )
    return route


PAGE_CENTRING_REACH_STEPS = 60


def centre_on_page_text(text: str) -> tuple[str, dict]:
    """Translate the whole drawing, by whole grid steps, to the centre of the usable frame.

    Offsets are tried nearest the exact centring first; the first whose drawing stays
    inside the frame and clear of the title block is used. The drawing is left where it
    is when no offset within PAGE_CENTRING_REACH_STEPS fits.
    """
    step = 1_270_000
    extent = content_extent(parse(text))
    left, top, right, bottom = FRAME
    ideal = (
        ((left + right) - (extent[0] + extent[2])) / 2 / step,
        ((top + bottom) - (extent[1] + extent[3])) / 2 / step,
    )
    base = (round(ideal[0]), round(ideal[1]))
    candidates = sorted(
        (
            (base[0] + i, base[1] + j)
            for i in range(-PAGE_CENTRING_REACH_STEPS, PAGE_CENTRING_REACH_STEPS + 1)
            for j in range(-PAGE_CENTRING_REACH_STEPS, PAGE_CENTRING_REACH_STEPS + 1)
        ),
        key=lambda move: (
            max(
                abs(axis)
                for axis in page_offset(
                    (
                        extent[0] + move[0] * step,
                        extent[1] + move[1] * step,
                        extent[2] + move[0] * step,
                        extent[3] + move[1] * step,
                    )
                )
            ),
            abs(move[0]) + abs(move[1]),
            move,
        ),
    )
    record = {
        "before_offset_fraction": [round(value, 3) for value in page_offset(extent)],
        "extent_mm": [round(value / 1e6, 2) for value in extent],
    }
    for dx, dy in candidates:
        moved = (
            extent[0] + dx * step,
            extent[1] + dy * step,
            extent[2] + dx * step,
            extent[3] + dy * step,
        )
        if not placement_fits(moved):
            continue
        record["after_offset_fraction"] = [round(value, 3) for value in page_offset(moved)]
        record["dx_mm"], record["dy_mm"] = round(dx * 1.27, 2), round(dy * 1.27, 2)
        if dx == 0 and dy == 0:
            return text, record
        action = TranslateSheet(operation="translate_sheet", dx_mm=dx * 1.27, dy_mm=dy * 1.27)
        return edit_schematic_text(text, [action]), record
    record["refused"] = "no grid offset keeps the drawing inside the frame"
    return text, record


def _translate_block(block: str, dx_mm: float, dy_mm: float) -> str:
    """Translate every `at`/`xy` coordinate in a native form, leaving quoted text intact."""

    def translate(match: re.Match[str]) -> str:
        if match[1] is None:
            return match[0]
        return match[1] + f"{float(match[2]) + dx_mm:.6f} " + f"{float(match[3]) + dy_mm:.6f}"

    return re.sub(
        r'"(?:\\.|[^"\\])*"|(\((?:at|xy)\s+)([-+0-9.eE]+)\s+([-+0-9.eE]+)', translate, block
    )


def _nm_point(node: list) -> Point:
    return (round(float(node[1]) * 1_000_000), round(float(node[2]) * 1_000_000))


def _wire_point(point: Point) -> WirePoint:
    return WirePoint(x_mm=point[0] / 1_000_000, y_mm=point[1] / 1_000_000)


def _insert_wire_route(text: str, route: list[WirePoint]) -> str:
    """Append one orthogonal wire route and the T-junctions it creates on existing wires."""
    forms = _top_level_forms(text)
    existing = {
        frozenset((float(point[1]), float(point[2])) for point in children(one(node, "pts"), "xy"))
        for _, _, node in forms
        if node[0] == "wire"
    }
    existing_segments = [
        (_nm_point(first), _nm_point(second))
        for _, _, node in forms
        if node[0] == "wire"
        for first, second in zip(
            children(one(node, "pts"), "xy"), children(one(node, "pts"), "xy")[1:]
        )
    ]
    orthogonal = [route[0]]
    for point in route[1:]:
        previous = orthogonal[-1]
        if previous.x_mm != point.x_mm and previous.y_mm != point.y_mm:
            orthogonal.append(WirePoint(x_mm=point.x_mm, y_mm=previous.y_mm))
        orthogonal.append(point)
    segments = list(zip(orthogonal, orthogonal[1:]))
    if all(
        frozenset(((first.x_mm, first.y_mm), (second.x_mm, second.y_mm))) in existing
        for first, second in segments
    ):
        raise ValueError("add_wire_path duplicates existing wire geometry")
    wires = []
    for first, second in segments:
        wires.append(
            "\n (wire (pts (xy "
            f"{first.x_mm:.6f} {first.y_mm:.6f}) (xy {second.x_mm:.6f} {second.y_mm:.6f})) "
            f"(stroke (width 0) (type default)) (uuid {quote(str(uuid4()))}))"
        )
    junction_points = {
        (round(point.x_mm * 1_000_000), round(point.y_mm * 1_000_000))
        for point in orthogonal
        if any(
            point_on_segment(
                (round(point.x_mm * 1_000_000), round(point.y_mm * 1_000_000)), first, second
            )
            for first, second in existing_segments
        )
    }
    existing_junctions = {
        _nm_point(one(node, "at")) for _, _, node in forms if node[0] == "junction"
    }
    junctions = [
        "\n (junction (at "
        f"{x / 1_000_000:.6f} {y / 1_000_000:.6f}) (diameter 0) "
        f"(color 0 0 0 0) (uuid {quote(str(uuid4()))}))"
        for x, y in sorted(junction_points - existing_junctions)
    ]
    insert = text.rfind(")")
    if insert < 0:
        raise ValueError("schematic root form is missing")
    return text[:insert] + "".join(wires) + "".join(junctions) + "\n" + text[insert:]


def _wire_trees(tree: list) -> tuple[list[tuple[Point, Point]], list[int], list[int]]:
    """Return wire segments, each segment's source wire index and its connected-tree id."""
    segments, owners = [], []
    for index, wire in enumerate(children(tree, "wire")):
        points = [_nm_point(point) for point in children(one(wire, "pts"), "xy")]
        for first, second in zip(points, points[1:]):
            segments.append((first, second))
            owners.append(index)
    parent = list(range(len(segments)))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for index, (first, second) in enumerate(segments):
        for other in range(index + 1, len(segments)):
            third, fourth = segments[other]
            if (
                owners[index] == owners[other]
                or any(point_on_segment(point, third, fourth) for point in (first, second))
                or any(point_on_segment(point, first, second) for point in (third, fourth))
            ):
                parent[find(index)] = find(other)
    return segments, owners, [find(index) for index in range(len(segments))]


def _point_groups(tree: list, points: list[Point]) -> list[list[int]]:
    """Group points that native wire geometry joins; labels intentionally add no joins."""
    return [indexes for indexes, _segments in _point_group_wiring(tree, points)]


def _point_group_wiring(
    tree: list, points: list[Point]
) -> list[tuple[list[int], list[tuple[Point, Point]]]]:
    """Return each wire-joined point group with the native wire segments of its trees."""
    segments, _owners, roots = _wire_trees(tree)
    groups: dict[object, list[int]] = {}
    for index, point in enumerate(points):
        key: object = ("point", point)
        for segment, root in zip(segments, roots):
            if point_on_segment(point, *segment):
                key = ("tree", root)
                break
        groups.setdefault(key, []).append(index)
    return [
        (
            indexes,
            [
                segment
                for segment, root in zip(segments, roots)
                if key[0] == "tree" and root == key[1]
            ],
        )
        for key, indexes in groups.items()
    ]


def _terminal_keepouts(terminal_inventory: list[dict]) -> list[tuple[int, int, int, int]]:
    return [
        (
            round(item["x_mm"] * 1_000_000) - 400_000,
            round(item["y_mm"] * 1_000_000) - 400_000,
            round(item["x_mm"] * 1_000_000) + 400_000,
            round(item["y_mm"] * 1_000_000) + 400_000,
        )
        for item in terminal_inventory
    ]


def _grid_projection(point: Point, segment: tuple[Point, Point]) -> Point:
    """Nearest connection-grid point on an orthogonal wire segment."""
    (x1, y1), (x2, y2) = segment

    def clamp(value: int, low: int, high: int) -> int:
        low, high = min(low, high), max(low, high)
        snapped = round(min(max(value, low), high) / PITCH) * PITCH
        if snapped < low:
            snapped += PITCH
        if snapped > high:
            snapped -= PITCH
        return snapped

    return (clamp(point[0], x1, x2), clamp(point[1], y1, y2))


def _route_length(route: list[WirePoint]) -> int:
    return sum(
        round(abs(first.x_mm - second.x_mm) * 1_000_000)
        + round(abs(first.y_mm - second.y_mm) * 1_000_000)
        for first, second in zip(route, route[1:])
    )


# The independent layout observer rejects a net longer than 250 mm.
MAXIMUM_CONNECTED_NET_LENGTH = 240_000_000
# Under brief v3, rail routes longer than this give way to power symbols.
MAXIMUM_DETOUR_FACTOR = 3
MINIMUM_DETOUR_ALLOWANCE = 25_400_000
# Under brief v3, a rail is wired between its separately drawn terminal groups only by
# routes up to this long; farther groups get power symbols (supply arrows or ground
# glyphs) instead of long rail wires around the page.
MAXIMUM_RAIL_ROUTE = 25_400_000


def _connect_point_groups(
    text: str,
    points: list[Point],
    keepouts: list[tuple[int, int, int, int]],
    description: str,
    partial: bool = False,
    max_route: int | None = None,
) -> str:
    """Join wire-disconnected points with the shortest obstacle-checked route found.

    With ``partial``, groups that cannot reach the largest group may still be joined to
    each other, and the routes found are kept when some groups stay unreachable.
    """
    wiring = _point_group_wiring(parse(text), points)
    while len(wiring) > 1:
        main = max(wiring, key=lambda item: (len(item[0]), -min(item[0])))
        existing_length = sum(
            abs(a[0] - b[0]) + abs(a[1] - b[1]) for _, segments in wiring for a, b in segments
        )
        successes = []
        pairings = [[(main, other) for other in wiring if other is not main]]
        if partial:
            pairings.append(
                [
                    (first, second)
                    for index, first in enumerate(wiring)
                    for second in wiring[index + 1 :]
                    if main not in (first, second)
                ]
            )
        for pairs in pairings:
            candidates = set()
            for group, other in pairs:
                for first, first_segments, second, second_segments in (
                    (group[0], group[1], other[0], other[1]),
                    (other[0], other[1], group[0], group[1]),
                ):
                    for index in first:
                        start = points[index]
                        targets = [points[item] for item in second] + [
                            _grid_projection(start, segment) for segment in second_segments
                        ]
                        candidates.update((start, target) for target in targets if target != start)
            ordered = sorted(
                candidates,
                key=lambda pair: (
                    abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]),
                    pair,
                ),
            )
            for start, finish in ordered[:32]:
                try:
                    route = route_around_existing_wires(
                        text, [_wire_point(start), _wire_point(finish)], keepouts=keepouts
                    )
                    candidate = _insert_wire_route(text, route)
                except ValueError:
                    continue
                if existing_length + _route_length(route) > MAXIMUM_CONNECTED_NET_LENGTH:
                    continue
                direct = abs(start[0] - finish[0]) + abs(start[1] - finish[1])
                if partial and _route_length(route) > max(
                    MAXIMUM_DETOUR_FACTOR * direct, direct + MINIMUM_DETOUR_ALLOWANCE
                ):
                    # A lap around the drawing reads worse than a power symbol.
                    continue
                if max_route is not None and _route_length(route) > max_route:
                    continue
                if len(_point_groups(parse(candidate), points)) < len(wiring):
                    successes.append((_route_length(route), len(successes), candidate))
                    if len(successes) == 4:
                        break
            if successes:
                break
        if not successes:
            if partial:
                return text
            raise ValueError(
                f"no obstacle-free native wire route joins the remaining {description} groups"
            )
        text = min(successes)[2]
        wiring = _point_group_wiring(parse(text), points)
    return text


def connect_rail_text(
    text: str,
    net: str,
    terminal_inventory: list[dict],
    power_symbols_allowed: bool = False,
    rail: dict | None = None,
    replace_existing: bool = False,
) -> str:
    """Make every intended terminal of one net reachable through visible native wires.

    Under the power-symbol rail policy (brief v3), every group that can be routed is
    wired, and only the groups no wire can reach are marked with matching power symbols.
    Groups are wired only by routes up to MAXIMUM_RAIL_ROUTE; farther groups get power
    symbols. A fully wired return rail also gets one ground symbol, as schematics
    conventionally show ground.
    """
    terminals = [item for item in terminal_inventory if item["net"] == net]
    if len(terminals) < 2:
        raise ValueError(f"connect_rail requires at least two observed terminals on {net}")
    points = list(
        dict.fromkeys(
            (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000)) for item in terminals
        )
    )
    joined = len(_point_groups(parse(text), points)) == 1
    if replace_existing:
        rail = rail or {}
        text = remove_rail_runs_text(
            text, net, terminal_inventory, rail.get("flags", []), rail.get("local_pairs", [])
        )
        joined = False
    elif joined and not (power_symbols_allowed and _needs_ground_symbol(text, net)):
        raise ValueError(f"connect_rail made no change; {net} terminals are already wire-joined")
    keepouts = _terminal_keepouts([item for item in terminal_inventory if item["net"] != net])
    if power_symbols_allowed:
        wired = (
            text
            if joined
            else _connect_point_groups(
                text,
                points,
                keepouts,
                f"{net} wire",
                partial=True,
                max_route=MAXIMUM_RAIL_ROUTE,
            )
        )
        rail = rail or {}
        if len(_point_groups(parse(wired), points)) == 1:
            if not _needs_ground_symbol(wired, net):
                return wired
            try:
                return use_power_symbols_text(
                    wired,
                    net,
                    terminal_inventory,
                    rail.get("flags", []),
                    rail.get("local_pairs", []),
                    rail.get("layout_check"),
                    prune_rail_wiring=False,
                )
            except ValueError as error:
                if joined:
                    raise ValueError(
                        f"connect_rail made no change; {net} is wired and no clear position "
                        f"exists for its ground symbol: {error}"
                    ) from error
                return wired
        try:
            return use_power_symbols_text(
                wired,
                net,
                terminal_inventory,
                rail.get("flags", []),
                rail.get("local_pairs", []),
                rail.get("layout_check"),
                prune_rail_wiring=False,
            )
        except ValueError as error:
            raise ValueError(
                f"connect_rail wired what it could of {net}, but marking the unreachable "
                f"groups failed: {error}"
            ) from error
    try:
        return _connect_point_groups(text, points, keepouts, f"{net} wire")
    except ValueError as error:
        references = sorted({item["reference"] for item in terminals})
        if power_symbols_allowed:
            raise ValueError(
                f"{error}. Repeating connect_rail for {net} will fail again on this revision; "
                f"request use_power_symbols for {net} to draw it with power symbols instead"
            ) from error
        raise ValueError(
            f"{error}. Repeating connect_rail for {net} will fail again on this revision; "
            f"first request move_symbols for one of {references} by a grid-aligned offset "
            "into open space, then request connect_rail again"
        ) from error


def _needs_ground_symbol(text: str, net: str) -> bool:
    """A return rail drawn without any ground symbol."""
    return glyph_for_net(net) == "power:GND" and not any(
        item["net"] == net for item in power_symbols(parse(text))
    )


def move_symbols_text(text: str, action: MoveSymbols, terminal_inventory: list[dict]) -> str:
    """Move a symbol group with its private wiring; reroute nets shared with other symbols."""
    dx, dy = round(action.dx_mm * 1_000_000), round(action.dy_mm * 1_000_000)
    if dx % PITCH or dy % PITCH:
        raise ValueError(f"move_symbols offsets must use the KiCad {PITCH / 1_000_000:g} mm grid")
    moved = set(action.references)
    tree = parse(text)
    found = {
        prop[2]
        for symbol in children(tree, "symbol")
        for prop in children(symbol, "property")
        if prop[1] == "Reference" and prop[2] in moved
    }
    if found != moved:
        raise ValueError(f"move_symbols references not found: {sorted(moved - found)}")

    def pin_point(item: dict) -> Point:
        return (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000))

    moved_pins = {pin_point(item) for item in terminal_inventory if item["reference"] in moved}
    # Pin-mounted decorations such as power flags travel with the pin they mark.
    pins_by_reference: dict[str, set[Point]] = {}
    for item in terminal_inventory:
        pins_by_reference.setdefault(item["reference"], set()).add(pin_point(item))
    moved |= {
        reference
        for reference, pins in pins_by_reference.items()
        if reference not in moved and pins <= moved_pins
    }
    fixed_pins = {pin_point(item) for item in terminal_inventory if item["reference"] not in moved}
    segments, owners, roots = _wire_trees(tree)
    labels = [(_nm_point(one(label, "at")), label) for label in children(tree, "label")]
    junctions = [_nm_point(one(node, "at")) for node in children(tree, "junction")]

    def touches(root: int, point: Point) -> bool:
        return any(
            point_on_segment(point, *segment)
            for segment, other in zip(segments, roots)
            if other == root
        )

    carried_wires, removed_wires = set(), set()
    carried_roots: set[int] = set()
    carried_points: set[Point] = set(moved_pins)
    removed_points: set[Point] = set()
    reconnect: list[list[Point]] = []
    for root in sorted(set(roots)):
        wire_indexes = {owner for owner, other in zip(owners, roots) if other == root}
        moving = {point for point in moved_pins if touches(root, point)}
        fixed = {point for point in fixed_pins if touches(root, point)}
        if not moving:
            continue
        attached_labels = {point for point, _label in labels if touches(root, point)}
        attached_junctions = {point for point in junctions if touches(root, point)}
        if not fixed:
            carried_wires |= wire_indexes
            carried_points |= attached_labels | attached_junctions
            carried_roots.add(root)
            continue
        removed_wires |= wire_indexes
        removed_points |= attached_junctions
        reconnect.append(sorted({(x + dx, y + dy) for x, y in moving} | fixed | attached_labels))

    # Power flags and power symbols on a carried stub travel with it, not left stranded.
    for symbol in children(tree, "symbol"):
        if not one(symbol, "lib_id")[1].startswith("power:"):
            continue
        point = _nm_point(one(symbol, "at"))
        if any(touches(root, point) for root in carried_roots):
            moved.add(
                next(prop[2] for prop in children(symbol, "property") if prop[1] == "Reference")
            )

    rewritten = []
    wire_index = -1
    for start, end, node in _top_level_forms(text):
        block = text[start:end]
        if node[0] == "wire":
            wire_index += 1
            if wire_index in removed_wires:
                rewritten.append((start, end, ""))
            elif wire_index in carried_wires:
                rewritten.append((start, end, _translate_block(block, action.dx_mm, action.dy_mm)))
        elif node[0] == "symbol":
            if any(p[1] == "Reference" and p[2] in moved for p in children(node, "property")):
                rewritten.append((start, end, _translate_block(block, action.dx_mm, action.dy_mm)))
        elif node[0] in {"label", "junction", "no_connect"}:
            point = _nm_point(one(node, "at"))
            if node[0] == "junction" and point in removed_points:
                rewritten.append((start, end, ""))
            elif point in carried_points:
                rewritten.append((start, end, _translate_block(block, action.dx_mm, action.dy_mm)))
    for start, end, block in reversed(rewritten):
        text = text[:start] + block + text[end:]
    shifted = [
        dict(item, x_mm=item["x_mm"] + action.dx_mm, y_mm=item["y_mm"] + action.dy_mm)
        if item["reference"] in moved
        else item
        for item in terminal_inventory
    ]
    for points in reconnect:
        point_set = set(points)
        keepouts = _terminal_keepouts(
            [item for item in shifted if pin_point(item) not in point_set]
        )
        text = _connect_point_groups(text, points, keepouts, "rerouted moved-symbol net")
    return text


Box = tuple[int, int, int, int]

# Half a 1.27 mm pin-name line plus the 0.25 mm body padding.
BODYLESS_UNIT_HALF_WIDTH = 885_000


def _drawn_boxes(
    tree: list, bodyless: list[tuple[str, Box]] | None = None
) -> tuple[list[tuple[str, Box]], list[tuple[str, Box]]]:
    """Padded symbol body/pin-stub boxes and visible field/label text boxes of a sheet.

    The column boxes of units drawn without a body are also appended to ``bodyless``.
    """
    library_symbols = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    symbol_boxes: list[tuple[str, Box]] = []
    text_boxes: list[tuple[str, Box]] = []
    for label in children(tree, "label"):
        (x, y), angle = _nm_point(one(label, "at")), int(float(one(label, "at")[3]))
        width = label_text_width(label[1])
        bounds = {
            0: (x, y - 2_000_000, x + width, y),
            180: (x - width, y - 2_000_000, x, y),
            90: (x - 2_000_000, y - width, x, y),
            270: (x - 2_000_000, y, x, y + width),
        }.get(angle % 360, (x - width, y - width, x + width, y + width))
        text_boxes.append((f"label-{label[1]}", bounds))
    for symbol in children(tree, "symbol"):
        reference = next(prop[2] for prop in children(symbol, "property") if prop[1] == "Reference")
        library = library_symbols.get(one(symbol, "lib_id")[1])
        if library is None:
            continue
        at = one(symbol, "at")
        origin = (_nm(at[1]), _nm(at[2]))
        angle = int(at[3])
        for prop in children(symbol, "property"):
            if prop[1] not in {"Reference", "Value"} or children(prop, "hide"):
                continue
            effects = children(prop, "effects")
            if effects and (children(effects[0], "hide") or "hide" in effects[0]):
                continue
            size = one(one(effects[0], "font"), "size") if effects else None
            font_scale = max(_nm(size[1]), _nm(size[2])) / 1_270_000 if size else 1.0
            prop_at = one(prop, "at")
            text_angle = property_page_angle(angle, int(float(prop_at[3])))
            width, height = text_extents(prop[2], text_angle)
            half_width, half_height = (
                round(width * font_scale / 2),
                round(height * font_scale / 2),
            )
            center_x, center_y = _nm(prop_at[1]), _nm(prop_at[2])
            text_boxes.append(
                (
                    reference,
                    (
                        center_x - half_width - 500_000,
                        center_y - half_height - 500_000,
                        center_x + half_width + 500_000,
                        center_y + half_height + 500_000,
                    ),
                )
            )
        mirrors = children(symbol, "mirror")
        mirror = mirrors[0][1] if mirrors else None
        units = children(symbol, "unit")
        unit = units[0][1] if units else "1"
        body_points: list[Point] = []
        inner_ends: list[Point] = []
        for body in children(library, "symbol"):
            body_unit = body[1].rsplit("_", 2)[-2] if body[1].count("_") >= 2 else "0"
            if body_unit not in {"0", str(unit)}:
                continue
            for pin in children(body, "pin"):
                pin_at, length = one(pin, "at"), _nm(one(pin, "length")[1])
                direction = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}.get(
                    int(float(pin_at[3])) % 360
                )
                if direction is None or length <= 0:
                    continue
                stub = []
                for x, y in (
                    (_nm(pin_at[1]), _nm(pin_at[2])),
                    (
                        _nm(pin_at[1]) + direction[0] * length,
                        _nm(pin_at[2]) + direction[1] * length,
                    ),
                ):
                    dx, dy = transform_library_point(x, y, angle, mirror)
                    stub.append((origin[0] + dx, origin[1] + dy))
                # The stub stops short of its connection point so wires may still land there.
                (x1, y1), (x2, y2) = stub
                inner_ends.append((x2, y2))
                step_x = (x2 > x1) - (x2 < x1)
                step_y = (y2 > y1) - (y2 < y1)
                x1, y1 = x1 + step_x * 500_000, y1 + step_y * 500_000
                symbol_boxes.append(
                    (
                        reference,
                        (
                            min(x1, x2) - 250_000,
                            min(y1, y2) - 250_000,
                            max(x1, x2) + 250_000,
                            max(y1, y2) + 250_000,
                        ),
                    )
                )
            shapes = [(shape, "rectangle") for shape in children(body, "rectangle")]
            shapes.extend((shape, "polyline") for shape in children(body, "polyline"))
            for shape, kind in shapes:
                if kind == "rectangle":
                    corners = [one(shape, "start"), one(shape, "end")]
                else:
                    corners = children(one(shape, "pts"), "xy")
                for corner in corners:
                    dx, dy = transform_library_point(_nm(corner[1]), _nm(corner[2]), angle, mirror)
                    body_points.append((origin[0] + dx, origin[1] + dy))
        # One union box per placed unit, matching the independent layout observer.
        if body_points:
            symbol_boxes.append(
                (
                    reference,
                    (
                        min(point[0] for point in body_points) - 250_000,
                        min(point[1] for point in body_points) - 250_000,
                        max(point[0] for point in body_points) + 250_000,
                        max(point[1] for point in body_points) + 250_000,
                    ),
                )
            )
        elif len(inner_ends) > 1:
            # A unit drawn without a body, such as an op-amp power unit, reads as one
            # column from pin to pin with the pin names along it; keep wires out of it.
            column = (
                reference,
                (
                    min(point[0] for point in inner_ends) - BODYLESS_UNIT_HALF_WIDTH,
                    min(point[1] for point in inner_ends) - BODYLESS_UNIT_HALF_WIDTH,
                    max(point[0] for point in inner_ends) + BODYLESS_UNIT_HALF_WIDTH,
                    max(point[1] for point in inner_ends) + BODYLESS_UNIT_HALF_WIDTH,
                ),
            )
            symbol_boxes.append(column)
            if bodyless is not None:
                bodyless.append(column)

    return symbol_boxes, text_boxes


def wires_through_bodyless_units(tree: list) -> list[dict]:
    """Wires drawn across the pin column of a unit that has no body, such as U1C.

    A wire crosses the column when it passes from one side to the other, or runs along
    it between the pins' inner ends where the pin names are. Wires that only end at a
    pin's inner end, as the compiler draws a local decoupling pair, are not crossings.
    """
    columns: list[tuple[str, Box]] = []
    _drawn_boxes(tree, columns)
    pad = BODYLESS_UNIT_HALF_WIDTH
    crossings = []
    for reference, (left, top, right, bottom) in columns:
        vertical = bottom - top >= right - left
        for wire in children(tree, "wire"):
            points = children(one(wire, "pts"), "xy")
            (x1, y1), (x2, y2) = _nm_point(points[0]), _nm_point(points[1])
            if not vertical:
                # Work in the column's frame: along = the axis between the pins.
                x1, y1, x2, y2 = y1, x1, y2, x2
                left, top, right, bottom = top, left, bottom, right
            across = x1 != x2 and y1 == y2 and top <= y1 <= bottom
            crosses = across and min(x1, x2) < left and max(x1, x2) > right
            along = (
                x1 == x2
                and left <= x1 <= right
                and min(max(y1, y2), bottom - pad) - max(min(y1, y2), top + pad) > 0
            )
            if not vertical:
                x1, y1, x2, y2 = y1, x1, y2, x2
                left, top, right, bottom = top, left, bottom, right
            if crosses or along:
                crossings.append(
                    {
                        "kind": "wire_through_bodyless_unit",
                        "reference": reference,
                        "wire_mm": [[x1 / 1e6, y1 / 1e6], [x2 / 1e6, y2 / 1e6]],
                    }
                )
    return crossings


def route_around_existing_wires(
    text: str,
    requested: list[WirePoint],
    *,
    keepouts: list[tuple[int, int, int, int]] = (),
) -> list[WirePoint]:
    """Plan requested legs around wires, symbol bodies, visible fields, labels and keepouts."""
    nanometers = 1_000_000
    points: list[Point] = [
        (round(point.x_mm * nanometers), round(point.y_mm * nanometers)) for point in requested
    ]
    if len(points) < 2:
        raise ValueError("wire route requires two distinct terminals")
    if any(first == second for first, second in zip(points, points[1:])):
        raise ValueError("wire route contains a zero-length leg")
    if any(x % PITCH or y % PITCH for x, y in points):
        raise ValueError(f"wire route points must use the KiCad {PITCH / 1_000_000:g} mm grid")

    tree = parse(text)
    wires = []
    for index, wire in enumerate(children(tree, "wire")):
        coordinates = [
            (round(float(point[1]) * nanometers), round(float(point[2]) * nanometers))
            for point in children(one(wire, "pts"), "xy")
        ]
        for first, second in zip(coordinates, coordinates[1:]):
            wires.append((f"existing-wire-{index}", first, second))

    symbol_boxes, text_boxes = _drawn_boxes(tree)
    symbol_boxes = [("keepout", bounds) for bounds in keepouts] + symbol_boxes

    planned: list[Point] = [points[0]]
    for start, finish in zip(points, points[1:]):
        # Existing wire stubs that terminate at a named pin are allowed to
        # leave that pin. The independent KiCad layout and net gates still
        # validate the resulting complete candidate.
        wire_obstacles = tuple(
            Reservation(
                f"wire-{index}",
                "exclusive",
                owner,
                "native_wire",
                (
                    min(first[0], second[0]) - 100_000,
                    min(first[1], second[1]) - 100_000,
                    max(first[0], second[0]) + 100_000,
                    max(first[1], second[1]) + 100_000,
                ),
            )
            for index, (owner, first, second) in enumerate(wires)
            if not any(point_on_segment(endpoint, first, second) for endpoint in (start, finish))
        )
        body_obstacles = tuple(
            Reservation(f"body-{index}", "exclusive", reference, "symbol_body", trimmed)
            for index, (reference, bounds) in enumerate(symbol_boxes)
            if (trimmed := _release_endpoints(bounds, (start, finish))) is not None
        )
        text_obstacles = tuple(
            Reservation(f"text-{index}", "exclusive", reference, "symbol_text", trimmed)
            for index, (reference, bounds) in enumerate(text_boxes)
            if (trimmed := _release_endpoints(bounds, (start, finish))) is not None
        )
        obstacles = wire_obstacles + body_obstacles + text_obstacles
        segments, _expansions = _connect(
            start,
            finish,
            obstacles,
            (),
            net="review-route",
            owner="new-review-wire",
            allowed_contacts=frozenset(),
            route_bounds=(0, 0, 297_000_000, 210_000_000),
        )
        if segments is None:
            path = _grid_route(start, finish, obstacles)
            if path is None:
                raise ValueError(
                    "no obstacle-free native wire route exists between named terminals"
                )
            planned.extend(path[1:])
        else:
            for _first, second in segments:
                if second != planned[-1]:
                    planned.append(second)
    return [WirePoint(x_mm=x / nanometers, y_mm=y / nanometers) for x, y in planned]


def _release_endpoints(
    bounds: tuple[int, int, int, int], endpoints: tuple[Point, ...]
) -> tuple[int, int, int, int] | None:
    """Pull a padded body edge off a route endpoint that touches it; drop deep containment."""
    left, top, right, bottom = bounds
    edge_band = 400_000
    for x, y in endpoints:
        if not (left <= x <= right and top <= y <= bottom):
            continue
        if bottom - y <= edge_band:
            bottom = y - 100_000
        elif y - top <= edge_band:
            top = y + 100_000
        elif right - x <= edge_band:
            right = x - 100_000
        elif x - left <= edge_band:
            left = x + 100_000
        else:
            return None
        if left >= right or top >= bottom:
            return None
    return left, top, right, bottom


def _grid_route(
    start: Point,
    finish: Point,
    obstacles: tuple[Reservation, ...],
) -> tuple[Point, ...] | None:
    """Search every KiCad connection-grid cell when sparse routing tracks fail."""
    step = PITCH
    if start[0] % step != finish[0] % step or start[1] % step != finish[1] % step:
        return None

    def inside(point: Point) -> bool:
        return 0 <= point[0] <= 297_000_000 and 0 <= point[1] <= 210_000_000

    def heuristic(point: Point) -> int:
        return (abs(finish[0] - point[0]) + abs(finish[1] - point[1])) // step

    # Rasterize each exclusive obstacle once into the unit grid edges it strictly
    # intersects; this is the same test segment_is_admissible applies per edge.
    origin_x, origin_y = start[0] % step, start[1] % step

    def grid_values(low: int, high: int, origin: int) -> range:
        first = low - ((low - origin) % step) + step
        return range(first, high, step)

    blocked_horizontal: set[Point] = set()
    blocked_vertical: set[Point] = set()
    for reservation in obstacles:
        if reservation.owner == "new-review-wire":
            continue
        left, top, right, bottom = reservation.rect
        for y in grid_values(top, bottom, origin_y):
            for x in grid_values(left - step, right, origin_x):
                blocked_horizontal.add((x, y))
        for x in grid_values(left, right, origin_x):
            for y in grid_values(top - step, bottom, origin_y):
                blocked_vertical.add((x, y))

    def admissible(point: Point, dx: int, dy: int) -> bool:
        if dx > 0:
            return point not in blocked_horizontal
        if dx < 0:
            return (point[0] - step, point[1]) not in blocked_horizontal
        if dy > 0:
            return point not in blocked_vertical
        return (point[0], point[1] - step) not in blocked_vertical

    directions = ((step, 0), (0, step), (-step, 0), (0, -step))
    initial = (start, -1)
    serial = count()
    queue = [(heuristic(start), 0.0, next(serial), initial)]
    costs = {initial: 0.0}
    previous = {}
    goal = None
    expansions = 0
    while queue and expansions < 700_000:
        _estimate, cost, _order, state = heapq.heappop(queue)
        if cost != costs.get(state):
            continue
        point, prior_direction = state
        if point == finish:
            goal = state
            break
        expansions += 1
        for direction, (dx, dy) in enumerate(directions):
            candidate = (point[0] + dx, point[1] + dy)
            if not inside(candidate) or not admissible(point, dx, dy):
                continue
            bend_cost = 0.2 if prior_direction not in (-1, direction) else 0.0
            next_state = (candidate, direction)
            new_cost = cost + 1 + bend_cost
            if new_cost >= costs.get(next_state, float("inf")):
                continue
            costs[next_state] = new_cost
            previous[next_state] = state
            estimate = new_cost + heuristic(candidate)
            heapq.heappush(queue, (estimate, new_cost, next(serial), next_state))
    if goal is None:
        return None
    states = [goal]
    while states[-1] != initial:
        states.append(previous[states[-1]])
    states.reverse()
    path = [state[0] for state in states]
    compact = [path[0]]
    for index in range(1, len(path) - 1):
        before, current, after = path[index - 1 : index + 2]
        if (before[0] == current[0] == after[0]) or (before[1] == current[1] == after[1]):
            continue
        compact.append(current)
    compact.append(path[-1])
    return tuple(compact)


def terminal_inventory_for_design(design: dict, observed: dict) -> list[dict]:
    """Attach intended net ownership to independently observed terminal positions."""
    references = {component["id"]: component["refdes"] for component in design["components"]}
    return [
        {
            "net": net["id"],
            "reference": references[component_id],
            "pin": pin,
            "x_mm": observed["pin_positions"][(references[component_id], pin)][0] / 1_000_000,
            "y_mm": observed["pin_positions"][(references[component_id], pin)][1] / 1_000_000,
        }
        for net in design["nets"]
        for component_id, pin in net["members"]
        if (references[component_id], pin) in observed.get("pin_positions", {})
    ]


def _name_nets_from_power_labels(observed: dict) -> dict:
    """Name an auto-named net after the power symbol a candidate places on it.

    Rail plans are checked against the netlist of the sheet before the rails were drawn.
    A rail drawn there only with wires has a KiCad auto-name (``Net-(J1-Pin_5)``); once a
    plan marks it with a power symbol, KiCad names the net after that symbol. In the label
    view the symbol is a label, so the old netlist name would make the rail's wires look
    like they belong to two nets.
    """
    nets = observed["nets"]
    wires = observed.get("wires", [])
    renames: dict[str, str] = {}
    for label, point in observed["labels"]:
        if label in nets:
            continue
        # The pins the label reaches: one at its point, or any on the wires it sits on.
        reached = {point}
        group = {i for i, wire in enumerate(wires) if point_on_segment(point, *wire)}
        frontier = list(group)
        while frontier:
            a, b = wires[frontier.pop()]
            for j, other in enumerate(wires):
                if j not in group and (
                    point_on_segment(a, *other)
                    or point_on_segment(b, *other)
                    or point_on_segment(other[0], a, b)
                    or point_on_segment(other[1], a, b)
                ):
                    group.add(j)
                    frontier.append(j)
        found = {
            name
            for name, members in nets.items()
            for member in members
            if (pin := observed["pin_positions"].get(tuple(member))) is not None
            and (pin in reached or any(point_on_segment(pin, *wires[i]) for i in group))
        }
        if len(found) == 1 and (name := next(iter(found))).startswith("Net-("):
            renames.setdefault(name, label)
    if not renames:
        return observed
    return dict(observed, nets={renames.get(name, name): members for name, members in nets.items()})


def _layout_checker(design: dict, name: str, netlist: Path):
    """The protected observer's objection to a candidate sheet's label form, if any."""

    def layout_check(candidate: str) -> str | None:
        with tempfile.TemporaryDirectory(prefix=".label-view-") as folder:
            view = Path(folder) / name
            view.write_text(label_view_text(candidate))
            try:
                observed = _name_nets_from_power_labels(observe(view, netlist))
                check_observed_layout(view, observed, design)
            except (InputError, ValueError, KeyError) as error:
                return str(error)
        return None

    return layout_check


def rail_context_for_design(design: dict, observed: dict) -> dict[str, dict]:
    """Per rail: power-flag pins, and terminal pairs the design wires locally."""
    references = {component["id"]: component["refdes"] for component in design["components"]}
    pin_net = {
        (references[component], pin): net["id"]
        for net in design["nets"]
        for component, pin in net["members"]
    }
    positions = observed["pin_positions"]
    context: dict[str, dict] = {}
    for assertion in design.get("power_assertions", []):
        entry = context.setdefault(assertion["net"], {"flags": [], "local_pairs": []})
        entry["flags"].append(positions[(assertion["refdes"], "1")])
    for relation in design.get("relationships", []):
        if relation["kind"] != "decoupling":
            continue
        consumer = (references[relation["consumer"][0]], relation["consumer"][1])
        net = pin_net.get(consumer)
        capacitor = next(
            (
                (references[relation["component"]], number)
                for number in ("1", "2")
                if pin_net.get((references[relation["component"]], number)) == net
            ),
            None,
        )
        if net in context and capacitor and consumer in positions and capacitor in positions:
            context[net]["local_pairs"].append((positions[consumer], positions[capacitor]))
    return context


def field_collision_witnesses(tree: list) -> list[list[str]]:
    """Measure visible property envelopes, including fields on the same symbol."""
    boxes = []
    for symbol in children(tree, "symbol"):
        props = {p[1]: p for p in children(symbol, "property")}
        reference = props["Reference"][2]
        unit = one(symbol, "unit")[1]
        symbol_angle = int(float(one(symbol, "at")[3]))
        for name in ("Reference", "Value"):
            prop = props.get(name)
            if prop is None or children(prop, "hide"):
                continue
            effect_nodes = children(prop, "effects")
            if effect_nodes and (children(effect_nodes[0], "hide") or "hide" in effect_nodes[0]):
                continue
            scale = 1.0
            if effect_nodes:
                size = one(one(effect_nodes[0], "font"), "size")
                scale = max(float(size[1]), float(size[2])) / 1.27
            at = one(prop, "at")
            angle = property_page_angle(symbol_angle, int(float(at[3])))
            width, height = text_extents(prop[2], angle)
            width, height = width / 1e6 * scale, height / 1e6 * scale
            x, y = float(at[1]), float(at[2])
            boxes.append(
                (
                    f"{reference}:{unit}.{name}",
                    (x - width / 2, y - height / 2, x + width / 2, y + height / 2),
                )
            )
    return [
        [first[0], second[0]]
        for i, first in enumerate(boxes)
        for second in boxes[i + 1 :]
        if overlaps(first[1], second[1])
    ]


def parse_ffmpeg_bbox(stderr: str) -> tuple[int, int, int, int]:
    """Return the nontransparent SVG drawing crop `(width, height, x, y)`."""
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", stderr)
    if not matches:
        raise RuntimeError("FFmpeg could not find visible drawing content in the SVG")
    return tuple(map(int, matches[-1]))


def write_locked_symbol_table(
    directory: Path, resolved: dict, extra: dict[str, str] | None = None
) -> tuple[Path, dict]:
    """Register the exact resolved symbol definitions in an isolated KiCad configuration."""
    libraries = {}
    definitions = {library_id: asset.definition for library_id, asset in resolved.items()}
    for library_id, definition in sorted({**definitions, **(extra or {})}.items()):
        library, name = library_id.split(":", 1)
        libraries.setdefault(library, []).append(
            definition.replace(
                f"(symbol {quote(library_id)}",
                f"(symbol {quote(name)}",
                1,
            )
        )
    folder = directory / "locked-symbols"
    folder.mkdir()
    entries, hashes = [], {}
    for library, definitions in sorted(libraries.items()):
        path = folder / f"{library}.kicad_sym"
        path.write_text(
            '(kicad_symbol_lib (version 20241209) (generator "ai_kicad")\n'
            + "\n".join(definitions)
            + ")\n"
        )
        hashes[library] = file_hash(path)
        entries.append(
            f'(lib (name {quote(library)}) (type "KiCad") '
            f'(uri {quote(str(path.resolve()))}) (options "") (descr "Locked symbols"))'
        )
    table = folder / "sym-lib-table"
    table.write_text("(sym_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    return table, hashes


# Terminal references such as 'J1.3' named in a refused rail edit.
RAIL_BLOCKER = re.compile(r"'([A-Z][A-Z0-9_]*?\d+)\.[A-Za-z0-9_+-]+'")
# Grid offsets (mm) tried for a part blocking every rail plan, nearest first.
RAIL_PLAN_MOVES = sorted(
    (
        (dx, dy)
        for dx in (-25.4, -12.7, 0.0, 12.7, 25.4)
        for dy in (-25.4, -12.7, 0.0, 12.7, 25.4)
        if (dx, dy) != (0.0, 0.0)
    ),
    key=lambda offset: (abs(offset[0]) + abs(offset[1]), -offset[0], offset[1]),
)
# Every offset up to this Manhattan distance is compared before a farther one is tried.
RAIL_PLAN_REACH_MM = 25.4


# How far beside its pin, along the pin's end, a decoupling capacitor may be moved.
DECOUPLING_REACH = 20 * PITCH
DECOUPLING_NEAREST = 4 * PITCH


def _path_length(path: list[tuple[Point, Point]]) -> int:
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in path)


def straighten_decoupling_text(
    text: str, inventory: list[dict], context: dict, check
) -> tuple[str, dict | None]:
    """Move one decoupling capacitor whose wire to its pin detours, so the wire is straight.

    A capacitor in a declared local pair whose wire is longer than the direct distance
    to its consumer pin (for example looping around the capacitor to reach a pin on its
    far side) is moved so that its paired pin sits level with the consumer pin's end,
    beside it, with the capacitor body extending the way that pin points. The nearest
    position whose pair wire is one straight run and that the protected layout check
    accepts is used. Only a capacitor that already points that way is moved; at most one
    move is made, so the caller can observe the new drawing before the next.
    """

    def at(item: dict) -> Point:
        return (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000))

    owner = {at(item): item["reference"] for item in inventory}
    # Power flags are not design terminals, but a moved part's rails must stay wired to
    # them, so the move reroutes to each flag's pin as to a fixed terminal.
    terminals = inventory + [
        {
            "net": net,
            "reference": f"flag:{net}:{index}",
            "pin": "1",
            "x_mm": point[0] / 1_000_000,
            "y_mm": point[1] / 1_000_000,
        }
        for net in sorted(context)
        for index, point in enumerate(context[net].get("flags", []))
    ]
    tree = parse(text)
    segments = _wire_segments(tree)
    outward = _pin_directions(tree)
    for net in sorted(context):
        for consumer, capacitor in context[net].get("local_pairs", []):
            direct = abs(consumer[0] - capacitor[0]) + abs(consumer[1] - capacitor[1])
            path = _flag_paths(segments, consumer, {capacitor})
            if not path or _path_length(path) <= direct:
                continue
            way = outward.get(consumer)
            reference = owner.get(capacitor)
            others = [point for point, name in owner.items() if name == reference]
            others = [point for point in others if point != capacitor]
            if way is None or way[0] or len(others) != 1:
                continue
            other = others[0]
            if other[0] != capacitor[0] or (other[1] > capacitor[1]) != (way[1] > 0):
                continue
            side = 1 if capacitor[0] >= consumer[0] else -1
            for steps in range(DECOUPLING_NEAREST // PITCH, DECOUPLING_REACH // PITCH + 1):
                for sign in (side, -side):
                    target = (consumer[0] + sign * steps * PITCH, consumer[1])
                    dx, dy = target[0] - capacitor[0], target[1] - capacitor[1]
                    if not dx and not dy:
                        continue
                    action = MoveSymbols(
                        operation="move_symbols",
                        references=[reference],
                        dx_mm=dx / 1_000_000,
                        dy_mm=dy / 1_000_000,
                    )
                    try:
                        moved = move_symbols_text(text, action, terminals)
                    except ValueError:
                        continue
                    wire = _flag_paths(_wire_segments(parse(moved)), consumer, {target})
                    if _path_length(wire) != steps * PITCH or check(moved) is not None:
                        continue
                    return moved, {
                        "net": net,
                        "reference": reference,
                        "dx_mm": dx / 1_000_000,
                        "dy_mm": dy / 1_000_000,
                        "pair_wire_mm": [_path_length(path) / 1_000_000, steps * PITCH / 1e6],
                    }
    return text, None


def _search_rail_plans(
    base: str, nets: list[str], inventory: list[dict], context: dict, check
) -> tuple[tuple | None, list[dict]]:
    """Every rail order, rerouting existing runs; best = fewest symbols, then wire.

    Every rail is rerouted, so that a long compiler run gives way to power symbols.
    """
    plans: list[dict] = []
    best = None
    for replace in (True,):
        for order in itertools.permutations(nets):
            record: dict = {"order": list(order), "replace_existing": replace}
            text = base
            try:
                for net in order:
                    try:
                        text = connect_rail_text(
                            text,
                            net,
                            inventory,
                            power_symbols_allowed=True,
                            rail=context.get(net),
                            replace_existing=replace,
                        )
                    except ValueError as error:
                        if "made no change" not in str(error):
                            raise
            except ValueError as error:
                record["refused"] = str(error)
                plans.append(record)
                continue
            tree = parse(text)
            problems = rail_presentation(tree, inventory, nets)
            problems += power_symbol_collisions(text)
            problems += wires_through_bodyless_units(tree)
            objection = check(text)
            symbols = len(power_symbols(tree))
            wire = sum(
                abs(first[0] - second[0]) + abs(first[1] - second[1])
                for first, second in _wire_segments(tree)
            )
            record.update(
                {
                    "valid": not problems and objection is None,
                    "power_symbols": symbols,
                    "wire_length_mm": round(wire / 1_000_000, 2),
                    "unresolved_references": sorted(
                        {
                            terminal.split(".")[0]
                            for problem in problems
                            if isinstance(problem, dict)
                            for terminal in problem.get("terminals", [])
                        }
                    ),
                }
            )
            plans.append(record)
            if record["valid"] and (best is None or (symbols, wire) < best[0]):
                best = ((symbols, wire), text, record)
    return best, plans


class NativeSchematicEngine:
    """Generate, render and independently inspect a single-sheet supported M2b design."""

    def __init__(
        self,
        design: dict,
        launcher: Path,
        *,
        source: Path | None = None,
        symbol_table: Path | None = None,
        maximum_field_distance_mm: float = 25.4,
        power_symbol_rails: bool = False,
        readability_checks: bool = False,
        page_balance: bool = False,
    ):
        self.resolved = assets()
        self.design = validate(design, self.resolved)
        self.launcher = launcher.resolve()
        self.source = source.resolve() if source else None
        self.symbol_table = symbol_table
        self.maximum_field_distance_mm = maximum_field_distance_mm
        # Brief v3: a rail may be presented by wires or by matching global power symbols.
        self.power_symbol_rails = power_symbol_rails
        # Brief v4: measured readability gates for defects the v3 checks and review missed.
        if readability_checks and not power_symbol_rails:
            raise ValueError("readability checks require the brief v3+ rail policy")
        self.readability_checks = readability_checks
        # Brief v5: the compiler output is centred on the page, and balance is a gate.
        if page_balance and not readability_checks:
            raise ValueError("page balance requires the brief v4+ readability checks")
        self.page_balance = page_balance
        self.power_symbols = power_symbol_definitions() if power_symbol_rails else {}
        self.environment = dict(os.environ, LC_ALL="C", TZ="UTC")
        self.renderer = shutil.which("rsvg-convert")
        self.convert = shutil.which("convert")
        self.ffmpeg = shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")
        self.use_ffmpeg_renderer = not (self.renderer and self.convert)
        if self.use_ffmpeg_renderer and not (self.ffmpeg and self.ffprobe):
            raise ValueError("schematic image review requires rsvg/convert or ffmpeg/ffprobe")
        version = self._run([str(self.launcher), "kicad-cli", "version"]).stdout.strip()
        if version != "10.0.6":
            raise ValueError("native schematic review requires pinned KiCad 10.0.6")
        self.toolchain = {
            "kicad_version": version,
            "launcher_sha256": file_hash(self.launcher),
            "cli_sha256": file_hash(self.launcher.parent / "shared/bin/kicad-cli"),
            "render_backend": "ffmpeg-librsvg" if self.use_ffmpeg_renderer else "rsvg-imagemagick",
            "renderer_version": (
                self._run([self.ffmpeg, "-version"]).stdout.splitlines()[0]
                if self.use_ffmpeg_renderer
                else self._run([self.renderer, "--version"]).stdout.strip()
            ),
            "convert_version": (
                "handled by ffmpeg"
                if self.use_ffmpeg_renderer
                else self._run([self.convert, "-version"]).stdout.splitlines()[0]
            ),
            "locked_host_qualification": False,
        }

    def _run(self, args: list[str], config: Path | None = None) -> subprocess.CompletedProcess:
        environment = dict(self.environment)
        if config is not None:
            environment["XDG_CONFIG_HOME"] = str(config.resolve())
        return subprocess.run(
            args, env=environment, capture_output=True, text=True, check=True, timeout=120
        )

    def _compile(self, directory: Path) -> Path:
        scene, composition = compose_with_evidence(self.design, self.resolved)
        schematic = emit(self.design, self.resolved, scene, directory)
        verify_serialized_scene(self.design, scene, schematic)
        write_json(directory / "composition.json", composition)
        # Pivot presentation steps on the verified compiler output; every change is recorded.
        # Net labels get room from pin numbers first, so rails are routed around them, and
        # again after the rails, which may move a part to where its labels have room;
        # rails are drawn before the field text so it is placed around the final wiring.
        presentation = {}
        text, label_moves = clear_label_pin_numbers_text(schematic.read_text())
        schematic.write_text(text)
        presentation["label_moves"] = label_moves
        if getattr(self, "power_symbol_rails", False):
            text, plans = self._plan_rails(schematic, directory)
            schematic.write_text(text)
            presentation["rail_plans"] = plans
        text, label_moves = clear_label_pin_numbers_text(schematic.read_text())
        schematic.write_text(text)
        presentation["label_moves_after_rails"] = label_moves
        text, turns = aim_power_flags_text(schematic.read_text())
        schematic.write_text(text)
        presentation["power_flag_turns"] = turns
        text, moves = tighten_vertical_fields_text(schematic.read_text())
        schematic.write_text(text)
        presentation["vertical_field_moves"] = moves
        if getattr(self, "page_balance", False):
            # Last, once every part, wire and field has its final place.
            text, centring = centre_on_page_text(schematic.read_text())
            schematic.write_text(text)
            presentation["page_centring"] = centring
        write_json(directory / "presentation.json", presentation)
        return schematic

    def _plan_rails(self, schematic: Path, directory: Path) -> tuple[str, list[dict]]:
        """Draw the asserted rails with the fewest power symbols over every plan.

        Each plan applies connect_rail to every rail in one order, keeping or rerouting
        existing rail runs. A plan counts only if every rail is presented, no power symbol
        touches another item, and the protected observer accepts its label form. Rail
        edits keep connectivity, so one KiCad netlist of the compiler output serves all.

        A decoupling capacitor whose wire to its pin detours is first moved beside that
        pin (straighten_decoupling_text), and the drawing is observed again.

        When no plan is valid, each part named in the refusals (for example a connector
        crowded against the page edge) is moved by every grid offset within
        RAIL_PLAN_REACH_MM (farther only if none of those works), the plans are searched
        again, and the best plan over all moves is used.
        """
        base = schematic.read_text()
        nets = sorted({item["net"] for item in self.design.get("power_assertions", [])})
        if not nets:
            return base, []
        with tempfile.TemporaryDirectory(dir=directory, prefix=".rail-plan-") as folder:
            work = Path(folder)
            table, _hashes = write_locked_symbol_table(work, self.resolved, self.power_symbols)
            run_headless(schematic, self.launcher, work, self.symbol_table or table)
            netlist = work / "reports/netlist.xml"
            check = _layout_checker(self.design, schematic.name, netlist)

            def inventory_of(path: Path) -> tuple[list[dict], dict]:
                observed = observe(path, netlist)
                context = rail_context_for_design(self.design, observed)
                for entry in context.values():
                    entry["layout_check"] = check
                return terminal_inventory_for_design(self.design, observed), context

            inventory, context = inventory_of(schematic)
            # Decoupling capacitors whose wire detours are moved beside their pins first.
            straightened = []
            moved_path = work / schematic.name
            for _round in range(4):
                base, move = straighten_decoupling_text(base, inventory, context, check)
                if move is None:
                    break
                straightened.append({"decoupling_move": move})
                moved_path.write_text(base)
                inventory, context = inventory_of(moved_path)
            best, plans = _search_rail_plans(base, nets, inventory, context, check)
            if best is None:
                blockers = sorted(
                    {
                        reference
                        for plan in plans
                        for reference in RAIL_BLOCKER.findall(plan.get("refused", ""))
                        + plan.get("unresolved_references", [])
                    }
                )
                moved_path = work / schematic.name
                found = []
                for dx, dy in RAIL_PLAN_MOVES:
                    if found and abs(dx) + abs(dy) > RAIL_PLAN_REACH_MM:
                        break
                    for reference in blockers:
                        move = {"references": [reference], "dx_mm": dx, "dy_mm": dy}
                        try:
                            moved = move_symbols_text(
                                base,
                                MoveSymbols(operation="move_symbols", **move),
                                inventory,
                            )
                        except ValueError as error:
                            plans.append({"move": move, "refused": str(error)})
                            continue
                        objection = check(moved)
                        if objection is not None:
                            plans.append({"move": move, "refused": objection})
                            continue
                        moved_path.write_text(moved)
                        moved_inventory, moved_context = inventory_of(moved_path)
                        moved_best, moved_plans = _search_rail_plans(
                            moved, nets, moved_inventory, moved_context, check
                        )
                        plans.append({"move": move, "plans": moved_plans})
                        if moved_best is not None:
                            found.append(moved_best)
                # Same preference as unmoved plans: fewest power symbols, then wire length.
                best = min(found, key=lambda item: item[0]) if found else None
        if best is None:
            return base, straightened + plans
        best[2]["chosen"] = True
        return best[1], straightened + plans

    def initial(self, directory: Path) -> Path:
        if self.source is None:
            return self._compile(directory)
        tree = parse(self.source.read_text())
        if tree[0] != "kicad_sch" or children(tree, "sheet"):
            raise ValueError("review supports single-sheet native KiCad schematics only")
        supported = {
            "version",
            "generator",
            "generator_version",
            "uuid",
            "paper",
            "lib_symbols",
            "wire",
            "junction",
            "label",
            "no_connect",
            "symbol",
            "embedded_fonts",
            "title_block",
        }
        if any(isinstance(node, list) and node[0] not in supported for node in tree[1:]):
            raise ValueError("source contains unsupported native schematic constructs")
        project = directory / "project"
        project.mkdir()
        source = project / self.source.name
        source.write_bytes(self.source.read_bytes())
        return source

    def assess(self, schematic: Path, directory: Path) -> SchematicAssessment:
        diagnostics = []
        generated_table, symbol_hashes = write_locked_symbol_table(
            directory, self.resolved, self.power_symbols
        )
        rail_check = "rail_presentation" if self.power_symbol_rails else "visible_rail_continuity"
        checks = {
            "native_tools": "PASS",
            "erc": "FAIL",
            "electrical_equivalence": "FAIL",
            "observed_layout": "FAIL",
            rail_check: "FAIL",
        }
        try:
            run_headless(schematic, self.launcher, directory, self.symbol_table or generated_table)
        except ToolFailure as error:
            checks["native_tools"] = "FAIL"
            diagnostics.append(str(error))
        erc_file = directory / "reports/erc.json"
        erc = json.loads(erc_file.read_text()) if erc_file.is_file() else {}
        sheets = erc.get("sheets", [])
        if sheets and all(not sheet["violations"] for sheet in sheets):
            checks["erc"] = "PASS"
        electrical, layout, observed = {}, {}, {}
        netlist = directory / "reports/netlist.xml"
        # The protected observers inspect the compiler's label form of any power symbols.
        inspected = schematic
        placed_power = power_symbols(parse(schematic.read_text()))
        if placed_power:
            if not self.power_symbol_rails:
                raise ValueError("power symbols require the brief v3 rail policy")
            inspected = directory / "label-view" / schematic.name
            inspected.parent.mkdir()
            inspected.write_text(label_view_text(schematic.read_text()))
        if netlist.is_file():
            try:
                observed = observe(inspected, netlist)
                virtual = {item["reference"] for item in placed_power}
                observed["nets"] = {
                    name: [node for node in nodes if node[0] not in virtual]
                    for name, nodes in observed["nets"].items()
                }
                observed["xml_components"] = {
                    reference: item
                    for reference, item in observed["xml_components"].items()
                    if reference not in virtual
                }
                electrical = compare(self.design, observed, self.resolved)
                checks["electrical_equivalence"] = (
                    "PASS" if electrical["status"] == "pass" else "FAIL"
                )
                diagnostics.extend(electrical.get("diagnostics", []))
                try:
                    layout = check_observed_layout(inspected, observed, self.design)
                    checks["observed_layout"] = "PASS"
                    rail_witnesses = layout.get("observed_power_rail_wire_path_witnesses", [])
                    if self.power_symbol_rails:
                        rail_witnesses = rail_presentation(
                            parse(schematic.read_text()),
                            terminal_inventory_for_design(self.design, observed),
                            sorted({item["net"] for item in self.design["power_assertions"]}),
                        )
                        layout["rail_presentation_witnesses"] = rail_witnesses
                        # The protected observer's wire-only witnesses list every rail joined
                        # by power symbols as "no continuous native wire path". Under brief v3
                        # that contradicts a passing rail_presentation, and the reviewer quoted
                        # it as a defect (review_qualification_v3_2026-11-12_qwen35_256k_run1).
                        layout.pop("observed_power_rail_wire_path_witnesses", None)
                    checks[rail_check] = "FAIL" if rail_witnesses else "PASS"
                    if rail_witnesses and self.power_symbol_rails:
                        diagnostics.append(
                            "asserted power-net wire groups are neither joined nor marked by a "
                            f"matching power symbol: {rail_witnesses}"
                        )
                    elif rail_witnesses:
                        diagnostics.append(
                            "asserted power-net terminals lack a continuous visible wire path: "
                            f"{rail_witnesses}"
                        )
                except InputError as error:
                    diagnostics.append(str(error))
            except (InputError, ValueError, KeyError) as error:
                diagnostics.append(str(error))
        if self.power_symbol_rails:
            collisions = power_symbol_collisions(schematic.read_text())
            checks["power_symbol_clearance"] = "FAIL" if collisions else "PASS"
            if collisions:
                diagnostics.append(f"power symbols touch other drawing items: {collisions}")
        readability = {}
        if getattr(self, "readability_checks", False):
            drawn = parse(schematic.read_text())
            readability["bodyless_unit_clearance"] = wires_through_bodyless_units(drawn)
            # Without an observed netlist the rail terminals are unknown, so the check fails.
            readability["rail_route_detour"] = (
                rail_route_detours(
                    drawn,
                    terminal_inventory_for_design(self.design, observed),
                    sorted({item["net"] for item in self.design["power_assertions"]}),
                )
                if observed
                else [{"reason": "no observed netlist to identify rail terminals"}]
            )
            readability["power_symbol_direction"] = power_symbols_against_convention(drawn)
            if getattr(self, "page_balance", False):
                readability["page_balance"] = page_balance_witnesses(drawn)
            messages = {
                "bodyless_unit_clearance": "wires run through a bodyless unit's pin-name column",
                "rail_route_detour": "rail wiring detours beyond 1.15x and 7.62 mm of the "
                "shortest route joining its terminals",
                "power_symbol_direction": "power symbols point against convention "
                "(supply arrow down or ground glyph up)",
                "page_balance": "the drawing is outside the usable frame or more than 0.25 of "
                "the half-frame from the page centre",
            }
            for name, witnesses in readability.items():
                checks[name] = "FAIL" if witnesses else "PASS"
                if witnesses:
                    diagnostics.append(f"{messages[name]}: {witnesses}")
        # Field checks concern component fields; power-symbol text is checked above.
        tree = parse(inspected.read_text())
        field_collisions = field_collision_witnesses(tree)
        checks["field_separation"] = "FAIL" if field_collisions else "PASS"
        if field_collisions:
            diagnostics.append(f"overlapping reference/value fields: {field_collisions}")
        locality = measure_field_locality(tree, self.maximum_field_distance_mm)
        checks["field_locality"] = "FAIL" if locality["witnesses"] else "PASS"
        if locality["witnesses"]:
            diagnostics.append(
                f"reference/value fields too far from their symbols: {locality['witnesses']}"
            )
        association = measure_field_association(tree)
        checks["field_owner_association"] = "FAIL" if association["witnesses"] else "PASS"
        if association["witnesses"]:
            diagnostics.append(
                "reference/value fields are substantially closer to another symbol: "
                f"{association['witnesses']}"
            )
        fields = []
        for symbol in children(tree, "symbol"):
            props = {p[1]: p for p in children(symbol, "property")}
            for name in ("Reference", "Value"):
                prop = props.get(name)
                if prop is not None:
                    at = one(prop, "at")
                    fields.append(
                        {
                            "reference": props["Reference"][2],
                            "unit": int(one(symbol, "unit")[1]),
                            "field": name,
                            "text": prop[2],
                            "x_mm": float(at[1]),
                            "y_mm": float(at[2]),
                            "angle": int(float(at[3])),
                        }
                    )
        images = self._render(schematic, directory)
        terminal_inventory = terminal_inventory_for_design(self.design, observed)
        report = {
            "checks": checks,
            "diagnostics": diagnostics,
            "erc": erc,
            "electrical": electrical,
            "layout": layout,
            "field_inventory": fields,
            "field_collision_witnesses": field_collisions,
            "field_locality": locality,
            "field_owner_association": association,
            "readability_witnesses": readability,
            "terminal_inventory": terminal_inventory,
            "intended_circuit": self.design,
            "toolchain": self.toolchain,
            "symbol_table_sha256": file_hash(self.symbol_table or generated_table),
            "locked_symbol_library_sha256": symbol_hashes,
            "schematic_sha256": file_hash(schematic),
            "image_sha256": {p.name: file_hash(p) for p in images},
        }
        write_json(directory / "assessment.json", report)
        return SchematicAssessment(schematic, images, report)

    def _render(self, schematic: Path, directory: Path) -> list[Path]:
        renders = directory / "review-images"
        renders.mkdir()
        sheet_svg = directory / "renders/schematic" / f"{schematic.stem}.svg"
        if not sheet_svg.is_file():
            raise RuntimeError("no native schematic SVG available for visual review")
        full_page = renders / "page.png"
        if self.use_ffmpeg_renderer:
            self._render_page_ffmpeg(sheet_svg, full_page)
            self._run(
                [
                    str(self.launcher),
                    "kicad-cli",
                    "sch",
                    "export",
                    "svg",
                    "--exclude-drawing-sheet",
                    "--no-background-color",
                    "--output",
                    str(renders),
                    str(schematic),
                ],
                config=directory / "config",
            )
            drawing_svg = renders / f"{schematic.stem}.svg"
            detail = renders / "drawing.png"
            self._render_detail_ffmpeg(drawing_svg, detail)
            return [full_page, detail]

        self._run(
            [
                self.renderer,
                "--background-color=white",
                "--width=1800",
                f"--output={full_page}",
                str(sheet_svg),
            ]
        )
        self._run(
            [
                str(self.launcher),
                "kicad-cli",
                "sch",
                "export",
                "svg",
                "--exclude-drawing-sheet",
                "--no-background-color",
                "--output",
                str(renders),
                str(schematic),
            ],
            config=directory / "config",
        )
        drawing_svg = renders / f"{schematic.stem}.svg"
        detail = renders / "drawing.png"
        self._run(
            [
                self.renderer,
                "--background-color=white",
                "--width=3600",
                f"--output={detail}",
                str(drawing_svg),
            ]
        )
        self._run(
            [
                self.convert,
                str(detail),
                "-trim",
                "+repage",
                "-bordercolor",
                "white",
                "-border",
                "30",
                "-resize",
                "1600x1200",
                str(detail),
            ]
        )
        return [full_page, detail]

    def _render_page_ffmpeg(self, svg: Path, output: Path) -> None:
        dimensions = self._run(
            [
                self.ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=s=x:p=0",
                str(svg),
            ]
        ).stdout.strip()
        try:
            source_width, source_height = map(int, dimensions.split("x"))
        except ValueError as error:
            raise RuntimeError(f"could not read SVG dimensions: {dimensions!r}") from error
        width = 1800
        height = round(width * source_height / source_width)
        graph = (
            f"[0:v]scale={width}:{height}:flags=lanczos[fg];"
            f"color=c=white:s={width}x{height}[bg];"
            "[bg][fg]overlay=0:0,format=rgb24[out]"
        )
        self._run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(svg),
                "-filter_complex",
                graph,
                "-map",
                "[out]",
                "-frames:v",
                "1",
                "-y",
                str(output),
            ]
        )

    def _render_detail_ffmpeg(self, svg: Path, output: Path) -> None:
        bbox = self._run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-i",
                str(svg),
                "-vf",
                "bbox",
                "-frames:v",
                "1",
                "-f",
                "null",
                "-",
            ]
        ).stderr
        width, height, x, y = parse_ffmpeg_bbox(bbox)
        graph = (
            f"[0:v]crop={width}:{height}:{x}:{y},"
            "scale=1540:1140:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
            "color=c=white:s=1600x1200[bg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=rgb24[out]"
        )
        self._run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(svg),
                "-filter_complex",
                graph,
                "-map",
                "[out]",
                "-frames:v",
                "1",
                "-y",
                str(output),
            ]
        )

    def apply(self, schematic: Path, directory: Path, actions: list[SchematicAction]) -> Path:
        if directory.exists():
            raise ValueError("candidate output already exists")
        design = getattr(self, "design", {})
        asserted_nets = {item["net"] for item in design.get("power_assertions", [])}
        if not getattr(self, "power_symbol_rails", False) and any(
            isinstance(action, UsePowerSymbols) for action in actions
        ):
            raise ValueError(
                "use_power_symbols requires the brief v3 rail policy; this review requires "
                "visible rail wiring"
            )
        wire_actions = [
            action
            for action in actions
            if isinstance(action, AddWirePath | ConnectRail | MoveSymbols | UsePowerSymbols)
        ]
        if any(
            not isinstance(action, MoveSymbols) and action.net not in asserted_nets
            for action in wire_actions
        ):
            raise ValueError(
                "add_wire_path, connect_rail and use_power_symbols are limited to explicitly "
                f"asserted power nets; valid nets are {sorted(asserted_nets)}"
            )
        inventory, rail_context = None, None
        if wire_actions:
            netlist = schematic.parent.parent / "reports/netlist.xml"
            if not netlist.is_file():
                raise ValueError("wire and symbol-move edits require the current assessed netlist")
            observed = observe(schematic, netlist)
            inventory = terminal_inventory_for_design(design, observed)
            rail_context = (
                rail_context_for_design(design, observed)
                if getattr(self, "power_symbol_rails", False)
                else None
            )

            layout_check = _layout_checker(design, schematic.name, netlist)
            for entry in (rail_context or {}).values():
                entry["layout_check"] = layout_check
            for action in wire_actions:
                if isinstance(action, AddWirePath):
                    resolve_wire_path_points(action, inventory)
            if any(isinstance(action, MoveSymbols) for action in wire_actions):
                listed = {(item["reference"], item["pin"]) for item in inventory}
                inventory += [
                    {
                        "net": None,
                        "reference": reference,
                        "pin": pin,
                        "x_mm": point[0] / 1_000_000,
                        "y_mm": point[1] / 1_000_000,
                    }
                    for (reference, pin), point in sorted(observed["pin_positions"].items())
                    if (reference, pin) not in listed
                ]
        regenerations = [i for i, a in enumerate(actions) if isinstance(a, RegenerateSchematic)]
        if regenerations and regenerations != [0]:
            raise ValueError("regeneration may occur once, as the first action")
        if regenerations and wire_actions:
            raise ValueError(
                "regeneration and wire-path edits must use separate reviewed revisions"
            )
        if wire_actions and any(isinstance(action, TranslateSheet) for action in actions):
            raise ValueError("wire-path edits and sheet translation must use separate revisions")
        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory.parent, prefix=".review-edit-") as tmp:
            stage = Path(tmp) / "candidate"
            stage.mkdir()
            if regenerations:
                target = self._compile(stage)
                actions = actions[1:]
            else:
                project = stage / "project"
                project.mkdir()
                target = project / schematic.name
                target.write_bytes(schematic.read_bytes())
            target.write_text(
                edit_schematic_text(target.read_text(), actions, inventory, rail_context)
            )
            relative = target.relative_to(stage)
            stage.rename(directory)
            return directory / relative
