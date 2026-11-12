"""Brief-v4 readability gates on the retained qualification drawings (no KiCad needed)."""

import json
import os
from pathlib import Path

import pytest

from ai_kicad.pivot.readability_checks import (
    MAXIMUM_PAGE_OFFSET,
    MINIMUM_FIELD_OWNER_GAP_NM,
    content_extent,
    fields_nearer_another_part,
    page_balance_witnesses,
    power_symbols_against_convention,
    rail_route_detours,
)
from ai_kicad.pivot.schematic_review_brief import (
    SchematicReviewBriefV4,
    SchematicReviewBriefV5,
    SchematicReviewBriefV6,
    brief_allows_power_symbol_rails,
    brief_requires_field_ownership,
    brief_requires_page_balance,
    brief_requires_readability_checks,
    load_review_brief,
)
from ai_kicad.pivot.schematic_review_native import (
    centre_on_page_text,
    wires_through_bodyless_units,
)
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ROOT / "fixtures/pivot/experiments/review_qualification_v3_2026-11-12_qwen35_256k_run1/cases"
)
BRIEF_V3 = ROOT / "fixtures/pivot/schematic_review_brief_v3.json"
BRIEF_V4 = ROOT / "fixtures/pivot/schematic_review_brief_v4.json"
SCHEMA_V4 = ROOT / "fixtures/pivot/schematic_review_brief.v4.schema.json"
KNOWN_GOOD = sorted(path.name for path in CASES.glob("*__known_good"))
# Historical defects that passed every brief-v3 check and the model review, and the v4
# gate that must now fail each one.
MISSED_BY_V3 = {
    "dual_buffer__wire_across_power_unit": "bodyless_unit_clearance",
    "inverting_gain__wire_across_power_unit": "bodyless_unit_clearance",
    "noninverting_gain__wire_across_power_unit": "bodyless_unit_clearance",
    "rc_to_buffer__wire_across_power_unit": "bodyless_unit_clearance",
    "inverting_gain__long_supply_loops": "rail_route_detour",
    "inverting_gain__long_ref_wire_and_loop": "rail_route_detour",
    "timer_astable__vcc_arrows_into_text": "power_symbol_direction",
    # These two drawings' own defects are not measured; their long rails are.
    "inverting_gain__r1_r2_text_misplaced": "rail_route_detour",
    "inverting_gain__sideways_ground": "rail_route_detour",
}


def gates(case: str) -> dict[str, list]:
    (schematic,) = (CASES / case / "project").glob("*.kicad_sch")
    tree = parse(schematic.read_text())
    report = json.loads((CASES / case / "assessment.json").read_text())
    rails = sorted({item["net"] for item in report["intended_circuit"]["power_assertions"]})
    return {
        "bodyless_unit_clearance": wires_through_bodyless_units(tree),
        "rail_route_detour": rail_route_detours(tree, report["terminal_inventory"], rails),
        "power_symbol_direction": power_symbols_against_convention(tree),
    }


def test_known_good_cases_are_present():
    assert len(KNOWN_GOOD) == 15


@pytest.mark.parametrize("case", KNOWN_GOOD)
def test_accepted_drawings_pass_every_readability_gate(case):
    assert gates(case) == {
        "bodyless_unit_clearance": [],
        "rail_route_detour": [],
        "power_symbol_direction": [],
    }


@pytest.mark.parametrize(("case", "gate"), sorted(MISSED_BY_V3.items()))
def test_defects_missed_by_v3_fail_a_readability_gate(case, gate):
    assert gates(case)[gate]


def test_long_supply_loop_is_reported_with_its_ratio():
    (vplus,) = [
        w
        for w in gates("inverting_gain__long_supply_loops")["rail_route_detour"]
        if w["net"] == "VPLUS"
    ]
    assert vplus["ratio"] > 2 and vplus["wire_length_mm"] - vplus["shortest_route_mm"] > 100


def test_short_power_symbol_stubs_are_not_detours():
    # timer_astable's VCC stub is 2.5x its 2.54 mm direct distance but only 3.81 mm longer.
    assert gates("timer_astable__known_good")["rail_route_detour"] == []


def test_downward_supply_arrow_is_reported():
    witnesses = gates("timer_astable__vcc_arrows_into_text")["power_symbol_direction"]
    assert [(w["net"], w["points"]) for w in witnesses] == [("VCC", "down")]


def test_v4_brief_enables_power_symbols_and_readability_gates():
    assert isinstance(load_review_brief(BRIEF_V4), SchematicReviewBriefV4)
    assert brief_allows_power_symbol_rails(BRIEF_V4)
    assert brief_requires_readability_checks(BRIEF_V4)
    assert not brief_requires_readability_checks(BRIEF_V3)
    assert not brief_requires_readability_checks(None)


def test_v4_brief_schema_matches_typed_contract():
    schema = json.loads(SCHEMA_V4.read_text())
    expected = SchematicReviewBriefV4.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v4.json"
    assert schema == expected


