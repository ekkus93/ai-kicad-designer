"""A wired rail group that enters through a connector is marked there, not at a far part."""

import json
from pathlib import Path

from ai_kicad.m2_geometry import label_text_rect
from ai_kicad.pivot.field_layout import _obstacles
from ai_kicad.pivot.power_symbols import (
    _forms,
    _split_wire_at,
    power_symbol_collisions,
    power_symbols,
    use_power_symbols_text,
)
from ai_kicad.pivot.schematic_review_native import _name_nets_from_power_labels
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED = (
    ROOT
    / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-11-09_qwen35_256k_run1"
    / "inverting_gain/candidates/000"
)
MM = 1_000_000


def without_symbols(text: str, references: set[str]) -> str:
    pieces, cursor = [], 0
    for start, end, node in _forms(text):
        if node[0] == "symbol" and any(f'"{name}"' in text[start:end] for name in references):
            pieces.append(text[cursor:start])
            cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def test_wired_ground_group_is_marked_at_the_connector():
    """The 2026-11-09 drawing marks the J1-wired REF group at C1's pin (72.39, 82.55),
    sideways. Re-marked, its ground symbol hangs down from J1 pin 5's wire instead;
    C2, which only a symbol connects, keeps its own, also pointing down."""
    text = without_symbols(
        (ACCEPTED / "project/InvertingGain.kicad_sch").read_text(), {"#PWR01", "#PWR02"}
    )
    inventory = json.loads((ACCEPTED / "assessment.json").read_text())["terminal_inventory"]
    marked = use_power_symbols_text(text, "REF", inventory, [], [], None, prune_rail_wiring=False)
    placed = {
        (item["point"], item["angle"])
        for item in power_symbols(parse(marked))
        if item["net"] == "REF"
    }
    assert placed == {
        ((round(40.64 * MM), round(45.72 * MM)), 0),
        ((round(99.06 * MM), round(82.55 * MM)), 0),
    }
    # The symbol sits on a wire end: the J1 wire was split where it lands.
    ends = {
        (round(float(xy[1]) * MM), round(float(xy[2]) * MM))
        for wire in children(parse(marked), "wire")
        for xy in children(one(wire, "pts"), "xy")
    }
    assert (round(40.64 * MM), round(45.72 * MM)) in ends


def test_split_wire_meets_at_the_point():
    text = (
        "(kicad_sch (wire (pts (xy 10 20) (xy 30 20)) (stroke (width 0) (type default)) "
        '(uuid "00000000-0000-0000-0000-000000000001")))'
    )
    split = _split_wire_at(text, (15 * MM, 20 * MM))
    wires = [
        tuple((float(xy[1]), float(xy[2])) for xy in children(one(wire, "pts"), "xy"))
        for wire in children(parse(split), "wire")
    ]
    assert sorted(wires) == [((10.0, 20.0), (15.0, 20.0)), ((15.0, 20.0), (30.0, 20.0))]


def test_power_label_on_a_wire_names_the_pins_that_wire_reaches():
    """A ground symbol placed mid-wire names the auto-named net of the pins on that wire."""
    pin, label = (10 * MM, 10 * MM), (20 * MM, 10 * MM)
    observed = {
        "nets": {"Net-(J1-Pin_5)": [("J1", "5"), ("C1", "2")]},
        "labels": [("REF", label)],
        "pin_positions": {("J1", "5"): pin, ("C1", "2"): (20 * MM, 30 * MM)},
        "wires": [(pin, label), (label, (20 * MM, 30 * MM))],
    }
    assert _name_nets_from_power_labels(observed)["nets"] == {"REF": [("J1", "5"), ("C1", "2")]}


def test_field_text_keeps_clear_of_power_symbol_label_forms():
    """The protected observers read a power symbol as a label; field moves avoid it."""
    text = (ACCEPTED / "project/InvertingGain.kicad_sch").read_text()
    tree = parse(text)
    boxes = _obstacles(text, tree, ("R2", 1))
    for item in power_symbols(tree):
        assert label_text_rect(item["net"], item["point"]) in boxes


def test_ground_symbol_writes_its_name_beside_the_glyph_above_a_wire():
    """C2's ground pin (99.06, 82.55) is 3.81 mm above U1C's V- wire at y 86.36: room for
    the downward glyph but not for "REF" under it. The name goes right of the triangle."""
    text = without_symbols(
        (ACCEPTED / "project/InvertingGain.kicad_sch").read_text(), {"#PWR01", "#PWR02"}
    )
    inventory = json.loads((ACCEPTED / "assessment.json").read_text())["terminal_inventory"]
    marked = use_power_symbols_text(text, "REF", inventory, [], [], None, prune_rail_wiring=False)
    (c2,) = [
        item
        for item in power_symbols(parse(marked))
        if item["point"] == (round(99.06 * MM), round(82.55 * MM))
    ]
    assert c2["angle"] == 0
    value_x, value_y = c2["value"]
    assert value_x > round(99.06 * MM + 1.27 * MM)
    assert round(82.55 * MM) < value_y < round(86.36 * MM)
    assert power_symbol_collisions(marked) == []
