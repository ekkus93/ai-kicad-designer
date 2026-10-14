"""Deterministic bounded route trees over fragment gateways and reservations."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import pairwise

from .ir import InputError
from .m2_conflicts import ConflictKind, TypedConflict
from .m2a import PITCH
from .m2_fragments import Point
from .m2_geometry import (
    ConductorSegment,
    Gateway,
    Reservation,
    canonical_conductor_tree,
    point_on_segment,
    segment_is_admissible,
)
from .m2_pack import BOTTOM, LEFT, RIGHT, TOP, PlacedFragment
from .m2_semantics import SemanticEdge, SemanticPlan
from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations


MAX_TRACKS_PER_SIDE = 8
MAX_TAPS_PER_ATTACHMENT = 32
MAX_ROUTE_STATES_PER_TAP = 4_096
MAX_CANONICAL_LENGTH = 250_000_000
MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE = 80_000_000


def _floor_grid(value: int) -> int:
    return value // PITCH * PITCH


def _ceil_grid(value: int) -> int:
    return -((-value) // PITCH) * PITCH


@dataclass(frozen=True)
class RouteTree:
    net: str
    edges: tuple[SemanticEdge, ...]
    segments: tuple[tuple[Point, Point], ...]
    junctions: tuple[Point, ...]
    owner: str = ""
    segment_provenance: tuple[tuple[str, ...], ...] = ()
    tap_tests: int = 0
    state_expansions: int = 0
    strategy: str = "producer_centered"
    plan_tests: int = 1
    planned_corridors: tuple[Reservation, ...] = ()


class RouteBlockedConflict(InputError):
    """A terminal-backed island whose legal gateway could not reach the tree."""

    kind = "blocked_gateway"

    def __init__(self, net: str, gateways: tuple[str, ...], taps: int, states: int):
        self.category = ConflictKind.BLOCKED_GATEWAY
        self.net = net
        self.gateways = gateways
        self.taps = taps
        self.states = states
        super().__init__(
            f"ROUTE_BLOCKED: net={net} gateways={','.join(gateways)} taps={taps} states={states}"
        )


class RouteLengthBoundConflict(TypedConflict):
    """A fixed partial conductor union already exceeds the unchanged net gate."""

    def __init__(self, net: str, lower_bound: int):
        super().__init__(
            ConflictKind.CANONICAL_LENGTH,
            f"ROUTE_LENGTH_LOWER_BOUND: net={net} lower_bound={lower_bound} "
            f"limit={MAX_CANONICAL_LENGTH}",
            net=net,
            actual=lower_bound,
            limit=MAX_CANONICAL_LENGTH,
            lower_bound=lower_bound,
            repair_classes=("distribution_placement", "gateway_access"),
        )


def _gateway(item: PlacedFragment, net: str, output: bool) -> Gateway:
    roles = {"signal_out", "power_out"} if output else {"signal_in", "power_in"}
    role_by_id = {port.port.id: port.port.role for port in item.ports}
    candidates = [
        gateway
        for gateway in item.gateways
        if gateway.net == net and role_by_id[gateway.id] in roles
    ]
    if not candidates:
        candidates = [gateway for gateway in item.gateways if gateway.net == net]
    if not candidates:
        raise InputError(f"ROUTE_PORT_MISSING: {item.fragment.block.id}:{net}")
    return sorted(candidates, key=lambda gateway: gateway.id)[0]


def _advance(point: Point, direction: str, amount: int = PITCH) -> Point:
    dx, dy = {
        "left": (-amount, 0),
        "right": (amount, 0),
        "up": (0, -amount),
        "down": (0, amount),
    }[direction]
    return point[0] + dx, point[1] + dy


def _gateway_channel(gateway: Gateway) -> Reservation:
    """Reserve the complete bounded-repair escape without inflating its fragment."""
    end = _advance(gateway.point, gateway.escape_direction, PITCH)
    return Reservation(
        f"route-demand.{gateway.id}",
        "channel",
        gateway.island,
        "escape",
        (
            min(gateway.point[0], end[0]) - PITCH,
            min(gateway.point[1], end[1]) - PITCH,
            max(gateway.point[0], end[0]) + PITCH,
            max(gateway.point[1], end[1]) + PITCH,
        ),
        gateway.net,
        1,
    )


def _escape_obstacles(
    obstacles: tuple[Reservation, ...], gateway: Gateway
) -> tuple[Reservation, ...]:
    """Allow only the gateway's own same-net terminal wire at its owned exit."""
    block_owner = gateway.island.split(":", 1)[0]
    terminal_pin_suffixes = tuple(f".pin.{pin}" for _, pin in gateway.terminals)
    return tuple(
        reservation
        for reservation in obstacles
        if not (
            reservation.owner == block_owner
            and reservation.rect[0] <= gateway.point[0] <= reservation.rect[2]
            and reservation.rect[1] <= gateway.point[1] <= reservation.rect[3]
            and (
                (
                    reservation.clearance_class in {"wire", "protected"}
                    and reservation.permitted_net == gateway.net
                )
                or (
                    reservation.clearance_class == "pin"
                    and reservation.id.endswith(terminal_pin_suffixes)
                )
            )
        )
    )


