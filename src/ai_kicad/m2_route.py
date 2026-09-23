"""Deterministic bounded route trees over fragment gateways and reservations."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import pairwise

from .ir import InputError
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


MAX_TRACKS_PER_SIDE = 8
MAX_TAPS_PER_ATTACHMENT = 32
MAX_ROUTE_STATES_PER_TAP = 4_096


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
            candidates.append((bends, length, compact))
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


def route_between_fragments(
    plan: SemanticPlan,
    placed: tuple[PlacedFragment, ...],
    *,
    retry_index: int = 0,
) -> tuple[RouteTree, ...]:
    """Attach all required gateways with one obstacle-checked tree per net/island."""
    by_id = {item.fragment.block.id: item for item in placed}
    grouped: dict[str, list[SemanticEdge]] = {}
    for edge in plan.edges:
        if edge.net and edge.kind in {"signal", "power", "branch"}:
            grouped.setdefault(edge.net, []).append(edge)

    def group_order(item: tuple[str, list[SemanticEdge]]) -> tuple[int, int, int, str]:
        net, edges = item
        endpoints = tuple((by_id[edge.source], True) for edge in edges) + tuple(
            (by_id[edge.target], False) for edge in edges
        )
        legal_directions = min(
            len(_gateway(fragment, net, output).approach_directions)
            for fragment, output in endpoints
        )
        fanout = len({_gateway(fragment, net, output).id for fragment, output in endpoints})
        return _route_class(edges), legal_directions, -fanout, net

    ordered_groups = sorted(grouped.items(), key=group_order)
    active_gateway_ids = {
        gateway.id
        for net, edges in ordered_groups
        for edge in edges
        for item, output in ((by_id[edge.source], True), (by_id[edge.target], False))
        for gateway in (_gateway(item, net, output),)
    }
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
                    reservation.clearance_class == "label" and reservation.permitted_net == net
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
                key=lambda gateway: (len(gateway.approach_directions), gateway.id),
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
            raise InputError(
                f"ROUTE_BLOCKED: net={net} gateway={seed.id} illegal_seed_escape "
                f"retry={retry_index}"
            )
        conductors = [ConductorSegment(seed.point, seed_external, net, owner, (seed.id, "seed"))]
        connected = {seed.id}
        tap_tests = state_expansions = 0
        while len(connected) != len(gateways):
            base_tree = canonical_conductor_tree(conductors)
            attachment_candidates = []
            blocked_targets = []
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
                    continue
                taps = {point for segment in conductors for point in (segment.start, segment.end)}
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
                    if gateway.id in connected and gateway.id != seed.id
                }
                taps.difference_update(occupied_gateway_points)
                ordered_taps = sorted(
                    taps,
                    key=lambda point: (
                        abs(point[0] - target_external[0]) + abs(point[1] - target_external[1]),
                        point[0],
                        point[1],
                    ),
                )[:MAX_TAPS_PER_ATTACHMENT]
                target_choices = []
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
                        bends = max(0, trial_tree.bends - base_tree.bends)
                        length = trial_tree.length - base_tree.length
                        target_choices.append(
                            (
                                bends,
                                length,
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
                else:
                    target_choices.sort(key=lambda item: item[:5] + (item[8],))
                    attachment_candidates.append(
                        target_choices[min(retry_index, len(target_choices) - 1)]
                    )
            if not attachment_candidates:
                raise InputError(
                    f"ROUTE_BLOCKED: net={net} gateways={','.join(blocked_targets)} "
                    f"taps={tap_tests} "
                    f"states={state_expansions} retry={retry_index}"
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
        tree = canonical_conductor_tree(conductors)
        previous.extend((net, segment.start, segment.end) for segment in tree.segments)
        result.append(
            RouteTree(
                net,
                tuple(ordered),
                tuple((segment.start, segment.end) for segment in tree.segments),
                tree.junctions,
                owner,
                tuple(segment.provenance for segment in tree.segments),
                tap_tests,
                state_expansions,
            )
        )
    return tuple(result)
