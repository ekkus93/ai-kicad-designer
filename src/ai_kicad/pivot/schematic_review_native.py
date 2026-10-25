"""Native KiCad adapter for image review of a pinned M2b circuit."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from ai_kicad.ir import InputError
from ai_kicad.kicad import ToolFailure, run_headless
from ai_kicad.m2_text_layout import overlaps, property_page_angle, text_extents
from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a_artifacts import emit, observe, verify_serialized_scene
from ai_kicad.m2b import assets, check_observed_layout, compare, validate
from ai_kicad.sexpr import children, one, parse, quote

from .schematic_review import (
    MoveField,
    RegenerateSchematic,
    SchematicAction,
    SchematicAssessment,
    TranslateSheet,
    file_hash,
    write_json,
)
from .schematic_fields import measure_field_locality


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


def edit_schematic_text(text: str, actions: list[SchematicAction]) -> str:
    """Allow only field placement and whole-sheet translation; no library or net edits."""
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
            start, end, _ = matches[0]
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
        elif isinstance(action, TranslateSheet):
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
        if not self.renderer or not self.convert:
            raise ValueError("rsvg-convert and ImageMagick convert are required")
        version = self._run([str(self.launcher), "kicad-cli", "version"]).stdout.strip()
        if version != "10.0.6":
            raise ValueError("native schematic review requires pinned KiCad 10.0.6")
        self.toolchain = {
            "kicad_version": version,
            "launcher_sha256": file_hash(self.launcher),
            "cli_sha256": file_hash(self.launcher.parent / "shared/bin/kicad-cli"),
            "renderer_version": self._run([self.renderer, "--version"]).stdout.strip(),
            "convert_version": self._run([self.convert, "-version"]).stdout.splitlines()[0],
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
        electrical, layout = {}, {}
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
        report = {
            "checks": checks,
            "diagnostics": diagnostics,
            "erc": erc,
            "electrical": electrical,
            "layout": layout,
            "field_inventory": fields,
            "field_collision_witnesses": field_collisions,
            "field_locality": locality,
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

    def apply(self, schematic: Path, directory: Path, actions: list[SchematicAction]) -> Path:
        if directory.exists():
            raise ValueError("candidate output already exists")
        regenerations = [i for i, a in enumerate(actions) if isinstance(a, RegenerateSchematic)]
        if regenerations and regenerations != [0]:
            raise ValueError("regeneration may occur once, as the first action")
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
            target.write_text(edit_schematic_text(target.read_text(), actions))
            relative = target.relative_to(stage)
            stage.rename(directory)
            return directory / relative
