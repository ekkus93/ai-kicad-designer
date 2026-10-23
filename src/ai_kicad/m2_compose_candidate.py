"""Implementation details for m2 compose candidate."""

from __future__ import annotations

from dataclasses import dataclass

from .ir import InputError
from .m2_compose_repairs import ConductorLengthConflict
from .m2_conflicts import ConflictKind, TypedConflict
from .m2_geometry import (
    ConductorSegment,
    GeometryItem,
    Reservation,
    canonical_conductor_tree,
    label_text_rect,
    prove_conductor_graph,
    prove_gateway_witnesses,
    prove_no_cross_net_contacts,
    prove_reservation_allocation,
)
from .m2_pack import (
    BOTTOM,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    RIGHT,
    TOP,
    Packing,
)
from .m2_route import (
    _interface_enclosures,
    _optional_reference_nets,
    _routable_edges,
    route_between_fragments,
)
from .m2_semantics import check_placement_constraints
from .m2a import PITCH
from .m2b import Draft, measure


@dataclass(frozen=True)
class StageGraph:
    """Compatibility view of signal-like relationship ordering."""

    ports: dict[str, tuple[str, str]]
    order: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]


class LayoutBudgetError(InputError):
    """Bounded composition failure retaining every completed attempt."""

    def __init__(self, message: str, attempts: tuple[dict, ...], evidence: dict | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.evidence = evidence or {}


def stage_graph(design: dict) -> StageGraph:
    """Return the legacy relation projection; composition uses the typed plan."""
    ports = {
        relation["id"]: (relation["input"], relation["output"])
        for relation in design["relationships"]
        if relation["kind"] in ("series", "amplifier", "power_stage") and not relation.get("unused")
    }
    ports.update(
        (relation["id"], (relation["supply"], relation["output"]))
        for relation in design["relationships"]
        if relation["kind"] == "timer"
    )
    edges = tuple(
        sorted(
            (first, second, output)
            for first, (_, output) in ports.items()
            for second, (input_net, _) in ports.items()
            if first != second and output == input_net
        )
    )
    remaining, order = set(ports), []
    while remaining:
        ready = sorted(
            stage
            for stage in remaining
            if not any(first in remaining and second == stage for first, second, _ in edges)
        )
        if not ready:
            raise InputError(f"unsupported stage graph cycle: {sorted(remaining)}")
        order.extend(ready)
        remaining.difference_update(ready)
    return StageGraph(ports, tuple(order), edges)


def _translate(point: tuple[int, int], delta: tuple[int, int]) -> tuple[int, int]:
    return point[0] + delta[0], point[1] + delta[1]


def _translated_rect(rect, delta):
    return tuple(value + shift for value, shift in zip(rect, (*delta, *delta), strict=True))


def _source_marker_placement(candidates, body, obstacles, wires=()):
    """Choose one existing electrical contact and a measured glyph orientation."""
    left, top, right, bottom = body
    for point in dict.fromkeys(candidates):
        for angle in (0, 180):
            local = (left, -top, right, -bottom)
            if angle == 180:
                local = (-right, bottom, -left, top)
            rect = tuple(v + d for v, d in zip(local, (*point, *point), strict=True))
            if rect[0] < LEFT or rect[1] < TOP or rect[2] > RIGHT or rect[3] > BOTTOM:
                continue
            if any(
                max(rect[0], other[0]) < min(rect[2], other[2])
                and max(rect[1], other[1]) < min(rect[3], other[3])
                for other in obstacles
            ):
                continue
            if any(
                (
                    first[0] == second[0]
                    and rect[0] < first[0] < rect[2]
                    and max(min(first[1], second[1]), rect[1])
                    < min(max(first[1], second[1]), rect[3])
                )
                or (
                    first[1] == second[1]
                    and rect[1] < first[1] < rect[3]
                    and max(min(first[0], second[0]), rect[0])
                    < min(max(first[0], second[0]), rect[2])
                )
                for first, second in wires
            ):
                continue
            return point, angle, rect
    raise InputError("COMPOSE_SOURCE_GLYPH_CLEARANCE: no measured source-marker slot")


def _assemble_candidate(design: dict, resolved: dict, plan, packing: Packing, retry: int):
    draft = Draft(design, resolved, {}, {}, [], [], [], [], {})
    conductors: list[ConductorSegment] = []
    reservations = [reservation for item in packing.fragments for reservation in item.reservations]
    occupied = []
    for placed in packing.fragments:
        fragment, delta = placed.fragment, placed.delta
        for key, point in fragment.positions.items():
            if key in draft.positions:
                raise TypedConflict(
                    ConflictKind.OWNERSHIP,
                    f"COMPOSE_GEOMETRY_OWNER_CONFLICT: {key}",
                    owners=(key[0],),
                )
            draft.positions[key] = _translate(point, delta)
        draft.angles.update(fragment.angles)
        draft.mirrors.update(fragment.mirrors)
        draft.text_positions.update(
            (key, _translate(point, delta)) for key, point in fragment.text_positions.items()
        )
        draft.labels.extend((net, _translate(point, delta)) for net, point in fragment.labels)
        occupied.extend(
            GeometryItem(
                item.id,
                item.kind,
                item.owner,
                _translated_rect(item.rect, delta),
                item.provenance,
            )
            for item in fragment.occupied_geometry
        )
        conductors.extend(
            ConductorSegment(
                _translate(first, delta),
                _translate(second, delta),
                net,
                fragment.block.id,
                provenance,
            )
            for (first, second), net, provenance in zip(
                fragment.wires,
                fragment.wire_nets,
                fragment.wire_provenance,
                strict=True,
            )
        )

    # Pin inequalities are hard gates on this exact translated candidate.
    placement_proofs = check_placement_constraints(plan, draft.point)

    route_trees = route_between_fragments(plan, packing.fragments, retry_index=retry)
    for tree in route_trees:
        reservations.extend(tree.planned_corridors)
        conductors.extend(
            ConductorSegment(first, second, tree.net, tree.owner, provenance)
            for (first, second), provenance in zip(
                tree.segments, tree.segment_provenance, strict=True
            )
        )
        for index, (first, second) in enumerate(tree.segments):
            occupied.append(
                GeometryItem(
                    f"route.{tree.net}.{index}",
                    "wire",
                    tree.owner,
                    (
                        min(first[0], second[0]),
                        min(first[1], second[1]),
                        max(first[0], second[0]),
                        max(first[1], second[1]),
                    ),
                    (tree.net, *tree.segment_provenance[index]),
                )
            )

    canonical_trees = []
    pruned_route_leaves: dict[str, int] = {}
    for net in sorted({segment.net for segment in conductors}):
        pins = tuple(
            draft.point(component["id"], pin.number)
            for component in design["components"]
            for unit, unit_pins in resolved[component["asset"]].units.items()
            if (component["id"], unit) in draft.positions
            for pin in unit_pins
            if any(
                net_item["id"] == net and [component["id"], pin.number] in net_item["members"]
                for net_item in design["nets"]
            )
        )
        required_contacts = (
            set(pins)
            | {point for label_net, point in draft.labels if label_net == net}
            | {
                gateway.point
                for item in packing.fragments
                for gateway in item.gateways
                if gateway.net == net
            }
        )
        net_segments = tuple(segment for segment in conductors if segment.net == net)
        removed = 0
        while True:
            tree = canonical_conductor_tree(
                net_segments,
                junctions=(
                    *draft.junctions,
                    *(point for route in route_trees for point in route.junctions),
                ),
                pins=pins,
            )
            redundant = {
                segment
                for segment in tree.segments
                if any(
                    tree.degree.get(point) == 1 and point not in required_contacts
                    for point in (segment.start, segment.end)
                )
            }
            if not redundant:
                break
            net_segments = tuple(segment for segment in tree.segments if segment not in redundant)
            removed += len(redundant)
            if not net_segments:
                raise InputError(f"CONDUCTOR_NET_MISSING: {net}")
        if removed:
            pruned_route_leaves[net] = removed
        canonical_trees.append(tree)
    conductors = [segment for tree in canonical_trees for segment in tree.segments]
    assertion_points = {}
    assertion_glyphs = {}
    marker_obstacles = [
        item.rect for item in occupied if item.kind in {"body", "text", "label", "pin"}
    ]
    marker_obstacles.extend(label_text_rect(net, point) for net, point in draft.labels)
    for assertion in design["power_assertions"]:
        candidates = sorted(point for net, point in draft.labels if net == assertion["net"])
        candidates.extend(
            sorted(
                gateway.point
                for item in packing.fragments
                for gateway in item.gateways
                if gateway.net == assertion["net"]
            )
        )
        candidates.extend(
            sorted(
                {
                    point
                    for tree in canonical_trees
                    if tree.net == assertion["net"]
                    for segment in tree.segments
                    for point in (segment.start, segment.end)
                }
            )
        )
        if not candidates:
            raise InputError(
                f"COMPOSE_ASSERTION_PORT_MISSING: {assertion['id']}:{assertion['net']}"
            )
        source_body = resolved["power:PWR_FLAG"].bodies[0]
        point, angle, rect = _source_marker_placement(
            candidates,
            source_body,
            marker_obstacles,
            [(segment.start, segment.end) for segment in conductors],
        )
        assertion_points[assertion["id"]] = point
        assertion_glyphs[assertion["id"]] = rect
        draft.angles[(assertion["id"], 1)] = angle
        marker_obstacles.append(rect)
    net_proofs = []
    presentation_by_net = {item.id: item for item in plan.presentation_nets}
    for tree in canonical_trees:
        presentation = presentation_by_net.get(tree.net)
        if presentation is None:
            raise InputError(f"CONDUCTOR_NET_UNDECLARED: {tree.net}")
        net_proofs.append(
            prove_conductor_graph(
                tree,
                {terminal: draft.point(*terminal) for terminal in presentation.terminals},
                labels=(point for net, point in draft.labels if net == tree.net),
                allow_labeled_islands=not presentation.explicit_geometry_required,
                # The canonical junction inventory is the one serialization
                # will write; earlier local lists are construction inputs.
                declared_junctions=tree.junctions,
                intentional_ends=(
                    *(
                        gateway.point
                        for item in packing.fragments
                        for gateway in item.gateways
                        if gateway.net == tree.net and not presentation.explicit_geometry_required
                    ),
                    *(
                        assertion_points[assertion["id"]]
                        for assertion in design["power_assertions"]
                        if assertion["net"] == tree.net
                    ),
                ),
            )
        )
    missing_nets = set(presentation_by_net) - {tree.net for tree in canonical_trees}
    if missing_nets:
        raise InputError(f"CONDUCTOR_NET_MISSING: {sorted(missing_nets)}")
    tree_by_net = {tree.net: tree for tree in canonical_trees}
    gateway_proofs = []
    for item in packing.fragments:
        for gateway in item.gateways:
            tree = tree_by_net.get(gateway.net)
            if tree is None:
                raise TypedConflict(
                    ConflictKind.GATEWAY_WITNESS,
                    f"GATEWAY_NET_MISSING: {gateway.id}:{gateway.net}",
                    net=gateway.net,
                    owners=(item.fragment.block.id,),
                    repair_classes=("gateway_access", "distribution_placement"),
                )
            proved = prove_gateway_witnesses(
                tree,
                gateway,
                {terminal: draft.point(*terminal) for terminal in gateway.terminals},
                require_escape=False,
            )
            gateway_proofs.append((gateway, proved))
    prove_no_cross_net_contacts(conductors)
    terminal_inventory = {item.terminal for item in plan.terminals if item.net}
    proved_terminals = {
        terminal for proof in net_proofs for terminal, _ in proof.terminal_components
    }
    if terminal_inventory != proved_terminals:
        raise InputError(
            f"COMPOSE_TERMINAL_INVENTORY: missing={sorted(terminal_inventory - proved_terminals)} "
            f"extra={sorted(proved_terminals - terminal_inventory)}"
        )
    excessive = [tree for tree in canonical_trees if tree.length > 250_000_000]
    if excessive:
        worst = max(excessive, key=lambda tree: (tree.length, tree.net))
        local_segments = [
            segment
            for segment in conductors
            if segment.net == worst.net and not segment.owner.startswith("tree.")
        ]
        global_segments = [
            segment
            for segment in conductors
            if segment.net == worst.net and segment.owner.startswith("tree.")
        ]
        local_length = canonical_conductor_tree(local_segments).length if local_segments else 0
        global_length = canonical_conductor_tree(global_segments).length if global_segments else 0
        raise ConductorLengthConflict(worst.net, worst.length, local_length, global_length)
    draft.wires = [
        (segment.start, segment.end) for tree in canonical_trees for segment in tree.segments
    ]
    draft.wire_nets = [tree.net for tree in canonical_trees for _ in tree.segments]
    draft.junctions = [point for tree in canonical_trees for point in tree.junctions]

    component_ids = {component["id"] for component in design["components"]}
    expected = set(plan.owners)
    actual = {key for key in draft.positions if key[0] in component_ids}
    if actual != expected:
        raise TypedConflict(
            ConflictKind.OWNERSHIP,
            f"COMPOSE_OWNER_INCOMPLETE: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}",
            owners=tuple(sorted({item[0] for item in expected ^ actual})),
        )
    for assertion in design["power_assertions"]:
        point = assertion_points[assertion["id"]]
        draft.positions[(assertion["id"], 1)] = point
        # KiCad serializes hidden source properties too. Give them a measured
        # on-page position instead of the emitter's unmeasured fallback offset.
        draft.text_positions[(assertion["id"], 1)] = (
            min(max(point[0], LEFT), RIGHT),
            min(max(point[1], TOP + 2 * PITCH), BOTTOM - 2 * PITCH),
        )
        text_x, text_y = draft.text_positions[(assertion["id"], 1)]
        for offset in (0, 2 * PITCH):
            property_item = GeometryItem(
                f"{assertion['id']}.hidden_property.{offset}",
                "source_property",
                assertion["id"],
                (text_x, text_y + offset, text_x, text_y + offset),
            )
            occupied.append(property_item)
            reservations.append(
                Reservation(
                    f"source_property.{assertion['id']}.{offset}",
                    "exclusive",
                    assertion["id"],
                    "source_property",
                    property_item.rect,
                )
            )
        glyph = GeometryItem(
            assertion["id"],
            "source_glyph",
            assertion["id"],
            assertion_glyphs[assertion["id"]],
        )
        occupied.append(glyph)
        reservations.append(
            Reservation(
                f"source.{assertion['id']}",
                "exclusive",
                assertion["id"],
                "source_glyph",
                glyph.rect,
            )
        )

    # Locked KiCad A4 worksheet: native border starts at (177.0022, 166.0072) mm.
    # Reserve its stroke as an obstacle independently of the 210 x 140 spread gate.
    worksheet = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
    page_geometry = [item.rect for item in occupied] + [
        (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])) for a, b in draft.wires
    ]
    for rectangle in page_geometry:
        if (
            rectangle[0] < worksheet[2]
            and rectangle[2] > worksheet[0]
            and rectangle[1] < worksheet[3]
            and rectangle[3] > worksheet[1]
        ):
            raise TypedConflict(
                ConflictKind.PAGE_SPREAD,
                f"PAGE_WORKSHEET_OVERLAP: geometry={rectangle}",
                offending_geometry=(rectangle,),
            )

    allocation_witnesses = prove_reservation_allocation(occupied, reservations)
    final_rect = (
        min(item.rect[0] for item in occupied),
        min(item.rect[1] for item in occupied),
        max(item.rect[2] for item in occupied),
        max(item.rect[3] for item in occupied),
    )
    # The packing corridor uses an inset search box. Final occupied geometry
    # is certified against the historical A4 content margins themselves.
    if (
        final_rect[0] < 20_320_000
        or final_rect[1] < 25_400_000
        or final_rect[2] > 276_680_000
        or final_rect[3] > 184_600_000
    ):
        raise TypedConflict(
            ConflictKind.PAGE_SPREAD,
            f"PAGE_CONTENT_OVERFLOW: final={final_rect}",
            offending_geometry=(final_rect,),
        )
    final_width = final_rect[2] - final_rect[0]
    final_height = final_rect[3] - final_rect[1]
    if final_width > MAX_CONTENT_WIDTH or final_height > MAX_CONTENT_HEIGHT:
        raise TypedConflict(
            ConflictKind.PAGE_SPREAD,
            f"SPREAD_OVERFLOW: actual={final_width}x{final_height} "
            f"threshold={MAX_CONTENT_WIDTH}x{MAX_CONTENT_HEIGHT}",
            offending_geometry=(final_rect,),
            actual=max(final_width, final_height),
            limit=max(MAX_CONTENT_WIDTH, MAX_CONTENT_HEIGHT),
        )
    metrics = measure(design, resolved, draft)
    invalid_metrics = {
        key: metrics.get(key)
        for key in (
            "body_overlap_count",
            "wire_through_body_count",
            "wire_through_text_count",
            "unrelated_wire_crossing_count",
            "unrouted_pin_count",
        )
        if metrics.get(key) != 0
    }
    if invalid_metrics or not metrics.get("page_margin_pass"):
        raise TypedConflict(
            ConflictKind.COLLISION,
            f"COMPOSE_GEOMETRY_CERTIFICATE_FAILED: collisions={invalid_metrics} "
            f"page_margin={metrics.get('page_margin_pass')}",
            owners=tuple(sorted(invalid_metrics)),
        )
    metrics.update(
        {
            "semantic_block_count": len(plan.blocks),
            "semantic_edge_count": len(plan.edges),
            "packing_attempts": list(packing.attempts),
            "final_content_envelope": list(final_rect),
            "final_content_width_mm": final_width / 1_000_000,
            "final_content_height_mm": final_height / 1_000_000,
            "reservation_containment_pass": True,
            "reservation_allocation_count": len(allocation_witnesses),
            "reservation_allocation_witnesses": [
                {"owner": owner, "geometry": item, "reservation": reservation}
                for owner, item, reservation in allocation_witnesses
            ],
            "pre_emission_conductor_components": {
                proof.net: len(proof.components) for proof in net_proofs
            },
            "pre_emission_terminal_coverage": {
                proof.net: len(proof.terminal_components) for proof in net_proofs
            },
            "pre_emission_precedence_count": len(plan.precedence),
            "pruned_route_leaves": pruned_route_leaves,
            "pre_emission_placement_proofs": [list(item) for item in placement_proofs],
            "pre_emission_net_witnesses": [
                {
                    "net": proof.net,
                    "component_count": len(proof.components),
                    "terminal_components": [
                        [list(terminal), component]
                        for terminal, component in proof.terminal_components
                    ],
                    "label_components": [
                        [list(point), component] for point, component in proof.label_components
                    ],
                    "canonical_length_nm": proof.length,
                }
                for proof in net_proofs
            ],
            "pre_emission_terminal_inventory_count": len(terminal_inventory),
            "pre_emission_gateway_witness_count": len(gateway_proofs),
            "pre_emission_gateway_witnesses": [
                {
                    "id": gateway.id,
                    "net": gateway.net,
                    "point": list(gateway.point),
                    "anchor": list(gateway.anchor),
                    "terminals": [
                        {"id": list(terminal), "point": list(draft.point(*terminal))}
                        for terminal in proved
                    ],
                    "proved": True,
                }
                for gateway, proved in gateway_proofs
            ],
            "pre_emission_local_span_count": len(plan.local_spans),
        }
    )
    return draft, route_trees, canonical_trees, tuple(reservations), metrics


