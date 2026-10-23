"""Bounded post-POC requirements, catalog and engineering calculations."""

from __future__ import annotations

import csv
import hashlib
import math
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from .evidence import StrictModel
from ai_kicad.sexpr import children, parse


class RequirementError(ValueError):
    pass


class CircuitRequirements(StrictModel):
    function: str = Field(min_length=1)
    supply_nominal_v: float = Field(gt=0)
    supply_min_v: float = Field(gt=0)
    supply_max_v: float = Field(gt=0)
    output_load_ma: float = Field(ge=0)
    environment: str = Field(min_length=1)
    safety_class: str = Field(min_length=1)
    assumptions: list[str]
    unresolved: list[str]

    @model_validator(mode="after")
    def valid_range(self) -> CircuitRequirements:
        if not self.supply_min_v <= self.supply_nominal_v <= self.supply_max_v:
            raise ValueError("nominal supply must be inside the stated range")
        if self.safety_class != "benign-low-voltage" and self.unresolved:
            raise ValueError("safety-critical requirements cannot retain unresolved values")
        return self


class SupplierMapping(StrictModel):
    supplier: str = Field(min_length=1)
    supplier_part_number: str = Field(min_length=1)
    product_url: str = Field(pattern=r"^https://")
    checked_on: str = Field(pattern=r"^20\d{2}-\d{2}-\d{2}$")

    @field_validator("checked_on")
    @classmethod
    def valid_check_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class CatalogPart(StrictModel):
    mpn: str
    manufacturer: str = Field(min_length=1)
    category: str
    package: str
    footprint: str
    pin_map: dict[str, str]
    voltage_min_v: float | None = None
    voltage_max_v: float | None = None
    power_rating_w: float | None = None
    resistance_ohm: float | None = Field(default=None, gt=0)
    capacitance_f: float | None = Field(default=None, gt=0)
    tolerance_percent: float | None = Field(default=None, gt=0, le=100)
    dielectric: str | None = None
    polarity: str | None = None
    approved: bool
    datasheet_url: str
    datasheet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    supplier_mappings: list[SupplierMapping] = Field(default_factory=list)

    @model_validator(mode="after")
    def approved_supplier_identity(self) -> CatalogPart:
        if self.approved and not self.supplier_mappings:
            raise ValueError("approved catalog parts require a dated supplier mapping")
        if len({mapping.supplier for mapping in self.supplier_mappings}) != len(
            self.supplier_mappings
        ):
            raise ValueError("duplicate supplier mapping")
        return self


class AssemblyPlacement(StrictModel):
    reference: str = Field(pattern=r"^[A-Z]+[0-9]+$")
    x_mm: float
    y_mm: float
    side: str = Field(pattern=r"^(Top|Bottom)$")
    rotation_deg: float = Field(ge=0, lt=360)
    footprint: str = Field(min_length=1)


def select_part(
    catalog: list[CatalogPart],
    *,
    category: str,
    package: str,
    minimum_voltage_v: float = 0,
    required_pin_map: dict[str, str] | None = None,
    minimum_power_w: float = 0,
    required_resistance_ohm: float | None = None,
    required_capacitance_f: float | None = None,
    required_dielectric: str | None = None,
    required_polarity: str | None = None,
) -> CatalogPart:
    matches = [
        part
        for part in catalog
        if part.approved
        and part.category == category
        and part.package == package
        and (
            minimum_voltage_v <= 0
            or part.voltage_max_v is not None
            and part.voltage_max_v >= minimum_voltage_v
        )
        and (
            minimum_power_w <= 0
            or part.power_rating_w is not None
            and part.power_rating_w >= minimum_power_w
        )
        and (required_resistance_ohm is None or part.resistance_ohm == required_resistance_ohm)
        and (required_capacitance_f is None or part.capacitance_f == required_capacitance_f)
        and (required_dielectric is None or part.dielectric == required_dielectric)
        and (required_polarity is None or part.polarity == required_polarity)
        and (required_pin_map is None or part.pin_map == required_pin_map)
    ]
    if len(matches) != 1:
        raise RequirementError(f"selection is {'ambiguous' if matches else 'unsupported'}")
    return matches[0]


def astable_555(ra_ohm: float, rb_ohm: float, capacitance_f: float) -> dict:
    if min(ra_ohm, rb_ohm, capacitance_f) <= 0:
        raise RequirementError("555 timing values must be positive")
    high = math.log(2) * (ra_ohm + rb_ohm) * capacitance_f
    low = math.log(2) * rb_ohm * capacitance_f
    return {
        "high_s": high,
        "low_s": low,
        "period_s": high + low,
        "frequency_hz": 1 / (high + low),
        "duty_cycle": high / (high + low),
    }


