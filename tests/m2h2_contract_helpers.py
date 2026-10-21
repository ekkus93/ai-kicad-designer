"""Small independent helpers shared by M2H2 contract tests."""

from collections import defaultdict, deque

from ai_kicad.m2_geometry import ConductorSegment


def reference_components(segments: tuple[ConductorSegment, ...]) -> int:
    """Cell-walk oracle, independent of the production segment canonicalizer."""
    cells: set[tuple[int, int]] = set()
    for segment in segments:
        first, second = segment.start, segment.end
        if first[0] == second[0]:
            cells.update(
                (first[0], y) for y in range(min(first[1], second[1]), max(first[1], second[1]) + 1)
            )
        else:
            cells.update(
                (x, first[1]) for x in range(min(first[0], second[0]), max(first[0], second[0]) + 1)
            )
    adjacent = defaultdict(set)
    for x, y in cells:
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in cells:
                adjacent[(x, y)].add(neighbor)
    count = 0
    remaining = set(cells)
    while remaining:
        count += 1
        pending = deque((min(remaining),))
        remaining.remove(pending[0])
        while pending:
            for neighbor in adjacent[pending.popleft()] & remaining:
                remaining.remove(neighbor)
                pending.append(neighbor)
    return count


def segment(a: tuple[int, int], b: tuple[int, int], net: str = "N") -> ConductorSegment:
    return ConductorSegment(a, b, net, "synthetic")
