"""Local geometry constructors for instance-based M2 schematic composition."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping

from .ir import InputError
from .m2_geometry import (
    AccessWindow,
    ConductorSegment,
    Gateway,
    GeometryItem,
    PathObligation,
    ProtectedPath,
    Reservation,
    canonical_conductor_tree,
    content_envelope,
    prove_gateway_witnesses,
)
from .m2a import Asset, PITCH, Pin
from .m2b import Draft, choose_text_slots, orientation_for_flow, _turn
from .m2_semantics import BlockPlan, Occurrence, SemanticPlan, SemanticPort


Point = tuple[int, int]
Rect = tuple[int, int, int, int]


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


def _clear_nonpassive_text(design: dict, draft: Draft) -> None:
    components = {component["id"]: component for component in design["components"]}
    for key in sorted(draft.text_positions):
        component = components.get(key[0])
        if component is None or component["asset"] in {"Device:C", "Device:R"}:
            continue
        sx, sy = draft.positions[key]
        candidates = (
            draft.text_positions[key],
            (sx, sy - 12 * PITCH),
            (sx + 12 * PITCH, sy - 8 * PITCH),
            (sx - 12 * PITCH, sy - 8 * PITCH),
            (sx + 12 * PITCH, sy + 6 * PITCH),
            (sx - 12 * PITCH, sy + 6 * PITCH),
        )
        for x, y in candidates:
            rectangles = []
            for value, py in ((component["refdes"], y), (component["value"], y + 2 * PITCH)):
                half = max(635_000, len(value) * 445_000)
                rectangles.append(
                    (x - half - 1_000_000, py - 1_850_000, x + half + 1_000_000, py + 1_850_000)
                )
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
        half = max(635_000, len(net) * 445_000)
        items.append(
            GeometryItem(
                f"label.{index}",
                "label",
                block.id,
                (point[0] - half, point[1] - 850_000, point[0] + half, point[1] + 850_000),
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
    draft: Draft, resolved: dict[str, Asset], design: dict, terminal_nets: dict, net: str
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


def _finish(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    draft: Draft,
    anchors: dict[str, tuple[Point, str]],
    *,
    variant_suffix: str = "v0",
) -> FragmentVariant:
    if set(draft.positions) != set(block.occurrences):
        raise InputError(
            f"FRAGMENT_OWNER_MISMATCH: {block.id} expected={sorted(block.occurrences)} "
            f"actual={sorted(draft.positions)}"
        )
    component_ids = {component["id"] for component in design["components"]}
    terminal_nets = {
        tuple(member): net["id"] for net in design["nets"] for member in net["members"]
    }
    interface_components = {
        component["id"]
        for component in design["components"]
        if component["asset"].startswith("Connector")
    }
    interface_nets = {
        net["id"]
        for net in design["nets"]
        if any(member[0] in interface_components for member in net["members"])
    }
    block_component_ids = {occurrence[0] for occurrence in block.occurrences}
    local_only_nets = {
        net["id"]
        for net in design["nets"]
        if all(member[0] in block_component_ids for member in net["members"])
    }
    ports = []
    gateways = []
    original_wire_count = len(draft.wires)
    escape_length = (
        3 * PITCH
        if block.kind in {"package_power", "power_stage", "timer", "led_branch", "rc", "series"}
        else PITCH
    )
    direction_delta = {
        "left": (-escape_length, 0),
        "right": (escape_length, 0),
        "up": (0, -escape_length),
        "down": (0, escape_length),
    }
    for port in block.ports:
        suffix = port.id.rsplit(".", 1)[-1]
        if suffix not in anchors:
            raise InputError(f"FRAGMENT_PORT_MISSING: {port.id}")
        anchor, direction = anchors[suffix]
        witnesses = port.terminals or tuple(
            sorted(
                terminal
                for terminal, net in terminal_nets.items()
                if net == port.net
                and any(occurrence[0] == terminal[0] for occurrence in block.occurrences)
            )
        )
        if not witnesses or any(terminal_nets.get(terminal) != port.net for terminal in witnesses):
            raise InputError(f"FRAGMENT_PORT_TERMINAL_IDENTITY: {port.id}:{port.net}")
        port_escape_length = (
            PITCH
            if port.role == "reference"
            and block.kind
            in {
                "buffer",
                "unused_amplifier",
                "noninverting_amplifier",
                "inverting_amplifier",
                "sallen_key",
                "interface",
            }
            else escape_length
        )
        dx, dy = {
            "left": (-port_escape_length, 0),
            "right": (port_escape_length, 0),
            "up": (0, -port_escape_length),
            "down": (0, port_escape_length),
        }[direction]
        gateway_point = (anchor[0] + dx, anchor[1] + dy)
        draft.route(port.net, anchor, gateway_point)
        if port.net in local_only_nets or port.net in interface_nets:
            draft.label(port.net, gateway_point)
        access_end = gateway_point
        access = AccessWindow(
            (
                min(gateway_point[0], access_end[0]) - PITCH,
                min(gateway_point[1], access_end[1]) - PITCH,
                max(gateway_point[0], access_end[0]) + PITCH,
                max(gateway_point[1], access_end[1]) + PITCH,
            ),
            frozenset({direction}),
            port.net,
        )
        gateway = Gateway(
            port.id,
            port.net,
            witnesses,
            f"{block.id}:{port.net}",
            anchor,
            direction,
            (anchor, gateway_point),
            frozenset({direction}),
            (access,),
        )
        gateway.validate(terminal_nets)
        gateways.append(gateway)
        ports.append(PortAnchor(port, gateway_point, direction))

    # Required fields are final local geometry, never a post-pack cosmetic pass.
    # Include the bounded external approach while selecting slots so text can
    # never consume a gateway that was certified before measurement.
    emitted_wire_count = len(draft.wires)
    for gateway in gateways:
        draft.wires.append(
            (
                gateway.point,
                (
                    gateway.point[0] + direction_delta[gateway.escape_direction][0],
                    gateway.point[1] + direction_delta[gateway.escape_direction][1],
                ),
            )
        )
        draft.wire_nets.append(gateway.net)
    choose_text_slots(design, draft)
    _clear_nonpassive_text(design, draft)
    del draft.wires[emitted_wire_count:]
    del draft.wire_nets[emitted_wire_count:]
    occupied = _occupied_geometry(design, resolved, draft, block)
    content = content_envelope(occupied)
    obstacles = tuple(
        _body_rect(design, resolved, draft, key)
        for key in sorted(draft.positions)
        if key[0] in component_ids
    )
    taps = tuple(
        (net, first, second)
        for net, (first, second) in zip(draft.wire_nets, draft.wires, strict=True)
        if any(port.net == net for port in block.ports)
    )
    reservations: list[Reservation] = []
    for item in occupied:
        clearance = (
            PITCH
            if item.kind in {"body", "text", "label", "pin"}
            else 250_000
            if item.kind == "wire"
            else 0
        )
        reserved_left, reserved_right = item.rect[0], item.rect[2]
        if item.kind == "text" and item.id.endswith(".reference"):
            center = (item.rect[0] + item.rect[2]) // 2
            half = max(1_780_000, (item.rect[2] - item.rect[0]) // 2)
            reserved_left, reserved_right = center - half, center + half
        raw_rect = (
            reserved_left - clearance,
            item.rect[1] - clearance,
            reserved_right + clearance,
            item.rect[3] + clearance,
        )
        reservation_rect = (
            (
                raw_rect[0] // PITCH * PITCH,
                raw_rect[1] // PITCH * PITCH,
                -((-raw_rect[2]) // PITCH) * PITCH,
                -((-raw_rect[3]) // PITCH) * PITCH,
            )
            if item.kind == "text"
            else raw_rect
        )
        reservations.append(
            Reservation(
                f"reservation.{item.id}",
                "exclusive",
                item.owner,
                item.kind,
                reservation_rect,
                item.provenance[0] if item.kind in {"label", "wire"} else None,
            )
        )
    reservations.extend(
        Reservation(
            f"gateway.{gateway.id}",
            "channel",
            block.id,
            "escape",
            window.rect,
            gateway.net,
            1,
        )
        for gateway in gateways
        for window in gateway.tap_windows
    )
    local_segments = tuple(
        ConductorSegment(first, second, net, block.id, (f"{block.id}.wire.{index}",))
        for index, (net, (first, second)) in enumerate(
            zip(draft.wire_nets, draft.wires, strict=True)
        )
    )
    for net in sorted(set(draft.wire_nets)):
        tree = canonical_conductor_tree(
            (segment for segment in local_segments if segment.net == net),
            junctions=draft.junctions,
            pins=_placed_terminal_points(draft, resolved, design, terminal_nets, net),
        )
        for gateway in (item for item in gateways if item.net == net):
            prove_gateway_witnesses(
                tree,
                gateway,
                {terminal: draft.point(*terminal) for terminal in gateway.terminals},
            )
    protected_edges = local_segments[:original_wire_count]
    protected_corridors = tuple(
        Reservation(
            f"protected.{index}",
            "exclusive",
            block.id,
            "protected",
            (
                min(segment.start[0], segment.end[0]) - 500_000,
                min(segment.start[1], segment.end[1]) - 500_000,
                max(segment.start[0], segment.end[0]) + 500_000,
                max(segment.start[1], segment.end[1]) + 500_000,
            ),
            segment.net,
        )
        for index, segment in enumerate(protected_edges)
    )
    protected_paths = (
        ProtectedPath(
            f"{block.id}.local",
            block.relationships,
            block.id,
            tuple(terminal for gateway in gateways for terminal in gateway.terminals),
            "*",
            f"{block.id}:local",
            (),
            protected_edges,
            protected_corridors,
            tuple(window for gateway in gateways for window in gateway.tap_windows),
            80_000_000,
        ),
    )
    obligations = tuple(
        PathObligation(
            f"obligation.{gateway.id}",
            block.id,
            gateway.net,
            gateway.island,
            gateway.terminals,
            "terminal_to_gateway",
            60_000_000
            if any(
                relation["kind"] == "decoupling" and relation["component"] == terminal[0]
                for relation in design["relationships"]
                for terminal in gateway.terminals
            )
            else 80_000_000,
        )
        for gateway in gateways
    )
    reservation_tuple = tuple(reservations) + protected_corridors
    packing_envelope = _reservation_envelope(reservation_tuple)
    return FragmentVariant(
        f"{block.id}.{variant_suffix}",
        block,
        dict(draft.positions),
        dict(draft.angles),
        dict(draft.text_positions),
        tuple(draft.wires),
        tuple(draft.wire_nets),
        tuple(draft.labels),
        tuple(draft.junctions),
        tuple(ports),
        packing_envelope,
        frozenset(range(original_wire_count)),
        origins=block.relationships,
        obstacles=obstacles,
        tap_segments=taps,
        occupied_geometry=occupied,
        content_envelope=content,
        reservations=reservation_tuple,
        packing_envelope=packing_envelope,
        gateways=tuple(gateways),
        protected_paths=protected_paths,
        obligations=obligations,
        wire_provenance=tuple(segment.provenance for segment in local_segments),
    )


def _new_draft(design: dict, resolved: dict[str, Asset]) -> Draft:
    return Draft(design, resolved, {}, {}, [], [], [], [], {})


def _amplifier_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    feedback_side: str = "below",
) -> FragmentVariant:
    stage = next(
        r
        for r in design["relationships"]
        if r["kind"] == "amplifier" and r["id"] in block.relationships
    )
    feedback = next(
        r
        for r in design["relationships"]
        if r["kind"] == "feedback" and r["id"] in block.relationships
    )
    amp = _component(design, stage["component"])
    function = next(f for f in amp["functions"] if f["id"] == stage["function"])
    d = _new_draft(design, resolved)
    ax, ay = 70 * PITCH, 35 * PITCH
    d.add(amp["id"], ax, ay, function["unit"])
    plus = d.point(amp["id"], function["pins"]["plus"])
    minus = d.point(amp["id"], function["pins"]["minus"])
    out = d.point(amp["id"], function["pins"]["out"])
    out_net = stage["output"]
    corridor_sign = 1 if feedback_side == "below" else -1
    corridor_y = minus[1] + corridor_sign * 9 * PITCH
    sense_x = minus[0] - 5 * PITCH
    branch_x = out[0] + 7 * PITCH
    feedback_node = (sense_x, corridor_y)
    branch = (branch_x, out[1])
    feedback_resistor = feedback.get("resistor")
    if feedback_resistor:
        d.add(feedback_resistor, ax + 7 * PITCH, corridor_y, angle=90)
        left, right = d.point(feedback_resistor, "1"), d.point(feedback_resistor, "2")
        d.route(
            _terminal_net(design, feedback_resistor, "1"),
            minus,
            (sense_x, minus[1]),
            feedback_node,
            left,
        )
        d.route(out_net, right, (branch_x, corridor_y), branch, out)
    else:
        d.route(
            out_net, minus, (sense_x, minus[1]), feedback_node, (branch_x, corridor_y), branch, out
        )
    d.junctions.append(branch)
    output_end = (branch_x + 4 * PITCH, branch[1])
    d.route(out_net, branch, output_end)

    relationships = [_relationship(design, rid) for rid in block.relationships]
    series = [r for r in relationships if r["kind"] == "series"]
    shunts = [r for r in relationships if r["kind"] == "shunt"]
    bridges = [r for r in relationships if r["kind"] == "bridge"]
    anchors: dict[str, tuple[Point, str]] = {"output": (output_end, "right")}
    if block.kind == "sallen_key":
        bridge = bridges[0]
        upstream = next(r for r in series if r["output"] == bridge["first"])
        filter_relation = next(r for r in series if r is not upstream)
        shunt = shunts[0]
        first_x = ax - 56 * PITCH
        second_x = ax - 34 * PITCH
        d.add(upstream["component"], first_x, plus[1], angle=90)
        d.add(filter_relation["component"], second_x, plus[1], angle=90)
        up_left, up_right = d.point(upstream["component"], "1"), d.point(upstream["component"], "2")
        f_left, f_right = (
            d.point(filter_relation["component"], "1"),
            d.point(filter_relation["component"], "2"),
        )
        intermediate = (ax - 45 * PITCH, plus[1])
        filter_node = (plus[0] - 13 * PITCH, plus[1])
        d.route(upstream["output"], up_right, intermediate, f_left)
        d.route(filter_relation["output"], f_right, filter_node, plus)
        d.junctions.extend((intermediate, filter_node))
        d.add(shunt["component"], filter_node[0], plus[1] + 16 * PITCH)
        cap_top, cap_bottom = d.point(shunt["component"], "1"), d.point(shunt["component"], "2")
        d.route(shunt["node"], filter_node, cap_top)
        ref_end = (cap_bottom[0], cap_bottom[1] + 5 * PITCH)
        d.route(shunt["reference"], cap_bottom, ref_end)
        d.add(bridge["component"], ax - 9 * PITCH, plus[1] - 19 * PITCH, angle=90)
        bridge_left, bridge_right = (
            d.point(bridge["component"], "1"),
            d.point(bridge["component"], "2"),
        )
        d.route(bridge["first"], intermediate, (intermediate[0], bridge_left[1]), bridge_left)
        d.route(bridge["second"], bridge_right, (branch_x, bridge_right[1]), branch)
        input_end = (up_left[0] - 5 * PITCH, up_left[1])
        d.route(upstream["input"], up_left, input_end)
        anchors.update(input=(input_end, "left"), reference=(ref_end, "down"))
    elif block.kind == "inverting_amplifier":
        input_leg = series[0]
        d.add(input_leg["component"], ax - 18 * PITCH, minus[1], angle=90)
        first, second = d.point(input_leg["component"], "1"), d.point(input_leg["component"], "2")
        d.route(input_leg["output"], second, minus)
        d.junctions.append(minus)
        input_end = (first[0] - 4 * PITCH, first[1])
        d.route(input_leg["input"], first, input_end)
        reference_end = (plus[0] - 2 * PITCH, plus[1])
        d.route(stage["reference"], plus, reference_end)
        anchors.update(input=(input_end, "left"), reference=(reference_end, "left"))
    elif block.kind == "noninverting_amplifier":
        gain = shunts[0]
        d.add(
            gain["component"],
            sense_x,
            corridor_y + corridor_sign * 9 * PITCH,
            angle=0 if corridor_sign > 0 else 180,
        )
        top, bottom = d.point(gain["component"], "1"), d.point(gain["component"], "2")
        minus_net = gain["node"]
        d.route(minus_net, feedback_node, top)
        d.junctions.append(feedback_node)
        reference_end = (bottom[0], bottom[1] + corridor_sign * 2 * PITCH)
        d.route(gain["reference"], bottom, reference_end)
        input_end = (plus[0] - 5 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(
            input=(input_end, "left"),
            reference=(reference_end, "down" if corridor_sign > 0 else "up"),
        )
    else:
        input_end = (plus[0] - 5 * PITCH, plus[1])
        d.route(stage["input"], plus, input_end)
        anchors.update(input=(input_end, "left"), reference=(input_end, "left"))
    return _finish(design, resolved, block, d, anchors)


def _package_fragment(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    *,
    reference_side: str = "down",
) -> FragmentVariant:
    rail = next(
        r
        for r in design["relationships"]
        if r["kind"] == "power_rails" and r["id"] in block.relationships
    )
    supports = [
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    ]
    d = _new_draft(design, resolved)
    amp = rail["component"]
    px, py = 35 * PITCH, 28 * PITCH
    d.add(amp, px, py, rail["unit"])
    pos, neg = d.point(amp, "8"), d.point(amp, "4")
    cap_pos = next(r for r in supports if r["supply"] == rail["positive"])
    cap_neg = next(r for r in supports if r["return"] == rail["negative"])
    d.add(
        cap_pos["component"],
        px - 11 * PITCH,
        py,
        angle=180 if reference_side == "up" else 0,
    )
    d.add(cap_neg["component"], px + 11 * PITCH, py)
    cp1, cp2 = d.point(cap_pos["component"], "1"), d.point(cap_pos["component"], "2")
    cn1, cn2 = d.point(cap_neg["component"], "1"), d.point(cap_neg["component"], "2")
    pos_end = (pos[0], cp1[1])
    neg_end = (neg[0], cn2[1])
    if reference_side == "up":
        positive_side_x = cp1[0] - 5 * PITCH
        d.route(
            rail["positive"],
            pos,
            (positive_side_x, pos[1]),
            (positive_side_x, cp1[1]),
            cp1,
        )
        pos_end = (positive_side_x, cp2[1] - 2 * PITCH)
    else:
        d.route(rail["positive"], pos, pos_end, cp1)
    d.route(rail["negative"], neg, neg_end, cn2)
    ref1, ref2 = cp2, cn1
    # Both decoupler returns belong to the same physical reference island.
    # The right-hand capacitor's upper pin needs a side approach so the wire
    # does not pass through its body or the package power unit.
    if reference_side == "up":
        d.route(rail["reference"], cp2, cn1)
    else:
        reference_bottom = max(cp2[1], cn1[1]) + 9 * PITCH
        reference_right = cn1[0] + 5 * PITCH
        d.route(
            rail["reference"],
            cp2,
            (cp2[0], reference_bottom),
            (reference_right, reference_bottom),
            (reference_right, cn1[1]),
            cn1,
        )
    d.label(rail["reference"], ref1)
    d.label(rail["reference"], ref2)
    dividers = [
        r
        for r in design["relationships"]
        if r["kind"] == "reference_divider" and r["id"] in block.relationships
    ]
    if dividers:
        divider = dividers[0]
        dx = px - 34 * PITCH
        d.add(divider["upper"], dx, py - 13 * PITCH)
        d.add(divider["lower"], dx, py + 13 * PITCH)
        ut, ub = d.point(divider["upper"], "1"), d.point(divider["upper"], "2")
        lt, lb = d.point(divider["lower"], "1"), d.point(divider["lower"], "2")
        local = (dx, cp2[1])
        d.route(rail["reference"], ub, local, lt)
        d.route(rail["reference"], local, cp2)
        d.junctions.append(local)
        d.route(rail["positive"], ut, (ut[0], ut[1] - 5 * PITCH))
        d.label(rail["positive"], (ut[0], ut[1] - 5 * PITCH))
        d.route(rail["negative"], lb, (lb[0], lb[1] + 5 * PITCH))
        d.label(rail["negative"], (lb[0], lb[1] + 5 * PITCH))
        ref1 = local
    positive_anchor = pos_end
    positive_direction = "up"
    anchors = {
        "positive": (positive_anchor, positive_direction),
        "negative": (neg_end, "down"),
        "reference": (
            ref1,
            "left" if dividers else ("up" if reference_side == "up" else "down"),
        ),
    }
    return _finish(design, resolved, block, d, anchors)


def _power_stage_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    stage = next(
        r
        for r in design["relationships"]
        if r["kind"] == "power_stage" and r["id"] in block.relationships
    )
    supports = [
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    ]
    d = _new_draft(design, resolved)
    sx, sy = 35 * PITCH, 25 * PITCH
    d.add(
        stage["component"],
        sx,
        sy,
        angle=orientation_for_flow(
            resolved[_component(design, stage["component"])["asset"]],
            stage["pins"]["input"],
            stage["pins"]["output"],
            "right",
        ),
    )
    pin_in, pin_out, pin_ref = (
        d.point(stage["component"], stage["pins"][name])
        for name in ("input", "output", "reference")
    )
    rail_nodes = {}
    for relation, x, rail in (
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["input"]),
            sx - 10 * PITCH,
            stage["input"],
        ),
        (
            next(r for r in supports if r["consumer"][1] == stage["pins"]["output"]),
            sx + 10 * PITCH,
            stage["output"],
        ),
    ):
        d.add(relation["component"], x, sy + 18 * PITCH)
        rail_pin = d.point(relation["component"], "1")
        ref_pin = d.point(relation["component"], "2")
        node = (rail_pin[0], sy)
        target = pin_in if rail == stage["input"] else pin_out
        d.route(rail, target, node, rail_pin)
        d.junctions.append(node)
        d.label(stage["reference"], ref_pin)
        rail_nodes[rail] = node
    # The support branch continues beyond each regulator pin.  Its certified
    # external gateway therefore belongs at the outer junction, not midway
    # along the protected local support conductor.
    in_end = rail_nodes[stage["input"]]
    out_end = rail_nodes[stage["output"]]
    ref_end = pin_ref
    return _finish(
        design,
        resolved,
        block,
        d,
        {"input": (in_end, "left"), "output": (out_end, "right"), "reference": (ref_end, "down")},
    )


def _timer_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan, *, compact: bool = False
) -> FragmentVariant:
    timer = next(
        r
        for r in design["relationships"]
        if r["kind"] == "timer" and r["id"] in block.relationships
    )
    ladder = next(
        r
        for r in design["relationships"]
        if r["kind"] == "timing_ladder" and r["id"] in block.relationships
    )
    control = next(
        r
        for r in design["relationships"]
        if r["kind"] == "decoupling" and r["id"] in block.relationships
    )
    d = _new_draft(design, resolved)
    tx, ty, lx = 42 * PITCH, 38 * PITCH, 15 * PITCH
    d.add(timer["component"], tx, ty)
    p = {role: d.point(timer["component"], number) for role, number in timer["pins"].items()}
    # The compact construction keeps the same ordered ladder terminals while
    # using separate measured body/text clearances for a shorter support band.
    d.add(ladder["upper"], lx, ty - (14 if compact else 20) * PITCH)
    d.add(ladder["lower"], lx, ty)
    d.add(ladder["capacitor"], lx, ty + (17 if compact else 24) * PITCH)
    # Keep the control bypass out of the timing-ladder/discharge corridor.
    d.add(control["component"], tx + 14 * PITCH, ty - (8 if compact else 10) * PITCH)
    ut, ub = d.point(ladder["upper"], "1"), d.point(ladder["upper"], "2")
    lt, lb = d.point(ladder["lower"], "1"), d.point(ladder["lower"], "2")
    ct, cb = d.point(ladder["capacitor"], "1"), d.point(ladder["capacitor"], "2")
    cot, cob = d.point(control["component"], "1"), d.point(control["component"], "2")
    supply_end = ut
    d.label(timer["supply"], supply_end)
    timer_supply_end = p["supply"]
    d.label(timer["supply"], timer_supply_end)
    d.label(timer["supply"], p["reset"])
    discharge_y = (ub[1] + lt[1]) // 2
    discharge_x = p["discharge"][0] - 8 * PITCH
    d.route(timer["discharge"], ub, (lx, discharge_y), lt)
    d.route(
        timer["discharge"],
        (lx, discharge_y),
        (discharge_x, discharge_y),
        (discharge_x, p["discharge"][1]),
        p["discharge"],
    )
    timing_y = p["trigger"][1] + 6 * PITCH
    sense_x = p["trigger"][0] - 7 * PITCH
    d.route(timer["timing"], lb, (lx, timing_y), ct)
    d.route(
        timer["timing"],
        (lx, timing_y),
        (sense_x, timing_y),
        (sense_x, p["threshold"][1]),
        p["threshold"],
    )
    d.route(timer["timing"], (sense_x, p["trigger"][1]), p["trigger"])
    d.junctions.append((sense_x, p["trigger"][1]))
    output_end = (p["output"][0] + 12 * PITCH, p["output"][1])
    d.route(timer["output"], p["output"], output_end)
    # Reference support terminals are typed rail contacts, not part of the
    # protected timing/discharge path.  Keep the timer terminal's gateway
    # explicit and avoid a long cosmetic bottom bus between independent
    # support returns.
    d.label(timer["reference"], cb)
    reference_end = p["reference"]
    control_y = min(p["control"][1], cot[1]) - 5 * PITCH
    d.route(timer["control"], p["control"], (p["control"][0], control_y), (cot[0], control_y), cot)
    d.label(timer["reference"], cob)
    return _finish(
        design,
        resolved,
        block,
        d,
        {
            "supply": (timer_supply_end, "right"),
            "output": (output_end, "right"),
            "reference": (reference_end, "right"),
        },
    )


def _passive_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan, *, compact: bool = False
) -> FragmentVariant:
    relation = next(
        r
        for r in design["relationships"]
        if r["kind"] == "series" and r["id"] in block.relationships
    )
    d = _new_draft(design, resolved)
    anchors = {}
    if block.kind == "led_branch":
        polarity = next(
            r
            for r in design["relationships"]
            if r["kind"] == "polarity" and r["id"] in block.relationships
        )
        x, y = 20 * PITCH, 14 * PITCH
        d.add(relation["component"], x, y)
        first, second = d.point(relation["component"], "1"), d.point(relation["component"], "2")
        d.add(polarity["component"], x, y + (9 if compact else 12) * PITCH, angle=90)
        anode, cathode = d.point(polarity["component"], "2"), d.point(polarity["component"], "1")
        d.route(relation["output"], second, anode)
        input_end = (first[0], first[1] - (4 if compact else 5) * PITCH)
        reference_end = cathode
        d.route(relation["input"], first, input_end)
        anchors.update(
            input=(input_end, "up"), output=(anode, "down"), reference=(reference_end, "down")
        )
    else:
        x, y = 24 * PITCH, 15 * PITCH
        d.add(relation["component"], x, y, angle=90)
        first, second = d.point(relation["component"], "1"), d.point(relation["component"], "2")
        input_end, output_end = (first[0] - 7 * PITCH, first[1]), (second[0] + 7 * PITCH, second[1])
        d.route(relation["input"], input_end, first)
        d.route(relation["output"], second, output_end)
        anchors.update(input=(input_end, "left"), output=(output_end, "right"))
        if block.kind == "rc":
            shunt = next(
                r
                for r in design["relationships"]
                if r["kind"] == "shunt" and r["id"] in block.relationships
            )
            node = (second[0] + 4 * PITCH, second[1])
            d.add(shunt["component"], node[0], y + (11 if compact else 18) * PITCH)
            top, bottom = d.point(shunt["component"], "1"), d.point(shunt["component"], "2")
            d.route(relation["output"], second, node, top)
            d.route(relation["output"], node, output_end)
            d.junctions.append(node)
            ref_end = (bottom[0], bottom[1] + (2 if compact else 5) * PITCH)
            d.route(shunt["reference"], bottom, ref_end)
            anchors["reference"] = (ref_end, "down")
    return _finish(design, resolved, block, d, anchors)


def _interface_fragment(
    design: dict, resolved: dict[str, Asset], block: BlockPlan
) -> FragmentVariant:
    component_id = next(iter(block.occurrences))[0]
    d = _new_draft(design, resolved)
    d.add(component_id, 12 * PITCH, 16 * PITCH)
    anchors = {}
    for port in block.ports:
        pin = port.terminals[0][1]
        point = d.point(component_id, pin)
        end = (point[0] - 2 * PITCH, point[1])
        d.route(port.net, point, end)
        anchors[port.id.rsplit(".", 1)[-1]] = (end, "left")
    return _finish(design, resolved, block, d, anchors)


def _access_alternatives(
    design: dict,
    resolved: dict[str, Asset],
    base: FragmentVariant,
) -> tuple[FragmentVariant, ...]:
    """Derive finite gateway alternatives from the same complete local motif."""
    suffixes = {gateway.id.rsplit(".", 1)[-1]: gateway for gateway in base.gateways}
    configurable = [
        name
        for name in ("input", "supply", "positive", "reference", "output", "negative", "pin1")
        if name in suffixes
    ]
    if not configurable:
        return (base,)
    allowed_by_kind = {
        "power_stage": ("right", "up", "down"),
        "timer": ("right", "up", "down"),
        "buffer": ("right", "up", "down"),
        "unused_amplifier": ("right", "up", "down"),
        "noninverting_amplifier": ("right", "up", "down"),
        "inverting_amplifier": ("right", "up", "down"),
        "sallen_key": ("right", "up", "down"),
        "series": ("right", "up", "down"),
        "rc": ("right", "up", "down"),
        "led_branch": ("up", "right", "left"),
        "package_power": ("up", "right", "left"),
        "interface": ("left", "up", "down"),
    }
    variants = [base]
    gateway_points = {gateway.point for gateway in base.gateways}
    alternatives = [
        (name, direction)
        for name in configurable
        for direction in allowed_by_kind.get(base.block.kind, (suffixes[name].escape_direction,))
        if direction != suffixes[name].escape_direction
    ]
    for name, direction in alternatives:
        draft = Draft(
            design,
            resolved,
            dict(base.positions),
            dict(base.angles),
            list(base.wires[: len(base.protected_wires)]),
            list(base.wire_nets[: len(base.protected_wires)]),
            [item for item in base.labels if item[1] not in gateway_points],
            list(base.junctions),
            dict(base.text_positions),
        )
        anchors = {
            suffix: (
                gateway.anchor,
                direction if name == suffix else gateway.escape_direction,
            )
            for suffix, gateway in suffixes.items()
        }
        try:
            variant = _finish(
                design,
                resolved,
                base.block,
                draft,
                anchors,
                variant_suffix=f"v{len(variants)}",
            )
        except InputError:
            continue
        variants.append(
            FragmentVariant(
                **{
                    **variant.__dict__,
                    "rule_id": f"m2g2.local-access.{base.block.kind}.{name}.{direction}.v1",
                }
            )
        )
    distinct = {}
    for variant in variants:
        signature = tuple(
            (gateway.id.rsplit(".", 1)[-1], gateway.escape_direction)
            for gateway in variant.gateways
        )
        width = variant.envelope[2] - variant.envelope[0]
        height = variant.envelope[3] - variant.envelope[1]
        key = (signature, width, height)
        distinct.setdefault(key, variant)
    available = [variant for variant in variants if variant in distinct.values()]
    retained = [base]
    base_directions = {
        gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction for gateway in base.gateways
    }
    for name in configurable:
        representative = next(
            (
                variant
                for variant in available[1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == name
                    and gateway.escape_direction != base_directions.get(name)
                    for gateway in variant.gateways
                )
            ),
            None,
        )
        if representative is not None and representative not in retained:
            retained.append(representative)
    for variant in available[1:]:
        if variant not in retained:
            retained.append(variant)
        if len(retained) == 8:
            break
    return tuple(retained[:8])


def fragment_variants(
    design: dict, resolved: dict[str, Asset], plan: SemanticPlan
) -> dict[str, tuple[FragmentVariant, ...]]:
    """Build finite local variants without inspecting unrelated blocks."""
    result = {}
    for block in plan.blocks:
        if block.kind in {
            "buffer",
            "unused_amplifier",
            "noninverting_amplifier",
            "inverting_amplifier",
            "sallen_key",
        }:
            bases = [_amplifier_fragment(design, resolved, block)]
            try:
                bases.append(
                    _amplifier_fragment(
                        design,
                        resolved,
                        block,
                        feedback_side="above",
                    )
                )
            except InputError:
                pass
        elif block.kind == "package_power":
            bases = [_package_fragment(design, resolved, block)]
            try:
                bases.append(
                    _package_fragment(
                        design,
                        resolved,
                        block,
                        reference_side="up",
                    )
                )
            except InputError:
                pass
        elif block.kind == "power_stage":
            bases = [_power_stage_fragment(design, resolved, block)]
        elif block.kind == "timer":
            bases = [_timer_fragment(design, resolved, block)]
            try:
                bases.append(_timer_fragment(design, resolved, block, compact=True))
            except InputError:
                pass
        elif block.kind in {"series", "rc", "led_branch"}:
            bases = [_passive_fragment(design, resolved, block)]
            if block.kind in {"rc", "led_branch"}:
                try:
                    bases.append(_passive_fragment(design, resolved, block, compact=True))
                except InputError:
                    pass
        elif block.kind == "interface":
            bases = [_interface_fragment(design, resolved, block)]
        else:
            raise InputError(f"FRAGMENT_KIND_UNSUPPORTED: {block.id}:{block.kind}")
        families = [_access_alternatives(design, resolved, base) for base in bases]
        retained = []
        for rank in range(max(map(len, families))):
            for family_index, family in enumerate(families):
                if rank >= len(family):
                    continue
                candidate = family[rank]
                signature = (
                    tuple(sorted(candidate.positions.items())),
                    candidate.wires,
                    tuple(
                        (gateway.id, gateway.escape_direction, gateway.point)
                        for gateway in candidate.gateways
                    ),
                    candidate.envelope,
                )
                if any(item[0] == signature for item in retained):
                    continue
                retained.append((signature, candidate, family_index))
                if len(retained) == 8:
                    break
            if len(retained) == 8:
                break

        def structural_name(index: int) -> str:
            if block.kind in {"timer", "rc", "led_branch"}:
                return "compact" if index else "expanded"
            return "above" if index else "below"

        result[block.id] = tuple(
            replace(
                candidate,
                id=f"{block.id}.v{index}",
                rule_id=(
                    f"m2g2.local-aspect.{block.kind}.{structural_name(family_index)}.v1"
                    if len(families) > 1
                    else candidate.rule_id
                ),
            )
            for index, (_, candidate, family_index) in enumerate(retained)
        )
    return result
