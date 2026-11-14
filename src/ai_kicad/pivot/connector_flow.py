"""Orient and place single-pin connectors by pin facing and signal flow (spec R7.1).

A pivot-side step after the protected compiler, under brief v11. A single-pin connector
whose wire U-turns around it (its pin faces away from the part it feeds) or wraps around
another part to reach it is mirrored in place, or moved beside the nearest pin it joins
with its pin facing that pin. Each candidate is rerouted with the editor's obstacle-checked
router and kept only if the protected observer accepts it, no field check reports anything
new, and the connector's net detours shrink by more than a grid step. Otherwise the
connector stays as the compiler drew it, and the reason is recorded.
"""

from __future__ import annotations

import re
from typing import Callable
from uuid import uuid4

from ai_kicad.m2a_core import _nm
from ai_kicad.sexpr import children, one, parse

from .net_detours import pin_pair_detours
from .readability_checks import FRAME, content_extent
from .schematic_description import _instances

Point = tuple[int, int]
GRID = 1_270_000
# Distances from the target pin tried for a moved connector's pin.
PLACEMENT_REACH = (6, 8, 10, 12, 16)
# Required improvement in the connector net's total detour.
MINIMUM_GAIN = GRID * 2


def _single_pin_connectors(tree: list) -> list[dict]:
    return [
        item
        for item in _instances(tree)
        if item["lib_id"].startswith("Connector") and len(item["pins"]) == 1
    ]


def current_inventory(text: str, nets: dict[tuple[str, str], str]) -> list[dict]:
    """Terminal positions read from the drawing, with the nets of the original inventory."""
    rows = []
    for item in _instances(parse(text)):
        for pin in item["pins"]:
            net = nets.get((item["reference"], pin["number"]))
            if net is not None:
                rows.append(
                    {
                        "net": net,
                        "reference": item["reference"],
                        "pin": pin["number"],
                        "x_mm": pin["point"][0] / 1e6,
                        "y_mm": pin["point"][1] / 1e6,
                    }
                )
    return rows


def _net_detour(text: str, nets: dict, net: str) -> float:
    rows = pin_pair_detours(parse(text), current_inventory(text, nets))
    return sum(row["excess_mm"] for row in rows if row["net"] == net)


def _cost(text: str, nets: dict, net: str, reference: str) -> float:
    """The connector net's wired detours, plus the connector's distance to its nearest net
    pin when no wire reaches it (it is joined only by a label)."""
    terminals = current_inventory(text, nets)
    rows = pin_pair_detours(parse(text), terminals)
    total = sum(row["excess_mm"] for row in rows if row["net"] == net)
    if not any(any(p.startswith(reference + ".") for p in row["pins"]) for row in rows):
        own = [t for t in terminals if t["reference"] == reference and t["net"] == net]
        others = [t for t in terminals if t["net"] == net and t["reference"] != reference]
        if own and others:
            total += min(
                abs(o["x_mm"] - own[0]["x_mm"]) + abs(o["y_mm"] - own[0]["y_mm"]) for o in others
            )
    return round(total, 3)


def _detached(text: str, nets: dict, reference: str) -> bool:
    """No drawn wire joins the connector's pin to another pin of its net."""
    rows = pin_pair_detours(parse(text), current_inventory(text, nets))
    return not any(any(p.startswith(reference + ".") for p in row["pins"]) for row in rows)


def _flagged(text: str, nets: dict, reference: str) -> list[dict]:
    rows = pin_pair_detours(parse(text), current_inventory(text, nets))
    return [
        row
        for row in rows
        if any(pin.startswith(reference + ".") for pin in row["pins"])
        and row["excess_mm"] > 2.54
        and (
            any(pin.startswith(reference + ".") for pin in row["u_turn_at"])
            or row["leaves_part_box"]
        )
    ]