def led_resistor(v_supply: float, v_forward: float, resistance_ohm: float, rating_w: float) -> dict:
    if resistance_ohm <= 0 or rating_w <= 0 or v_supply <= v_forward:
        raise RequirementError("invalid LED current-limit inputs")
    current = (v_supply - v_forward) / resistance_ohm
    power = current * current * resistance_ohm
    return {
        "current_a": current,
        "resistor_power_w": power,
        "rating_w": rating_w,
        "margin_ratio": rating_w / power,
        "status": "PASS" if rating_w >= power * 2 else "FAIL",
    }


def resistor_power(current_a: float, resistance_ohm: float, rating_w: float) -> dict:
    if current_a < 0 or resistance_ohm <= 0 or rating_w <= 0:
        raise RequirementError("invalid resistor power inputs")
    power = current_a * current_a * resistance_ohm
    return {
        "power_w": power,
        "rating_w": rating_w,
        "margin_ratio": rating_w / power if power else float("inf"),
        "status": "PASS" if rating_w >= power * 2 else "FAIL",
    }


def regulator_thermal(
    input_v: float, output_v: float, load_a: float, theta_ja_c_per_w: float, ambient_c: float
) -> dict:
    if input_v < output_v or min(load_a, theta_ja_c_per_w) <= 0:
        raise RequirementError("invalid linear regulator thermal inputs")
    power = (input_v - output_v) * load_a
    junction = ambient_c + theta_ja_c_per_w * power
    return {
        "dissipation_w": power,
        "estimated_junction_c": junction,
        "status": "REQUIRES_PART_LIMIT_CHECK",
        "limitation": "Use the exact package thermal resistance and derating curve from its datasheet.",
    }


def decoupling_capacitance(load_step_a: float, response_s: float, allowed_ripple_v: float) -> dict:
    if min(load_step_a, response_s, allowed_ripple_v) <= 0:
        raise RequirementError("invalid decoupling inputs")
    return {
        "minimum_ideal_capacitance_f": load_step_a * response_s / allowed_ripple_v,
        "status": "SCREENING_ESTIMATE",
        "limitation": "ESR, ESL, regulator loop stability and placement inductance require separate review.",
    }


