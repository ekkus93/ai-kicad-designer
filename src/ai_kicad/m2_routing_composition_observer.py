"""Routing-clarity observer for M2h2 human-composition evidence.

The routines in this module consume already-observed route geometry. They do not
trust generator objective scores and they do not make acceptance claims; they
emit stable witnesses that can be bound into later qualification records.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
from math import isclose

Point = tuple[int, int]
Segment = tuple[Point, Point]
Rect = tuple[int, int, int, int]
LabelPair = tuple[str, Point, Point]


@dataclass(frozen=True)
class RoutingReadabilityMetrics:
    route_length: int
    bend_count: int
    normalized_length_excess: float
    normalized_bend_excess: float
    unrelated_crossings: int
    u_shaped_detours: int
    branch_points: tuple[Point, ...]
    sibling_branch_geometry_inconsistency: int
    route_excursions: tuple[Segment, ...]
    label_mediated_local_disconnects: tuple[str, ...]


def measure_routing_readability(
    segments: tuple[Segment, ...],
    *,
    semantic_local_length: int,
    semantic_local_bends: int = 0,
    unrelated_segments: tuple[Segment, ...] = (),
    unrelated_blocks: tuple[Rect, ...] = (),
    local_label_pairs: tuple[LabelPair, ...] = (),
    direct_distance_limit: int = 80_000_000,
) -> RoutingReadabilityMetrics:
    """Measure route clarity from emitted segments and independent local baselines."""
    length = sum(_segment_length(segment) for segment in segments)
    bend_count = _bend_count(segments)
    branch_points = _branch_points(segments)
    return RoutingReadabilityMetrics(
        route_length=length,
        bend_count=bend_count,
        normalized_length_excess=_normalized_excess(length, semantic_local_length),
        normalized_bend_excess=_normalized_excess(bend_count, semantic_local_bends),
        unrelated_crossings=_unrelated_crossing_count(segments, unrelated_segments),
        u_shaped_detours=_u_shaped_detours(segments),
        branch_points=branch_points,
        sibling_branch_geometry_inconsistency=_branch_inconsistency(segments, branch_points),
        route_excursions=_route_excursions(segments, unrelated_blocks),
        label_mediated_local_disconnects=_local_label_disconnects(
            segments,
            local_label_pairs,
            direct_distance_limit,
        ),
    )


def _segment_length(segment: Segment) -> int:
    return abs(segment[0][0] - segment[1][0]) + abs(segment[0][1] - segment[1][1])


def _direction(segment: Segment) -> str:
    if segment[0][0] == segment[1][0]:
        return "vertical"
    if segment[0][1] == segment[1][1]:
        return "horizontal"
    return "diagonal"


def _bend_count(segments: tuple[Segment, ...]) -> int:
    """Count orthogonal two-arm corners, not seams, crossings, or tee branches.

    Counting raw incident strokes is not invariant to duplicate strokes or
    collinear wire segmentation. Visible cardinal arms encode the geometry
    independently of those serialization details.
    """
    bends = 0
    for point in {endpoint for segment in segments for endpoint in segment}:
        arms = _incident_cardinal_arms(point, segments)
        if len(arms) == 2 and arms & {"left", "right"} and arms & {"up", "down"}:
            bends += 1
    return bends


def _incident_cardinal_arms(point: Point, segments: tuple[Segment, ...]) -> set[str]:
    """Derive distinct visible directions, including at endpoint-on-wire tees."""
    x, y = point
    arms: set[str] = set()
    for first, second in segments:
        if first == second:
            continue
        if first[1] == second[1] == y:
            left, right = sorted((first[0], second[0]))
            if left <= x <= right:
                if left < x:
                    arms.add("left")
                if x < right:
                    arms.add("right")
        elif first[0] == second[0] == x:
            top, bottom = sorted((first[1], second[1]))
            if top <= y <= bottom:
                if top < y:
                    arms.add("up")
                if y < bottom:
                    arms.add("down")
    return arms


def _branch_points(segments: tuple[Segment, ...]) -> tuple[Point, ...]:
    """Report junctions invariant to splitting and duplicate wire strokes.

    Only emitted endpoints are junction candidates. Two wire interiors
    crossing without a shared endpoint cannot create a false branch.
    """
    endpoints = {point for segment in segments for point in segment}
    return tuple(
        point for point in sorted(endpoints) if len(_incident_cardinal_arms(point, segments)) > 2
    )


def _normalized_excess(actual: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0 if actual <= 0 else float(actual)
    value = (actual - baseline) / baseline
    return 0.0 if isclose(value, 0.0, abs_tol=1e-12) else value


def _unrelated_crossing_count(
    segments: tuple[Segment, ...], unrelated_segments: tuple[Segment, ...]
) -> int:
    """Count distinct unrelated orthogonal intersections, not serialized pairs.

    A crossing is one geometric location even when either wire is split,
    duplicated, or reversed. Endpoint-on-interior contacts remain visible
    conflicts rather than disappearing when a route is split at the crossing.
    """
    primary = {tuple(sorted(edge)) for edge in segments if edge[0] != edge[1]}
    unrelated = {tuple(sorted(edge)) for edge in unrelated_segments if edge[0] != edge[1]}
    return len(
        {
            point
            for first in primary
            for second in unrelated
            if (point := _orthogonal_intersection(first, second)) is not None
        }
    )


def _orthogonal_intersection(first: Segment, second: Segment) -> Point | None:
    first_direction = _direction(first)
    second_direction = _direction(second)
    if {first_direction, second_direction} != {"horizontal", "vertical"}:
        return None
    horizontal, vertical = (first, second) if first_direction == "horizontal" else (second, first)
    x, y = vertical[0][0], horizontal[0][1]
    hx1, hx2 = sorted((horizontal[0][0], horizontal[1][0]))
    vy1, vy2 = sorted((vertical[0][1], vertical[1][1]))
    return (x, y) if hx1 <= x <= hx2 and vy1 <= y <= vy2 else None


def _coalesced_route_edges(segments: tuple[Segment, ...]) -> tuple[Segment, ...]:
    """Remove collinear segmentation seams without erasing actual junctions."""
    edges = {
        tuple(sorted(edge))
        for edge in segments
        if edge[0] != edge[1] and _direction(edge) != "diagonal"
    }
    incident: dict[Point, set[Segment]] = defaultdict(set)
    for edge in edges:
        for point in edge:
            incident[point].add(edge)
    pending = list(incident)
    heapify(pending)
    while pending:
        point = heappop(pending)
        connected = incident[point]
        if len(connected) != 2:
            continue
        first, second = sorted(connected)
        direction = _direction(first)
        if direction != _direction(second):
            continue
        straight = {"left", "right"} if direction == "horizontal" else {"up", "down"}
        if _incident_cardinal_arms(point, tuple(edges)) != straight:
            continue
        other_first = first[1] if first[0] == point else first[0]
        other_second = second[1] if second[0] == point else second[0]
        if other_first == other_second:
            continue
        merged = tuple(sorted((other_first, other_second)))
        for edge in (first, second):
            edges.remove(edge)
            for endpoint in edge:
                incident[endpoint].discard(edge)
        edges.add(merged)
        for endpoint in merged:
            incident[endpoint].add(merged)
            heappush(pending, endpoint)
    return tuple(sorted(edges))


def _u_shaped_detours(segments: tuple[Segment, ...]) -> int:
    """Detect U-turns regardless of edge order, direction, or wire splitting."""
    edges = _coalesced_route_edges(segments)
    incident: dict[Point, list[Segment]] = defaultdict(list)
    for edge in edges:
        for point in edge:
            incident[point].append(edge)
    count = 0
    for middle in edges:
        for before in incident[middle[0]]:
            if before == middle or _direction(before) == _direction(middle):
                continue
            first = (before[1], before[0]) if before[0] == middle[0] else before
            for after in incident[middle[1]]:
                if after == middle or after == before:
                    continue
                third = after if after[0] == middle[1] else (after[1], after[0])
                if _direction(first) == _direction(third) and _opposite_parallel(first, third):
                    count += 1
    return count


def _opposite_parallel(first: Segment, second: Segment) -> bool:
    direction = _direction(first)
    if direction == "horizontal":
        return (first[1][0] - first[0][0]) * (second[1][0] - second[0][0]) < 0
    if direction == "vertical":
        return (first[1][1] - first[0][1]) * (second[1][1] - second[0][1]) < 0
    return False


def _straight_arm_length(
    point: Point,
    direction: str,
    segments: tuple[Segment, ...],
    endpoints: set[Point],
) -> int:
    """Trace a straight branch arm to its next terminal, bend, or junction.

    Collinear wire-segment seams do not end an arm. No unrelated crossing is
    treated as a junction because only actual emitted endpoints may stop it.
    """
    axis = 0 if direction in {"left", "right"} else 1
    start = point[axis]
    forward = direction in {"right", "down"}
    intervals = [
        tuple(sorted((first[axis], second[axis])))
        for first, second in segments
        if first[1 - axis] == second[1 - axis] == point[1 - axis]
    ]
    reach = start
    while True:
        if forward:
            farther = max((high for low, high in intervals if low <= reach < high), default=reach)
        else:
            farther = min((low for low, high in intervals if low < reach <= high), default=reach)
        if farther == reach:
            break
        reach = farther
    if reach == start:
        return 0

    straight = {"left", "right"} if axis == 0 else {"up", "down"}
    stops = [
        abs(other[axis] - start)
        for other in endpoints
        if other[1 - axis] == point[1 - axis]
        and ((start < other[axis] <= reach) if forward else (reach <= other[axis] < start))
        and _incident_cardinal_arms(other, segments) != straight
    ]
    return min(stops, default=abs(reach - start))


def _branch_inconsistency(segments: tuple[Segment, ...], branch_points: tuple[Point, ...]) -> int:
    endpoints = {point for segment in segments for point in segment}
    worst = 0
    for point in branch_points:
        lengths = [
            _straight_arm_length(point, direction, segments, endpoints)
            for direction in sorted(_incident_cardinal_arms(point, segments))
        ]
        if lengths:
            worst = max(worst, max(lengths) - min(lengths))
    return worst


def _route_excursions(
    segments: tuple[Segment, ...], unrelated_blocks: tuple[Rect, ...]
) -> tuple[Segment, ...]:
    return tuple(
        segment
        for segment in segments
        if any(_segment_intersects_rect(segment, block) for block in unrelated_blocks)
    )


def _segment_intersects_rect(segment: Segment, rect: Rect) -> bool:
    if _point_inside_rect(segment[0], rect) or _point_inside_rect(segment[1], rect):
        return True
    direction = _direction(segment)
    if direction == "horizontal":
        y = segment[0][1]
        left, right = sorted((segment[0][0], segment[1][0]))
        return rect[1] < y < rect[3] and max(left, rect[0]) < min(right, rect[2])
    if direction == "vertical":
        x = segment[0][0]
        top, bottom = sorted((segment[0][1], segment[1][1]))
        return rect[0] < x < rect[2] and max(top, rect[1]) < min(bottom, rect[3])
    return False


def _point_inside_rect(point: Point, rect: Rect) -> bool:
    return rect[0] < point[0] < rect[2] and rect[1] < point[1] < rect[3]


def _local_label_disconnects(
    segments: tuple[Segment, ...],
    local_label_pairs: tuple[LabelPair, ...],
    direct_distance_limit: int,
) -> tuple[str, ...]:
    # Labels may attach anywhere along a wire, not only at an emitted endpoint.
    # A crossing of two unrelated segment interiors is ambiguous and must not
    # invent a junction. Shared endpoints and explicit endpoint-on-wire T-junctions
    # join components; pure interior crossings never do.
    components = _endpoint_components(segments)
    disconnected = []
    for label_id, first, second in local_label_pairs:
        if _manhattan(first, second) > direct_distance_limit:
            continue
        first_component = _label_component(first, segments, components)
        second_component = _label_component(second, segments, components)
        if first_component is None or first_component != second_component:
            disconnected.append(label_id)
    return tuple(sorted(set(disconnected)))


def _label_component(
    point: Point, segments: tuple[Segment, ...], components: dict[Point, int]
) -> int | None:
    """Resolve an interior wire label without joining a crossing by proximity."""
    if point in components:
        return components[point]
    touched = {
        components[first]
        for first, second in segments
        if first in components and _point_on_orthogonal_segment(point, (first, second))
    }
    return next(iter(touched)) if len(touched) == 1 else None


def _point_on_orthogonal_segment(point: Point, segment: Segment) -> bool:
    (ax, ay), (bx, by) = segment
    x, y = point
    return (ax == bx == x and min(ay, by) <= y <= max(ay, by)) or (
        ay == by == y and min(ax, bx) <= x <= max(ax, bx)
    )


def _endpoint_components(segments: tuple[Segment, ...]) -> dict[Point, int]:
    adjacency: dict[Point, set[Point]] = defaultdict(set)
    for first, second in segments:
        adjacency[first].add(second)
        adjacency[second].add(first)

    # Serialized orthogonal wires can terminate on the interior of a longer
    # segment. Their exact endpoint provides the explicit T-junction witness;
    # two segments crossing only at their interiors remain unrelated.
    for point in tuple(sorted(adjacency)):
        for first, second in segments:
            if (
                point != first
                and point != second
                and _point_on_orthogonal_segment(point, (first, second))
            ):
                adjacency[point].update((first, second))
                adjacency[first].add(point)
                adjacency[second].add(point)

    components: dict[Point, int] = {}
    for start in sorted(adjacency):
        if start in components:
            continue
        component_id = len(components)
        pending = [start]
