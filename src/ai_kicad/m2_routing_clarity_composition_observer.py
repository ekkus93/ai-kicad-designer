"""Independent routing-clarity and label-discipline observer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

Point = tuple[int, int]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class RoutedPath:
    path_id: str
    points: tuple[Point, ...]
    role: str = "signal"
    source_id: str | None = None
    owner_block_id: str | None = None
    allowed_block_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlockArea:
    block_id: str
    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class LabelUse:
    net_id: str
    endpoint_a: Point
    endpoint_b: Point
    direct_visible_connection_legal: bool = True
    global_distribution: bool = False


@dataclass(frozen=True)
class RouteLength:
    path_id: str
    bend_count: int
    canonical_length: int


@dataclass(frozen=True)
class RouteExcursion:
    path_id: str
    block_id: str


@dataclass(frozen=True)
class LabelDisconnect:
    net_id: str
    distance: int


@dataclass(frozen=True)
class RoutingClarityMetrics:
    routes: tuple[RouteLength, ...]
    total_bend_count: int
    total_canonical_length: int
    unrelated_crossings: tuple[str, ...]
    u_shaped_detour_path_ids: tuple[str, ...]
    unrelated_block_excursions: tuple[RouteExcursion, ...]
    sibling_branch_geometry_inconsistency: tuple[str, ...]
    label_mediated_local_disconnects: tuple[LabelDisconnect, ...]


def measure_routing_clarity(
    paths: tuple[RoutedPath, ...],
    *,
    labels: tuple[LabelUse, ...] = (),
    blocks: tuple[BlockArea, ...] = (),
    local_label_distance: int = 60,
) -> RoutingClarityMetrics:
    """Measure route bends, detours, crossings, block excursions, and labels."""
    lengths = tuple(
        RouteLength(path.path_id, _bend_count(path.points), _path_length(path.points))
        for path in sorted(paths, key=lambda item: item.path_id)
    )
    total_bends = sum(route.bend_count for route in lengths)
    total_length = sum(route.canonical_length for route in lengths)
    crossings = _unrelated_crossings(paths)
    u_detours = tuple(
        sorted(
            route.path_id
            for route in lengths
            if route.bend_count >= 3 and _is_excessive_detour(route)
        )
    )
    excursions = _block_excursions(paths, blocks)
    branch_inconsistency = _branch_geometry_inconsistency(paths)
    label_disconnects = tuple(
        sorted(
            (
                LabelDisconnect(label.net_id, _manhattan(label.endpoint_a, label.endpoint_b))
                for label in labels
                if label.direct_visible_connection_legal
                and not label.global_distribution
                and _manhattan(label.endpoint_a, label.endpoint_b) <= local_label_distance
            ),
            key=lambda item: item.net_id,
        )
    )
    return RoutingClarityMetrics(
        lengths,
        total_bends,
        total_length,
        crossings,
        u_detours,
        excursions,
        branch_inconsistency,
        label_disconnects,
    )


def _bend_count(points: tuple[Point, ...]) -> int:
    if len(points) < 3:
        return 0
    bends = 0
    previous = _direction(points[0], points[1])
    for first, second in zip(points[1:], points[2:], strict=True):
        direction = _direction(first, second)
        if direction != previous:
            bends += 1
        previous = direction
    return bends


def _direction(first: Point, second: Point) -> str:
    if first[0] == second[0]:
        return "vertical"
    if first[1] == second[1]:
        return "horizontal"
    return "diagonal"


def _path_length(points: tuple[Point, ...]) -> int:
    return sum(_manhattan(first, second) for first, second in zip(points, points[1:], strict=True))


def _is_excessive_detour(route: RouteLength) -> bool:
    # Direct length is unavailable in the summarized witness, so use a conservative
    # route-internal proxy: high length per bend identifies rectangular/U-shaped loops.
    return route.canonical_length >= 80 and route.canonical_length / max(1, route.bend_count) >= 25


def _segments(path: RoutedPath) -> tuple[Segment, ...]:
    return tuple(zip(path.points, path.points[1:], strict=True))


def _unrelated_crossings(paths: tuple[RoutedPath, ...]) -> tuple[str, ...]:
    witnesses: list[str] = []
    for index, first in enumerate(paths):
        for second in paths[index + 1 :]:
            if first.source_id is not None and first.source_id == second.source_id:
                continue
            for first_segment in _segments(first):
                for second_segment in _segments(second):
                    if _orthogonal_cross(first_segment, second_segment):
                        witnesses.append(f"{first.path_id}:{second.path_id}")
                        break
                else:
                    continue
                break
    return tuple(sorted(set(witnesses)))


def _orthogonal_cross(first: Segment, second: Segment) -> bool:
    (a, b), (c, d) = first, second
    if set(first) & set(second):
        return False
    if a[1] == b[1] and c[0] == d[0]:
        return min(a[0], b[0]) < c[0] < max(a[0], b[0]) and min(c[1], d[1]) < a[1] < max(
            c[1], d[1]
        )
    if a[0] == b[0] and c[1] == d[1]:
        return min(c[0], d[0]) < a[0] < max(c[0], d[0]) and min(a[1], b[1]) < c[1] < max(
            a[1], b[1]
        )
    return False


def _block_excursions(
    paths: tuple[RoutedPath, ...], blocks: tuple[BlockArea, ...]
) -> tuple[RouteExcursion, ...]:
    excursions: list[RouteExcursion] = []
    for path in paths:
        allowed = set(path.allowed_block_ids)
        if path.owner_block_id is not None:
            allowed.add(path.owner_block_id)
        for block in blocks:
            if block.block_id in allowed:
                continue
            if any(_segment_hits_block(segment, block) for segment in _segments(path)):
                excursions.append(RouteExcursion(path.path_id, block.block_id))
    return tuple(sorted(excursions, key=lambda item: (item.path_id, item.block_id)))


def _segment_hits_block(segment: Segment, block: BlockArea) -> bool:
    (first, second) = segment
    if first[0] == second[0]:
        x_value = first[0]
        return block.left <= x_value <= block.right and _ranges_overlap(
            first[1], second[1], block.top, block.bottom
        )
    if first[1] == second[1]:
        y_value = first[1]
        return block.top <= y_value <= block.bottom and _ranges_overlap(
            first[0], second[0], block.left, block.right
        )
    return False


def _ranges_overlap(first_a: int, first_b: int, second_a: int, second_b: int) -> bool:
    return max(min(first_a, first_b), min(second_a, second_b)) <= min(
        max(first_a, first_b), max(second_a, second_b)
    )


def _branch_geometry_inconsistency(paths: tuple[RoutedPath, ...]) -> tuple[str, ...]:
    by_source: dict[str, list[RoutedPath]] = defaultdict(list)
    for path in paths:
        if path.role == "branch" and path.source_id is not None:
            by_source[path.source_id].append(path)
    inconsistent: list[str] = []
    for source_id, source_paths in by_source.items():
        if len(source_paths) < 2:
            continue
        bends = [_bend_count(path.points) for path in source_paths]
        lengths = [_path_length(path.points) for path in source_paths]
        if max(bends) - min(bends) > 1 or max(lengths) - min(lengths) > 40:
            inconsistent.append(source_id)
    return tuple(sorted(inconsistent))


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