def export_through_hole_assembly(board_report: dict, bom: dict, destination: Path) -> dict:
    """Export BOM-only assembly data; through-hole centroid is explicitly unsupported."""
    destination.mkdir(parents=True, exist_ok=False)
    items = bom["items"]
    references = set(board_report["component_references"])
    if references != {item["refdes"] for item in items}:
        raise RequirementError("BOM and board references disagree")
    with (destination / "bom.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["Reference", "Quantity", "MPN", "Footprint"])
        writer.writeheader()
        for item in sorted(items, key=lambda value: value["refdes"]):
            writer.writerow(
                {
                    "Reference": item["refdes"],
                    "Quantity": item["quantity"],
                    "MPN": item["mpn"],
                    "Footprint": item["footprint"],
                }
            )
    return {
        "status": "PARTIAL",
        "bom": "bom.csv",
        "centroid": "UNSUPPORTED",
        "paste": "UNSUPPORTED",
        "assembly_drawing": "previews/board-top.png",
        "reason": "Reference design is entirely through-hole; SMT PnP and paste outputs do not apply.",
    }


def export_smt_assembly(
    placements: list[AssemblyPlacement],
    bom_rows: list[dict],
    destination: Path,
) -> dict:
    """Write PCBWay column-compatible SMT BOM and pick-and-place CSV files."""
    references = [placement.reference for placement in placements]
    if len(references) != len(set(references)):
        raise RequirementError("duplicate assembly placement")
    bom_references = [row.get("reference") for row in bom_rows]
    if len(bom_references) != len(set(bom_references)):
        raise RequirementError("duplicate SMT BOM reference")
    bom_by_reference = {row["reference"]: row for row in bom_rows}
    if set(references) != set(bom_by_reference):
        raise RequirementError("SMT BOM and placement references disagree")
    grouped_bom = {}
    for placement in placements:
        row = bom_by_reference[placement.reference]
        if (
            type(row.get("quantity")) is not int
            or row["quantity"] != 1
            or row.get("footprint") != placement.footprint
        ):
            raise RequirementError("SMT BOM quantity or footprint mismatch")
        mpn = row.get("mpn")
        if not isinstance(mpn, str) or not mpn.strip():
            raise RequirementError("SMT BOM manufacturer part number is required")
        values = {
            "part_number": row.get("part_number") or mpn,
            "description": row.get("description", ""),
            "package": row.get("package") or placement.footprint,
            "manufacturer": row.get("manufacturer", row.get("manufacturer_name", "")),
            "mpn": mpn,
            "distributor_part_number": row.get("distributor_part_number", ""),
            "footprint": placement.footprint,
        }
        if any(not isinstance(value, str) for value in values.values()):
            raise RequirementError("SMT BOM part details must be strings")
        key = tuple(values.values())
        grouped_bom.setdefault(key, {"values": values, "references": []})["references"].append(
            placement.reference
        )
    groups = sorted(grouped_bom.values(), key=lambda group: min(group["references"]))
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "bom.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "Line#",
                "Quantity Per Part Number",
                "Reference Designator",
                "Part Number",
                "Part Description",
                "Package",
                "Type",
                "Manufacturer Name",
                "Manufacturer Part Number",
                "Distributor Part Number",
                "Footprint",
            ],
        )
        writer.writeheader()
        for line_number, group in enumerate(groups, start=1):
            values = group["values"]
            designators = sorted(group["references"])
            writer.writerow(
                {
                    "Line#": line_number,
                    "Quantity Per Part Number": len(designators),
                    "Reference Designator": ", ".join(designators),
                    "Part Number": values["part_number"],
                    "Part Description": values["description"],
                    "Package": values["package"],
                    "Type": "Surface mount",
                    "Manufacturer Name": values["manufacturer"],
                    "Manufacturer Part Number": values["mpn"],
                    "Distributor Part Number": values["distributor_part_number"],
                    "Footprint": values["footprint"],
                }
            )
    with (destination / "centroid.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
        )
        writer.writeheader()
        for placement in sorted(placements, key=lambda item: item.reference):
            writer.writerow(
                {
                    "Designator": placement.reference,
                    "Mid X": f"{placement.x_mm:.4f}mm",
                    "Mid Y": f"{placement.y_mm:.4f}mm",
                    "Layer": placement.side,
                    "Rotation": f"{placement.rotation_deg:.2f}",
                }
            )
    return {
        "status": "PASS",
        "bom": "bom.csv",
        "centroid": "centroid.csv",
        "placement_count": len(placements),
        "bom_line_count": len(grouped_bom),
        "rotation_convention": "Counter-clockwise degrees as viewed from the placement side.",
        "paste_layers_required": sorted({placement.side for placement in placements}),
    }


