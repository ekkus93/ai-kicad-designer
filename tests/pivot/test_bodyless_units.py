"""Wires stay out of the pin column of a unit drawn without a body, such as an op-amp's
power unit, where its pin names are written."""

import json
from pathlib import Path

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a_artifacts import emit
from ai_kicad.m2b import assets, validate
from ai_kicad.pivot.schematic_review_native import (
    WirePoint,
    _drawn_boxes,
    _insert_wire_route,
    _name_nets_from_power_labels,
    route_around_existing_wires,
    wires_through_bodyless_units,
)
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED = (
    ROOT
    / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-11-05_qwen35_256k_run1"
    / "inverting_gain/candidates/000/project/InvertingGain.kicad_sch"
)
MM = 1_000_000


def compiled_text(name: str, directory: Path) -> str:
    resolved = assets()
    source = ROOT / "fixtures/m2b" / f"{name}.json"
    design = validate(json.loads(source.read_text()), resolved)
    scene, _composition = compose_with_evidence(design, resolved)
    return emit(design, resolved, scene, directory).read_text()


def test_power_unit_column_spans_both_pin_names():
    """U1C's pins end at y 74.93 (V+) and 82.55 (V-) on x 82.55; the column covers both."""
    columns = []
    symbol_boxes, _text = _drawn_boxes(parse(ACCEPTED.read_text()), columns)
    assert len(columns) == 1
    reference, (left, top, right, bottom) = columns[0]
    assert reference == "U1"
    assert left < round(82.55 * MM) < right
    assert top < round(74.93 * MM) and round(82.55 * MM) < bottom
    # Neither pin's connection point is covered, so wires can still land there.
    assert top > round(71.12 * MM) and bottom < round(86.36 * MM)
    assert columns[0] in symbol_boxes


def test_accepted_ground_wire_through_u1c_is_reported():
    """The 2026-11-05 drawing jogs the C1-C2 ground wire to y 81.28, across V-."""
    crossings = wires_through_bodyless_units(parse(ACCEPTED.read_text()))
    assert [item["wire_mm"] for item in crossings] == [[[81.28, 81.28], [97.79, 81.28]]]
    assert crossings[0]["reference"] == "U1"


def test_compiler_ground_wire_is_a_crossing_but_its_decoupling_wires_are_not(tmp_path):
    """The compiler runs ground straight across U1C at y 82.55. Its C1 wire that ends on
    the V+ pin and runs along that pin's stub only reaches the column, so it is allowed."""
    text = compiled_text("inverting_gain", tmp_path)
    crossings = wires_through_bodyless_units(parse(text))
    assert [item["wire_mm"] for item in crossings] == [[[72.39, 82.55], [99.06, 82.55]]]


def test_router_goes_around_the_power_unit_column(tmp_path):
    text = compiled_text("inverting_gain", tmp_path)
    route = route_around_existing_wires(
        text, [WirePoint(x_mm=72.39, y_mm=82.55), WirePoint(x_mm=99.06, y_mm=82.55)]
    )
    drawn = _insert_wire_route(text, route)
    new = [item for item in wires_through_bodyless_units(parse(drawn))]
    assert new == wires_through_bodyless_units(parse(text))


def test_auto_named_net_takes_the_power_symbol_name_at_its_pin():
    point, other = (72_390_000, 82_550_000), (10_000_000, 10_000_000)
    observed = {
        "nets": {"Net-(J1-Pin_5)": [("J1", "5"), ("C1", "2")], "VPLUS": [("C1", "1")]},
        "labels": [("REF", point), ("VPLUS", other)],
        "pin_positions": {("C1", "2"): point, ("C1", "1"): other, ("J1", "5"): (0, 0)},
    }
    renamed = _name_nets_from_power_labels(observed)
    assert renamed["nets"] == {
        "REF": [("J1", "5"), ("C1", "2")],
        "VPLUS": [("C1", "1")],
    }
    assert observed["nets"].keys() == {"Net-(J1-Pin_5)", "VPLUS"}


def test_named_nets_are_never_renamed():
    point = (72_390_000, 82_550_000)
    observed = {
        "nets": {"GND": [("C1", "2")]},
        "labels": [("REF", point)],
        "pin_positions": {("C1", "2"): point},
    }
    assert _name_nets_from_power_labels(observed) is observed


def test_power_symbol_on_a_pin_inner_end_may_not_reach_into_the_column():
    """A glyph aimed from U1C's V+ inner end (82.55, 74.93) into the column would cover
    the pin names, even though the symbol's own point is on that pin."""
    from ai_kicad.pivot.power_symbols import _collisions

    tree = parse(ACCEPTED.read_text())
    item = {
        "lib_id": "power:GND",
        "point": (82_550_000, 74_930_000),
        "angle": 0,
        "net": "REF",
        "reference": "#PWR99",
    }
    assert "U1" in _collisions(ACCEPTED.read_text(), tree, item)


