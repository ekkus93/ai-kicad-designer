"""Part text kept clear of wires (reviewer loop spec R7, brief v11).

The protected observer reports the smallest gap between any part's reference or value
text and any wire (`observed_text_wire_clearance_mm`, the R2 text-clearance measure). A
part moved by an earlier step can leave its text hugging a wire (2026-11-17: U1B's text
0.5 mm either side of its own output wire on dual_buffer). This step places such text
again, with the same text box the observer uses, wherever every check still passes.
"""

from __future__ import annotations

from typing import Callable

from ai_kicad.sexpr import children, one, parse

from .block_moves import _replace_text
from .readability_checks import _segments

# The clearance below which a part's text is placed again: one grid step.
MINIMUM_MM = 1.27
MINIMUM = 1_270_000


def _nm(value: str) -> int:
    return round(float(value) * 1_000_000)


def text_wire_clearances(text: str) -> dict[tuple[str, int], int]:
    """Each part unit's smallest text-to-wire gap (nm), measured as the observer does."""
    tree = parse(text)
    wires = _segments(tree)
    result: dict[tuple[str, int], int] = {}
    for symbol in children(tree, "symbol"):
        if one(symbol, "lib_id")[1].startswith("power:"):
            continue
        props = {p[1]: p for p in children(symbol, "property")}
        if "Reference" not in props or "Value" not in props:
            continue
        unit = int(one(symbol, "unit")[1]) if children(symbol, "unit") else 1
        key = (props["Reference"][2], unit)
        for name in ("Reference", "Value"):
            prop = props[name]
            at = one(prop, "at")
            x, y = _nm(at[1]), _nm(at[2])
            half = max(635_000, len(prop[2]) * 445_000)
            box = (x - half, y - 850_000, x + half, y + 850_000)
            for a, b in wires:
                wire = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
                gap = max(box[0] - wire[2], wire[0] - box[2], 0) + max(
                    box[1] - wire[3], wire[1] - box[3], 0
                )
                result[key] = min(result.get(key, gap), gap)
    return result


def clear_text_from_wires_text(
    text: str,
    layout_check: Callable[[str], str | None],
    fields_ok: Callable[..., bool],
) -> tuple[str, list[dict]]:
    """Place again the text of every part unit closer than MINIMUM_MM to a wire, at the
    first spot the observer and every field check accept with the gap restored."""
    moves = []
    for key, gap in sorted(text_wire_clearances(text).items()):
        if gap >= MINIMUM:
            continue

        def check(candidate: str, key=key) -> str | None:
            if text_wire_clearances(candidate).get(key, MINIMUM) < MINIMUM:
                return f"{key[0]} text within {MINIMUM_MM} mm of a wire"
            return layout_check(candidate)

        placed = _replace_text(text, key, check, fields_ok)
        if placed is None:
            moves.append(
                {
                    "part": f"{key[0]} unit {key[1]}",
                    "change": None,
                    "gap_mm": gap / 1e6,
                    "kept_because": ["no spot with the gap restored passes every check"],
                }
            )
            continue
        text = placed
        moves.append(
            {
                "part": f"{key[0]} unit {key[1]}",
                "change": "text placed again",
                "gap_mm": {"before": gap / 1e6, "after": text_wire_clearances(text)[key] / 1e6},
            }
        )
    return text, moves
