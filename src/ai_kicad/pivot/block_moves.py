"""Place functional blocks as units under brief v11 (reviewer loop spec R7.2).

Two moves, each of a whole unit together with its power symbols, flags, labels and
private wires (the editor's ``move_units``, which carries a pin's private wiring and
reroutes nets it shares):

* a parked op-amp unit is moved next to its active sibling;
* a return connector is moved to sit with the supply connector of its power interface.

Each candidate is validated as a unit (the protected observer accepts it, no field check
reports anything new, it stays on the page) and the nearest valid one is kept; otherwise
the part stays where it was and the reason is recorded.
"""

from __future__ import annotations

import re
from typing import Callable

from ai_kicad.sexpr import parse

from .blocks import partition
from .readability_checks import FRAME, content_extent
from .schematic_description import _instances

GRID = 1_270_000
# Offsets tried, in grid steps, between a moved part and its anchor.
PARKED_REACH = range(8, 41, 2)
RETURN_REACH = range(4, 15, 2)
# A return connector nearer than this to its interface is already grouped.
GROUPED_MM = 15.24


def _centre(item: dict) -> tuple[int, int]:
    body = item["body"]
    return (body[0] + body[2]) // 2, (body[1] + body[3]) // 2


def _snap(value: int) -> int:
    return round(value / GRID) * GRID


def _units(text: str) -> dict[tuple[str, int], dict]:
    return {(item["reference"], item["unit"]): item for item in _instances(parse(text))}


def _fits_the_page(before: str, after: str) -> bool:
    """The drawing still fits the usable frame (it is centred on the page last), or grows
    no larger than it already was."""
    old, new = content_extent(parse(before)), content_extent(parse(after))
    width, height = new[2] - new[0], new[3] - new[1]
    fits = width <= FRAME[2] - FRAME[0] and height <= FRAME[3] - FRAME[1]
    return fits or (width <= old[2] - old[0] and height <= old[3] - old[1])


