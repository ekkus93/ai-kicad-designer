"""Jogs, collinear segments and idle junction dots (reviewer loop spec R7.5).

Three simplifications, each kept only when every check, KiCad's netlist and ERC among
them, still passes:

- a short hook (out, across, back) whose two ends line up becomes one straight wire
  (the regulator's U1 pin-2 return: right 1.27 mm, down, left 1.27 mm onto the bus);
- a junction dot where fewer than three wire directions or pins meet marks no branch and
  is removed;
- two collinear wires meeting end to end, with nothing else at that point, are merged.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from ai_kicad.sexpr import children, one, parse

from .block_moves import GRID, _units
from .power_symbols import _append_forms, power_symbols
from .readability_checks import _on, _segments
from .schematic_review_native import _top_level_forms

Point = tuple[int, int]
Segment = tuple[Point, Point]

# A hook's out and back legs are at most this long.
HOOK_MAX = 2 * GRID
NATIVE_BUDGET = 6


def _nm(value: str) -> int:
    return round(float(value) * 1_000_000)


def _attached(text: str) -> set[Point]:
    """Points where something other than a wire attaches: pins, labels, power symbols
    (flags included) and no-connect marks."""
    tree = parse(text)
    points = {p["point"] for u in _units(text).values() for p in u["pins"]}
    points |= {item["point"] for item in power_symbols(tree)}
    for symbol in children(tree, "symbol"):
        if one(symbol, "lib_id")[1].startswith("power:"):
            at = one(symbol, "at")
            points.add((_nm(at[1]), _nm(at[2])))
    for kind in ("label", "global_label", "hierarchical_label", "no_connect"):
        for node in children(tree, kind):
            at = one(node, "at")
            points.add((_nm(at[1]), _nm(at[2])))
    return points


def _directions(point: Point, segments: list[Segment], attached: set[Point]) -> int:
    """How many ways connections leave a point: one per wire end there, two per wire
    passing through it, one per pin or other attachment."""
    count = 1 if point in attached else 0
    for a, b in segments:
        if point in (a, b):
            count += 1
        elif _on(point, (a, b)):
            count += 2
    return count


def _rewrite(text: str, drop_wires: set[Segment], drop_junctions: set[Point], add: list) -> str:
    rewritten = []
    for start, end, node in _top_level_forms(text):
        if node[0] == "wire":
            first, second = children(one(node, "pts"), "xy")[:2]
            seg = ((_nm(first[1]), _nm(first[2])), (_nm(second[1]), _nm(second[2])))
            if seg in drop_wires or (seg[1], seg[0]) in drop_wires:
                rewritten.append((start, end))
        elif node[0] == "junction":
            at = one(node, "at")
            if (_nm(at[1]), _nm(at[2])) in drop_junctions:
                rewritten.append((start, end))
    for start, end in reversed(rewritten):
        text = text[:start] + text[end:]
    if add:
        text = _append_forms(text, add)
    return text


def _wire(a: Point, b: Point) -> str:
    identity = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-kicad-cleanup-wire:{a}:{b}")
    return (
        f"(wire (pts (xy {a[0] / 1e6:.6f} {a[1] / 1e6:.6f}) (xy {b[0] / 1e6:.6f} "
        f'{b[1] / 1e6:.6f})) (stroke (width 0) (type default)) (uuid "{identity}"))'
    )


def _hooks(text: str) -> list[tuple[list[Segment], Point, Point]]:
    """Out-across-back hooks whose two ends line up across the middle leg."""
    tree = parse(text)
    segments = _segments(tree)
    attached = _attached(text)
    found = []
    for middle in segments:
        p1, p2 = middle
        legs = []
        for corner in (p1, p2):
            if corner in attached or _directions(corner, segments, attached) != 2:
                break
            leg = [s for s in segments if s != middle and corner in s]
            if len(leg) != 1:
                break
            other = leg[0][0] if leg[0][1] == corner else leg[0][1]
            legs.append((leg[0], other))
        if len(legs) != 2:
            continue
        (first, p0), (last, p3) = legs
        along = (p2[0] - p1[0], p2[1] - p1[1])
        out = (p1[0] - p0[0], p1[1] - p0[1])
        back = (p3[0] - p2[0], p3[1] - p2[1])
        # Both legs perpendicular to the middle, opposite ways, short and equal: the ends
        # line up and one straight wire joins them.
        if along[0] * out[0] + along[1] * out[1] or out != (-back[0], -back[1]):
            continue
        if abs(out[0]) + abs(out[1]) > HOOK_MAX:
            continue
        found.append(([first, middle, last], p0, p3))
    return found


def _contained(text: str) -> set[Segment]:
    """Wires lying wholly inside another wire: drawn twice, joined anyway."""
    segments = _segments(parse(text))
    found = set()
    for seg in segments:
        for other in segments:
            if other != seg and _on(seg[0], other) and _on(seg[1], other):
                found.add(seg)
                break
    return found


def _jogs_onto_wires(text: str) -> list[tuple[list[Segment], Point, Point]]:
    """A short jog out of a point, then a run that lands on a crossing wire: the run can
    start straight from the point and land beside where it did."""
    tree = parse(text)
    segments = _segments(tree)
    attached = _attached(text)
    found = []
    for out in segments:
        for p0, p1 in (out, out[::-1]):
            if p1 in attached or _directions(p1, segments, attached) != 2:
                continue
            length = abs(p1[0] - p0[0]) + abs(p1[1] - p0[1])
            if not 0 < length <= HOOK_MAX:
                continue
            runs = [s for s in segments if s != out and p1 in s]
            if len(runs) != 1:
                continue
            run = runs[0]
            p2 = run[0] if run[1] == p1 else run[1]
            along = (p2[0] - p1[0], p2[1] - p1[1])
            step = (p1[0] - p0[0], p1[1] - p0[1])
            if along[0] * step[0] + along[1] * step[1]:
                continue
            target = (p0[0] + along[0], p0[1] + along[1])
            # p2 and the new landing both lie on one crossing wire.
            if any(seg not in (out, run) and _on(p2, seg) and _on(target, seg) for seg in segments):
                found.append(([out, run], p0, target))
    return found


def _idle_junctions(text: str) -> set[Point]:
    tree = parse(text)
    segments = _segments(tree)
    attached = _attached(text)
    idle = set()
    for node in children(tree, "junction"):
        at = one(node, "at")
        point = (_nm(at[1]), _nm(at[2]))
        if _directions(point, segments, attached) < 3:
            idle.add(point)
    return idle


def _collinear_pairs(text: str) -> list[tuple[Segment, Segment, Point, Point]]:
    tree = parse(text)
    segments = _segments(tree)
    attached = _attached(text)
    pairs, used = [], set()
    for index, first in enumerate(segments):
        for second in segments[index + 1 :]:
            shared = set(first) & set(second)
            if len(shared) != 1 or first in used or second in used:
                continue
            (point,) = shared
            if point in attached or _directions(point, segments, attached) != 2:
                continue
            a = first[0] if first[1] == point else first[1]
            b = second[0] if second[1] == point else second[1]
            if not (a[0] == point[0] == b[0] or a[1] == point[1] == b[1]):
                continue
            pairs.append((first, second, a, b))
            used |= {first, second}
    return pairs


def simplify_wires_text(
    text: str,
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
    native_ok: Callable[[str], str | None] | None,
) -> tuple[str, dict]:
    """Straighten hooks, then drop idle dots and merge collinear wires, each kept only if
    every check passes. Returns the text and a record of what changed and what did not."""
    started = time.monotonic()
    record = {"hooks": [], "junctions_removed": 0, "merged": 0, "native": 0, "refused": []}

    from .text_clearance import MINIMUM, text_wire_clearances

    def accept(candidate: str, label: str) -> bool:
        # Never bring part text closer to a wire than a grid step (or than it already was).
        before = min(text_wire_clearances(text).values(), default=MINIMUM)
        after = min(text_wire_clearances(candidate).values(), default=MINIMUM)
        if after < min(before, MINIMUM):
            record["refused"].append(f"{label}: text would be {after / 1e6} mm from a wire")
            return False
        objection = layout_check(candidate)
        if objection:
            record["refused"].append(f"{label}: layout check: {objection[:80]}")
            return False
        if not fields_ok(candidate):
            record["refused"].append(f"{label}: a field check would report something new")
            return False
        if record["native"] >= NATIVE_BUDGET:
            record["refused"].append(f"{label}: native budget spent")
            return False
        record["native"] += 1
        failure = native_ok(candidate) if native_ok else None
        if failure:
            record["refused"].append(f"{label}: native check: {failure[:80]}")
            return False
        return True

    tried: set[tuple[Point, Point]] = set()
    while True:
        hooks = [h for h in _hooks(text) + _jogs_onto_wires(text) if (h[1], h[2]) not in tried]
        if not hooks:
            break
        legs, p0, p3 = hooks[0]
        tried.add((p0, p3))
        label = f"straighten hook {p0[0] / 1e6:.2f},{p0[1] / 1e6:.2f}"
        candidate = _rewrite(text, set(legs), set(), [_wire(p0, p3)])
        # Dots the hook's corners needed are idle now.
        candidate = _rewrite(candidate, _contained(candidate), set(), [])
        candidate = _rewrite(candidate, set(), _idle_junctions(candidate), [])
        if accept(candidate, label):
            text = candidate
            record["hooks"].append(label)
    # Then every idle dot and collinear pair, together, in one checked change.
    idle = _idle_junctions(text)
    pairs = _collinear_pairs(text)
    if idle or pairs:
        candidate = _rewrite(
            text,
            {s for first, second, _a, _b in pairs for s in (first, second)},
            idle,
            [_wire(a, b) for _first, _second, a, b in pairs],
        )
        candidate = _rewrite(candidate, set(), _idle_junctions(candidate), [])
        if accept(candidate, "remove idle dots and merge collinear wires"):
            record["junctions_removed"] = len(idle)
            record["merged"] = len(pairs)
            text = candidate
    record["seconds"] = round(time.monotonic() - started, 1)
    record["refused"] = record["refused"][:6]
    return text, record