def export_kicad_smt_assembly(
    launcher: list[str],
    board: Path,
    smt_bom_rows: list[dict],
    destination: Path,
) -> dict:
    """Export PCBWay-style SMT BOM/PnP, paste Gerbers and assembly drawing from one board."""
    if not launcher or not board.is_file() or not smt_bom_rows:
        raise RequirementError("KiCad launcher, native board and nonempty SMT BOM are required")
    references = [row.get("reference") for row in smt_bom_rows]
    if any(not isinstance(reference, str) for reference in references):
        raise RequirementError("SMT BOM references must be strings")
    if len(references) != len(set(references)):
        raise RequirementError("duplicate SMT BOM reference")
    if destination.exists():
        raise RequirementError("assembly destination already exists")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".kicad-smt-assembly-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        package = stage / "package"
        raw_positions = stage / "native_positions.csv"
        position_command = [
            *launcher,
            "pcb",
            "export",
            "pos",
            "--format",
            "csv",
            "--units",
            "mm",
            "--smd-only",
            "--exclude-dnp",
            "--side",
            "both",
            "--output",
            str(raw_positions),
            str(board),
        ]
        completed = subprocess.run(
            position_command,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode:
            raise RequirementError(
                "KiCad position export failed: " + completed.stderr.strip()[-1000:]
            )
        with raw_positions.open(newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"Ref", "Package", "PosX", "PosY", "Rot", "Side"}
            if not required <= set(reader.fieldnames or ()):
                raise RequirementError("KiCad position CSV has unsupported columns")
            records = list(reader)
        if not records:
            raise RequirementError("native board contains no SMT placements")
        if {record["Ref"] for record in records} != set(references):
            raise RequirementError("SMT BOM and native placement references disagree")
        if len(records) != len(references):
            raise RequirementError("native position file contains duplicate references")

        board_tree = parse(board.read_text())
        board_footprints = {}
        requested_references = set(references)
        for footprint in children(board_tree, "footprint"):
            props = [prop for prop in children(footprint, "property") if prop[1] == "Reference"]
            if len(props) != 1:
                raise RequirementError("native board has ambiguous footprint reference")
            reference = props[0][2]
            if reference in requested_references:
                if reference in board_footprints:
                    raise RequirementError("native board has duplicate SMT footprint reference")
                board_footprints[reference] = footprint[1]
        rows_by_reference = {row["reference"]: row for row in smt_bom_rows}
        placements = []
        for record in records:
            reference = record["Ref"]
            bom_row = rows_by_reference[reference]
            if bom_row.get("quantity") != 1:
                raise RequirementError("SMT BOM quantity must be one per reference")
            board_footprint = board_footprints.get(reference)
            bom_footprint = bom_row.get("footprint", "")
            qualified_footprint_mismatch = ":" in bom_footprint and board_footprint != bom_footprint
            if (
                board_footprint is None
                or qualified_footprint_mismatch
                or board_footprint.split(":", 1)[-1] != bom_footprint.split(":", 1)[-1]
                or record["Package"] != board_footprint.split(":", 1)[-1]
            ):
                raise RequirementError("SMT BOM footprint differs from native board")
            side = {"front": "Top", "top": "Top", "back": "Bottom", "bottom": "Bottom"}.get(
                record["Side"].strip().lower()
            )
            if side is None:
                raise RequirementError("KiCad position CSV has an unsupported board side")
            try:
                placements.append(
                    AssemblyPlacement(
                        reference=reference,
                        x_mm=float(record["PosX"].removesuffix("mm")),
                        y_mm=float(record["PosY"].removesuffix("mm")),
                        side=side,
                        rotation_deg=float(record["Rot"]) % 360,
                        footprint=bom_row["footprint"],
                    )
                )
            except (KeyError, ValueError) as error:
                raise RequirementError(f"invalid native placement for {reference}") from error

        report = export_smt_assembly(placements, smt_bom_rows, package)
        paste_dir = package / "paste"
        paste_dir.mkdir()
        gerber_command = [
            *launcher,
            "pcb",
            "export",
            "gerbers",
            "--layers",
            "F.Paste,B.Paste",
            "--output",
            str(paste_dir),
            str(board),
        ]
        gerbers = subprocess.run(
            gerber_command, check=False, capture_output=True, text=True, timeout=120
        )
        if gerbers.returncode:
            raise RequirementError("KiCad paste export failed: " + gerbers.stderr.strip()[-1000:])
        paste_files = sorted(
            path
            for path in paste_dir.iterdir()
            if path.is_file() and "_Paste." in path.name and path.stat().st_size
        )
        if not paste_files:
            raise RequirementError("KiCad produced no nonempty paste-layer Gerbers")
        required_paste_markers = {
            "Top": "-F_Paste.",
            "Bottom": "-B_Paste.",
        }
        for side in {placement.side for placement in placements}:
            marker = required_paste_markers[side]
            if not any(marker in path.name for path in paste_files):
                raise RequirementError(f"KiCad produced no nonempty {side} paste Gerber")

        drawing = package / "assembly.pdf"
        pdf_command = [
            *launcher,
            "pcb",
            "export",
            "pdf",
            "--mode-single",
            "--layers",
            "F.Fab,B.Fab,F.SilkS,B.SilkS,Edge.Cuts",
            "--output",
            str(drawing),
            str(board),
        ]
        pdf = subprocess.run(pdf_command, check=False, capture_output=True, text=True, timeout=120)
        if pdf.returncode or not drawing.is_file() or not drawing.stat().st_size:
            raise RequirementError("KiCad assembly drawing export failed")
        outputs = [
            package / "bom.csv",
            package / "centroid.csv",
            drawing,
            *paste_dir.iterdir(),
        ]
        report.update(
            paste=[str(path.relative_to(package)) for path in paste_files],
            assembly_drawing="assembly.pdf",
            source_board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
            output_sha256={
                str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in outputs
            },
            native_position_export="kicad-cli pcb export pos --smd-only --exclude-dnp",
            coordinate_origin="KiCad page origin (top-left); drill/place origin option omitted",
            bottom_x_negated=False,
            rotation_source="native KiCad Rot field normalized modulo 360 degrees",
        )
        package.rename(destination)
        return report


SUPPORTED_DOMAINS = {
    "low_voltage_through_hole_analog": "verified-reference-only",
    "higher_current": "unsupported",
    "mains_or_high_voltage": "unsupported",
    "rf": "unsupported",
    "switching_power": "unsupported",
    "high_speed_digital": "unsupported",
    "multilayer": "unsupported",
    "thermal_design": "unsupported",
}
