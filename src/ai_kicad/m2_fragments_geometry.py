"""Implementation details for m2 fragments geometry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ir import InputError
from .m2_fragments_base import (
    FragmentVariant,
    PortAnchor,
    _body_rect,
    _place_component_text,
    _component,
    _occupied_geometry,
    _placed_terminal_points,
    _reservation_envelope,
)
from .m2_fragments_types import Point
from .m2_geometry import (
    AccessWindow,
    ConductorSegment,
    Gateway,
    PathObligation,
    ProtectedPath,
    Reservation,
    canonical_conductor_tree,
    content_envelope,
    label_text_rect,
    prove_gateway_witnesses,
    prove_no_cross_net_contacts,
    segment_is_admissible,
)
from .m2a_constants import PITCH
from .m2b import (
    Draft,
    choose_text_slots,
    pin_number_rectangles,
)

if TYPE_CHECKING:
    from .m2_semantics_core import BlockPlan
    from .m2a_core import Asset


def _finish(
    design: dict,
    resolved: dict[str, Asset],
    block: BlockPlan,
    draft: Draft,
    anchors: dict[str, tuple[Point, str]],
    *,
    variant_suffix: str = "v0",
    alternate_text_slots: bool = False,
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
        emit_label = (
            port.net in local_only_nets
            or port.net in interface_nets
            or (
                port.role in {"power_in", "power_out"}
                and not any(
                    relation["kind"] == "reference_divider" and relation["local"] == port.net
                    for relation in design["relationships"]
                )
            )
        )
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
        escape_polyline = (anchor, gateway_point)
        label_stub: tuple[Point, Point] | None = None
        if emit_label:
            bodies = [
                _body_rect(design, resolved, draft, occurrence)
                for occurrence in draft.positions
                if occurrence[0] in component_ids
            ]
            pin_text = []
            for occurrence, (sx, sy) in draft.positions.items():
                if occurrence[0] in component_ids:
                    component = _component(design, occurrence[0])
                    pin_text.extend(
                        pin_number_rectangles(
                            resolved[component["asset"]].definition,
                            occurrence[1],
                            sx,
                            sy,
                            draft.angles.get(occurrence, 0),
                        )
                    )
            step_x, step_y = {
                "left": (-PITCH, 0),
                "right": (PITCH, 0),
                "up": (0, -PITCH),
                "down": (0, PITCH),
            }[direction]
            for _ in range(32):
                x, y = gateway_point
                label_box = label_text_rect(port.net, (x, y))
                if not any(
                    max(label_box[0], body[0]) < min(label_box[2], body[2])
                    and max(label_box[1], body[1]) < min(label_box[3], body[3])
                    for body in bodies
                ):
                    break
                gateway_point = (x + step_x, y + step_y)
            else:
                raise InputError(f"LABEL_ESCAPE_INFEASIBLE: {port.id}")
            escape_polyline = (anchor, gateway_point)
            box = label_text_rect(port.net, gateway_point)
            if any(
                max(box[0], r[0]) < min(box[2], r[2]) and max(box[1], r[1]) < min(box[3], r[3])
                for r in pin_text
            ):
                original = gateway_point
                if len(block.ports) > 1:
                    candidates = tuple(
                        (original[0] + step * step_x, original[1] + step * step_y)
                        for step in range(1, 9)
                    )
                else:
                    # A single port keeps one straight outward lead. Its label
                    # hangs from the lead's end on a short orthogonal label
                    # stub that exists only to carry the label; composition
                    # drops the stub together with a redundant label, so a
                    # physically routed lead never folds back on itself.
                    orthogonal_steps = (2, -2, 3, -3, 4, -4, 6, -6)
                    candidates = (
                        tuple(
                            (original[0], original[1] + step * PITCH) for step in orthogonal_steps
                        )
                        if direction in {"left", "right"}
                        else tuple(
                            (original[0] + step * PITCH, original[1]) for step in orthogonal_steps
                        )
                    )
                for candidate in candidates:
                    box = label_text_rect(port.net, candidate)
                    if all(
                        max(box[0], r[0]) >= min(box[2], r[2])
                        or max(box[1], r[1]) >= min(box[3], r[3])
                        for r in bodies + pin_text
                    ):
                        if len(block.ports) > 1:
                            gateway_point = candidate
                            escape_polyline = (anchor, gateway_point)
                        else:
                            label_stub = (original, candidate)
                        break
                else:
                    raise InputError(f"LABEL_PIN_TEXT_ESCAPE_INFEASIBLE: {port.id}")
        draft.route(port.net, *escape_polyline)
        if label_stub is not None:
            draft.route(port.net, *label_stub)
        if emit_label:
            # A label at the gateway's source is redundant on the same escape
            # conductor and can overlap the final gateway label.
            draft.labels = [item for item in draft.labels if item != (port.net, anchor)]
            draft.label(port.net, label_stub[1] if label_stub is not None else gateway_point)
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
            escape_polyline,
            frozenset({direction}),
            (access,),
        )
        gateway.validate(terminal_nets)
        gateways.append(gateway)
        ports.append(PortAnchor(port, gateway_point, direction))

    draft.labels = list(dict.fromkeys(draft.labels))
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
    choose_text_slots(design, draft, alternate=alternate_text_slots)
    _place_component_text(design, resolved, draft)
    del draft.wires[emitted_wire_count:]
    del draft.wire_nets[emitted_wire_count:]
    occupied = _occupied_geometry(design, resolved, draft, block)
    body_keepouts = tuple(
        Reservation(f"body.{item.id}", "exclusive", item.owner, "body", item.rect)
        for item in occupied
        if item.kind == "body"
    )
    for gateway in gateways:
        if not (
            block.kind == "package_power"
            and "compact" in variant_suffix
            and gateway.id.endswith(".reference")
        ):
            continue
        direction = {
            "left": (-PITCH, 0),
            "right": (PITCH, 0),
            "up": (0, -PITCH),
            "down": (0, PITCH),
        }[gateway.escape_direction]
        outside = (gateway.point[0] + direction[0], gateway.point[1] + direction[1])
        if not segment_is_admissible(
            gateway.point,
            outside,
            body_keepouts,
            (),
            net=gateway.net,
            owner=f"gateway.{gateway.id}",
        ):
            raise InputError(f"FRAGMENT_GATEWAY_BODY_BLOCKED: {gateway.id}")
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
    prove_no_cross_net_contacts(local_segments)
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