def _symbol_form(text: str, reference: str):
    from .schematic_review_native import _top_level_forms

    for start, end, node in _top_level_forms(text):
        if node[0] == "symbol" and any(
            prop[1] == "Reference" and prop[2] == reference for prop in children(node, "property")
        ):
            return start, end, node
    raise KeyError(reference)


def _place(text: str, reference: str, mirror: bool, pin_target: Point | None) -> str:
    """Mirror the connector's symbol (and its text) if asked, then translate it so its pin
    lands on `pin_target`. Wiring is not touched."""
    import re

    from .schematic_review_native import _translate_block

    start, end, node = _symbol_form(text, reference)
    block = text[start:end]
    if mirror:
        if children(node, "mirror"):
            if one(node, "mirror")[1] != "y":
                raise ValueError("connector already mirrored about x")
            block = re.sub(r"\s*\(mirror\s+y\)", "", block, count=1)
        else:
            block = re.sub(r"(\(at\s+[^()]+\))", r"\1 (mirror y)", block, count=1)
        anchor_x = _nm(one(node, "at")[1])

        def reflect(match: re.Match[str]) -> str:
            x = _nm(match[2])
            return f"{match[1]}{(2 * anchor_x - x) / 1e6:.6f} {match[3]}"

        # Field text is reflected with the body, so it keeps its side relative to the pin.
        head, rest = block.split("(property", 1)
        rest = re.sub(
            r'(\(property\s+"(?:Reference|Value)"\s+"(?:\\.|[^"\\])*"\s+\(at\s+)([-+0-9.]+)\s+([-+0-9.]+)',
            reflect,
            "(property" + rest,
        )
        block = head + rest
    trial = text[:start] + block + text[end:]
    if pin_target is None:
        return trial
    (pin,) = next(
        item["pins"] for item in _instances(parse(trial)) if item["reference"] == reference
    )
    dx, dy = pin_target[0] - pin["point"][0], pin_target[1] - pin["point"][1]
    if dx or dy:
        start, end, _node = _symbol_form(trial, reference)
        block = _translate_block(trial[start:end], dx / 1e6, dy / 1e6)
        trial = trial[:start] + block + trial[end:]
    return trial


