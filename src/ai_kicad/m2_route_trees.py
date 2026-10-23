"""Implementation details for m2 route trees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_fragments_types import Point
from .m2_geometry import (
    ConductorSegment,
    Gateway,
    Reservation,
)
from .m2_pack_core import PlacedFragment
from .m2_route_constants import MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE
from .m2_route_core import (
    _advance,
    _ceil_grid,
    _connect,
    _floor_grid,
    _gateway,
    _path_legal,
)
from .m2_semantics_core import SemanticEdge
from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def _route_class(edges: list[SemanticEdge]) -> int:
    # Protected cross-fragment paths are represented by signal/branch
    # obligations; distributive supply/reference trees follow them.
    if any(edge.kind in {"signal", "branch"} for edge in edges):
        return 0
    return 1


def _distribution_initial_trees(
    net: str,
    owner: str,
    seed: Gateway,
    gateways: tuple[Gateway, ...],
    obstacles: tuple[Reservation, ...],
    previous: tuple[tuple[str, Point, Point], ...],
    route_bounds: tuple[int, int, int, int],
) -> tuple[tuple[str, tuple[ConductorSegment, ...], tuple[Point, Point] | None, int], ...]:
    """Enumerate distinct bounded trunk geometries before branch attachment."""
    seed_external = _advance(seed.point, seed.escape_direction, PITCH)
    seed_segment = ConductorSegment(seed.point, seed_external, net, owner, (seed.id, "seed"))
    result = [("producer_centered", (seed_segment,), None, 0)]
    external = tuple(
        _advance(gateway.point, gateway.escape_direction, PITCH) for gateway in gateways
    )
    left = min(point[0] for point in external)
    right = max(point[0] for point in external)
    top = min(point[1] for point in external)
    bottom = max(point[1] for point in external)
    above = sorted(
        {top - PITCH}
        | {
            _floor_grid(obstacle.rect[1] - PITCH)
            for obstacle in obstacles
            if obstacle.rect[1] <= top
        },
        reverse=True,
    )[:2]
    below = sorted(
        {bottom + PITCH}
        | {
            _ceil_grid(obstacle.rect[3] + PITCH)
            for obstacle in obstacles
            if obstacle.rect[3] >= bottom
        }
    )[:2]
    sides = sorted(
        (
            {left - PITCH}
            | {
                _floor_grid(obstacle.rect[0] - PITCH)
                for obstacle in obstacles
                if obstacle.rect[0] <= left
            }
        )
        | (
            {right + PITCH}
            | {
                _ceil_grid(obstacle.rect[2] + PITCH)
                for obstacle in obstacles
                if obstacle.rect[2] >= right
            }
        ),
        key=lambda x: (min(abs(x - left), abs(x - right)), x),
    )[:2]
    # Search nearby legal interior lanes when the gateway-row median is
    # obstructed. Retain up to two distinct seed-connected corridors within
    # the eight-plan budget; geometry/length validation remains authoritative.
    median_row = sorted(point[1] for point in external)[len(external) // 2]
    median_y = min(bottom - PITCH, max(top + PITCH, median_row))
    interior = []
    if top < median_y < bottom:
        lanes = {median_y}
        for step in (1, 2):
            lanes.update({median_y - step * PITCH, median_y + step * PITCH})
        for obstacle in obstacles:
            if obstacle.rect[0] < right and obstacle.rect[2] > left:
                lanes.add(_floor_grid(obstacle.rect[1] - PITCH))
                lanes.add(_ceil_grid(obstacle.rect[3] + PITCH))
        ordered_lanes = sorted(
            (y for y in lanes if top < y < bottom),
            key=lambda y: (
                sum(abs(point[1] - y) for point in external),
                abs(y - median_y),
                y,
            ),
        )[:8]
        for y in ordered_lanes:
            first, second = (left, y), (right, y)
            if first == second or not _path_legal(
                (first, second),
                obstacles,
                previous,
                net=net,
                owner=owner,
                allowed_contacts=frozenset(),
                route_bounds=route_bounds,
            ):
                continue
            projection = (seed_external[0], y)
            branch, expansions = _connect(
                seed_external,
                projection,
                obstacles,
                previous,
                net=net,
                owner=owner,
                allowed_contacts=frozenset({seed_external, projection}),
                route_bounds=route_bounds,
            )
            if branch is None:
                continue
            strategy = "horizontal_median" if y == median_y else "horizontal_clear_lane"
            conductors = (
                seed_segment,
                ConductorSegment(first, second, net, owner, (strategy, "trunk")),
                *(
                    ConductorSegment(p, q, net, owner, (strategy, "seed_branch"))
                    for p, q in branch
                    if p != q
                ),
            )
            interior.append((strategy, conductors, (first, second), expansions))
            if len(interior) == 2:
                break
    # A vertical interior trunk can be substantially shorter for shared nets
    # whose consumers are separated mostly in Y. Explore two distinct source-neutral,
    # seed-connected legal corridors before the outer perimeter alternatives,
    # without increasing the existing eight-plan budget or relaxing clearance.
    median_column = sorted(point[0] for point in external)[len(external) // 2]

    median_x = min(right - PITCH, max(left + PITCH, median_column))
    vertical_interior = []
    if left < median_x < right:
        lanes = {median_x}
        for step in (1, 2):
            lanes.update({median_x - step * PITCH, median_x + step * PITCH})
        for obstacle in obstacles:
            if obstacle.rect[1] < bottom and obstacle.rect[3] > top:
                lanes.add(_floor_grid(obstacle.rect[0] - PITCH))
                lanes.add(_ceil_grid(obstacle.rect[2] + PITCH))
        ordered_lanes = sorted(
            (x for x in lanes if left < x < right),
            key=lambda x: (
                sum(abs(point[0] - x) for point in external),
                abs(x - median_x),
                x,
            ),
        )[:8]
        for x in ordered_lanes:
            first, second = (x, top), (x, bottom)
            if first == second or not _path_legal(
                (first, second),
                obstacles,
                previous,
                net=net,
                owner=owner,
                allowed_contacts=frozenset(),
                route_bounds=route_bounds,
            ):
                continue
            projection = (x, seed_external[1])
            branch, expansions = _connect(
                seed_external,
                projection,
                obstacles,
                previous,
                net=net,
                owner=owner,
                allowed_contacts=frozenset({seed_external, projection}),
                route_bounds=route_bounds,
            )
            if branch is None:
                continue
            strategy = "vertical_median" if x == median_x else "vertical_clear_lane"
            conductors = (
                seed_segment,
                ConductorSegment(first, second, net, owner, (strategy, "trunk")),
                *(
                    ConductorSegment(p, q, net, owner, (strategy, "seed_branch"))
                    for p, q in branch
                    if p != q
                ),
            )
            vertical_interior.append((strategy, conductors, (first, second), expansions))
            if len(vertical_interior) == 2:
                break
    candidates = (
        [("horizontal_above", (left, y), (right, y), (seed_external[0], y)) for y in above]
        + [("horizontal_below", (left, y), (right, y), (seed_external[0], y)) for y in below]
        + [("vertical_side", (x, top), (x, bottom), (x, seed_external[1])) for x in sides]
    )
    # Round-robin perimeter families before the eight-plan cap: extra
    # obstacle-derived above/below lanes must not starve vertical-side
    # alternatives. Keep each family's original deterministic ordering.
    grouped_candidates = (
        [candidate for candidate in candidates if candidate[0] == "horizontal_above"],
        [candidate for candidate in candidates if candidate[0] == "horizontal_below"],
        [candidate for candidate in candidates if candidate[0] == "vertical_side"],
    )
    candidates = [
        group[rank]
        for rank in range(max(len(group) for group in grouped_candidates))
        for group in grouped_candidates
        if rank < len(group)
    ]
    for strategy, first, second, projection in candidates:
        if first == second or not _path_legal(
            (first, second),
            obstacles,
            previous,
            net=net,
            owner=owner,
            allowed_contacts=frozenset(),
            route_bounds=route_bounds,
        ):
            continue
        branch, expansions = _connect(
            seed_external,
            projection,
            obstacles,
            previous,
            net=net,
            owner=owner,
            allowed_contacts=frozenset({seed_external, projection}),
            route_bounds=route_bounds,
        )
        if branch is None:
            continue
        conductors = (
            seed_segment,
            ConductorSegment(first, second, net, owner, (strategy, "trunk")),
            *(
                ConductorSegment(a, b, net, owner, (strategy, "seed_branch"))
                for a, b in branch
                if a != b
            ),
        )
        result.append((strategy, conductors, (first, second), expansions))
    return tuple((result[:1] + interior + vertical_interior + result[1:])[:8])


def _routable_edges(plan: SemanticPlan) -> tuple[SemanticEdge, ...]:
    """Return generic cross-fragment routes, including unique passive interfaces.

    Passive connector pins are electrically typed as passive, so some external
    signal boundaries are represented by terminal-backed precedence rather than
    authored signal edges. When semantic inference identifies exactly one
    unambiguous producer/consumer relationship, require the same visible route
    tree as an authored signal edge. Ambiguous, power, and reference interfaces
    remain label/distribution governed and are never guessed.
    """
    edges = [edge for edge in plan.edges if edge.net and edge.kind in {"signal", "power", "branch"}]
    existing = {(edge.source, edge.target, edge.net) for edge in edges}
    for source, target, net in inferred_passive_interface_signal_relations(plan):
        if (source, target, net) in existing:
            continue
        edges.append(
            SemanticEdge(
                "signal",
                source,
                target,
                net,
                ("inferred_passive_interface",),
            )
        )
    return tuple(
        sorted(
            edges,
            key=lambda edge: (
                edge.net,
                edge.source,
                edge.target,
                edge.kind,
                edge.origins,
            ),
        )
    )


def _optional_local_visible_edges(
    plan: SemanticPlan, placed: tuple[PlacedFragment, ...]
) -> tuple[SemanticEdge, ...]:
    """Return unambiguous local signal interfaces eligible for optional visible routing.

    Labels remain the fallback.  Only a two-fragment signal net, not a shared or
    distributive net, can opt into this local route, and only while the observed
    gateway separation stays within the existing 80 mm locality bound.
    """
    by_id = {item.fragment.block.id: item for item in placed}
    presentation_by_net = {item.id: item for item in plan.presentation_nets}
    result = []
    for edge in _routable_edges(plan):
        if edge.origins != ("inferred_passive_interface",):
            continue
        presentation = presentation_by_net.get(edge.net)
        if (
            presentation is None
            or presentation.role != "signal"
            or presentation.explicit_geometry_required
            or set(presentation.fragments) != {edge.source, edge.target}
            or edge.source not in by_id
            or edge.target not in by_id
        ):
            continue
        source = _gateway(by_id[edge.source], edge.net, True)
        target = _gateway(by_id[edge.target], edge.net, False)
        distance = abs(source.point[0] - target.point[0]) + abs(source.point[1] - target.point[1])
        if distance <= MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE:
            result.append(edge)
    return tuple(sorted(result, key=lambda edge: (edge.net, edge.source, edge.target)))


def _optional_reference_nets(plan: SemanticPlan) -> frozenset[str]:
    """Return external reference nets that may be drawn as one physical tree.

    Such a net is distributive, carries no explicit geometry demand, reaches
    exactly one interface fragment and at least one internal reference
    terminal. Even a single capacitor return should be visibly wired to its
    external connector when an obstacle-checked route is feasible; same-name
    labels remain the fallback when no legal route fits.
    """
    block_by_id = {block.id: block for block in plan.blocks}
    result = set()
    for presentation in plan.presentation_nets:
        interface_fragments = {
            fragment
            for fragment in presentation.fragments
            if fragment in block_by_id and block_by_id[fragment].kind == "interface"
        }
        reference_fragments = {
            block.id
            for block in plan.blocks
            if block.id in presentation.fragments
            and block.kind != "interface"
            and any(
                port.net == presentation.id and port.role == "reference" for port in block.ports
            )
        }
        if (
            presentation.role == "distributive"
            and not presentation.explicit_geometry_required
            and len(interface_fragments) == 1
            and len(reference_fragments) >= 1
        ):
            result.add(presentation.id)
    return frozenset(result)
