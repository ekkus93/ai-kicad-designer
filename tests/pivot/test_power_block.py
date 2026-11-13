"""Brief v8 layout: a power unit's decoupling capacitors as one block, flags at entry."""

import json
from pathlib import Path

from ai_kicad.pivot.power_symbols import _flag_paths, _wire_segments
from ai_kicad.pivot.schematic_review_brief import (
    brief_requires_power_block,
    brief_requires_text_and_ground_checks,
    load_review_brief,
)
from ai_kicad.pivot.schematic_review_native import (
    balance_power_block_text,
    gather_power_flags_text,
)
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]
V7 = (
    ROOT
    / "fixtures/pivot/experiments/review_loop_corpus_v7_2026-11-13_qwen35_256k_run3"
    / "inverting_gain/candidates/000"
)
MM = 1_000_000


def _accepted() -> tuple[str, list[dict]]:
    text = next((V7 / "project").glob("*.kicad_sch")).read_text()
    inventory = json.loads((V7 / "assessment.json").read_text())["terminal_inventory"]
    return text, inventory


def _at(inventory: list[dict], reference: str, pin: str) -> tuple[int, int]:
    item = next(i for i in inventory if (i["reference"], i["pin"]) == (reference, pin))
    return (round(item["x_mm"] * MM), round(item["y_mm"] * MM))


def test_brief_v8_keeps_the_v7_gates_and_adds_the_power_block_layout():
    v8 = ROOT / "fixtures/pivot/schematic_review_brief_v8.json"
    assert load_review_brief(v8).brief_id == "owner-readability.v8"
    assert brief_requires_power_block(v8) and brief_requires_text_and_ground_checks(v8)
    assert not brief_requires_power_block(ROOT / "fixtures/pivot/schematic_review_brief_v7.json")


def test_bottom_pin_capacitor_mirrors_the_top_pin_capacitor():
    """Under v7, C1 sits 10.16 mm left of U1C's pin line with its VPLUS pin at y 74.93 and
    C2 hangs under pin 4. The block puts C2 10.16 mm right of the line at C1's height,
    wired to pin 4 by a path no longer than the rectilinear distance."""
    text, inventory = _accepted()
    pin8, pin4 = _at(inventory, "U1", "8"), _at(inventory, "U1", "4")
    c1, c2 = _at(inventory, "C1", "1"), _at(inventory, "C2", "2")
    context = {
        "VPLUS": {"flags": [], "local_pairs": [(pin8, c1)]},
        "VMINUS": {"flags": [], "local_pairs": [(pin4, c2)]},
    }
    moved, move = balance_power_block_text(text, inventory, context, lambda _text: None)
    assert move is not None and (move["reference"], move["mirrors"]) == ("C2", "C1")
    target = (2 * pin8[0] - c1[0], c1[1])
    assert (c2[0] + round(move["dx_mm"] * MM), c2[1] + round(move["dy_mm"] * MM)) == target
    path = _flag_paths(_wire_segments(parse(moved)), pin4, {target})
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in path)
    assert length == abs(pin4[0] - target[0]) + abs(pin4[1] - target[1])


def test_flag_on_a_capacitor_pin_moves_onto_its_own_wire():
    """Under v7 the VPLUS flag sits on C1's VPLUS pin. Without a connector spot, it moves
    onto C1's wire to pin 8, pointing across the wire, freeing the pin."""
    text, inventory = _accepted()
    pin8, c1 = _at(inventory, "U1", "8"), _at(inventory, "C1", "1")
    flags = [
        (round(float(one(s, "at")[1]) * MM), round(float(one(s, "at")[2]) * MM))
        for s in children(parse(text), "symbol")
        if one(s, "lib_id")[1] == "power:PWR_FLAG"
    ]
    assert c1 in flags
    context = {"VPLUS": {"flags": [c1], "local_pairs": [(pin8, c1)]}}
    moved, move = gather_power_flags_text(
        text, inventory, context, lambda _text: None, to_connector=False
    )
    assert move is not None and move["on"] == "decoupling wire"
    point = (round(move["to_mm"][0] * MM), round(move["to_mm"][1] * MM))
    assert point != c1
    segments = _wire_segments(parse(moved))
    assert any(point in segment for segment in segments)
