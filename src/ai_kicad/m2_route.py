"""Deterministic bounded routing between placed M2 fragments."""

from __future__ import annotations

from dataclasses import dataclass

from .ir import InputError
from .m2a import PITCH
from .m2_fragments import Point, PortAnchor
from .m2_pack import PlacedFragment
from .m2_semantics import SemanticEdge, SemanticPlan


@dataclass(frozen=True)
class RouteTree:
    net: str
    edges: tuple[SemanticEdge, ...]
    segments: tuple[tuple[Point, Point], ...]
    junctions: tuple[Point, ...]


def _port(item: PlacedFragment, net: str, output: bool) -> PortAnchor:
    roles = {"signal_out", "power_out"} if output else {"signal_in", "power_in"}
    candidates = [
        anchor for anchor in item.ports if anchor.port.net == net and anchor.port.role in roles
    ]
    if not candidates:
        candidates = [anchor for anchor in item.ports if anchor.port.net == net]
    if not candidates:
        raise InputError(f"ROUTE_PORT_MISSING: {item.fragment.block.id}:{net}")
    return sorted(candidates, key=lambda anchor: anchor.port.id)[0]


def _orthogonal(source: PortAnchor, target: PortAnchor) -> tuple[tuple[Point, Point], ...]:
    a, b = source.point, target.point
    if a[1] == b[1] or a[0] == b[0]:
        return ((a, b),) if a != b else ()
    if a[0] < b[0]:
        bend_x = ((a[0] + b[0]) // (2 * PITCH)) * PITCH
        points = (a, (bend_x, a[1]), (bend_x, b[1]), b)
    else:
        bend_y = ((a[1] + b[1]) // (2 * PITCH)) * PITCH
        points = (a, (a[0], bend_y), (b[0], bend_y), b)
    return tuple((first, second) for first, second in zip(points, points[1:]) if first != second)


def _branch_attachment(
    source_item: PlacedFragment,
    target_item: PlacedFragment,
    source: PortAnchor,
    target: PortAnchor,
) -> tuple[tuple[Point, Point], ...]:
    """Leave a source through its accessible side before dropping to a load band."""
    lane_x = source_item.envelope[2]
    if target_item.envelope[1] >= source_item.envelope[3]:
        lane_y = target_item.envelope[1]
        target_x = target_item.envelope[0]
        points = (
            source.point,
            (lane_x, source.point[1]),
            (lane_x, lane_y),
            (target_x, lane_y),
            (target_x, target.point[1]),
            target.point,
        )
    else:
        points = (
            source.point,
            (lane_x, source.point[1]),
            (lane_x, target.point[1]),
            target.point,
        )
    return tuple((first, second) for first, second in zip(points, points[1:]) if first != second)


def _vertical_escape_x(item: PlacedFragment, source: PortAnchor, lane_y: int) -> int:
    """Find the first grid track to the right that clears measured body obstacles."""
    x = source.point[0]
    low, high = sorted((source.point[1], lane_y))
    obstacles = [
        tuple(value + shift for value, shift in zip(rect, (*item.delta, *item.delta), strict=True))
        for rect in item.fragment.obstacles
    ]
    while True:
        blocked = [
            rect
            for rect in obstacles
            if rect[0] < x < rect[2] and max(low, rect[1]) < min(high, rect[3])
        ]
        if not blocked:
            return x
        right = max(rect[2] for rect in blocked)
        x = ((right + PITCH - 1) // PITCH) * PITCH


def route_between_fragments(
    plan: SemanticPlan, placed: tuple[PlacedFragment, ...]
) -> tuple[RouteTree, ...]:
    """Create stable net route trees for sequencing and load-attachment edges."""
    by_id = {item.fragment.block.id: item for item in placed}
    grouped: dict[str, list[SemanticEdge]] = {}
    for edge in plan.edges:
        if edge.kind in {"signal", "power", "branch"}:
            grouped.setdefault(edge.net, []).append(edge)
    result = []
    for net, edges in sorted(grouped.items()):
        segments = set()
        junctions = set()
        ordered = sorted(edges, key=lambda edge: (edge.source, edge.target, edge.kind))
        if len(ordered) > 1 and len({edge.source for edge in ordered}) == 1:
            source_item = by_id[ordered[0].source]
            source = _port(source_item, net, True)
            targets = [_port(by_id[edge.target], net, False) for edge in ordered]
            target_items = [by_id[edge.target] for edge in ordered]
            if all(target.point[1] == source.point[1] for target in targets):
                lane_y = source.point[1]
                root = source.point
            elif all(item.envelope[1] >= source_item.envelope[3] for item in target_items):
                lane_y = min(item.envelope[1] for item in target_items)
                escape_x = _vertical_escape_x(source_item, source, lane_y)
                escape = (escape_x, source.point[1])
                root = (escape_x, lane_y)
                segments.add((source.point, escape))
                segments.add((escape, root))
            else:
                lane_y = source_item.envelope[1] - 2 * PITCH
                root = (source.point[0], lane_y)
                segments.add((source.point, root))
            taps = [(target.point[0], lane_y) for target in targets]
            trunk_points = [root, *taps]
            left = min(trunk_points)
            right = max(trunk_points)
            if left != right:
                segments.add((left, right))
            for target, tap in zip(targets, taps, strict=True):
                segments.add((tap, target.point))
                if tap not in {left, right}:
                    junctions.add(tap)
            junctions.add(root)
        else:
            for edge in ordered:
                source = _port(by_id[edge.source], net, True)
                target = _port(by_id[edge.target], net, False)
                route = (
                    _branch_attachment(by_id[edge.source], by_id[edge.target], source, target)
                    if edge.kind == "branch"
                    else _orthogonal(source, target)
                )
                segments.update(route)
                if len(route) > 1:
                    junctions.update(segment[1] for segment in route[:-1])
        result.append(
            RouteTree(
                net,
                tuple(ordered),
                tuple(sorted(segments)),
                tuple(sorted(junctions)),
            )
        )
    return tuple(result)
