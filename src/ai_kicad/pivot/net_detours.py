"""Per-net, per-pin-pair structural detours of drawn wiring (reviewer loop spec R7.3).

For each net and each pair of its pins joined by visible wire, the drawn path between
them (shortest path along the wires), its Manhattan distance, the excess, whether the
path leaves the box of the two parts it joins and comes back, and whether it starts by
going away from the other pin (a U-turn at that pin). Pins joined only through matching
power symbols are not on one wire and are not measured. Report-only.
"""

from __future__ import annotations

import heapq
import itertools

from .readability_checks import _on, _segments
from .schematic_description import _instances

Point = tuple[int, int]
# A path leaving the joined parts' box by more than this counts as leaving it.
BOX_SLACK = 1_270_000


def _mm(value: float) -> float:
    return round(value / 1_000_000, 3)


def _graph(segments: list, points: set[Point]) -> dict[Point, dict[Point, int]]:
    """Wire graph whose nodes are segment ends and the given points lying on segments."""
    nodes = {end for segment in segments for end in segment} | points
    graph: dict[Point, dict[Point, int]] = {}
    for start, end in segments:
        on = sorted(
            (node for node in nodes if _on(node, (start, end))),
            key=lambda p: (p[0] - start[0]) ** 2 + (p[1] - start[1]) ** 2,
        )
        for a, b in zip(on, on[1:]):
            length = abs(a[0] - b[0]) + abs(a[1] - b[1])
            graph.setdefault(a, {})[b] = length
            graph.setdefault(b, {})[a] = length
    return graph


def _path(graph, start: Point, goal: Point) -> list[Point] | None:
    queue, seen = [(0, start, [start])], set()
    while queue:
        cost, node, path = heapq.heappop(queue)
        if node == goal:
            return path
        if node in seen:
            continue
        seen.add(node)
        for other, length in graph.get(node, {}).items():
            if other not in seen:
                heapq.heappush(queue, (cost + length, other, [*path, other]))
    return None


def pin_pair_detours(tree: list, terminal_inventory: list[dict]) -> list[dict]:
    """Every wired pin pair on every net, with its drawn path and detour."""
    instances = _instances(tree)
    boxes: dict[str, tuple[int, int, int, int]] = {}
    for item in instances:
        xs = [item["body"][0], item["body"][2], *(p["point"][0] for p in item["pins"])]
        ys = [item["body"][1], item["body"][3], *(p["point"][1] for p in item["pins"])]
        box = (min(xs), min(ys), max(xs), max(ys))
        old = boxes.get(item["reference"])
        boxes[item["reference"]] = (
            box
            if old is None
            else (
                min(old[0], box[0]),
                min(old[1], box[1]),
                max(old[2], box[2]),
                max(old[3], box[3]),
            )
        )
    pins: dict[str, list[tuple[str, Point]]] = {}
    for item in terminal_inventory:
        point = (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6))
        pins.setdefault(item["net"], []).append((f"{item['reference']}.{item['pin']}", point))
    segments = _segments(tree)
    graph = _graph(segments, {point for members in pins.values() for _name, point in members})
    result = []
    for net, members in sorted(pins.items()):
        for (first, a), (second, b) in itertools.combinations(sorted(members), 2):
            path = _path(graph, a, b)
            if path is None:
                continue
            length = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(path, path[1:]))
            manhattan = abs(a[0] - b[0]) + abs(a[1] - b[1])
            parts = [boxes.get(name.split(".")[0]) for name in (first, second)]
            parts = [box for box in parts if box]
            leaves = False
            if parts:
                box = (
                    min(p[0] for p in parts) - BOX_SLACK,
                    min(p[1] for p in parts) - BOX_SLACK,
                    max(p[2] for p in parts) + BOX_SLACK,
                    max(p[3] for p in parts) + BOX_SLACK,
                )
                leaves = any(not (box[0] <= x <= box[2] and box[1] <= y <= box[3]) for x, y in path)

            def away(start: Point, step: Point, goal: Point) -> bool:
                # The first move from `start` increases the distance to `goal` on its axis.
                dx, dy = step[0] - start[0], step[1] - start[1]
                return dx * (goal[0] - start[0]) < 0 or dy * (goal[1] - start[1]) < 0

            u_turn = []
            if len(path) > 1 and away(a, path[1], b):
                u_turn.append(first)
            if len(path) > 1 and away(b, path[-2], a):
                u_turn.append(second)
            result.append(
                {
                    "net": net,
                    "pins": [first, second],
                    "path_mm": _mm(length),
                    "manhattan_mm": _mm(manhattan),
                    "excess_mm": _mm(length - manhattan),
                    "leaves_part_box": leaves,
                    "u_turn_at": u_turn,
                    "path": [[_mm(x), _mm(y)] for x, y in path],
                }
            )
    return result
