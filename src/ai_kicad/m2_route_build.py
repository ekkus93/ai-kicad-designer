"""Implementation details for m2 route build."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_conflicts import ConflictKind, TypedConflict
from .m2_fragments_types import Point
from .m2_geometry import (
    ConductorSegment,
    Gateway,
    Reservation,
    canonical_conductor_tree,
    point_on_segment,
)
from .m2_pack_core import PlacedFragment
from .m2_route_constants import (
    MAX_CANONICAL_LENGTH,
    MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH,
    MAX_TAPS_PER_ATTACHMENT,
)
from .m2_route_core import (
    RouteBlockedConflict,
    RouteLengthBoundConflict,
    RouteTree,
    _advance,
    _connect,
    _escape_obstacles,
    _gateway,
    _gateway_channel,
    _interface_enclosures,
    _path_legal,
    _point_to_trunk_distance,
)
from .m2_route_trees import (
    _distribution_initial_trees,
    _optional_local_visible_edges,
    _optional_reference_nets,
    _route_class,
)
from .m2_semantics_core import SemanticEdge
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def route_between_fragments(
    plan: SemanticPlan,
    placed: tuple[PlacedFragment, ...],
    *,
    retry_index: int = 0,
) -> tuple[RouteTree, ...]:
    """Attach all required gateways with one obstacle-checked tree per net/island."""
    by_id = {item.fragment.block.id: item for item in placed}
    # Keep authored routing on its proved semantic edge inventory. Add only
    # unique, local passive-interface outputs from the inference pass; routing
    # every inferred pair broke dual-buffer and V5/V6 layouts.
    grouped: dict[str, list[SemanticEdge]] = {}
    for edge in plan.edges:
        if edge.net and edge.kind in {"signal", "power", "branch"}:
            grouped.setdefault(edge.net, []).append(edge)
    optional_output_edges = tuple(
        edge
        for edge in _optional_local_visible_edges(plan, placed)
        if any(
            port.net == edge.net and port.role == "signal_out"
            for port in by_id[edge.source].fragment.block.ports
        )
    )
    optional_output_nets = {edge.net for edge in optional_output_edges}
    for edge in optional_output_edges:
        grouped.setdefault(edge.net, []).append(edge)
    # External reference connectors may be represented by matching labels. A
    # complete physical tree is attempted first; when none is legal within the
    # route bounds the proven label presentation remains, and candidate
    # ranking prefers layouts whose reference tree is physical.
    optional_reference_nets = _optional_reference_nets(plan)
    for net in sorted(optional_reference_nets):
        grouped.setdefault(net, [])
    # A shared internal reference has no connector and may have no directed
    # edge at all. Its terminal inventory still demands a physical distribution.
    for net in plan.presentation_nets:
        if net.explicit_geometry_required and len(net.fragments) > 1:
            grouped.setdefault(net.id, [])
    distribution_nets = {
        item.id for item in plan.presentation_nets if item.explicit_geometry_required
    }
    shared_tree_nets = (
        distribution_nets
        | optional_reference_nets
        | optional_output_nets
        | {
            net
            for net, edges in grouped.items()
            if any(edge.kind == "power" for edge in edges)
            and len({owner for edge in edges for owner in (edge.source, edge.target)}) >= 3
            and any(
                port.net == net and port.role == "power_out"
                for block in plan.blocks
                for port in block.ports
            )
        }
    )

    def net_gateways(net: str) -> tuple[Gateway, ...]:
        return tuple(gateway for item in placed for gateway in item.gateways if gateway.net == net)

    def group_order(item: tuple[str, list[SemanticEdge]]) -> tuple[int, int, int, int, str]:
        net, edges = item
        priority = (
            2 if net in optional_reference_nets else (1 if net in optional_output_nets else 0)
        )
        endpoints = tuple((by_id[edge.source], True) for edge in edges) + tuple(
            (by_id[edge.target], False) for edge in edges
        )
        selected_by_id = {
            gateway.id: gateway
            for gateway in (_gateway(fragment, net, output) for fragment, output in endpoints)
        }
        if net in distribution_nets or not endpoints:
            selected_by_id.update((gateway.id, gateway) for gateway in net_gateways(net))
        selected = tuple(selected_by_id.values())
        if not selected:
            raise TypedConflict(
                ConflictKind.GATEWAY_WITNESS,
                f"ROUTE_REQUIRED_GATEWAY_MISSING: {net}",
                net=net,
            )
        legal_directions = min(len(gateway.approach_directions) for gateway in selected)
        fanout = len({gateway.id for gateway in selected})
        return priority, _route_class(edges), legal_directions, -fanout, net

    ordered_groups = sorted(grouped.items(), key=group_order)
    producer_fragments = {net.id: set(net.producer_fragments) for net in plan.presentation_nets}
    presentation_by_net = {net.id: net for net in plan.presentation_nets}
    gateway_fragment = {
        gateway.id: item.fragment.block.id for item in placed for gateway in item.gateways
    }
    active_gateway_ids = set()
    for net, edges in ordered_groups:
        for edge in edges:
            active_gateway_ids.add(_gateway(by_id[edge.source], net, True).id)
            active_gateway_ids.add(_gateway(by_id[edge.target], net, False).id)
        if net in distribution_nets or not edges:
            active_gateway_ids.update(gateway.id for gateway in net_gateways(net))
    scene_reservations = tuple(
        reservation for item in placed for reservation in item.reservations
    ) + tuple(
        _gateway_channel(gateway)
        for item in placed
        for gateway in item.gateways
        if gateway.id in active_gateway_ids
    )
    content_left = min(item.content_envelope[0] for item in placed if item.content_envelope)
    content_top = min(item.content_envelope[1] for item in placed if item.content_envelope)
    content_right = max(item.content_envelope[2] for item in placed if item.content_envelope)
    content_bottom = max(item.content_envelope[3] for item in placed if item.content_envelope)
    route_bounds = (
        content_right - 210_000_000,
        content_bottom - 140_000_000,
        content_left + 210_000_000,
        content_top + 140_000_000,
    )
    previous: list[tuple[str, Point, Point]] = []
    result = []
    for net, edges in ordered_groups:
        obstacles = tuple(
            reservation
            for reservation in scene_reservations
            if (
                reservation.occupancy == "exclusive"
                and reservation.clearance_class
                in {
                    "body",
                    "text",
                    "label",
                    "pin",
                    "wire",
                    "protected",
                }
                and not (
                    reservation.clearance_class
                    in ({"label", "wire", "protected"} if net in shared_tree_nets else {"label"})
                    and reservation.permitted_net == net
                )
            )
            or (reservation.occupancy == "channel" and reservation.permitted_net not in {None, net})
        )
        ordered = sorted(
            edges, key=lambda edge: (edge.source, edge.target, edge.kind, edge.origins)
        )
        gateways: dict[str, Gateway] = {}
        for edge in ordered:
            source = _gateway(by_id[edge.source], net, True)
            target = _gateway(by_id[edge.target], net, False)

            gateways[source.id] = source
            gateways[target.id] = target
        if net in distribution_nets or not ordered:
            gateways.update((gateway.id, gateway) for gateway in net_gateways(net))
        if net in distribution_nets:
            required = set(presentation_by_net[net].fragments)
            exposed = {gateway_fragment[gateway.id] for gateway in gateways.values()}
            if missing := required - exposed:
                raise TypedConflict(
                    ConflictKind.GATEWAY_WITNESS,
                    f"ROUTE_REQUIRED_GATEWAY_MISSING: {net}:{sorted(missing)}",
                    net=net,
                    owners=tuple(sorted(missing)),
                )
        role_by_id = {port.port.id: port.port.role for item in placed for port in item.ports}
        sources = sorted(
            (
                gateway
                for gateway in gateways.values()
                if role_by_id[gateway.id] in {"signal_out", "power_out"}
            ),
            key=lambda gateway: (len(gateway.approach_directions), gateway.id),
        )
        seed = (
            sources[0]
            if sources
            else min(
                gateways.values(),
                key=lambda gateway: (
                    gateway_fragment[gateway.id] not in producer_fragments.get(net, set()),
                    len(gateway.approach_directions),
                    gateway.id,
                ),
            )
        )
        owner = f"tree.{net}"
        seed_external = _advance(seed.point, seed.escape_direction, PITCH)
        if not _path_legal(
            (seed.point, seed_external),
            _escape_obstacles(obstacles, seed),
            tuple(previous),
            net=net,
            owner=owner,
            allowed_contacts=frozenset({seed.point}),
            route_bounds=route_bounds,
        ):
            if net in optional_output_nets or net in optional_reference_nets:
                continue
            raise RouteBlockedConflict(net, (seed.id,), 0, 0)
        local_conductors = tuple(
            ConductorSegment(
                (first[0] + item.delta[0], first[1] + item.delta[1]),
                (second[0] + item.delta[0], second[1] + item.delta[1]),
                net,
                item.fragment.block.id,
            )
            for item in placed
            for (first, second), wire_net in zip(
                item.fragment.wires, item.fragment.wire_nets, strict=True
            )
            if wire_net == net
        )
        plans = (
            _distribution_initial_trees(
                net,
                owner,
                seed,
                tuple(gateways.values()),
                obstacles,
                tuple(previous),
                route_bounds,
            )
            if net in shared_tree_nets and len(gateways) >= 3
            else (
                (
                    "producer_centered",
                    (ConductorSegment(seed.point, seed_external, net, owner, (seed.id, "seed")),),
                    None,
                    0,
                ),
            )
        )
        if net in optional_reference_nets:
            # Keep optional reference-tree search bounded to eight distinct
            # initial trunks. Other mandatory distributive nets keep the full
            # alternative search.
            plans = plans[:8]
        candidates = []
        blocked_plans = []
        length_prunes: list[int] = []
        aggregate_taps = aggregate_states = 0
        for strategy, initial, trunk, initial_expansions in plans:
            conductors = list(initial)
            fixed_length = canonical_conductor_tree((*local_conductors, *conductors)).length
            if fixed_length > MAX_CANONICAL_LENGTH:
                length_prunes.append(fixed_length)
                continue
            connected = {seed.id}
            tap_tests = 0
            state_expansions = initial_expansions
            try:
                while len(connected) != len(gateways):
                    base_tree = canonical_conductor_tree((*local_conductors, *conductors))
                    attachment_candidates = []
                    blocked_targets = []
                    inaccessible_targets = []
                    target_length_prunes = []
                    for target in sorted(
                        (gateway for gateway in gateways.values() if gateway.id not in connected),
                        key=lambda gateway: (len(gateway.approach_directions), gateway.id),
                    ):
                        target_external = _advance(target.point, target.escape_direction, PITCH)
                        if not _path_legal(
                            (target.point, target_external),
                            _escape_obstacles(obstacles, target),
                            tuple(previous),
                            net=net,
                            owner=owner,
                            allowed_contacts=frozenset({target.point}),
                            route_bounds=route_bounds,
                        ):
                            blocked_targets.append(target.id)
                            inaccessible_targets.append(target.id)
                            continue
                        taps = {
                            point
                            for segment in conductors
                            for point in (segment.start, segment.end)
                        }
                        for segment in conductors:
                            projection = (
                                (segment.start[0], target_external[1])
                                if segment.start[0] == segment.end[0]
                                else (target_external[0], segment.start[1])
                            )
                            if point_on_segment(projection, segment.start, segment.end):
                                taps.add(projection)
                        occupied_gateway_points = {
                            gateway.point
                            for gateway in gateways.values()
                            if gateway.id in connected
                        }
                        taps.difference_update(occupied_gateway_points)
                        ordered_taps = sorted(
                            taps,
                            key=lambda point: (
                                abs(point[0] - target_external[0])
                                + abs(point[1] - target_external[1]),
                                point[0],
                                point[1],
                            ),
                        )[:MAX_TAPS_PER_ATTACHMENT]
                        target_choices = []
                        target_had_length_prune = False
                        for tap in ordered_taps:
                            tap_tests += 1
                            route, expansions = _connect(
                                target_external,
                                tap,
                                obstacles,
                                tuple(previous),
                                net=net,
                                owner=owner,
                                allowed_contacts=frozenset({tap, target.point}),
                                route_bounds=route_bounds,
                            )
                            state_expansions += expansions
                            if route is not None:
                                trial_tree = canonical_conductor_tree(
                                    (
                                        *local_conductors,
                                        *conductors,
                                        ConductorSegment(
                                            target.point,
                                            target_external,
                                            net,
                                            owner,
                                            (target.id, "escape"),
                                        ),
                                        *(
                                            ConductorSegment(first, second, net, owner)
                                            for first, second in route
                                            if first != second
                                        ),
                                    )
                                )
                                if net in shared_tree_nets and any(
                                    (
                                        trial_tree.degree.get(gateway.point, 0) < 2
                                        or trial_tree.degree.get(
                                            _advance(
                                                gateway.point, gateway.escape_direction, PITCH
                                            ),
                                            0,
                                        )
                                        == 1
                                    )
                                    for gateway in gateways.values()
                                    if gateway.id in connected | {target.id}
                                    and not any(
                                        label_net == net
                                        and (point[0] + item.delta[0], point[1] + item.delta[1])
                                        == gateway.point
                                        for item in placed
                                        for label_net, point in item.fragment.labels
                                    )
                                ):
                                    # Returning through a local escape can make
                                    # its tip a dangling leaf after interval union.
                                    # Preserve actual attachment at every joined
                                    # gateway, not just electrical reachability.
                                    continue
                                bends = max(0, trial_tree.bends - base_tree.bends)
                                length = trial_tree.length - base_tree.length
                                if trial_tree.length > MAX_CANONICAL_LENGTH:
                                    target_length_prunes.append(trial_tree.length)
                                    target_had_length_prune = True
                                    continue
                                target_choices.append(
                                    (
                                        length,
                                        bends,
                                        target.id,
                                        tap[0],
                                        tap[1],
                                        target,
                                        target_external,
                                        tap,
                                        route,
                                    )
                                )
                        if not target_choices:
                            blocked_targets.append(target.id)
                            if not target_had_length_prune:
                                inaccessible_targets.append(target.id)
                        else:
                            target_choices.sort(key=lambda item: item[:5] + (item[8],))
                            attachment_candidates.append(
                                target_choices[min(retry_index, len(target_choices) - 1)]
                            )
                    if not attachment_candidates:
                        if target_length_prunes and not inaccessible_targets:
                            raise RouteLengthBoundConflict(net, min(target_length_prunes))
                        raise RouteBlockedConflict(
                            net, tuple(sorted(blocked_targets)), tap_tests, state_expansions
                        )
                    attachment_candidates.sort(key=lambda item: item[:5] + (item[8],))
                    _, _, _, _, _, target, target_external, tap, route = attachment_candidates[
                        min(retry_index, len(attachment_candidates) - 1)
                    ]
                    conductors.append(
                        ConductorSegment(
                            target.point,
                            target_external,
                            net,
                            owner,
                            (target.id, "escape"),
                        )
                    )
                    conductors.extend(
                        ConductorSegment(first, second, net, owner, (target.id, f"tap.{tap}"))
                        for first, second in route
                        if first != second
                    )
                    connected.add(target.id)
            except RouteBlockedConflict as conflict:
                aggregate_taps += conflict.taps
                aggregate_states += conflict.states
                blocked_plans.append(conflict)
                continue
            except RouteLengthBoundConflict as conflict:
                aggregate_taps += tap_tests
                aggregate_states += state_expansions
                length_prunes.append(conflict.lower_bound)
                continue
            aggregate_taps += tap_tests
            aggregate_states += state_expansions
            tree = canonical_conductor_tree(conductors)
            complete = canonical_conductor_tree((*local_conductors, *conductors))
            if (
                net in optional_output_nets
                and complete.length > MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH
            ):
                length_prunes.append(complete.length)
                continue
            if trunk is None:
                worst_to_trunk = 0
            else:
                first, second = trunk
                worst_to_trunk = max(
                    _point_to_trunk_distance(gateway.point, first, second)
                    for gateway in gateways.values()
                )
            foreign_interface_anchors = tuple(
                gateway.anchor
                for item in placed
                if item.fragment.block.kind == "interface"
                for gateway in item.gateways
                if gateway.net != net
            )
            interface_enclosures = _interface_enclosures(complete, foreign_interface_anchors)
            candidates.append(
                (
                    interface_enclosures,
                    complete.length,
                    worst_to_trunk,
                    complete.bends,
                    tuple((segment.start, segment.end) for segment in tree.segments),
                    strategy,
                    tree,
                )
            )
        if not candidates:
            if net in optional_output_nets or net in optional_reference_nets:
                continue
            if length_prunes and not blocked_plans:
                raise RouteLengthBoundConflict(net, min(length_prunes))
            if blocked_plans:
                blocked = max(blocked_plans, key=lambda item: (len(item.gateways), item.gateways))
                raise RouteBlockedConflict(net, blocked.gateways, aggregate_taps, aggregate_states)
            raise RouteBlockedConflict(
                net, tuple(sorted(gateways)), aggregate_taps, aggregate_states
            )
        _, _, _, _, _, strategy, tree = min(candidates)

        planned_corridors = tuple(
            Reservation(
                f"route.{net}.{index}",
                "channel",
                owner,
                "global_route",
                (
                    min(segment.start[0], segment.end[0]) - 250_000,
                    min(segment.start[1], segment.end[1]) - 250_000,
                    max(segment.start[0], segment.end[0]) + 250_000,
                    max(segment.start[1], segment.end[1]) + 250_000,
                ),
                net,
                1,
            )
            for index, segment in enumerate(tree.segments)
        )
        previous.extend((net, segment.start, segment.end) for segment in tree.segments)
        result.append(
            RouteTree(
                net,
                tuple(ordered),
                tuple((segment.start, segment.end) for segment in tree.segments),
                tree.junctions,
                owner,
                tuple(segment.provenance for segment in tree.segments),
                aggregate_taps,
                aggregate_states,
                strategy,
                len(plans),
                planned_corridors,
            )
        )
    # Label-eligible connector nets historically remained disconnected islands.
    # Add visible conductors only for unique, local semantic relations. Output
    # interfaces must be physically reached; their labels cannot stand in for
    # an output connection. Input-side links remain best-effort because their
    # symbol escape direction can make a short visual link awkward.
    routed_nets = {tree.net for tree in result}
    for edge in _optional_local_visible_edges(plan, placed):
        if edge.net in routed_nets:
            continue
        net = edge.net
        required_output = any(
            port.net == net and port.role == "signal_out"
            for port in by_id[edge.source].fragment.block.ports
        )
        owner = f"tree.{net}.local-visible"
        source = _gateway(by_id[edge.source], net, True)
        target = _gateway(by_id[edge.target], net, False)
        obstacles = tuple(
            reservation
            for reservation in scene_reservations
            if (
                reservation.occupancy == "exclusive"
                and reservation.clearance_class
                in {"body", "text", "label", "pin", "wire", "protected"}
                and not (
                    reservation.clearance_class == "label" and reservation.permitted_net == net
                )
            )
            or (reservation.occupancy == "channel" and reservation.permitted_net not in {None, net})
        )
        source_external = _advance(source.point, source.escape_direction, PITCH)
        target_external = _advance(target.point, target.escape_direction, PITCH)
        if not _path_legal(
            (source.point, source_external),
            _escape_obstacles(obstacles, source),
            tuple(previous),
            net=net,
            owner=owner,
            allowed_contacts=frozenset({source.point}),
            route_bounds=route_bounds,
        ):
            if required_output:
                raise RouteBlockedConflict(net, (source.id, target.id), 0, 0)
            continue
        if not _path_legal(
            (target.point, target_external),
            _escape_obstacles(obstacles, target),
            tuple(previous),
            net=net,
            owner=owner,
            allowed_contacts=frozenset({target.point}),
            route_bounds=route_bounds,
        ):
            if required_output:
                raise RouteBlockedConflict(net, (source.id, target.id), 0, 0)
            continue
        route_path, expansions = _connect(
            source_external,
            target_external,
            obstacles,
            tuple(previous),
            net=net,
            owner=owner,
            allowed_contacts=frozenset({source.point, target.point}),
            route_bounds=route_bounds,
        )
        if route_path is None:
            if required_output:
                raise RouteBlockedConflict(net, (source.id, target.id), 0, expansions)
            continue
        conductors = (
            ConductorSegment(
                source.point,
                source_external,
                net,
                owner,
                (source.id, "optional-visible"),
            ),
            *(
                ConductorSegment(first, second, net, owner, ("optional-visible",))
                for first, second in route_path
                if first != second
            ),
            ConductorSegment(
                target.point,
                target_external,
                net,
                owner,
                (target.id, "optional-visible"),
            ),
        )
        local_conductors = tuple(
            ConductorSegment(
                (first[0] + item.delta[0], first[1] + item.delta[1]),
                (second[0] + item.delta[0], second[1] + item.delta[1]),
                net,
                item.fragment.block.id,
            )
            for item in placed
            for (first, second), wire_net in zip(
                item.fragment.wires, item.fragment.wire_nets, strict=True
            )
            if wire_net == net
        )
        complete = canonical_conductor_tree((*local_conductors, *conductors))
        if complete.length > MAX_CANONICAL_LENGTH:
            if required_output:
                raise RouteLengthBoundConflict(net, complete.length)
            continue
        if required_output and complete.length > MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH:
            raise RouteLengthBoundConflict(
                net, complete.length, limit=MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH
            )
        tree = canonical_conductor_tree(conductors)
        planned_corridors = tuple(
            Reservation(
                f"route.{net}.optional.{index}",
                "channel",
                owner,
                "global_route",
                (
                    min(segment.start[0], segment.end[0]) - 250_000,
                    min(segment.start[1], segment.end[1]) - 250_000,
                    max(segment.start[0], segment.end[0]) + 250_000,
                    max(segment.start[1], segment.end[1]) + 250_000,
                ),
                net,
                1,
            )
            for index, segment in enumerate(tree.segments)
        )
        previous.extend((net, segment.start, segment.end) for segment in tree.segments)
        result.append(
            RouteTree(
                net,
                (edge,),
                tuple((segment.start, segment.end) for segment in tree.segments),
                tree.junctions,
                owner,
                tuple(segment.provenance for segment in tree.segments),
                0,
                expansions,
                "local_visible_optional",
                1,
                planned_corridors,
            )
        )
        routed_nets.add(net)
    return tuple(result)
