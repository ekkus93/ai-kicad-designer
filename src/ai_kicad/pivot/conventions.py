"""Drawing conventions: labels for generated midpoints and unused units (spec R7.5).

Both are presentation only. A reference midpoint made by a divider (B12's VREF) is drawn
as bare wires, so its name appears nowhere; it gets a local net label with its intended
name near the divider node. A parked op-amp unit (its inputs tied so it is idle) gets a
plain-text "unused" note beside it. The label is checked natively, since a label names a
net; the note is plain text and joins nothing.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from ai_kicad.sexpr import children, one, parse

from .block_moves import GRID, _units
from .blocks import partition
from .connector_flow import current_inventory
from .power_symbols import _append_forms, power_symbols
from .readability_checks import _on, _segments, wire_groups
from .supply_blocks import OPAMP_SUPPLY, reference_nets

LABEL_GEOMETRIC_BUDGET = 12
LABEL_NATIVE_BUDGET = 3
UNUSED_TEXT = "unused"


def _mm(value: int) -> str:
    return f"{value / 1_000_000:.6f}"


def _box(x: int, y: int, value: str) -> tuple[int, int, int, int]:
    """The observer's box for a 1.27 mm text centred at a point."""
    half = max(635_000, len(value) * 445_000)
    return (x - half, y - 850_000, x + half, y + 850_000)


def _endpoints(design: dict) -> set[str]:
    """Supply and rail nets a divider can sit between."""
    nets = {item["net"] for item in design.get("power_assertions", [])}
    for net in design["nets"]:
        for component, pin in net["members"]:
            part = next(p for p in design["components"] if p["id"] == component)
            if part["asset"].startswith("Amplifier_Operational:") and pin in OPAMP_SUPPLY:
                nets.add(net["id"])
    return nets


def _label_form(net: str, point: tuple[int, int]) -> str:
    identity = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-kicad-reference-label:{net}:{point}")
    return (
        f'(label "{net}" (at {_mm(point[0])} {_mm(point[1])} 0) '
        "(effects (font (size 1.27 1.27)) (justify left bottom)) "
        f'(uuid "{identity}"))'
    )


def _text_form(value: str, point: tuple[int, int], key: tuple[str, int]) -> str:
    identity = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-kicad-unused-note:{key[0]}:{key[1]}")
    return (
        f'(text "{value}" (exclude_from_sim no) (at {_mm(point[0])} {_mm(point[1])} 0) '
        f'(effects (font (size 1.27 1.27))) (uuid "{identity}"))'
    )


def label_reference_nets_text(
    text: str,
    design: dict,
    nets: dict,
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
    native_ok: Callable[[str], str | None] | None,
) -> tuple[str, list[dict]]:
    """Give every divider midpoint without a label a local label with its name."""
    moves = []
    tree = parse(text)
    labelled = {label[1] for label in children(tree, "label")}
    pins_of: dict[str, list[tuple[int, int]]] = {}
    for item in current_inventory(text, nets):
        point = (round(item["x_mm"] * 1e6), round(item["y_mm"] * 1e6))
        pins_of.setdefault(item["net"], []).append(point)
    for net in sorted(reference_nets(design, _endpoints(design)) - labelled):
        started = time.monotonic()
        record = {"geometric": 0, "native": 0, "refused": []}
        groups = [
            g
            for g in wire_groups(_segments(tree))
            if any(_on(p, seg) for seg in g for p in pins_of.get(net, []))
        ]
        # The divider node: where the resistors joining the midpoint meet it.
        resistors = [
            (round(t["x_mm"] * 1e6), round(t["y_mm"] * 1e6))
            for t in current_inventory(text, nets)
            if t["net"] == net and t["reference"].startswith("R")
        ] or pins_of.get(net, [])
        node = (
            sum(p[0] for p in resistors) // len(resistors),
            sum(p[1] for p in resistors) // len(resistors),
        )
        points = set()
        for group in groups:
            for a, b in group:
                if a[1] != b[1]:
                    continue
                low, high = sorted((a[0], b[0]))
                for x in range(low + GRID, high, GRID):
                    points.add((x, a[1]))
        ordered = sorted(points, key=lambda p: (abs(p[0] - node[0]) + abs(p[1] - node[1]), p))
        chosen = None
        for point in ordered:
            if record["geometric"] >= LABEL_GEOMETRIC_BUDGET:
                record["refused"].append("geometric budget spent")
                break
            record["geometric"] += 1
            candidate = _append_forms(text, [_label_form(net, point)])
            objection = layout_check(candidate)
            if objection:
                record["refused"].append(f"at {_mm(point[0])},{_mm(point[1])}: {objection[:80]}")
                continue
            if not fields_ok(candidate):
                record["refused"].append(f"at {_mm(point[0])},{_mm(point[1])}: field check")
                continue
            if record["native"] >= LABEL_NATIVE_BUDGET:
                record["refused"].append("native budget spent")
                break
            record["native"] += 1
            failure = native_ok(candidate) if native_ok else None
            if failure:
                record["refused"].append(f"at {_mm(point[0])},{_mm(point[1])}: {failure[:80]}")
                continue
            chosen = (candidate, point)
            break
        record["seconds"] = round(time.monotonic() - started, 1)
        record["refused"] = record["refused"][:6]
        if chosen:
            text = chosen[0]
            tree = parse(text)
        moves.append(
            {
                "net": net,
                "change": f"label at {_mm(chosen[1][0])},{_mm(chosen[1][1])}" if chosen else None,
                "search": record,
            }
        )
    return text, moves