def _replace_text(
    text: str,
    key: tuple[str, int],
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
) -> str | None:
    """Re-place a moved part's reference/value pair right of, left of, above or below its
    body, keeping the first spot that every field check and the observer accept."""
    from .field_layout import (
        BODY_GAP,
        CONNECTOR_ROW_OFFSET,
        FIELD_HALF_HEIGHT,
        _field_box,
        _move_fields,
    )

    if fields_ok(text) and not layout_check(text):
        return text
    item = _units(text)[key]
    body = item["body"]
    texts = [item["name"], item["value"]]
    half = max(_field_box((0, 0), value)[2] for value in texts)
    middle = ((body[0] + body[2]) // 2, (body[1] + body[3]) // 2)
    spots = []
    for gap in (BODY_GAP, 2 * BODY_GAP, 3 * BODY_GAP):
        for x in (body[2] + gap + half, body[0] - gap - half):
            spots.append(
                {
                    "Reference": (_snap(x), middle[1] - CONNECTOR_ROW_OFFSET),
                    "Value": (_snap(x), middle[1] + CONNECTOR_ROW_OFFSET),
                }
            )
        above = body[1] - gap - FIELD_HALF_HEIGHT
        below = body[3] + gap + FIELD_HALF_HEIGHT
        spots.append(
            {
                "Reference": (middle[0], above - 2 * CONNECTOR_ROW_OFFSET),
                "Value": (middle[0], above),
            }
        )
        spots.append(
            {
                "Reference": (middle[0], below),
                "Value": (middle[0], below + 2 * CONNECTOR_ROW_OFFSET),
            }
        )
    for spot in spots:
        try:
            placed = _move_fields(text, key, spot)
        except (ValueError, KeyError):
            continue
        if fields_ok(placed) and not layout_check(placed):
            return placed
    return None


def _try_moves(
    text: str,
    key: tuple[str, int],
    deltas: list[tuple[int, int]],
    nets: dict,
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[[str], bool],
    skip: frozenset[str],
    native_ok: Callable[[str], str | None] | None = None,
) -> tuple[str | None, str | None, list[str]]:
    """The first delta, in order, whose move validates; with its label and the refusals."""
    from .connector_flow import current_inventory
    from .schematic_review import MoveUnits
    from .schematic_review_native import move_symbols_text

    reasons = []
    for dx, dy in deltas:
        label = f"move by {dx / 1e6:+.2f},{dy / 1e6:+.2f}"
        if f"{key[0]}|{label}" in skip:
            reasons.append(f"{label}: excluded after a later step objected")
            continue
        if not dx and not dy:
            continue
        action = MoveUnits(
            operation="move_units",
            units=[{"reference": key[0], "unit": key[1]}],
            dx_mm=dx / 1e6,
            dy_mm=dy / 1e6,
        )
        try:
            candidate = move_symbols_text(text, action, current_inventory(text, nets))
        except (ValueError, KeyError) as error:
            reasons.append(f"{label}: {error}")
            continue
        if not _fits_the_page(text, candidate):
            reasons.append(f"{label}: the drawing would no longer fit the page")
            continue
        objection = layout_check(candidate)
        # The moved part's own text is placed again by a later step, so an objection to
        # only that text does not refuse the move; the finished drawing is checked again.
        own_text = objection and re.search(
            rf"field overlaps body/label: {re.escape(key[0])} (Reference|Value)", objection
        )
        if objection and not own_text:
            reasons.append(f"{label}: layout check: {objection[:100]}")
            continue
        if not fields_ok(candidate, key[0]):
            reasons.append(f"{label}: a field check would report something new")
            continue
        if own_text or not fields_ok(candidate):
            # Its own text moved with it into a crowded spot: place the text again.
            placed = _replace_text(candidate, key, layout_check, fields_ok)
            if placed is None:
                reasons.append(f"{label}: no clear spot for its reference and value")
                continue
            candidate = placed
        # A moved part can lose a connection the cached netlist cannot show: KiCad decides.
        failure = native_ok(candidate) if native_ok else None
        if failure:
            reasons.append(f"{label}: native check: {failure[:120]}")
            continue
        return candidate, label, reasons
    return None, None, reasons


def place_blocks_text(
    text: str,
    design: dict,
    inventory: list[dict],
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[[str], bool],
    skip: frozenset[str] = frozenset(),
    native_ok: Callable[[str], str | None] | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Move parked units beside their active sibling and return connectors to their
    supply connector. Returns the text, the moves and the block partition."""
    nets = {(item["reference"], item["pin"]): item["net"] for item in inventory}
    moves = []
    blocks = partition(design, parse(text))
    for block in blocks:
        if block["role"] != "parked":
            continue
        (reference, unit) = block["members"][0]
        if reference in skip:
            moves.append(
                {"connector": reference, "unit": unit, "change": None, "kept_because": ["skipped"]}
            )
            continue
        units = _units(text)
        siblings = [
            key
            for key in units
            if key[0] == reference
            and key[1] != unit
            and any(b["role"] == "amplifier" and list(key) in b["members"] for b in blocks)
        ]
        if not siblings:
            continue
        here, there = _centre(units[(reference, unit)]), _centre(units[min(siblings)])
        deltas = []
        # Below or above the active sibling, then beside it; nearest first.
        for steps in PARKED_REACH:
            for offset in ((0, steps), (0, -steps), (steps, 0), (-steps, 0)):
                target = (there[0] + offset[0] * GRID, there[1] + offset[1] * GRID)
                deltas.append((_snap(target[0] - here[0]), _snap(target[1] - here[1])))
        before = abs(there[0] - here[0]) + abs(there[1] - here[1])
        deltas = [
            d
            for d in deltas
            if abs(there[0] - here[0] - d[0]) + abs(there[1] - here[1] - d[1]) < before
        ]
        candidate, label, reasons = _try_moves(
            text, (reference, unit), deltas, nets, layout_check, fields_ok, skip, native_ok
        )
        if candidate is not None:
            text = candidate
            moves.append(
                {
                    "connector": reference,
                    "unit": unit,
                    "block": "parked",
                    "change": label,
                    "beside": f"{reference} unit {min(siblings)[1]}",
                }
            )
        else:
            moves.append(
                {
                    "connector": reference,
                    "unit": unit,
                    "block": "parked",
                    "change": None,
                    "kept_because": reasons[:6],
                }
            )
    blocks = partition(design, parse(text))
    supplies = [
        tuple(block["members"][0])
        for block in blocks
        if block["role"] == "power_interface" and not block.get("returns")
    ]
    for block in blocks:
        if not (block["role"] == "power_interface" and block.get("returns")) or not supplies:
            continue
        key = tuple(block["members"][0])
        if key[0] in skip:
            moves.append({"connector": key[0], "change": None, "kept_because": ["skipped"]})
            continue
        units = _units(text)
        here = units[key]["pins"][0]["point"]
        supply = min(
            supplies,
            key=lambda s: abs(_centre(units[s])[0] - _centre(units[key])[0])
            + abs(_centre(units[s])[1] - _centre(units[key])[1]),
        )
        there = units[supply]["pins"][0]["point"]
        distance = abs(_centre(units[supply])[0] - _centre(units[key])[0]) + abs(
            _centre(units[supply])[1] - _centre(units[key])[1]
        )
        if distance <= GROUPED_MM * 1e6:
            continue
        # Above or below the supply connector's pin, in line with it or a little to
        # either side; nearest first.
        deltas = sorted(
            {
                (there[0] + side * GRID - here[0], there[1] + sign * steps * GRID - here[1])
                for steps in RETURN_REACH
                for sign in (1, -1)
                for side in (0, -2, 2, -4, 4, -6)
            },
            key=lambda d: (
                abs(there[0] - here[0] - d[0]) + abs(there[1] - here[1] - d[1]),
                d,
            ),
        )
        candidate, label, reasons = _try_moves(
            text, key, deltas, nets, layout_check, fields_ok, skip, native_ok
        )
        if candidate is not None:
            text = candidate
            moves.append(
                {
                    "connector": key[0],
                    "block": "power_interface",
                    "change": label,
                    "with": supply[0],
                }
            )
        else:
            moves.append(
                {
                    "connector": key[0],
                    "block": "power_interface",
                    "change": None,
                    "kept_because": reasons[:6],
                }
            )
    return text, moves, partition(design, parse(text))


def _clear_of_bodies(text: str, members: list[tuple[str, int]]) -> bool:
    """The moved parts' bodies keep a grid step from every other part's body."""
    units = _units(text)
    mine = [units[m]["body"] for m in members]
    others = [u["body"] for k, u in units.items() if k not in members]
    return not any(
        a[0] < b[2] + GRID and b[0] - GRID < a[2] and a[1] < b[3] + GRID and b[1] - GRID < a[3]
        for a in mine
        for b in others
    )


def place_indicators_text(
    text: str,
    design: dict,
    inventory: list[dict],
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
    native_ok: Callable[[str], str | None] | None = None,
    skip: frozenset[str] = frozenset(),
) -> tuple[str, list[dict]]:
    """Move each indicator block (an LED with its series resistor) beside the pin that
    drives it, as one unit (spec R7.2), when its drive net detours.

    Candidates put the block beside the driving part, on the driving pin's side, at grid
    offsets nearest first; one is kept when it validates and the drive net's detour
    shrinks by more than a grid step.
    """
    from .connector_flow import _net_detour, current_inventory
    from .schematic_review import MoveUnits
    from .schematic_review_native import move_symbols_text

    nets = {(item["reference"], item["pin"]): item["net"] for item in inventory}
    rails = frozenset(item["net"] for item in design.get("power_assertions", []))
    moves = []
    for block in partition(design, parse(text)):
        if block["role"] != "indicator":
            continue
        members = [tuple(m) for m in block["members"]]
        name = "+".join(m[0] for m in members)
        own_refs = {m[0] for m in members}
        units = _units(text)
        drive = None
        for reference, unit in members:
            for pin in units[(reference, unit)]["pins"]:
                net = nets.get((reference, pin["number"]))
                drivers = [
                    t
                    for t in current_inventory(text, nets)
                    if t["net"] == net
                    and t["reference"] not in own_refs
                    and not t["reference"].startswith("J")
                ]
                if drivers:
                    drive = (net, drivers[0], (reference, pin["number"]))
        if drive is None or any(m[0] in skip for m in members):
            continue
        net, driver, own_pin = drive

        def cost(candidate: str, net=net, driver=driver, own_pin=own_pin) -> float:
            # The block's drive pin's distance from the driving pin, plus the drive net's
            # wired detours: it counts whether the net is wired or joined by labels.
            terminals = {
                (t["reference"], t["pin"]): (t["x_mm"], t["y_mm"])
                for t in current_inventory(candidate, nets)
            }
            a, b = terminals[own_pin], terminals[(driver["reference"], driver["pin"])]
            return abs(a[0] - b[0]) + abs(a[1] - b[1]) + _net_detour(candidate, nets, net)

        before = cost(text)
        if before <= 25.4:
            continue
        driving_part = next(u for k, u in units.items() if k[0] == driver["reference"])
        pin_point = (round(driver["x_mm"] * 1e6), round(driver["y_mm"] * 1e6))
        body = driving_part["body"]
        side = 1 if pin_point[0] >= body[2] else -1 if pin_point[0] <= body[0] else 0
        boxes = [units[m]["body"] for m in members]
        left = min(b[0] for b in boxes)
        right = max(b[2] for b in boxes)
        top = min(b[1] for b in boxes)
        deltas = set()
        for gap in range(4, 21, 2):
            for drop in range(-16, 17, 2):
                if side >= 0:
                    x = pin_point[0] + gap * GRID - left
                else:
                    x = pin_point[0] - gap * GRID - right
                y = pin_point[1] + drop * GRID - top
                deltas.add((_snap(x), _snap(y)))
        ordered = sorted(deltas, key=lambda d: (abs(d[0]) + abs(d[1]), d))
        reasons, chosen = [], None
        for dx, dy in ordered[:80]:
            label = f"move by {dx / 1e6:+.2f},{dy / 1e6:+.2f}"
            if f"{members[0][0]}|{label}" in skip:
                continue
            action = MoveUnits(
                operation="move_units",
                units=[{"reference": r, "unit": u} for r, u in members],
                dx_mm=dx / 1e6,
                dy_mm=dy / 1e6,
            )
            try:
                candidate = move_symbols_text(
                    text, action, current_inventory(text, nets), drop_nets=rails
                )
            except (ValueError, KeyError) as error:
                reasons.append(f"{label}: {error}")
                continue
            if not _fits_the_page(text, candidate):
                continue
            # Its rail pins are re-marked by the rail planner later, so ERC and the
            # observer cannot judge it yet: geometry here, the finished drawing in full.
            if not _clear_of_bodies(candidate, members):
                reasons.append(f"{label}: overlaps another part")
                continue
            if not fields_ok(candidate):
                reasons.append(f"{label}: a field check would report something new")
                continue
            after = cost(candidate)
            if after >= before - 2 * GRID / 1e6:
                reasons.append(f"{label}: drive distance {after:.2f} mm not shorter")
                continue
            chosen = (candidate, label, after)
            break
        if chosen is None:
            moves.append(
                {
                    "connector": members[0][0],
                    "block": "indicator",
                    "parts": name,
                    "change": None,
                    "kept_because": reasons[:6],
                }
            )
            continue
        text = chosen[0]
        moves.append(
            {
                "connector": members[0][0],
                "block": "indicator",
                "parts": name,
                "change": chosen[1],
                "drive_distance_mm": {"before": round(before, 2), "after": round(chosen[2], 2)},
            }
        )
    return text, moves
