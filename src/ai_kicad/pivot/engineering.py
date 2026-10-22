"""Bounded post-POC requirements, catalog and engineering calculations."""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from .evidence import StrictModel


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
    category: str
    package: str
    footprint: str
    pin_map: dict[str, str]
    voltage_min_v: float | None = None
    voltage_max_v: float | None = None
    power_rating_w: float | None = None
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
) -> CatalogPart:
    matches = [
        part
        for part in catalog
        if part.approved
        and part.category == category
        and part.package == package
        and (part.voltage_max_v is None or part.voltage_max_v >= minimum_voltage_v)
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
    bom_by_reference = {row["reference"]: row for row in bom_rows}
    if set(references) != set(bom_by_reference):
        raise RequirementError("SMT BOM and placement references disagree")
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "bom.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["Designator", "Quantity", "Manufacturer Part Number", "Footprint"]
        )
        writer.writeheader()
        for placement in sorted(placements, key=lambda item: item.reference):
            row = bom_by_reference[placement.reference]
            if row.get("quantity") != 1 or row.get("footprint") != placement.footprint:
                raise RequirementError("SMT BOM quantity or footprint mismatch")
            writer.writerow(
                {
                    "Designator": placement.reference,
                    "Quantity": 1,
                    "Manufacturer Part Number": row["mpn"],
                    "Footprint": placement.footprint,
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
        "rotation_convention": "Counter-clockwise degrees as viewed from the placement side.",
        "paste_layers_required": sorted({placement.side for placement in placements}),
    }


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
