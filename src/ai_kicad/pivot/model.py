"""Canonical, versioned engineering design graph for the MCP pivot."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal
from pathlib import Path

from pydantic import Field, model_validator

from ai_kicad.assets import sha256
from ai_kicad.ir import InputError
from ai_kicad.m2a_core import Asset

from .evidence import StrictModel


class Pin(StrictModel):
    number: str = Field(min_length=1)
    name: str
    electrical_type: str = Field(min_length=1)


class PinPad(StrictModel):
    pin: str = Field(min_length=1)
    pad: str = Field(min_length=1)


class Component(StrictModel):
    component_id: str = Field(min_length=1)
    reference: str = Field(pattern=r"^[A-Z#][A-Z0-9#]*[0-9]+$")
    value: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    symbol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mpn: str = Field(min_length=1)
    pins: list[Pin] = Field(min_length=1)
    footprint: str | None = None
    footprint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    pin_pad_map: list[PinPad] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mapping(self) -> Component:
        pin_numbers = [pin.number for pin in self.pins]
        if len(pin_numbers) != len(set(pin_numbers)):
            raise ValueError("duplicate component pin")
        mapped = [mapping.pin for mapping in self.pin_pad_map]
        physical_pads = [mapping.pad for mapping in self.pin_pad_map]
        if (
            len(mapped) != len(set(mapped))
            or len(physical_pads) != len(set(physical_pads))
            or set(mapped) - set(pin_numbers)
        ):
            raise ValueError("duplicate or unknown pin/pad in pin/pad map")
        if self.footprint is None and (self.footprint_sha256 or self.pin_pad_map):
            raise ValueError("footprint details require a footprint")
        if self.footprint and (not self.footprint_sha256 or set(mapped) != set(pin_numbers)):
            raise ValueError("assigned footprint requires hash and complete pin/pad map")
        return self


class Terminal(StrictModel):
    component_id: str = Field(min_length=1)
    pin: str = Field(min_length=1)
    unit: int = Field(default=1, ge=1)
    sheet: str = Field(default="/", pattern=r"^/")


class Sheet(StrictModel):
    sheet_id: str = Field(pattern=r"^/")
    name: str = Field(min_length=1)
    parent_sheet_id: str | None = Field(default=None, pattern=r"^/")


class Net(StrictModel):
    net_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    terminals: list[Terminal] = Field(min_length=2)


class ElectricalAssertion(StrictModel):
    assertion_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    parameters: dict[str, int | float | str | bool]
    source: str = Field(min_length=1)


class ManufacturingProfile(StrictModel):
    profile_id: str = Field(min_length=1)
    board_width_mm: float = Field(gt=0)
    board_height_mm: float = Field(gt=0)
    copper_layers: Literal[2]
    thickness_mm: float = Field(gt=0)
    min_track_mm: float = Field(gt=0)
    min_clearance_mm: float = Field(gt=0)
    min_drill_mm: float = Field(gt=0)
    min_via_diameter_mm: float = Field(gt=0)
    copper_to_edge_mm: float = Field(gt=0)
    copper_weight_oz: float = Field(gt=0)
    material: str = Field(min_length=1)
    solder_mask_sides: Literal[2]
    silkscreen_sides: Literal[2]
    qualification_status: Literal["reference", "fabricator_vetted"]
    source: str = Field(min_length=1)


class DesignModel(StrictModel):
    schema_version: Literal["design-model.v1"]
    design_id: str = Field(min_length=1)
    revision_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_revision: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    title: str = Field(min_length=1)
    native_artifacts: dict[str, str] = Field(default_factory=dict)
    requirements: dict[str, str | int | float | bool]
    hierarchy: list[Sheet] = Field(min_length=1)
    components: list[Component] = Field(min_length=1)
    nets: list[Net] = Field(min_length=1)
    electrical_assertions: list[ElectricalAssertion]
    manufacturing_profile: ManufacturingProfile

    @model_validator(mode="after")
    def validate_graph(self) -> DesignModel:
        component_ids = [component.component_id for component in self.components]
        references = [component.reference for component in self.components]
        net_ids = [net.net_id for net in self.nets]
        sheet_ids = [sheet.sheet_id for sheet in self.hierarchy]
        if any(
            Path(path).is_absolute()
            or ".." in Path(path).parts
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for path, digest in self.native_artifacts.items()
        ):
            raise ValueError("native artifact inventory contains invalid path or hash")
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("duplicate component ID")
        if len(references) != len(set(references)):
            raise ValueError("duplicate reference")
        if len(net_ids) != len(set(net_ids)):
            raise ValueError("duplicate net ID")
        if len(sheet_ids) != len(set(sheet_ids)) or "/" not in sheet_ids:
            raise ValueError("hierarchy requires unique sheets and a root")
        for sheet in self.hierarchy:
            if sheet.sheet_id == "/" and sheet.parent_sheet_id is not None:
                raise ValueError("root sheet cannot have a parent")
            if sheet.parent_sheet_id is not None and sheet.parent_sheet_id not in sheet_ids:
                raise ValueError("sheet references unknown parent")
        components = {component.component_id: component for component in self.components}
        seen: set[tuple[str, int, str, str]] = set()
        for net in self.nets:
            local: set[tuple[str, int, str, str]] = set()
            for terminal in net.terminals:
                component = components.get(terminal.component_id)
                if component is None:
                    raise ValueError("net references unknown component")
                if terminal.sheet not in sheet_ids:
                    raise ValueError("terminal references unknown sheet")
                if terminal.pin not in {pin.number for pin in component.pins}:
                    raise ValueError("net references unknown component pin")
                identity = (terminal.sheet, terminal.unit, terminal.component_id, terminal.pin)
                if identity in local or identity in seen:
                    raise ValueError("terminal appears more than once")
                local.add(identity)
                seen.add(identity)
        return self

    def content_revision(self) -> str:
        content = self.model_dump(mode="json", exclude={"revision_id"})
        payload = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def require_revision_match(self) -> None:
        if self.revision_id != self.content_revision():
            raise ValueError("revision_id does not match canonical content")


def _placeholder_revision(payload: dict[str, Any]) -> str:
    temporary = dict(payload)
    temporary["revision_id"] = "sha256:" + "0" * 64
    model = DesignModel.model_validate(temporary)
    return model.content_revision()


def from_legacy_ir(
    legacy: dict[str, Any],
    resolved_assets: dict[str, Asset],
    bom: dict[str, Any],
    footprint_lock: dict[str, Any],
    board_profile: dict[str, Any],
) -> DesignModel:
    """Map the supported fixed-reference legacy subset without changing it."""
    entries = {item["refdes"]: item for item in bom["items"]}
    footprint_entries = {
        f"{item['library']}:{item['footprint']}": item for item in footprint_lock["assets"]
    }
    components = []
    for old in legacy["components"]:
        asset = resolved_assets.get(old["asset"])
        if asset is None:
            raise InputError(f"unknown legacy asset: {old['asset']}")
        nonempty_units = {unit: pins for unit, pins in asset.units.items() if unit > 0 and pins}
        if len(nonempty_units) != 1:
            raise InputError(f"unsupported multi-unit legacy asset: {old['asset']}")
        pins = next(iter(nonempty_units.values()))
        entry = entries.get(old["refdes"])
        if entry is None:
            raise InputError(f"missing BOM entry: {old['refdes']}")
        footprint = footprint_entries[entry["footprint"]]
        components.append(
            Component(
                component_id=old["id"],
                reference=old["refdes"],
                value=old["value"],
                symbol=old["asset"],
                symbol_sha256=sha256(asset.definition.encode()),
                mpn=entry["mpn"],
                pins=[
                    Pin(number=pin.number, name=pin.name, electrical_type=pin.electrical_type)
                    for pin in pins
                ],
                footprint=entry["footprint"],
                footprint_sha256=footprint["sha256"],
                pin_pad_map=[
                    PinPad(pin=pin, pad=pad)
                    for pin, pad in sorted(entry["symbol_pin_to_pad"].items())
                ],
            )
        )
    payload: dict[str, Any] = {
        "schema_version": "design-model.v1",
        "design_id": legacy["id"],
        "parent_revision": None,
        "title": legacy["name"],
        "requirements": {
            "function": "5 V NE555 astable LED flasher",
            "risk_class": "benign-low-voltage",
        },
        "hierarchy": [{"sheet_id": "/", "name": "Root", "parent_sheet_id": None}],
        "components": [component.model_dump(mode="json") for component in components],
        "nets": [
            {
                "net_id": net["id"],
                "role": net["id"].lower(),
                "terminals": [
                    {"component_id": component_id, "pin": pin, "unit": 1, "sheet": "/"}
                    for component_id, pin in net["members"]
                ],
            }
            for net in legacy["nets"]
        ],
        "electrical_assertions": [
            {
                "assertion_id": "supply_voltage_range",
                "kind": "inclusive_range",
                "parameters": {
                    "nominal_v": board_profile["constraints"]["supply_voltage_nominal_v"],
                    "minimum_v": board_profile["constraints"]["supply_voltage_min_v"],
                    "maximum_v": board_profile["constraints"]["supply_voltage_max_v"],
                },
                "source": board_profile["source"],
            }
        ],
        "manufacturing_profile": {
            "profile_id": board_profile["profile_id"],
            "board_width_mm": board_profile["outline"]["width"],
            "board_height_mm": board_profile["outline"]["height"],
            "copper_layers": 2,
            "thickness_mm": board_profile["stackup"]["thickness"],
            "min_track_mm": board_profile["minimums"]["track_width"],
            "min_clearance_mm": board_profile["minimums"]["clearance"],
            "min_drill_mm": board_profile["minimums"]["plated_hole_drill"],
            "min_via_diameter_mm": board_profile["minimums"]["via_diameter"],
            "copper_to_edge_mm": board_profile["minimums"]["copper_to_edge"],
            "copper_weight_oz": board_profile["stackup"]["copper_weight_oz_per_layer"],
            "material": board_profile["stackup"]["material"],
            "solder_mask_sides": 2,
            "silkscreen_sides": 2,
            "qualification_status": "reference",
            "source": board_profile["source"],
        },
    }
    payload["revision_id"] = _placeholder_revision(payload)
    model = DesignModel.model_validate(payload)
    model.require_revision_match()
    return model
