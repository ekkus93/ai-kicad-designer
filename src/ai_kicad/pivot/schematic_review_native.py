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
from ai_kicad.m2_geometry import Reservation, point_on_segment, segment_is_admissible
from ai_kicad.m2_fragments_types import Point
from ai_kicad.m2_route_core import _connect
from ai_kicad.m2_transform import transform_library_point
from ai_kicad.m2a_core import _nm
from ai_kicad.m2a_constants import PITCH
from ai_kicad.sexpr import children, one, parse, quote

from .schematic_review import (
    MoveField,
    AddWirePath,
    RegenerateSchematic,
    SchematicAction,
    SchematicAssessment,
    TranslateSheet,
    WirePoint,
    file_hash,
    write_json,
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
            route = route_around_existing_wires(text, route)
            existing = {
                frozenset(
                    (float(point[1]), float(point[2])) for point in children(one(node, "pts"), "xy")
                )
                for _, _, node in forms
                if node[0] == "wire"
            }
            existing_segments = [
                (
                    (round(float(first[1]) * 1_000_000), round(float(first[2]) * 1_000_000)),
                    (round(float(second[1]) * 1_000_000), round(float(second[2]) * 1_000_000)),
                )
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
                        (round(point.x_mm * 1_000_000), round(point.y_mm * 1_000_000)),
                        first,
                        second,
                    )
                    for first, second in existing_segments
                )
            }
            existing_junctions = {
                (
                    round(float(one(node, "at")[1]) * 1_000_000),
                    round(float(one(node, "at")[2]) * 1_000_000),
                )
                for _, _, node in forms
                if node[0] == "junction"
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
            text = text[:insert] + "".join(wires) + "".join(junctions) + "\n" + text[insert:]
        elif isinstance(action, TranslateSheet):
            if action.dx_mm == 0 and action.dy_mm == 0:
                raise ValueError("translate_sheet made no change; choose nonzero movement")
            for start, end, node in forms:
                if node[0] not in {"symbol", "wire", "junction", "label", "no_connect", "text"}:
                    continue

                def translate(match: re.Match[str]) -> str:
                    if match[1] is None:
                        return match[0]
                    return (
                        match[1]
                        + f"{float(match[2]) + action.dx_mm:.6f} "
                        + f"{float(match[3]) + action.dy_mm:.6f}"
                    )

                block = re.sub(
                    r'"(?:\\.|[^"\\])*"|(\((?:at|xy)\s+)([-+0-9.eE]+)\s+([-+0-9.eE]+)',
                    translate,
                    text[start:end],
                )
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


def route_around_existing_wires(text: str, requested: list[WirePoint]) -> list[WirePoint]:
    """Plan requested legs around wires, symbol bodies and visible symbol fields."""
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
    library_symbols = {item[1]: item for item in children(one(tree, "lib_symbols"), "symbol")}
    wires = []
    for index, wire in enumerate(children(tree, "wire")):
        coordinates = [
            (round(float(point[1]) * nanometers), round(float(point[2]) * nanometers))
            for point in children(one(wire, "pts"), "xy")
        ]
        for first, second in zip(coordinates, coordinates[1:]):
            wires.append((f"existing-wire-{index}", first, second))

    symbol_boxes = []
    text_boxes = []
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
        for body in children(library, "symbol"):
            shapes = [(shape, "rectangle") for shape in children(body, "rectangle")]
            shapes.extend((shape, "polyline") for shape in children(body, "polyline"))
            for shape, kind in shapes:
                if kind == "rectangle":
                    corners = [one(shape, "start"), one(shape, "end")]
                else:
                    corners = children(one(shape, "pts"), "xy")
                transformed = []
                for corner in corners:
                    dx, dy = transform_library_point(_nm(corner[1]), _nm(corner[2]), angle, mirror)
                    transformed.append((origin[0] + dx, origin[1] + dy))
                symbol_boxes.append(
                    (
                        reference,
                        (
                            min(point[0] for point in transformed) - 250_000,
                            min(point[1] for point in transformed) - 250_000,
                            max(point[0] for point in transformed) + 250_000,
                            max(point[1] for point in transformed) + 250_000,
                        ),
                    )
                )

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
            Reservation(f"body-{index}", "exclusive", reference, "symbol_body", bounds)
            for index, (reference, bounds) in enumerate(symbol_boxes)
            if not any(
                bounds[0] <= endpoint[0] <= bounds[2] and bounds[1] <= endpoint[1] <= bounds[3]
                for endpoint in (start, finish)
            )
        )
        text_obstacles = tuple(
            Reservation(f"text-{index}", "exclusive", reference, "symbol_text", bounds)
            for index, (reference, bounds) in enumerate(text_boxes)
            if not any(
                bounds[0] <= endpoint[0] <= bounds[2] and bounds[1] <= endpoint[1] <= bounds[3]
                for endpoint in (start, finish)
            )
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
            if not inside(candidate) or not segment_is_admissible(
                point,
                candidate,
                obstacles,
                (),
                net="review-route",
                owner="new-review-wire",
            ):
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


def write_locked_symbol_table(directory: Path, resolved: dict) -> tuple[Path, dict]:
    """Register the exact resolved symbol definitions in an isolated KiCad configuration."""
    libraries = {}
    for library_id, asset in sorted(resolved.items()):
        library, name = library_id.split(":", 1)
        libraries.setdefault(library, []).append(
            asset.definition.replace(
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
    ):
        self.resolved = assets()
        self.design = validate(design, self.resolved)
        self.launcher = launcher.resolve()
        self.source = source.resolve() if source else None
        self.symbol_table = symbol_table
        self.maximum_field_distance_mm = maximum_field_distance_mm
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
        generated_table, symbol_hashes = write_locked_symbol_table(directory, self.resolved)
        checks = {
            "native_tools": "PASS",
            "erc": "FAIL",
            "electrical_equivalence": "FAIL",
            "observed_layout": "FAIL",
            "visible_rail_continuity": "FAIL",
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
        if netlist.is_file():
            try:
                observed = observe(schematic, netlist)
                electrical = compare(self.design, observed, self.resolved)
                checks["electrical_equivalence"] = (
                    "PASS" if electrical["status"] == "pass" else "FAIL"
                )
                diagnostics.extend(electrical.get("diagnostics", []))
                try:
                    layout = check_observed_layout(schematic, observed, self.design)
                    checks["observed_layout"] = "PASS"
                    rail_witnesses = layout.get("observed_power_rail_wire_path_witnesses", [])
                    checks["visible_rail_continuity"] = "FAIL" if rail_witnesses else "PASS"
                    if rail_witnesses:
                        diagnostics.append(
                            "asserted power-net terminals lack a continuous visible wire path: "
                            f"{rail_witnesses}"
                        )
                except InputError as error:
                    diagnostics.append(str(error))
            except (InputError, ValueError, KeyError) as error:
                diagnostics.append(str(error))
        tree = parse(schematic.read_text())
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
        wire_actions = [action for action in actions if isinstance(action, AddWirePath)]
        if any(action.net not in asserted_nets for action in wire_actions):
            raise ValueError(
                "add_wire_path is limited to explicitly asserted power nets; "
                f"valid nets are {sorted(asserted_nets)}"
            )
        if wire_actions:
            netlist = schematic.parent.parent / "reports/netlist.xml"
            if not netlist.is_file():
                raise ValueError("add_wire_path requires the current assessed netlist")
            observed = observe(schematic, netlist)
            inventory = terminal_inventory_for_design(design, observed)
            for action in wire_actions:
                resolve_wire_path_points(action, inventory)
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
            inventory = terminal_inventory_for_design(design, observed) if wire_actions else None
            target.write_text(edit_schematic_text(target.read_text(), actions, inventory))
            relative = target.relative_to(stage)
            stage.rename(directory)
            return directory / relative