def _reroute(
    text: str, old_pin: Point, new_pin: Point, inventory: list[dict], target: Point
) -> str:
    """Remove the wire tree that reached `old_pin` and join its terminals again.

    When that tree reaches no other part's pin (the compiler joined the connector to its
    net only by a label), the private stub and its labels are removed, its power flags move
    to the new pin, and the connector is wired straight to `target`, a pin on its net.
    """
    from .schematic_review_native import (
        _connect_point_groups,
        _terminal_keepouts,
        _top_level_forms,
        _translate_block,
        _wire_trees,
    )
    from ai_kicad.m2_geometry import point_on_segment

    tree = parse(text)
    segments, owners, roots = _wire_trees(tree)
    touching = {
        root for segment, root in zip(segments, roots) if point_on_segment(old_pin, *segment)
    }
    if not touching:
        return text
    removed = {owner for owner, root in zip(owners, roots) if root in touching}

    def on_tree(point: Point) -> bool:
        return any(
            point_on_segment(point, *segment)
            for segment, root in zip(segments, roots)
            if root in touching
        )

    pins = {(round(i["x_mm"] * 1e6), round(i["y_mm"] * 1e6)) for i in inventory}
    # The moved pin's old position is no longer a terminal.
    keep = {point for point in pins if point not in (new_pin, old_pin) and on_tree(point)}
    private = not keep
    rewritten, wire_index, carried = [], -1, []
    for start, end, node in _top_level_forms(text):
        if node[0] == "wire":
            wire_index += 1
            if wire_index in removed:
                rewritten.append((start, end, ""))
        elif node[0] == "junction":
            point = (_nm(one(node, "at")[1]), _nm(one(node, "at")[2]))
            if on_tree(point):
                rewritten.append((start, end, ""))
        elif node[0] == "label":
            point = (_nm(one(node, "at")[1]), _nm(one(node, "at")[2]))
            if on_tree(point):
                if private:
                    rewritten.append((start, end, ""))
                else:
                    keep.add(point)
        elif node[0] == "symbol" and one(node, "lib_id")[1].startswith("power:"):
            point = (_nm(one(node, "at")[1]), _nm(one(node, "at")[2]))
            if private and on_tree(point):
                # Placed on the new wire once it is routed (below).
                carried.append(
                    (next(p[2] for p in children(node, "property") if p[1] == "Reference"), point)
                )
            elif point == old_pin:
                # A flag or power symbol on the moved pin travels with it.
                block = _translate_block(
                    text[start:end],
                    (new_pin[0] - old_pin[0]) / 1e6,
                    (new_pin[1] - old_pin[1]) / 1e6,
                )
                rewritten.append((start, end, block))
            elif on_tree(point):
                keep.add(point)
    for start, end, block in reversed(rewritten):
        text = text[:start] + block + text[end:]
    points = sorted({new_pin, target} if private else keep | {new_pin})
    keepouts = _terminal_keepouts(
        [i for i in inventory if (round(i["x_mm"] * 1e6), round(i["y_mm"] * 1e6)) not in points]
    )
    text = _connect_point_groups(text, points, keepouts, "connector flow reroute")
    if carried:
        # Carried flags sit on the new wire, two grid steps from the connector pin.
        leaving = [segment for segment in _wire_trees(parse(text))[0] if new_pin in segment]
        if not leaving:
            raise ValueError("no wire leaves the moved connector for its power flag")
        start, end = leaving[0]
        far = end if start == new_pin else start
        length = abs(far[0] - new_pin[0]) + abs(far[1] - new_pin[1])
        step = min(2 * GRID, length)
        sign = (
            (far[0] > new_pin[0]) - (far[0] < new_pin[0]),
            (far[1] > new_pin[1]) - (far[1] < new_pin[1]),
        )
        spot = (new_pin[0] + sign[0] * step, new_pin[1] + sign[1] * step)
        if spot != far:
            # KiCad joins a pin only at a wire end, so the wire is split at the flag.
            text = _split_wire(text, (start, end), spot)
        for reference, point in carried:
            begin, finish, _node = _symbol_form(text, reference)
            block = _translate_block(
                text[begin:finish], (spot[0] - point[0]) / 1e6, (spot[1] - point[1]) / 1e6
            )
            text = text[:begin] + block + text[finish:]
    return text


def _split_wire(text: str, segment: tuple[Point, Point], point: Point) -> str:
    """Replace the two-point wire `segment` by two wires meeting at `point`."""
    from .schematic_review_native import _top_level_forms

    for start, end, node in _top_level_forms(text):
        if node[0] != "wire":
            continue
        ends = tuple((_nm(xy[1]), _nm(xy[2])) for xy in children(one(node, "pts"), "xy"))
        if set(ends) != set(segment) or len(ends) != 2:
            continue
        block = text[start:end]

        def wire(a: Point, b: Point) -> str:
            points = (
                f"(pts (xy {a[0] / 1e6:.6f} {a[1] / 1e6:.6f}) "
                f"(xy {b[0] / 1e6:.6f} {b[1] / 1e6:.6f}))"
            )
            return re.sub(r"\(pts\s+\(xy[^)]*\)\s*\(xy[^)]*\)\)", points, block, count=1)

        first = wire(ends[0], point)
        second = wire(point, ends[1])
        second = re.sub(r'\(uuid "[^"]+"\)', f'(uuid "{uuid4()}")', second, count=1)
        return text[:start] + first + "\n " + second + text[end:]
    raise ValueError("wire to split not found")