@pytest.mark.parametrize(
    ("criterion", "check", "message"),
    [
        ("page_composition", "bodyless_unit_clearance", "bodyless-unit clearance"),
        ("visible_local_rails", "rail_route_detour", "rail-route detour"),
        ("visible_local_rails", "power_symbol_direction", "power-symbol direction"),
    ],
)
def test_v4_brief_requires_each_readability_gate(criterion, check, message):
    brief = json.loads(BRIEF_V4.read_text())
    item = next(c for c in brief["criteria"] if c["criterion_id"] == criterion)
    item["measurements"] = [m for m in item["measurements"] if m["check_id"] != check]
    with pytest.raises(ValueError, match=message):
        SchematicReviewBriefV4.model_validate(brief)


def test_v4_detour_threshold_matches_the_gate():
    from ai_kicad.pivot.readability_checks import MAXIMUM_RAIL_ROUTE_RATIO

    brief = json.loads(BRIEF_V4.read_text())
    rails = next(c for c in brief["criteria"] if c["criterion_id"] == "visible_local_rails")
    (detour,) = [m for m in rails["measurements"] if m["check_id"] == "rail_route_detour"]
    assert detour["threshold"] == MAXIMUM_RAIL_ROUTE_RATIO
    assert "7.62 mm" in detour["unit"]


@pytest.mark.skipif(
    not os.environ.get("AI_KICAD_APPRUN"), reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun"
)
@pytest.mark.parametrize(
    ("case", "failing"),
    [
        ("inverting_gain__known_good", set()),
        ("inverting_gain__long_supply_loops", {"rail_route_detour"}),
    ],
)
def test_v4_assessment_reports_readability_gates(tmp_path, case, failing):
    from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine

    (source,) = (CASES / case / "project").glob("*.kicad_sch")
    engine = NativeSchematicEngine(
        json.loads((ROOT / "fixtures/m2b/inverting_gain.json").read_text()),
        Path(os.environ["AI_KICAD_APPRUN"]),
        source=source,
        power_symbol_rails=True,
        readability_checks=True,
    )
    report = engine.assess(engine.initial(tmp_path), tmp_path).report
    gates = ("bodyless_unit_clearance", "rail_route_detour", "power_symbol_direction")
    assert {name for name in gates if report["checks"][name] == "FAIL"} == failing
    assert {name for name, value in report["checks"].items() if value == "FAIL"} == failing
    assert set(report["readability_witnesses"]) == set(gates)


BRIEF_V5 = ROOT / "fixtures/pivot/schematic_review_brief_v5.json"
SCHEMA_V5 = ROOT / "fixtures/pivot/schematic_review_brief.v5.schema.json"


def drawing(case: str) -> str:
    (schematic,) = (CASES / case / "project").glob("*.kicad_sch")
    return schematic.read_text()


@pytest.mark.parametrize("case", ["led_series__known_good", "sallen_key__known_good"])
def test_top_left_compiler_output_fails_page_balance(case):
    witnesses = page_balance_witnesses(parse(drawing(case)))
    assert any(item["reason"] == "drawing is off the page centre" for item in witnesses)


@pytest.mark.parametrize("case", KNOWN_GOOD)
def test_centring_balances_every_accepted_drawing(case):
    text, record = centre_on_page_text(drawing(case))
    assert "refused" not in record
    assert page_balance_witnesses(parse(text)) == []
    # Whole grid steps keep every wire end on the connection grid.
    assert round(record["dx_mm"] / 1.27, 6).is_integer()
    assert round(record["dy_mm"] / 1.27, 6).is_integer()


def test_centring_moves_every_item_by_the_same_offset():
    text, record = centre_on_page_text(drawing("inverting_gain__known_good"))
    before, after = parse(drawing("inverting_gain__known_good")), parse(text)
    old, new = content_extent(before), content_extent(after)
    shift = (round(record["dx_mm"] * 1e6), round(record["dy_mm"] * 1e6))
    assert [n - o for n, o in zip(new, old)] == [shift[0], shift[1], shift[0], shift[1]]


def test_injected_off_balance_page_fails_page_balance():
    folder = CASES.parent / "injected" / "led_series__off_balance_page"
    (schematic,) = folder.glob("*.kicad_sch")
    assert page_balance_witnesses(parse(schematic.read_text()))


def test_v5_brief_gates_page_balance_and_drops_the_utilization_target():
    brief = load_review_brief(BRIEF_V5)
    assert isinstance(brief, SchematicReviewBriefV5)
    assert brief_requires_page_balance(BRIEF_V5) and not brief_requires_page_balance(BRIEF_V4)
    composition = next(c for c in brief.criteria if c.criterion_id == "page_composition")
    checks = {m.check_id: m for m in composition.measurements}
    assert checks["page_balance"].threshold == MAXIMUM_PAGE_OFFSET
    assert "observed_page_utilization" not in checks


