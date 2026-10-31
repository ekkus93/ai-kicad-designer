"""Native KiCad adapter for image review of a pinned M2b circuit."""

from __future__ import annotations

import json
import heapq
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
from .field_layout import tighten_vertical_fields_text
from .power_symbols import (
    label_view_text,
    remove_rail_runs_text,
    use_power_symbols_text,
    power_symbol_collisions,
    power_symbol_definitions,
    power_symbols,
    rail_presentation,
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


def _connect_point_groups(
    text: str,
    points: list[Point],
    keepouts: list[tuple[int, int, int, int]],
    description: str,
    partial: bool = False,
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
    """
    terminals = [item for item in terminal_inventory if item["net"] == net]
    if len(terminals) < 2:
        raise ValueError(f"connect_rail requires at least two observed terminals on {net}")
    points = list(
        dict.fromkeys(
            (round(item["x_mm"] * 1_000_000), round(item["y_mm"] * 1_000_000)) for item in terminals
        )
    )
    if replace_existing:
        rail = rail or {}
        text = remove_rail_runs_text(
            text, net, terminal_inventory, rail.get("flags", []), rail.get("local_pairs", [])
        )
    elif len(_point_groups(parse(text), points)) == 1:
        raise ValueError(f"connect_rail made no change; {net} terminals are already wire-joined")
    keepouts = _terminal_keepouts([item for item in terminal_inventory if item["net"] != net])
    if power_symbols_allowed:
        wired = _connect_point_groups(text, points, keepouts, f"{net} wire", partial=True)
        if len(_point_groups(parse(wired), points)) == 1:
            return wired
        rail = rail or {}
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
            continue
        removed_wires |= wire_indexes
        removed_points |= attached_junctions
        reconnect.append(sorted({(x + dx, y + dy) for x, y in moving} | fixed | attached_labels))

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


def _drawn_boxes(tree: list) -> tuple[list[tuple[str, Box]], list[tuple[str, Box]]]:
    """Padded symbol body/pin-stub boxes and visible field/label text boxes of a sheet."""
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

    return symbol_boxes, text_boxes


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
    ):
        self.resolved = assets()
        self.design = validate(design, self.resolved)
        self.launcher = launcher.resolve()
        self.source = source.resolve() if source else None
        self.symbol_table = symbol_table
        self.maximum_field_distance_mm = maximum_field_distance_mm
        # Brief v3: a rail may be presented by wires or by matching global power symbols.
        self.power_symbol_rails = power_symbol_rails
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
        # Pivot presentation step on the verified compiler output; every move is recorded.
        text, moves = tighten_vertical_fields_text(schematic.read_text())
        schematic.write_text(text)
        write_json(directory / "presentation.json", {"vertical_field_moves": moves})
        return schematic

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

            def layout_check(candidate: str) -> str | None:
                """The protected observer's objection to a candidate's label form."""
                with tempfile.TemporaryDirectory(prefix=".label-view-") as folder:
                    view = Path(folder) / schematic.name
                    view.write_text(label_view_text(candidate))
                    try:
                        check_observed_layout(view, observe(view, netlist), design)
                    except (InputError, ValueError, KeyError) as error:
                        return str(error)
                return None

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
