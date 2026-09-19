"""Exact nanometer divider construction and KiCad 10 schematic emission."""

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from .assets import Symbol
from .sexpr import quote


class Infeasible(RuntimeError):
    """The fixed M1a envelope cannot fit the requested sheet."""


@dataclass(frozen=True)
class Layout:
    positions: dict[str, tuple[int, int]]
    wires: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    labels: tuple[tuple[str, int, int], ...]
    junction: tuple[int, int]


def layout_schematic(symbols: dict[str, Symbol]) -> Layout:
    """Derive divider spacing from the actual library pin envelopes."""
    resistor = symbols["sym.r"]
    connector = symbols["sym.j3"]
    rp = {number: (x, y) for number, x, y in resistor.pins}
    jp = {number: (x, y) for number, x, y in connector.pins}
    pitch = 1_270_000
    # The resistor chain is vertical; the connector sits to its left.
    x_r = 101_600_000
    y_upper = 71_120_000
    y_lower = y_upper + 24 * pitch
    x_j = x_r - 32 * pitch
    y_j = (y_upper + y_lower) // 2
    positions = {"r.upper": (x_r, y_upper), "r.lower": (x_r, y_lower), "j.io": (x_j, y_j)}

    def endpoint(component: str, pin: str) -> tuple[int, int]:
        x, y = positions[component]
        px, py = (jp if component == "j.io" else rp)[pin]
        return x + px, y - py

    top = endpoint("r.upper", "1")
    tap_upper = endpoint("r.upper", "2")
    tap_lower = endpoint("r.lower", "1")
    bottom = endpoint("r.lower", "2")
    j1, j2, j3 = (endpoint("j.io", pin) for pin in ("1", "2", "3"))
    tap = (x_r, y_j)
    vin_y = top[1] - 8 * pitch
    return_y = bottom[1] + 8 * pitch
    vin_x = j1[0] - 4 * pitch
    return_x = j3[0] - 8 * pitch
    wires = (
        (j1, (vin_x, j1[1])),
        ((vin_x, j1[1]), (vin_x, vin_y)),
        ((vin_x, vin_y), (x_r, vin_y)),
        ((x_r, vin_y), top),
        (tap_upper, tap),
        (tap, tap_lower),
        (j2, tap),
        (j3, (return_x, j3[1])),
        ((return_x, j3[1]), (return_x, return_y)),
        ((return_x, return_y), (x_r, return_y)),
        ((x_r, return_y), bottom),
    )
    for start, end in wires:
        for x, y in (start, end):
            if not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000):
                raise Infeasible("divider wiring exceeds the A4 drafting margins")
    labels = (("VIN", vin_x, vin_y), ("SENSE", j2[0] + 10 * pitch, j2[1]), ("0V", x_r, return_y))
    return Layout(positions, wires, labels, tap)


def _uuid(design_id: str, kind: str, key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{design_id}/{kind}/{key}"))


def _mm(nm: int) -> str:
    from decimal import Decimal

    value = format(Decimal(nm) / 1_000_000, "f")
    return value.rstrip("0").rstrip(".") if "." in value else value


def emit_schematic(design: dict, symbols: dict[str, Symbol], layout: Layout, out: Path) -> Path:
    project = out / "project"
    project.mkdir(parents=True, exist_ok=True)
    name = design["design"]["name"]
    design_id = design["design"]["id"]
    root_uuid = _uuid(design_id, "sheet", "root")
    lines = [
        '(kicad_sch (version 20250114) (generator "ai_kicad") (generator_version "0.1.0")',
        f'  (uuid {quote(root_uuid)}) (paper "A4")',
        "  (lib_symbols",
    ]
    for asset_id in sorted(symbols):
        symbol = symbols[asset_id]
        short = symbol.library_id.split(":", 1)[1]
        import re

        definition = re.sub(
            r"\(symbol\s+" + re.escape(quote(short)),
            f"(symbol {quote(symbol.library_id)}",
            symbol.definition,
            count=1,
        )
        lines.append(definition)
    lines.append("  )")
    for index, (start, end) in enumerate(layout.wires):
        lines.append(
            f"  (wire (pts (xy {_mm(start[0])} {_mm(start[1])}) "
            f"(xy {_mm(end[0])} {_mm(end[1])})) (stroke (width 0) (type default)) "
            f"(uuid {quote(_uuid(design_id, 'wire', str(index)))}) )"
        )
    jx, jy = layout.junction
    lines.append(
        f"  (junction (at {_mm(jx)} {_mm(jy)}) (diameter 0) (color 0 0 0 0) (uuid {quote(_uuid(design_id, 'junction', 'tap'))}))"
    )
    for label, x, y in layout.labels:
        lines.append(
            f"  (label {quote(label)} (at {_mm(x)} {_mm(y)} 0) "
            f"(effects (font (size 1.27 1.27)) (justify left bottom)) "
            f"(uuid {quote(_uuid(design_id, 'label', label))}))"
        )
    component_by_id = {component["id"]: component for component in design["logical"]["components"]}
    for use in sorted(design["schematic"]["symbols"], key=lambda item: item["id"]):
        component = component_by_id[use["component"]]
        x, y = layout.positions[component["id"]]
        symbol = symbols[use["asset"]]
        ref = component["refdes"]
        value = "10k" if component["kind"] == "resistor" else symbol.library_id.split(":")[1]
        lines.append(
            f"  (symbol (lib_id {quote(symbol.library_id)}) (at {_mm(x)} {_mm(y)} 0) "
            f"(unit 1) (in_bom yes) (on_board yes) (dnp no) "
            f"(uuid {quote(_uuid(design_id, 'symbol', use['id']))})"
        )
        property_x = x + (7_620_000 if component["kind"] == "resistor" else 0)
        property_y = y - (2_540_000 if component["kind"] == "resistor" else 7_620_000)
        lines.append(
            f'    (property "Reference" {quote(ref)} (at {_mm(property_x)} {_mm(property_y)} 0) (effects (font (size 1.27 1.27))))'
        )
        lines.append(
            f'    (property "Value" {quote(value)} (at {_mm(property_x)} {_mm(property_y + 2_540_000)} 0) (effects (font (size 1.27 1.27))))'
        )
        for number in sorted(use["pin_map"]):
            lines.append(
                f"    (pin {quote(number)} (uuid {quote(_uuid(design_id, 'pin', use['id'] + ':' + number))}))"
            )
        lines.append(
            f"    (instances (project {quote(name)} (path {quote('/' + root_uuid)} (reference {quote(ref)}) (unit 1)))) )"
        )
    lines.append("  (embedded_fonts no)")
    lines.append(")")
    schematic = project / f"{name}.kicad_sch"
    schematic.write_text("\n".join(lines) + "\n")
    (project / f"{name}.kicad_pro").write_text(
        json.dumps({"meta": {"filename": f"{name}.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    return schematic