def test_v5_brief_schema_matches_typed_contract():
    schema = json.loads(SCHEMA_V5.read_text())
    expected = SchematicReviewBriefV5.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v5.json"
    assert schema == expected


def test_v5_brief_requires_page_balance():
    brief = json.loads(BRIEF_V5.read_text())
    item = next(c for c in brief["criteria"] if c["criterion_id"] == "page_composition")
    item["measurements"] = [m for m in item["measurements"] if m["check_id"] != "page_balance"]
    with pytest.raises(ValueError, match="page-balance"):
        SchematicReviewBriefV5.model_validate(brief)


BRIEF_V6 = ROOT / "fixtures/pivot/schematic_review_brief_v6.json"
SCHEMA_V6 = ROOT / "fixtures/pivot/schematic_review_brief.v6.schema.json"
# Text-association defects and the field the v6 gate must report for each.
MISATTRIBUTED_TEXT = {
    "cases/inverting_gain__r1_r2_text_misplaced": {("R1", "Reference"), ("R1", "Value")},
    "injected/led_series__detached_value": {("D1", "Value")},
}


def schematic_text(case: str) -> str:
    folder = CASES.parent / case
    (schematic,) = list((folder / "project").glob("*.kicad_sch")) or list(
        folder.glob("*.kicad_sch")
    )
    return schematic.read_text()


@pytest.mark.parametrize("case", KNOWN_GOOD)
def test_accepted_drawings_keep_text_by_its_own_part(case):
    assert fields_nearer_another_part(parse(drawing(case))) == []


@pytest.mark.parametrize("case", KNOWN_GOOD)
def test_centred_drawings_keep_text_by_its_own_part(case):
    text, _record = centre_on_page_text(drawing(case))
    assert fields_nearer_another_part(parse(text)) == []


@pytest.mark.parametrize(("case", "fields"), sorted(MISATTRIBUTED_TEXT.items()))
def test_text_by_the_wrong_part_fails_field_nearest_owner(case, fields):
    witnesses = fields_nearer_another_part(parse(schematic_text(case)))
    assert {(w["reference"], w["field"]) for w in witnesses} == fields
    assert all(w["own_part_gap_mm"] > w["nearest_part_gap_mm"] for w in witnesses)


@pytest.mark.parametrize(
    "case", sorted(path.name for path in (CASES.parent / "injected").glob("*__detached_value"))
)
def test_every_injected_detached_value_fails_field_nearest_owner(case):
    assert fields_nearer_another_part(parse(schematic_text(f"injected/{case}")))


def test_text_slightly_nearer_a_neighbour_is_allowed():
    # Accepted inverting_gain: R1 sits 3.72 mm from its resistor and 2.91 mm from U1A.
    witnesses = fields_nearer_another_part(parse(drawing("inverting_gain__known_good")))
    assert witnesses == []


def test_bodyless_unit_label_is_exempt():
    # U1C's label stays beside its pin column by owner decision, 17-19 mm from the pins.
    text = drawing("inverting_gain__known_good")
    assert "(unit 3)" in text
    assert all(w["unit"] != 3 for w in fields_nearer_another_part(parse(text)))


def test_v6_brief_gates_field_ownership():
    brief = load_review_brief(BRIEF_V6)
    assert isinstance(brief, SchematicReviewBriefV6)
    assert brief_requires_field_ownership(BRIEF_V6)
    assert not brief_requires_field_ownership(BRIEF_V5)
    assert brief_requires_page_balance(BRIEF_V6) and brief_requires_readability_checks(BRIEF_V6)
    labels = next(c for c in brief.criteria if c.criterion_id == "label_association")
    (gate,) = [m for m in labels.measurements if m.check_id == "field_nearest_owner"]
    assert gate.threshold == 0
    assert f"{MINIMUM_FIELD_OWNER_GAP_NM / 1e6:.2f} mm" in gate.unit


def test_v6_brief_schema_matches_typed_contract():
    schema = json.loads(SCHEMA_V6.read_text())
    expected = SchematicReviewBriefV6.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v6.json"
    assert schema == expected


def test_v6_brief_requires_field_nearest_owner():
    brief = json.loads(BRIEF_V6.read_text())
    item = next(c for c in brief["criteria"] if c["criterion_id"] == "label_association")
    item["measurements"] = [
        m for m in item["measurements"] if m["check_id"] != "field_nearest_owner"
    ]
    with pytest.raises(ValueError, match="nearest-owner"):
        SchematicReviewBriefV6.model_validate(brief)


def test_field_ownership_requires_page_balance():
    from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine

    design = json.loads((ROOT / "fixtures/m2b/led_series.json").read_text())
    with pytest.raises(ValueError, match="page-balance"):
        NativeSchematicEngine(
            design,
            Path("/unused/AppRun"),
            power_symbol_rails=True,
            readability_checks=True,
            field_ownership=True,
        )