def _occupied(text: str) -> list[tuple[int, int, int, int]]:
    """Boxes of every body, field, label, power symbol point and wire, for a free note."""
    tree = parse(text)
    boxes = []
    for unit in _units(text).values():
        body = unit["body"]
        boxes.append(body)
        # Pin lines run from the pin end to the body edge.
        for pin in unit["pins"]:
            x, y = pin["point"]
            ex = min(max(x, body[0]), body[2])
            ey = min(max(y, body[1]), body[3])
            boxes.append((min(x, ex), min(y, ey), max(x, ex), max(y, ey)))
    for symbol in children(tree, "symbol"):
        if one(symbol, "lib_id")[1].startswith("power:"):
            continue
        for prop in children(symbol, "property"):
            if prop[1] in ("Reference", "Value"):
                at = one(prop, "at")
                boxes.append(_box(round(float(at[1]) * 1e6), round(float(at[2]) * 1e6), prop[2]))
    for label in children(tree, "label"):
        at = one(label, "at")
        x, y = round(float(at[1]) * 1e6), round(float(at[2]) * 1e6)
        boxes.append((x, y - 1_700_000, x + len(label[1]) * 890_000, y))
    for item in power_symbols(tree):
        x, y = item["point"]
        boxes.append((x - 2 * GRID, y - 3 * GRID, x + 2 * GRID, y + 3 * GRID))
    for a, b in _segments(tree):
        boxes.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    return boxes


def mark_unused_units_text(
    text: str,
    design: dict,
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
) -> tuple[str, list[dict]]:
    """Put an "unused" note beside every parked unit, clear of everything drawn."""
    moves = []
    for block in partition(design, parse(text)):
        if block["role"] != "parked":
            continue
        for member in block["members"]:
            key = (member[0], member[1])
            body = _units(text)[key]["body"]
            middle = ((body[0] + body[2]) // 2, (body[1] + body[3]) // 2)
            # First just under or over the unit's own reference and value text, so the note
            # reads as part of its label; then around the body.
            fields = [
                (round(float(one(p, "at")[1]) * 1e6), round(float(one(p, "at")[2]) * 1e6))
                for symbol in children(parse(text), "symbol")
                if any(q[1] == "Reference" and q[2] == key[0] for q in children(symbol, "property"))
                and (int(one(symbol, "unit")[1]) if children(symbol, "unit") else 1) == key[1]
                for p in children(symbol, "property")
                if p[1] in ("Reference", "Value")
            ]
            spots = []
            if fields:
                low = max(fields, key=lambda f: f[1])
                high = min(fields, key=lambda f: f[1])
                spots += [(low[0], low[1] + 2 * GRID), (high[0], high[1] - 2 * GRID)]
                # Beside the text block, on the reference's or value's line.
                for fx, fy in sorted(fields, key=lambda f: f[1]):
                    for side in (1, -1):
                        spots.append((fx + side * 6 * GRID, fy))
            for gap in range(2, 11):
                spots += [
                    (middle[0], body[3] + gap * GRID),
                    (middle[0], body[1] - gap * GRID),
                    (body[2] + gap * GRID + 3 * GRID, middle[1]),
                    (body[0] - gap * GRID - 3 * GRID, middle[1]),
                ]
            occupied = _occupied(text)
            others = [u["body"] for k, u in _units(text).items() if k != key]

            def reach(box, target) -> int:
                return max(target[0] - box[2], box[0] - target[2], 0) + max(
                    target[1] - box[3], box[1] - target[3], 0
                )

            chosen, reasons = None, []
            for x, y in spots:
                x, y = round(x / GRID) * GRID, round(y / GRID) * GRID
                box = _box(x, y, UNUSED_TEXT)
                # Two grid steps from everything, so the note never squeezes between wires.
                if any(
                    box[0] - 2 * GRID < b[2]
                    and b[0] < box[2] + 2 * GRID
                    and box[1] - 2 * GRID < b[3]
                    and b[1] < box[3] + 2 * GRID
                    for b in occupied
                ):
                    reasons.append(f"at {_mm(x)},{_mm(y)}: something is drawn there")
                    continue
                # The note must read as this unit's: nearer its body than any other part's.
                if any(reach(box, other) <= reach(box, body) for other in others):
                    reasons.append(f"at {_mm(x)},{_mm(y)}: nearer another part")
                    continue
                candidate = _append_forms(text, [_text_form(UNUSED_TEXT, (x, y), key)])
                objection = layout_check(candidate)
                if objection or not fields_ok(candidate):
                    reasons.append(f"at {_mm(x)},{_mm(y)}: {(objection or 'field check')[:80]}")
                    continue
                chosen = (candidate, (x, y))
                break
            if chosen:
                text = chosen[0]
            moves.append(
                {
                    "part": f"{key[0]} unit {key[1]}",
                    "change": f"noted unused at {_mm(chosen[1][0])},{_mm(chosen[1][1])}"
                    if chosen
                    else None,
                    "kept_because": None if chosen else reasons[:6],
                }
            )
    return text, moves