def _crosses(first: Point, second: Point, other_first: Point, other_second: Point) -> bool:
    if first[0] == second[0] and other_first[1] == other_second[1]:
        point = (first[0], other_first[1])
        return point_on_segment(point, first, second) and point_on_segment(
            point, other_first, other_second
        )
    if first[1] == second[1] and other_first[0] == other_second[0]:
        point = (other_first[0], first[1])
        return point_on_segment(point, first, second) and point_on_segment(
            point, other_first, other_second
        )
    if first[0] == second[0] == other_first[0] == other_second[0]:
        return max(min(first[1], second[1]), min(other_first[1], other_second[1])) <= min(
            max(first[1], second[1]), max(other_first[1], other_second[1])
        )
    if first[1] == second[1] == other_first[1] == other_second[1]:
        return max(min(first[0], second[0]), min(other_first[0], other_second[0])) <= min(
            max(first[0], second[0]), max(other_first[0], other_second[0])
        )
    return False


def _path_segments(points: tuple[Point, ...]) -> tuple[tuple[Point, Point], ...]:
    return tuple((first, second) for first, second in pairwise(points) if first != second)


def _compact_collinear(points: tuple[Point, ...]) -> tuple[Point, ...]:
    compact: list[Point] = []
    for point in points:
        if compact and point == compact[-1]:
            continue
        if len(compact) >= 2:
            first, middle = compact[-2:]
            if (first[0] == middle[0] == point[0]) or (first[1] == middle[1] == point[1]):
                compact[-1] = point
                continue
        compact.append(point)
    return tuple(compact)


def _path_legal(
    points: tuple[Point, ...],
    obstacles: tuple[Reservation, ...],
    previous: tuple[tuple[str, Point, Point], ...],
    *,
    net: str,
    owner: str,
    allowed_contacts: frozenset[Point],
    route_bounds: tuple[int, int, int, int] | None = None,
) -> bool:
    if route_bounds is not None and any(
        not (
            route_bounds[0] <= point[0] <= route_bounds[2]
            and route_bounds[1] <= point[1] <= route_bounds[3]
        )
        for point in points
    ):
        return False
    for first, second in _path_segments(points):
        if not segment_is_admissible(first, second, obstacles, (), net=net, owner=owner):
            return False
        for other_net, other_first, other_second in previous:
            if other_net == net or not _crosses(first, second, other_first, other_second):
                continue
            contacts = {
                point
                for point in (first, second, other_first, other_second)
                if point_on_segment(point, first, second)
                and point_on_segment(point, other_first, other_second)
            }
            if not contacts or not contacts <= allowed_contacts:
                return False
    return True


def _direct_paths(
    first: Point, second: Point, tracks_x: tuple[int, ...], tracks_y: tuple[int, ...]
):
    yield (first, second)
    yield (first, (second[0], first[1]), second)
    yield (first, (first[0], second[1]), second)
    for x in tracks_x:
        yield (first, (x, first[1]), (x, second[1]), second)
    for y in tracks_y:
        yield (first, (first[0], y), (second[0], y), second)
    # Deterministic perimeter channels provide sparse three-bend escapes when
    # two packed bands form an indivisible obstacle to every two-bend route.
    perimeter_x = tuple(
        [LEFT + index * PITCH for index in range(MAX_TRACKS_PER_SIDE)]
        + [RIGHT - index * PITCH for index in range(MAX_TRACKS_PER_SIDE)]
    )
    perimeter_y = tuple(
        [TOP + index * PITCH for index in range(MAX_TRACKS_PER_SIDE)]
        + [BOTTOM - index * PITCH for index in range(MAX_TRACKS_PER_SIDE)]
    )
    for x in perimeter_x:
        for y in perimeter_y:
            yield (first, (first[0], y), (x, y), (x, second[1]), second)
            yield (first, (x, first[1]), (x, y), (second[0], y), second)


