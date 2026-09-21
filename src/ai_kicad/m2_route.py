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
            source = _port(by_id[ordered[0].source], net, True)
            targets = [_port(by_id[edge.target], net, False) for edge in ordered]
            lane_y = min(by_id[edge.source].envelope[1] for edge in ordered) - 2 * PITCH
            root = (source.point[0], lane_y)
            segments.add((source.point, root))
            for target in targets:
                tap = (target.point[0], lane_y)
                segments.add((root, tap))
                segments.add((tap, target.point))
            junctions.add(root)
        else:
            for edge in ordered:
                source = _port(by_id[edge.source], net, True)
                target = _port(by_id[edge.target], net, False)
                route = _orthogonal(source, target)
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
