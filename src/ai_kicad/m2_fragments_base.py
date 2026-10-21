"""Implementation details for m2 fragments base."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from .ir import InputError
from .m2_fragments_types import Point, Rect
from .m2_geometry import (
    Gateway,
    GeometryItem,
    PathObligation,
    ProtectedPath,
    Reservation,
    label_text_rect,
)
from .m2a_constants import PITCH
from .m2a_core import Asset, Pin
from .m2b import (
    Draft,
    _turn,
)

if TYPE_CHECKING:
    from .m2_semantics_core import BlockPlan, SemanticPort
    from .m2_semantics_types import Occurrence


@dataclass(frozen=True)
class PortAnchor:
    port: SemanticPort
    point: Point
    direction: str


@dataclass(frozen=True)
class FragmentVariant:
    id: str
    block: BlockPlan
    positions: Mapping[Occurrence, Point]
    angles: Mapping[Occurrence, int]
    text_positions: Mapping[Occurrence, Point]
    wires: tuple[tuple[Point, Point], ...]
    wire_nets: tuple[str, ...]
    labels: tuple[tuple[str, Point], ...]
    junctions: tuple[Point, ...]
    ports: tuple[PortAnchor, ...]
    envelope: Rect
    protected_wires: frozenset[int]
    rule_id: str = "m2e1.local.v1"
    origins: tuple[str, ...] = ()
    obstacles: tuple[Rect, ...] = field(default_factory=tuple)
    tap_segments: tuple[tuple[str, Point, Point], ...] = field(default_factory=tuple)
    occupied_geometry: tuple[GeometryItem, ...] = field(default_factory=tuple)
    content_envelope: Rect | None = None
    reservations: tuple[Reservation, ...] = field(default_factory=tuple)
    packing_envelope: Rect | None = None
    gateways: tuple[Gateway, ...] = field(default_factory=tuple)
    protected_paths: tuple[ProtectedPath, ...] = field(default_factory=tuple)
    obligations: tuple[PathObligation, ...] = field(default_factory=tuple)
    wire_provenance: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    construction_trace: tuple[tuple[str, ...], ...] = ()
    construction_uncovered: tuple[str, ...] = ()
    retention_uncovered: tuple[str, ...] = ()

    def construction_evidence(self) -> dict:
        return {
            "proposal_limit": 32,
            "proposals_attempted": len(self.construction_trace),
            "attempts": [list(item) for item in self.construction_trace],
            "budget_uncovered": list(self.construction_uncovered),
            "retention_uncovered": list(self.retention_uncovered),
            "retained_variant_limit": 8,
        }

    def __post_init__(self) -> None:
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
        object.__setattr__(self, "angles", MappingProxyType(dict(self.angles)))
        object.__setattr__(self, "text_positions", MappingProxyType(dict(self.text_positions)))
        if self.content_envelope is None:
            object.__setattr__(self, "content_envelope", self.envelope)
        if self.packing_envelope is None:
            object.__setattr__(self, "packing_envelope", self.envelope)


def _component(design: dict, component_id: str) -> dict:
    return next(c for c in design["components"] if c["id"] == component_id)


def _relationship(design: dict, relationship_id: str) -> dict:
    return next(r for r in design["relationships"] if r["id"] == relationship_id)


def _terminal_net(design: dict, component: str, pin: str) -> str:
    return next(net["id"] for net in design["nets"] if [component, pin] in net["members"])


def _body_rect(design: dict, resolved: dict[str, Asset], draft: Draft, key: Occurrence) -> Rect:
    component = _component(design, key[0])
    body = resolved[component["asset"]].bodies.get(key[1]) or resolved[
        component["asset"]
    ].bodies.get(0)
    x, y = draft.positions[key]
    if not body:
        return x - 3 * PITCH, y - 3 * PITCH, x + 3 * PITCH, y + 3 * PITCH
    left, top, right, bottom = body
    corners = [
        _turn(Pin("", "", "", xx, yy), draft.angles.get(key, 0))
        for xx in (left, right)
        for yy in (top, bottom)
    ]
    xs, ys = [x + point[0] for point in corners], [y + point[1] for point in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _clear_nonpassive_text(design: dict, resolved: dict[str, Asset], draft: Draft) -> None:
    components = {component["id"]: component for component in design["components"]}
    for key in sorted(draft.text_positions):
        component = components.get(key[0])
        if component is None:
            continue
        if (
            component["asset"] in {"Device:C", "Device:R"}
            and max(len(component["refdes"]), len(component["value"])) <= 4
        ):
            continue
        sx, sy = draft.positions[key]
        tx, ty = draft.text_positions[key]
        nearby = tuple(
            (tx + dx * PITCH, ty + dy * PITCH)
            for dy in (-2, -4, 0, 2, 4)
            for dx in (0, 2, -2, 4, -4)
            if dx or dy
        )
        preferred_connector_slots = ()
        if component["asset"].startswith("Connector_Generic:"):
            asset = resolved[component["asset"]]
            pins = asset.units.get(key[1], asset.units.get(0, ()))
            if pins:
                dx, _dy = _turn(pins[0], draft.angles.get(key, 0))
                if dx:
                    side = -1 if dx > 0 else 1
                    preferred_connector_slots = tuple(
                        (sx + side * 8 * PITCH, sy - offset * PITCH) for offset in (2, 4, 6)
                    )
                else:
                    preferred_connector_slots = tuple(
                        (sx, sy - offset * PITCH) for offset in (6, 5)
                    )
        keep_long_connector_text_local = (
            component["asset"].startswith("Connector_Generic:")
            and max(len(component["refdes"]), len(component["value"])) > 10
        )
        connector_text_candidates = (
            (draft.text_positions[key], *preferred_connector_slots)
            if keep_long_connector_text_local
            else (*preferred_connector_slots, draft.text_positions[key])
        )
        candidates = (
            *connector_text_candidates,
            *nearby,
            (sx, sy - 12 * PITCH),
            (sx, sy - 16 * PITCH),
            (sx, sy - 20 * PITCH),
            (sx + 12 * PITCH, sy - 8 * PITCH),
            (sx - 12 * PITCH, sy - 8 * PITCH),
            (sx + 12 * PITCH, sy + 6 * PITCH),
            (sx - 12 * PITCH, sy + 6 * PITCH),
        )
        for x, y in candidates:
            rectangles = []
            for value, py in (
                (component["refdes"], y),
                (component["value"], y + 2 * PITCH),
            ):
                half = max(635_000, len(value) * 445_000)
                rectangles.append(
                    (
                        x - half - 1_000_000,
                        py - 1_850_000,
                        x + half + 1_000_000,
                        py + 1_850_000,
                    )
                )
            # Wires alone miss a field on a neighbouring body or net label.
            # Use the same transformed physical bodies that the fragment owns.
            obstacles = [
                _body_rect(design, resolved, draft, other)
                for other in draft.positions
                if other[0] in components
            ]
            obstacles.extend(label_text_rect(net, point) for net, point in draft.labels)
            for other, (ox, oy) in draft.text_positions.items():
                if other == key or other[0] not in components:
                    continue
                other_component = components[other[0]]
                for value, py in (
                    (other_component["refdes"], oy),
                    (other_component["value"], oy + 2 * PITCH),
                ):
                    half = max(635_000, len(value) * 445_000)
                    obstacles.append((ox - half, py - 850_000, ox + half, py + 850_000))
            if any(
                max(rect[0], obstacle[0]) < min(rect[2], obstacle[2])
                and max(rect[1], obstacle[1]) < min(rect[3], obstacle[3])
                for rect in rectangles
                for obstacle in obstacles
            ):
                continue
            if all(
                not (
                    (
                        a[0] == b[0]
                        and rect[0] < a[0] < rect[2]
                        and max(min(a[1], b[1]), rect[1]) < min(max(a[1], b[1]), rect[3])
                    )
                    or (
                        a[1] == b[1]
                        and rect[1] < a[1] < rect[3]
                        and max(min(a[0], b[0]), rect[0]) < min(max(a[0], b[0]), rect[2])
                    )
                )
                for rect in rectangles
                for a, b in draft.wires
            ):
                draft.text_positions[key] = (x, y)
                break
        else:
            raise InputError(f"TEXT_SLOT_INFEASIBLE: {component['id']} unit {key[1]}")


def _occupied_geometry(
    design: dict, resolved: dict[str, Asset], draft: Draft, block: BlockPlan
) -> tuple[GeometryItem, ...]:
    items: list[GeometryItem] = []
    component_ids = {component["id"] for component in design["components"]}
    for key in sorted(draft.positions):
        if key[0] not in component_ids:
            continue
        component = _component(design, key[0])
        owner = block.id
        items.append(
            GeometryItem(
                f"{key}.body",
                "body",
                owner,
                _body_rect(design, resolved, draft, key),
                (component["asset"],),
            )
        )
        x, y = draft.text_positions[key]
        for field_name, value, py in (
            ("reference", component["refdes"], y),
            ("value", component["value"], y + 2 * PITCH),
        ):
            half = max(635_000, len(value) * 445_000)
            items.append(
                GeometryItem(
                    f"{key}.{field_name}",
                    "text",
                    owner,
                    (x - half, py - 850_000, x + half, py + 850_000),
                    ("pinned-stroke-estimator.v1",),
                )
            )
        asset = resolved[component["asset"]]
        for pin in asset.units.get(key[1], asset.units.get(0, ())):
            point = draft.point(key[0], pin.number)
            items.append(
                GeometryItem(
                    f"{key}.pin.{pin.number}",
                    "pin",
                    owner,
                    (*point, *point),
                    (pin.name, pin.electrical_type),
                )
            )
    for index, ((first, second), net) in enumerate(zip(draft.wires, draft.wire_nets, strict=True)):
        items.append(
            GeometryItem(
                f"wire.{index}",
                "wire",
                block.id,
                (
                    min(first[0], second[0]),
                    min(first[1], second[1]),
                    max(first[0], second[0]),
                    max(first[1], second[1]),
                ),
                (net,),
            )
        )
    for index, (net, point) in enumerate(draft.labels):
        items.append(
            GeometryItem(
                f"label.{index}",
                "label",
                block.id,
                label_text_rect(net, point),
                (net,),
            )
        )
    for index, point in enumerate(draft.junctions):
        items.append(GeometryItem(f"junction.{index}", "junction", block.id, (*point, *point)))
    return tuple(items)


def _reservation_envelope(reservations: tuple[Reservation, ...]) -> Rect:
    return (
        min(item.rect[0] for item in reservations),
        min(item.rect[1] for item in reservations),
        max(item.rect[2] for item in reservations),
        max(item.rect[3] for item in reservations),
    )


def _placed_terminal_points(
    draft: Draft,
    resolved: dict[str, Asset],
    design: dict,
    terminal_nets: dict,
    net: str,
):
    components = {component["id"]: component for component in design["components"]}
    for (component_id, pin_number), terminal_net in terminal_nets.items():
        if terminal_net != net:
            continue
        component = components[component_id]
        unit = next(
            unit
            for unit, pins in resolved[component["asset"]].units.items()
            if any(pin.number == pin_number for pin in pins)
        )
        if (component_id, unit) in draft.positions:
            yield draft.point(component_id, pin_number)