def test_supply_arrow_keeps_off_the_power_unit_text_spot():
    """An upward VPLUS arrow on U1C pin 8 (82.55, 71.12) would take the spot above the unit
    where its "U1C / NE5532" text goes; a sideways arrow there leaves it free."""
    from ai_kicad.pivot.power_symbols import _collisions

    path = next(
        (
            ROOT
            / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-11-11_qwen35_256k_run3"
            / "inverting_gain/candidates/000/project"
        ).glob("*.kicad_sch")
    )
    text = path.read_text()
    tree = parse(text)

    def hits(angle: int) -> list[str]:
        item = {
            "lib_id": "power:VCC",
            "point": (82_550_000, 71_120_000),
            "angle": angle,
            "net": "VPLUS",
            "reference": "#PWR99",
        }
        return [hit for hit in _collisions(text, tree, item) if "power unit text" in hit]

    assert hits(0)
    assert not hits(90) and not hits(270)


def test_looping_decoupling_capacitor_is_moved_beside_its_pin():
    """In return_rail_symbols_2026-11-11_run1, C2's VMINUS wire leaves U1C pin 4
    (82.55, 86.36), runs right under C2 and up to C2's top pin (99.06, 74.93): 40.64 mm.
    Moved 11.43 mm left and down, C2's top pin sits 5.08 mm beside pin 4's end."""
    from ai_kicad.pivot.power_symbols import _flag_paths, _wire_segments
    from ai_kicad.pivot.schematic_review_native import straighten_decoupling_text

    folder = ROOT / "fixtures/pivot/experiments/return_rail_symbols_2026-11-11_run1/inverting_gain"
    text = next((folder / "project").glob("*.kicad_sch")).read_text()
    inventory = json.loads((folder / "assessment.json").read_text())["terminal_inventory"]
    pin, capacitor = (82_550_000, 86_360_000), (99_060_000, 74_930_000)
    context = {"VMINUS": {"flags": [], "local_pairs": [(pin, capacitor)]}}
    moved, move = straighten_decoupling_text(text, inventory, context, lambda _text: None)
    assert move is not None
    assert (move["reference"], move["dx_mm"], move["dy_mm"]) == ("C2", -11.43, 11.43)
    assert move["pair_wire_mm"] == [40.64, 5.08]
    target = (87_630_000, 86_360_000)
    path = _flag_paths(_wire_segments(parse(moved)), pin, {target})
    assert sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in path) == 5_080_000
    # Once straight, the pair is left alone.
    assert (
        straighten_decoupling_text(
            moved,
            inventory,
            {"VMINUS": {"flags": [], "local_pairs": [(pin, target)]}},
            lambda _t: None,
        )[1]
        is None
    )


def test_rail_name_keeps_a_grid_step_clear_of_pin_names():
    """In decoupling_placement_2026-11-11_run1, VMINUS points up from C2's top pin
    (87.63, 86.36) and its name sits about 1 mm right of U1C's "V-" pin name. It must
    now keep a grid step clear of the pin-name column."""
    from ai_kicad.pivot.power_symbols import _collisions, power_symbols

    path = next(
        (
            ROOT
            / "fixtures/pivot/experiments/decoupling_placement_2026-11-11_run1"
            / "inverting_gain/project"
        ).glob("*.kicad_sch")
    )
    text = path.read_text()
    tree = parse(text)
    (vminus,) = [
        item
        for item in power_symbols(tree)
        if item["net"] == "VMINUS" and item["point"] == (87_630_000, 86_360_000)
    ]
    assert vminus["angle"] == 0
    assert "U1 pin names" in _collisions(text, tree, vminus)


def test_rail_name_keeps_a_grid_step_clear_of_part_text():
    """In run5, "VMINUS" at (87.63, 85.09) sits about 1 mm above C2's "C2 / 100n"; J1's
    VPLUS and VMINUS names, stacked on adjacent pins and drawn the same way, may stay."""
    from ai_kicad.pivot.power_symbols import _collisions, power_symbols

    path = next(
        (
            ROOT
            / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-11-11_qwen35_256k_run5"
            / "inverting_gain/candidates/000/project"
        ).glob("*.kicad_sch")
    )
    text = path.read_text()
    tree = parse(text)
    symbols = {(item["net"], item["point"]): item for item in power_symbols(tree)}
    assert "C2 text" in _collisions(text, tree, symbols[("VMINUS", (87_630_000, 85_090_000))])
    assert not _collisions(text, tree, symbols[("VPLUS", (26_670_000, 38_100_000))])
