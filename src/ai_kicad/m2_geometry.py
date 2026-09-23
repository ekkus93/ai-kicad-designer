"""Integer geometry contracts shared by M2g2 planning and independent checks.

The observer rebuilds trees from emitted geometry; it never consumes planner
trees or ownership claims.  The records here are deliberately value objects so
that a measured fragment cannot be mutated after packing.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable, Literal

from .ir import InputError


Point = tuple[int, int]
Rect = tuple[int, int, int, int]
Direction = Literal["left", "right", "up", "down"]


def _ordered_segment(first: Point, second: Point) -> tuple[Point, Point]:
    return (first, second) if first <= second else (second, first)


def point_on_segment(point: Point, first: Point, second: Point) -> bool:
    return (
        first[0] == second[0] == point[0]
        and min(first[1], second[1]) <= point[1] <= max(first[1], second[1])
    ) or (
        first[1] == second[1] == point[1]
        and min(first[0], second[0]) <= point[0] <= max(first[0], second[0])
    )


def _strict_rect_intersection(first: Point, second: Point, rect: Rect) -> bool:
    left, top, right, bottom = rect
    if first[0] == second[0]:
        return left < first[0] < right and max(min(first[1], second[1]), top) < min(
            max(first[1], second[1]), bottom
        )
    return top < first[1] < bottom and max(min(first[0], second[0]), left) < min(
        max(first[0], second[0]), right
    )


@dataclass(frozen=True)
class GeometryItem:
    id: str
    kind: str
    owner: str
    rect: Rect
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reservation:
    id: str
    occupancy: Literal["exclusive", "channel"]
    owner: str
    clearance_class: str
    rect: Rect
    permitted_net: str | None = None
    capacity: int = 0

    def contains(self, rect: Rect) -> bool:
        return (
            self.rect[0] <= rect[0]
            and self.rect[1] <= rect[1]
            and self.rect[2] >= rect[2]
            and self.rect[3] >= rect[3]
        )

    def outward_growth(self, rect: Rect) -> tuple[int, int, int, int]:
        return (
            max(0, self.rect[0] - rect[0]),
            max(0, self.rect[1] - rect[1]),
            max(0, rect[2] - self.rect[2]),
            max(0, rect[3] - self.rect[3]),
        )


@dataclass(frozen=True)
class AccessWindow:
    rect: Rect
    approach_directions: frozenset[Direction]
    permitted_net: str

    def contains(self, point: Point) -> bool:
        return self.rect[0] <= point[0] <= self.rect[2] and self.rect[1] <= point[1] <= self.rect[3]


@dataclass(frozen=True)
class Gateway:
    id: str
    net: str
    terminals: tuple[tuple[str, str], ...]
    island: str
    anchor: Point
    escape_direction: Direction
    escape_polyline: tuple[Point, ...]
    approach_directions: frozenset[Direction]
    tap_windows: tuple[AccessWindow, ...]

    @property
    def point(self) -> Point:
        return self.escape_polyline[-1]

    def validate(self, terminal_nets: dict[tuple[str, str], str]) -> None:
        if not self.terminals or any(
            terminal_nets.get(item) != self.net for item in self.terminals
        ):
            raise InputError(f"GATEWAY_TERMINAL_IDENTITY: {self.id}:{self.net}")
        if len(self.escape_polyline) < 2 or self.escape_polyline[0] != self.anchor:
            raise InputError(f"GATEWAY_ESCAPE_INVALID: {self.id}")
        first, second = self.escape_polyline[:2]
        actual = (
            "right"
            if second[0] > first[0]
            else "left"
            if second[0] < first[0]
            else "down"
            if second[1] > first[1]
            else "up"
        )
        if actual != self.escape_direction:
            raise InputError(f"GATEWAY_ESCAPE_DIRECTION: {self.id}:{actual}")


@dataclass(frozen=True)
class ConductorSegment:
    start: Point
    end: Point
    net: str
    owner: str
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start == self.end or (
            self.start[0] != self.end[0] and self.start[1] != self.end[1]
        ):
            raise InputError(f"CONDUCTOR_SEGMENT_INVALID: {self.start}->{self.end}")


@dataclass(frozen=True)
class ProtectedPath:
    id: str
    relationship_origins: tuple[str, ...]
    owner: str
    terminal_pairs: tuple[tuple[str, str], ...]
    net: str
    island: str
    required_component_transitions: tuple[tuple[str, str], ...]
    local_tree_edges: tuple[ConductorSegment, ...]
    corridors: tuple[Reservation, ...]
    tap_windows: tuple[AccessWindow, ...]
    maximum_span: int
    label_break_budget: int = 0

    def __post_init__(self) -> None:
        if self.label_break_budget != 0:
            raise InputError(f"PROTECTED_PATH_LABEL_BUDGET: {self.id}")


@dataclass(frozen=True)
class PathObligation:
    id: str
    owner: str
    net: str
    island: str
    terminals: tuple[tuple[str, str], ...]
    kind: str
    maximum_span: int | None = None


@dataclass(frozen=True)
class CanonicalTree:
    net: str
    segments: tuple[ConductorSegment, ...]
    junctions: tuple[Point, ...]
    degree: dict[Point, int]
    length: int
    bends: int
    geometry_signature: tuple[tuple[Point, Point], ...]


@dataclass(frozen=True)
class ConductorProof:
    net: str
    components: tuple[frozenset[Point], ...]
    terminal_components: tuple[tuple[tuple[str, str], int], ...]
    label_components: tuple[tuple[Point, int], ...]
    length: int


def conductor_components(tree: CanonicalTree) -> tuple[frozenset[Point], ...]:
    """Report actual wire islands; a common net string creates no edge."""
    adjacency: dict[Point, set[Point]] = defaultdict(set)
    for segment in tree.segments:
        adjacency[segment.start].add(segment.end)
        adjacency[segment.end].add(segment.start)
    pending = set(adjacency)
    result = []
    while pending:
        seed = min(pending)
        reached = {seed}
        queue = deque((seed,))
        while queue:
            point = queue.popleft()
            for neighbor in adjacency[point] - reached:
                reached.add(neighbor)
                queue.append(neighbor)
        result.append(frozenset(reached))
        pending.difference_update(reached)
    return tuple(result)


def prove_conductor_graph(
    tree: CanonicalTree,
    terminals: dict[tuple[str, str], Point],
    *,
    labels: Iterable[Point] = (),
    allow_labeled_islands: bool = False,
    declared_junctions: Iterable[Point] = (),
    intentional_ends: Iterable[Point] = (),
) -> ConductorProof:
    """Prove terminal coverage and permitted island joins from exact geometry."""
    components = conductor_components(tree)

    def component_at(point: Point) -> int | None:
        for index, component in enumerate(components):
            if point in component or any(
                point_on_segment(point, segment.start, segment.end)
                and segment.start in component
                and segment.end in component
                for segment in tree.segments
            ):
                return index
        return None

    terminal_components = []
    label_points = set(labels)
    for terminal, point in sorted(terminals.items()):
        index = component_at(point)
        if index is None and allow_labeled_islands and point in label_points:
            # Explicit labels placed exactly on pins are an existing permitted
            # presentation choice for externally scoped nets.
            index = -1
        if index is None:
            raise InputError(f"CONDUCTOR_TERMINAL_DETACHED: {tree.net}:{terminal}:{point}")
        terminal_components.append((terminal, index))
    label_components = []
    for point in sorted(label_points):
        index = component_at(point)
        if index is None and allow_labeled_islands and point in terminals.values():
            index = -1
        if index is None:
            raise InputError(f"CONDUCTOR_LABEL_DETACHED: {tree.net}:{point}")
        label_components.append((point, index))
    missing_junctions = set(tree.junctions) - set(declared_junctions)
    if missing_junctions:
        raise InputError(f"CONDUCTOR_JUNCTION_MISSING: {tree.net}:{sorted(missing_junctions)}")
    if len(components) > 1 and not (
        allow_labeled_islands
        and set(range(len(components))) <= {index for _, index in label_components}
    ):
        raise InputError(f"CONDUCTOR_ISLANDS_DISCONNECTED: {tree.net}:{len(components)}")
    permitted_ends = set(terminals.values()) | label_points | set(intentional_ends)
    dangling = sorted(
        point
        for point, degree in tree.degree.items()
        if degree == 1 and point not in permitted_ends
    )
    if dangling:
        raise InputError(f"CONDUCTOR_ENDPOINT_DANGLING: {tree.net}:{dangling}")
    return ConductorProof(
        tree.net, components, tuple(terminal_components), tuple(label_components), tree.length
    )


def content_envelope(items: Iterable[GeometryItem]) -> Rect:
    values = tuple(items)
    if not values:
        raise InputError("CONTENT_ENVELOPE_EMPTY")
    return (
        min(item.rect[0] for item in values),
        min(item.rect[1] for item in values),
        max(item.rect[2] for item in values),
        max(item.rect[3] for item in values),
    )


def envelope_contains(
    envelope: Rect, items: Iterable[GeometryItem], *, exact_limit: bool = False
) -> bool:
    del exact_limit  # inclusive bounds are exact; the name documents boundary tests.
    return all(
        envelope[0] <= item.rect[0]
        and envelope[1] <= item.rect[1]
        and envelope[2] >= item.rect[2]
        and envelope[3] >= item.rect[3]
        for item in items
    )


def _intersection(first: ConductorSegment, second: ConductorSegment) -> Point | None:
    if first.start[0] == first.end[0] and second.start[1] == second.end[1]:
        point = (first.start[0], second.start[1])
    elif first.start[1] == first.end[1] and second.start[0] == second.end[0]:
        point = (second.start[0], first.start[1])
    else:
        return None
    return (
        point
        if point_on_segment(point, first.start, first.end)
        and point_on_segment(point, second.start, second.end)
        else None
    )


def canonical_conductor_tree(
    segments: Iterable[ConductorSegment],
    *,
    junctions: Iterable[Point] = (),
    pins: Iterable[Point] = (),
) -> CanonicalTree:
    """Return a subdivision-invariant conductor union with actual ray degree."""
    raw = tuple(segments)
    if not raw:
        raise InputError("CONDUCTOR_TREE_EMPTY")
    nets = {segment.net for segment in raw}
    if len(nets) != 1:
        raise InputError(f"CONDUCTOR_TREE_NET_MIX: {sorted(nets)}")
    declared_junctions = set(junctions)
    split: list[set[Point]] = [{segment.start, segment.end} for segment in raw]
    explicit = set(pins) | declared_junctions
    for index, segment in enumerate(raw):
        split[index].update(
            point for point in explicit if point_on_segment(point, segment.start, segment.end)
        )
    for left_index, left in enumerate(raw):
        for right_index in range(left_index + 1, len(raw)):
            right = raw[right_index]
            # Endpoint-on-segment contacts are conductor contacts even when the
            # trunk was emitted unsplit. Interior/interior crossings need a dot.
            for point in {left.start, left.end, right.start, right.end}:
                if point_on_segment(point, left.start, left.end) and point_on_segment(
                    point, right.start, right.end
                ):
                    split[left_index].add(point)
                    split[right_index].add(point)
            crossing = _intersection(left, right)
            if crossing in declared_junctions:
                split[left_index].add(crossing)
                split[right_index].add(crossing)
            # Collinear overlaps split at all endpoints, producing a union.
            if (left.start[0] == left.end[0] == right.start[0] == right.end[0]) or (
                left.start[1] == left.end[1] == right.start[1] == right.end[1]
            ):
                for point in {left.start, left.end, right.start, right.end}:
                    if point_on_segment(point, left.start, left.end):
                        split[left_index].add(point)
                    if point_on_segment(point, right.start, right.end):
                        split[right_index].add(point)

    atoms: dict[tuple[Point, Point], list[ConductorSegment]] = defaultdict(list)
    for segment, points in zip(raw, split, strict=True):
        ordered = (
            sorted(points, key=lambda point: (point[1], point[0]))
            if segment.start[0] == segment.end[0]
            else sorted(points)
        )
        for first, second in zip(ordered, ordered[1:]):
            if first != second:
                atoms[_ordered_segment(first, second)].append(segment)
    normalized = []
    for (first, second), sources in sorted(atoms.items()):
        owners = {source.owner for source in sources}
        if len(owners) != 1:
            raise InputError(f"CONDUCTOR_OWNER_CONFLICT: {first}->{second}:{sorted(owners)}")
        provenance = tuple(sorted({item for source in sources for item in source.provenance}))
        normalized.append(
            ConductorSegment(first, second, raw[0].net, next(iter(owners)), provenance)
        )

    rays: dict[Point, set[Direction]] = defaultdict(set)
    adjacency: dict[Point, set[Point]] = defaultdict(set)
    for segment in normalized:
        first, second = segment.start, segment.end
        adjacency[first].add(second)
        adjacency[second].add(first)
        if first[0] == second[0]:
            rays[first].add("down" if second[1] > first[1] else "up")
            rays[second].add("up" if second[1] > first[1] else "down")
        else:
            rays[first].add("right" if second[0] > first[0] else "left")
            rays[second].add("left" if second[0] > first[0] else "right")
    degree = {point: len(directions) for point, directions in sorted(rays.items())}
    actual_junctions = tuple(sorted(point for point, value in degree.items() if value >= 3))
    bends = sum(
        value == 2 and len({direction in {"left", "right"} for direction in rays[point]}) == 2
        for point, value in degree.items()
    )
    # Geometry metrics/signatures ignore harmless serialization points while
    # ``segments`` retains them so provenance remains attached to exact spans.
    mandatory = set(pins) | set(actual_junctions)
    mandatory.update(point for point, directions in rays.items() if len(directions) != 2)
    signature_parts: list[tuple[Point, Point]] = []
    for vertical in (False, True):
        lines: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for segment in normalized:
            if (segment.start[0] == segment.end[0]) != vertical:
                continue
            fixed = segment.start[0] if vertical else segment.start[1]
            values = (
                (segment.start[1], segment.end[1])
                if vertical
                else (segment.start[0], segment.end[0])
            )
            lines[fixed].append((min(values), max(values)))
        for fixed, intervals in sorted(lines.items()):
            merged: list[list[int]] = []
            for low, high in sorted(intervals):
                if merged and low <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], high)
                else:
                    merged.append([low, high])
            for low, high in merged:
                cuts = {low, high}
                cuts.update(
                    point[1] if vertical else point[0]
                    for point in mandatory
                    if (point[0] if vertical else point[1]) == fixed
                    and low < (point[1] if vertical else point[0]) < high
                )
                ordered_cuts = sorted(cuts)
                for a, b in zip(ordered_cuts, ordered_cuts[1:]):
                    first = (fixed, a) if vertical else (a, fixed)
                    second = (fixed, b) if vertical else (b, fixed)
                    signature_parts.append(_ordered_segment(first, second))
    signature = tuple(sorted(signature_parts))
    return CanonicalTree(
        raw[0].net,
        tuple(normalized),
        actual_junctions,
        degree,
        sum(
            abs(segment.start[0] - segment.end[0]) + abs(segment.start[1] - segment.end[1])
            for segment in normalized
        ),
        bends,
        signature,
    )


def conductor_reachable(
    tree: CanonicalTree,
    first: Point,
    second: Point,
    *,
    labels: Iterable[tuple[str, Point]] = (),
) -> bool:
    """Check explicit conductor reachability; labels intentionally add no edges."""
    del labels
    adjacency: dict[Point, set[Point]] = defaultdict(set)
    for segment in tree.segments:
        adjacency[segment.start].add(segment.end)
        adjacency[segment.end].add(segment.start)
    starts = {point for point in adjacency if point == first}
    goals = {point for point in adjacency if point == second}
    if not starts:
        starts = {
            endpoint
            for segment in tree.segments
            if point_on_segment(first, segment.start, segment.end)
            for endpoint in (segment.start, segment.end)
        }
    if not goals:
        goals = {
            endpoint
            for segment in tree.segments
            if point_on_segment(second, segment.start, segment.end)
            for endpoint in (segment.start, segment.end)
        }
    pending, visited = deque(starts), set(starts)
    while pending:
        point = pending.popleft()
        if point in goals:
            return True
        for neighbor in adjacency[point] - visited:
            visited.add(neighbor)
            pending.append(neighbor)
    return first == second and bool(starts)


def prove_gateway_witnesses(
    tree: CanonicalTree,
    gateway: Gateway,
    actual_pins: dict[tuple[str, str], Point],
) -> tuple[tuple[str, str], ...]:
    """Prove every declared witness through preserved conductor geometry."""
    if gateway.net != tree.net or not gateway.terminals:
        raise InputError(f"GATEWAY_GRAPH_IDENTITY: {gateway.id}")
    if not conductor_reachable(tree, gateway.anchor, gateway.point):
        raise InputError(f"GATEWAY_ESCAPE_DETACHED: {gateway.id}")
    for terminal in gateway.terminals:
        point = actual_pins.get(terminal)
        if point is None or not conductor_reachable(tree, point, gateway.point):
            raise InputError(f"GATEWAY_PIN_DETACHED: {gateway.id}:{terminal}:{point}")
    return gateway.terminals


def segment_is_admissible(
    first: Point,
    second: Point,
    obstacles: Iterable[Reservation],
    protected: Iterable[Reservation],
    *,
    net: str,
    owner: str,
    tap: Point | None = None,
    tap_windows: Iterable[AccessWindow] = (),
) -> bool:
    if first == second or (first[0] != second[0] and first[1] != second[1]):
        return False
    for reservation in tuple(obstacles) + tuple(protected):
        if not _strict_rect_intersection(first, second, reservation.rect):
            continue
        if reservation.owner == owner:
            continue
        legal_tap = tap is not None and any(
            window.permitted_net == net and window.contains(tap) for window in tap_windows
        )
        if not legal_tap:
            return False
    return True
