"""Routing-clarity observer for M2h2 human-composition evidence.

The routines in this module consume already-observed route geometry. They do not
trust generator objective scores and they do not make acceptance claims; they
emit stable witnesses that can be bound into later qualification records.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
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
    by_point: dict[Point, list[str]] = defaultdict(list)
    for segment in segments:
        direction = _direction(segment)
        by_point[segment[0]].append(direction)
        by_point[segment[1]].append(direction)
    bends = 0
    for directions in by_point.values():
        if len(directions) == 2 and len(set(directions)) == 2:
            bends += 1
    return bends


def _branch_points(segments: tuple[Segment, ...]) -> tuple[Point, ...]:
    by_point: dict[Point, int] = defaultdict(int)
    for segment in segments:
        by_point[segment[0]] += 1
        by_point[segment[1]] += 1
    return tuple(sorted(point for point, count in by_point.items() if count > 2))


def _normalized_excess(actual: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0 if actual <= 0 else float(actual)
    value = (actual - baseline) / baseline
    return 0.0 if isclose(value, 0.0, abs_tol=1e-12) else value


def _unrelated_crossing_count(
    segments: tuple[Segment, ...], unrelated_segments: tuple[Segment, ...]
) -> int:
    return sum(
        1
        for first in segments
        for second in unrelated_segments
        if _crosses_without_shared_endpoint(first, second)
    )


def _crosses_without_shared_endpoint(first: Segment, second: Segment) -> bool:
    if set(first) & set(second):
        return False
    first_direction = _direction(first)
    second_direction = _direction(second)
    if {first_direction, second_direction} != {"horizontal", "vertical"}:
        return False
    horizontal, vertical = (first, second) if first_direction == "horizontal" else (second, first)
    hx1, hx2 = sorted((horizontal[0][0], horizontal[1][0]))
    vy1, vy2 = sorted((vertical[0][1], vertical[1][1]))
    return hx1 < vertical[0][0] < hx2 and vy1 < horizontal[0][1] < vy2


def _u_shaped_detours(segments: tuple[Segment, ...]) -> int:
    count = 0
    for first, second, third in zip(segments, segments[1:], segments[2:], strict=False):
        if first[1] != second[0] or second[1] != third[0]:
            continue
        if _direction(first) != _direction(third) or _direction(second) == _direction(first):
            continue
        if _opposite_parallel(first, third):
            count += 1
    return count


def _opposite_parallel(first: Segment, second: Segment) -> bool:
    direction = _direction(first)
    if direction == "horizontal":
        return (first[1][0] - first[0][0]) * (second[1][0] - second[0][0]) < 0
    if direction == "vertical":
        return (first[1][1] - first[0][1]) * (second[1][1] - second[0][1]) < 0
    return False


def _branch_inconsistency(segments: tuple[Segment, ...], branch_points: tuple[Point, ...]) -> int:
    worst = 0
    for point in branch_points:
        lengths = [_segment_length(segment) for segment in segments if point in segment]
        if lengths:
            worst = max(worst, max(lengths) - min(lengths))
    return worst


def _route_excursions(segments: tuple[Segment, ...], unrelated_blocks: tuple[Rect, ...]) -> tuple[Segment, ...]:
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
    segments: tuple[Segment, ...], local_label_pairs: tuple[LabelPair, ...], direct_distance_limit: int
) -> tuple[str, ...]:
    disconnected = []
    for label_id, first, second in local_label_pairs:
        if _manhattan(first, second) > direct_distance_limit:
            continue
        if not any(_segment_connects(segment, first, second) for segment in segments):
            disconnected.append(label_id)
    return tuple(disconnected)


def _segment_connects(segment: Segment, first: Point, second: Point) -> bool:
    return first in segment and second in segment


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