def _visibility_path(
    first: Point,
    second: Point,
    obstacles: tuple[Reservation, ...],
    previous: tuple[tuple[str, Point, Point], ...],
    *,
    net: str,
    owner: str,
    allowed_contacts: frozenset[Point],
    route_bounds: tuple[int, int, int, int] | None,
) -> tuple[tuple[Point, ...] | None, int]:
    x_values = {first[0], second[0]}
    y_values = {first[1], second[1]}
    for obstacle in obstacles:
        x_values.update(
            (
                _floor_grid(obstacle.rect[0] - PITCH),
                _ceil_grid(obstacle.rect[2] + PITCH),
            )
        )
        y_values.update(
            (
                _floor_grid(obstacle.rect[1] - PITCH),
                _ceil_grid(obstacle.rect[3] + PITCH),
            )
        )
    xs = sorted(
        x_values,
        key=lambda value: (min(abs(value - first[0]), abs(value - second[0])), value),
    )[:64]
    ys = sorted(
        y_values,
        key=lambda value: (min(abs(value - first[1]), abs(value - second[1])), value),
    )[:64]
    xs = sorted(set(xs) | {first[0], second[0]})
    ys = sorted(set(ys) | {first[1], second[1]})
    heuristic = abs(first[0] - second[0]) + abs(first[1] - second[1])
    queue = [(heuristic, 0, first[0], first[1], "", 0, first, (first,))]
    best = {(first, ""): (0, 0)}
    expansions = 0
    while queue and expansions < MAX_ROUTE_STATES_PER_TAP:
        _, bends, _, _, arrival, cost, point, path = heapq.heappop(queue)
        expansions += 1
        if point == second:
            return path, expansions
        x_index, y_index = xs.index(point[0]), ys.index(point[1])
        neighbors = []
        if x_index:
            neighbors.append((xs[x_index - 1], point[1]))
        if x_index + 1 < len(xs):
            neighbors.append((xs[x_index + 1], point[1]))
        if y_index:
            neighbors.append((point[0], ys[y_index - 1]))
        if y_index + 1 < len(ys):
            neighbors.append((point[0], ys[y_index + 1]))
        for candidate in neighbors:
            direction = "h" if candidate[1] == point[1] else "v"
            new_bends = bends + bool(arrival and arrival != direction)
            new_cost = cost + abs(candidate[0] - point[0]) + abs(candidate[1] - point[1])
            state = (candidate, direction)
            if best.get(state, (10**30, 10**30)) <= (new_cost, new_bends):
                continue
            if not _path_legal(
                (point, candidate),
                obstacles,
                previous,
                net=net,
                owner=owner,
                allowed_contacts=allowed_contacts,
                route_bounds=route_bounds,
            ):
                continue
            best[state] = (new_cost, new_bends)
            heapq.heappush(
                queue,
                (
                    new_cost + abs(candidate[0] - second[0]) + abs(candidate[1] - second[1]),
                    new_bends,
                    candidate[0],
                    candidate[1],
                    direction,
                    new_cost,
                    candidate,
                    (*path, candidate),
                ),
            )
    return None, expansions