def orient_connectors_text(
    text: str,
    inventory: list[dict],
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[[str], bool],
    skip: frozenset[str] = frozenset(),
) -> tuple[str, list[dict]]:
    """Mirror or move each single-pin connector whose wire U-turns or wraps (R7.1).

    Connectors in `skip` stay as drawn; the compile step uses it to drop a move that a
    later presentation step could not accommodate.
    """
    nets = {(item["reference"], item["pin"]): item["net"] for item in inventory}
    moves = []
    for connector in sorted(_single_pin_connectors(parse(text)), key=lambda c: c["reference"]):
        reference = connector["reference"]
        if reference in skip:
            moves.append({"connector": reference, "change": None, "kept_because": ["skipped"]})
            continue
        detached = _detached(text, nets, reference)
        if not detached and not _flagged(text, nets, reference):
            continue
        terminals = current_inventory(text, nets)
        (pin,) = next(c["pins"] for c in _instances(parse(text)) if c["reference"] == reference)
        old_pin = pin["point"]
        net = nets.get((reference, pin["number"]))
        others = [
            (round(t["x_mm"] * 1e6), round(t["y_mm"] * 1e6))
            for t in terminals
            if t["net"] == net and t["reference"] != reference
        ]
        if net is None or not others:
            continue
        ranked = sorted(others, key=lambda p: (abs(p[0] - old_pin[0]) + abs(p[1] - old_pin[1]), p))
        target = ranked[0]
        body = connector["body"]
        facing_left = old_pin[0] < (body[0] + body[2]) // 2
        before = _cost(text, nets, net, reference)
        candidates = [("mirror in place", True, None, target)]
        # Beside each of the three nearest pins of its net, the pin facing that pin.
        for pin_target in ranked[:3]:
            for steps in PLACEMENT_REACH:
                for side in (-1, 1):
                    point = (pin_target[0] + side * steps * GRID, pin_target[1])
                    # The pin must face the target: a left-facing pin sits right of it.
                    needs_left = side > 0
                    candidates.append(
                        (
                            f"move pin to {point[0] / 1e6:.2f},{point[1] / 1e6:.2f} beside "
                            f"{pin_target[0] / 1e6:.2f},{pin_target[1] / 1e6:.2f}",
                            needs_left != facing_left,
                            point,
                            pin_target,
                        )
                    )
        best, reasons = None, []
        for label, mirror, point, aim in candidates:
            if f"{reference}|{label}" in skip:
                reasons.append(f"{label}: excluded after a later step objected")
                continue
            try:
                if point is None:
                    placed = _place(text, reference, True, None)
                    (new,) = next(
                        c["pins"] for c in _instances(parse(placed)) if c["reference"] == reference
                    )
                    new_pin = new["point"]
                else:
                    placed = _place(text, reference, mirror, point)
                    new_pin = point
                candidate = _reroute(placed, old_pin, new_pin, terminals, aim)
            except (ValueError, KeyError) as error:
                reasons.append(f"{label}: {error}")
                continue
            extent = content_extent(parse(candidate))
            if not (
                FRAME[0] <= extent[0]
                and extent[2] <= FRAME[2]
                and FRAME[1] <= extent[1]
                and extent[3] <= FRAME[3]
            ):
                reasons.append(f"{label}: leaves the page frame")
                continue
            objection = layout_check(candidate)
            if objection:
                reasons.append(f"{label}: layout check: {objection[:120]}")
                continue
            if not fields_ok(candidate):
                reasons.append(f"{label}: a field check would report something new")
                continue
            after = _cost(candidate, nets, net, reference)
            if best is None or after < best[0]:
                best = (after, label, candidate)
        if best is not None and best[0] < before - MINIMUM_GAIN / 1e6:
            text = best[2]
            moves.append(
                {
                    "connector": reference,
                    "net": net,
                    "change": best[1],
                    "trigger": "joined only by a label" if detached else "wire detour",
                    "net_cost_mm": {"before": before, "after": best[0]},
                }
            )
        else:
            moves.append(
                {
                    "connector": reference,
                    "net": net,
                    "change": None,
                    "kept_because": reasons[:6]
                    or [f"no candidate cut the net detour below {before:.2f} mm by a grid step"],
                }
            )
    return text, moves
