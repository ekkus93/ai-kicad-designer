"""Implementation details for m2 route core."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import pairwise

from .ir import InputError
from .m2_conflicts import ConflictKind, TypedConflict
from .m2_fragments_types import Point
from .m2_geometry import (
    Gateway,
    Reservation,
    point_on_segment,
    segment_is_admissible,
)
from .m2_pack_constants import BOTTOM, LEFT, RIGHT, TOP
from .m2_pack_core import PlacedFragment
from .m2_route_constants import (
    MAX_CANONICAL_LENGTH,
    MAX_ROUTE_STATES_PER_TAP,
    MAX_TRACKS_PER_SIDE,
)
from .m2_semantics_core import SemanticEdge
from .m2a_constants import PITCH


def _floor_grid(value: int) -> int:
    return value // PITCH * PITCH


def _ceil_grid(value: int) -> int:
    return -((-value) // PITCH) * PITCH


def _bounded_tracks(values: set[int], a: int, b: int) -> tuple[int, ...]:
    """Retain near-outside tracks and span-diverse interior escape lanes.

    Every interior lane has the same Manhattan distance to both endpoints;
    taking the first eight by coordinate discards the far side of dense bands.
    Quantile indices preserve both extremes and sample the intervening span
    without increasing the existing per-region routing budget.
    """
    low, high = sorted((a, b))
    below = sorted((value for value in values if value < low), reverse=True)[:MAX_TRACKS_PER_SIDE]
    above = sorted(value for value in values if value > high)[:MAX_TRACKS_PER_SIDE]
    between = sorted(value for value in values if low <= value <= high)
    if len(between) > MAX_TRACKS_PER_SIDE:
        count = MAX_TRACKS_PER_SIDE
        between = [between[index * (len(between) - 1) // (count - 1)] for index in range(count)]
    return tuple(below + between + above)


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

    def __init__(
        self,
        net: str,
        lower_bound: int,
        limit: int = MAX_CANONICAL_LENGTH,
    ):
        super().__init__(
            ConflictKind.CANONICAL_LENGTH,
            f"ROUTE_LENGTH_LOWER_BOUND: net={net} lower_bound={lower_bound} limit={limit}",
            net=net,
            actual=lower_bound,
            limit=limit,
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
    return min(candidates, key=lambda gateway: gateway.id)


def _advance(point: Point, direction: str, amount: int = PITCH) -> Point:
    dx, dy = {
        "left": (-amount, 0),
        "right": (amount, 0),
        "up": (0, -amount),
        "down": (0, amount),
    }[direction]
    return point[0] + dx, point[1] + dy


def _point_to_trunk_distance(point: Point, first: Point, second: Point) -> int:
    """Exact Manhattan distance to a horizontal or vertical trunk segment.

    Clamp the orthogonal projection to the conductor's finite span. Measuring
    only endpoints penalizes nearby gateways next to long valid trunks.
    """
    if first[0] == second[0]:
        low, high = sorted((first[1], second[1]))
        return abs(point[0] - first[0]) + max(low - point[1], 0, point[1] - high)
    if first[1] == second[1]:
        low, high = sorted((first[0], second[0]))
        return abs(point[1] - first[1]) + max(low - point[0], 0, point[0] - high)
    raise ValueError("Trunk must be axis-aligned")


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


def _interface_enclosures(tree, interface_points: tuple[Point, ...]) -> int:
    """Count foreign interfaces boxed in by adjacent sides of one route tree."""
    halo = 12 * PITCH
    enclosed = 0
    for x, y in interface_points:
        sides = set()
        for segment in tree.segments:
            first, second = segment.start, segment.end
            if (
                first[1] == second[1]
                and max(
                    min(first[0], second[0]) - x,
                    0,
                    x - max(first[0], second[0]),
                )
                <= 3 * PITCH
            ):
                if 0 < y - first[1] <= halo:
                    sides.add("above")
                elif 0 < first[1] - y <= halo:
                    sides.add("below")
            elif (
                first[0] == second[0]
                and max(
                    min(first[1], second[1]) - y,
                    0,
                    y - max(first[1], second[1]),
                )
                <= 3 * PITCH
            ):
                if 0 < x - first[0] <= halo:
                    sides.add("left")
                elif 0 < first[0] - x <= halo:
                    sides.add("right")
        enclosed += len(sides) >= 2
    return enclosed


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
    # A bounded pair of obstacle-derived interior tracks can avoid a packed
    # corner without detouring to the page perimeter. These are ordinary
    # candidates: full clearance, prior-net, page and length checks still
    # apply in _connect. Keep the cross-product small and deterministic.
    nearest_x = sorted(
        set(tracks_x),
        key=lambda x: (min(abs(x - first[0]), abs(x - second[0])), x),
    )[:4]
    nearest_y = sorted(
        set(tracks_y),
        key=lambda y: (min(abs(y - first[1]), abs(y - second[1])), y),
    )[:4]
    for x in nearest_x:
        for y in nearest_y:
            if x in {first[0], second[0]} or y in {first[1], second[1]}:
                continue
            yield (first, (x, first[1]), (x, y), (second[0], y), second)
            yield (first, (first[0], y), (x, y), (x, second[1]), second)
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

    tracks_x = _bounded_tracks(
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
    tracks_y = _bounded_tracks(
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