def _connect(
    first: Point,
    second: Point,
    obstacles: tuple[Reservation, ...],
    previous: tuple[tuple[str, Point, Point], ...],
    *,
    net: str,
    owner: str,
    allowed_contacts: frozenset[Point],
    route_bounds: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[tuple[Point, Point], ...] | None, int]:
    prior_keepouts = tuple(
        Reservation(
            f"previous.{index}",
            "exclusive",
            f"tree.{other_net}",
            "global_route",
            (
                min(a[0], b[0]) - 250_000,
                min(a[1], b[1]) - 250_000,
                max(a[0], b[0]) + 250_000,
                max(a[1], b[1]) + 250_000,
            ),
            other_net,
        )
        for index, (other_net, a, b) in enumerate(previous)
        if other_net != net
    )
    routing_obstacles = obstacles + prior_keepouts

    def bounded_tracks(values: set[int], a: int, b: int) -> tuple[int, ...]:
        low, high = sorted((a, b))
        below = sorted((value for value in values if value < low), reverse=True)[
            :MAX_TRACKS_PER_SIDE
        ]
        above = sorted(value for value in values if value > high)[:MAX_TRACKS_PER_SIDE]
        between = sorted(
            (value for value in values if low <= value <= high),
            key=lambda value: (abs(value - a) + abs(value - b), value),
        )[:MAX_TRACKS_PER_SIDE]
        return tuple(below + between + above)

    tracks_x = bounded_tracks(
        {
            value
            for obstacle in routing_obstacles
            for value in (
                _floor_grid(obstacle.rect[0] - PITCH),
                _ceil_grid(obstacle.rect[2] + PITCH),
            )
        }
        | {LEFT, RIGHT},
        first[0],
        second[0],
    )
    tracks_y = bounded_tracks(
        {
            value
            for obstacle in routing_obstacles
            for value in (
                _floor_grid(obstacle.rect[1] - PITCH),
                _ceil_grid(obstacle.rect[3] + PITCH),
            )
        }
        | {TOP, BOTTOM},
        first[1],
        second[1],
    )
    candidates = []
    for points in _direct_paths(first, second, tracks_x, tracks_y):
        compact = tuple(
            point for index, point in enumerate(points) if index == 0 or point != points[index - 1]
        )
        if _path_legal(
            compact,
            routing_obstacles,
            previous,
            net=net,
            owner=owner,
            allowed_contacts=allowed_contacts,
            route_bounds=route_bounds,
        ):
            segments = _path_segments(compact)
            bends = max(0, len(segments) - 1)
            length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segments)
            # A distributive net is charged for conductor union, not for the
            # visual simplicity of its first branch.  Choosing bends first
            # can consume the entire net budget before later taps are added.
            candidates.append((length, bends, compact))
    if candidates:
        points = min(candidates, key=lambda value: (value[0], value[1], value[2]))[2]
        return _path_segments(points), 0
    points, expansions = _visibility_path(
        first,
        second,
        routing_obstacles,
        previous,
        net=net,
        owner=owner,
        allowed_contacts=allowed_contacts,
        route_bounds=route_bounds,
    )
    return (
        None if points is None else _path_segments(_compact_collinear(points)),
        expansions,
    )


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
    # An interior trunk can reduce long shared-rail branches when endpoints
    # occupy several rows. Retain the perimeter alternatives and the original
    # producer-centered tree; legality and the fixed 250 mm union gate still
    # decide which plans survive. Only one interior lane is considered so the
    # deterministic search budget remains bounded to eight initial plans.
    median_y = _floor_grid((top + bottom) // 2)
    interior = (
        [("horizontal_median", (left, median_y), (right, median_y), (seed_external[0], median_y))]
        if top < median_y < bottom
        else []
    )
    candidates = (
        interior
        + [("horizontal_above", (left, y), (right, y), (seed_external[0], y)) for y in above]
        + [("horizontal_below", (left, y), (right, y), (seed_external[0], y)) for y in below]
        + [("vertical_side", (x, top), (x, bottom), (x, seed_external[1])) for x in sides]
    )
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
    return tuple(result[:8])


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


def route_between_fragments(
    plan: SemanticPlan,
    placed: tuple[PlacedFragment, ...],
    *,
    retry_index: int = 0,
) -> tuple[RouteTree, ...]:
    """Attach all required gateways with one obstacle-checked tree per net/island."""
    by_id = {item.fragment.block.id: item for item in placed}
    # Keep emitted routing on the historically proved semantic edge inventory.
    # Inferred passive-interface relations are observer evidence only until
    # their additional conductor length and gateway feasibility are qualified.
    # Eagerly routing every inferred pair broke existing dual-buffer and V5/V6
    # cases by exhausting the bounded planner or exceeding the 250 mm gate.
    grouped: dict[str, list[SemanticEdge]] = {}
    for edge in plan.edges:
        if edge.net and edge.kind in {"signal", "power", "branch"}:
            grouped.setdefault(edge.net, []).append(edge)
    # A shared internal reference has no connector and may have no directed
    # edge at all. Its terminal inventory still demands a physical distribution.
    for net in plan.presentation_nets:
        if net.explicit_geometry_required and len(net.fragments) > 1:
            grouped.setdefault(net.id, [])
    distribution_nets = {
        item.id for item in plan.presentation_nets if item.explicit_geometry_required
    }
    shared_tree_nets = distribution_nets | {
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

    def net_gateways(net: str) -> tuple[Gateway, ...]:
        return tuple(gateway for item in placed for gateway in item.gateways if gateway.net == net)

    def group_order(item: tuple[str, list[SemanticEdge]]) -> tuple[int, int, int, str]:
        net, edges = item
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
        return _route_class(edges), legal_directions, -fanout, net

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
                in {"body", "text", "label", "pin", "wire", "protected"}
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