def _structural_signature(packing: Packing) -> tuple[tuple, ...]:
    """Normalize row and left-to-right decisions without absolute coordinates."""
    items = tuple(item for item in packing.fragments if item.fragment.block.kind != "interface")
    x_order = {
        item.fragment.block.id: index
        for index, item in enumerate(
            sorted(
                items,
                key=lambda item: (
                    item.envelope[0] + item.envelope[2],
                    item.fragment.block.id,
                ),
            )
        )
    }
    band_tops = []
    band_by_top = {}
    for top in sorted({item.envelope[1] for item in items}):
        if not band_tops or top - band_tops[-1] > PITCH:
            band_tops.append(top)
        band_by_top[top] = len(band_tops) - 1
    return tuple(
        (
            item.fragment.block.kind,
            x_order[item.fragment.block.id],
            band_by_top[item.envelope[1]],
            item.envelope[2] - item.envelope[0] > item.envelope[3] - item.envelope[1],
        )
        for item in sorted(items, key=lambda item: item.fragment.block.id)
    )


def _route_interface_enclosure_count(plan, draft: Draft, canonical_trees) -> int:
    """Count route trees that frame a connector belonging to another net."""
    interface_points = {}
    for block in plan.blocks:
        if block.kind != "interface":
            continue
        for port in block.ports:
            interface_points.setdefault(port.net, set()).update(
                draft.point(*terminal) for terminal in port.terminals
            )
    return sum(
        _interface_enclosures(
            tree,
            tuple(
                point
                for net, points in interface_points.items()
                if net != tree.net
                for point in sorted(points)
            ),
        )
        for tree in canonical_trees
    )


def _missing_interface_output_routes(plan, route_trees) -> int:
    """Count inferred signal outputs that lack a physical route to a connector."""
    blocks = {block.id: block for block in plan.blocks}
    required = {
        edge.net
        for edge in _routable_edges(plan)
        if blocks[edge.source].kind != "interface"
        and blocks[edge.target].kind == "interface"
        and any(
            port.net == edge.net and port.role == "signal_out" for port in blocks[edge.source].ports
        )
    }
    routed = {tree.net for tree in route_trees}
    return len(required - routed)


def _missing_optional_reference_routes(plan, route_trees) -> int:
    """Count external reference nets left to labels although a tree was eligible."""
    routed = {tree.net for tree in route_trees}
    return len(_optional_reference_nets(plan) - routed)
