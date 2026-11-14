"""Unit-safe symbol nudges in the edit menu (docs/pivot/REVIEWER_LOOP_SPEC.md R3)."""

import glob
import json
import os
from pathlib import Path

from pydantic import ValidationError
import pytest

from ai_kicad.pivot.edit_menu import (
    MenuPolicy,
    ValidationCache,
    symbol_nudge_proposals,
    units_named_by_failing_checks,
)
from ai_kicad.pivot.schematic_description import _instances
from ai_kicad.pivot.schematic_review import ACTION_ADAPTER, MoveUnits
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
KICAD = pytest.mark.skipif(
    not os.environ.get("AI_KICAD_APPRUN"),
    reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun",
)
V9_FLAGS = dict(
    power_symbol_rails=True,
    readability_checks=True,
    page_balance=True,
    field_ownership=True,
    text_and_ground_checks=True,
    power_block=True,
    level_power_block=True,
)


def test_move_units_names_units_canonically():
    action = MoveUnits(
        operation="move_units", units=[{"reference": "U1", "unit": 3}], dx_mm=1.27, dy_mm=0
    )
    assert action.units[0].unit == 3
    for bad in (
        {"units": [{"reference": "U1 unit 3", "unit": 3}]},
        {"units": [{"reference": "U1", "unit": 0}]},
        {"units": [{"reference": "U1", "unit": 1}, {"reference": "U1", "unit": 1}]},
        {"units": [{"reference": "U1", "unit": 1}], "dx_mm": 0},
    ):
        with pytest.raises(ValidationError):
            MoveUnits.model_validate({"operation": "move_units", "dx_mm": 1.27, "dy_mm": 0, **bad})


def test_nudges_target_units_named_by_failing_checks():
    """inverting_gain 000 (review_loop_corpus_v3_2026-10-31_qwen35_32k_run1): U1C's text
    reads as R1's and C2's, so U1C and those neighbours are nudge targets."""
    directory = (
        ROOT
        / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1"
        / "inverting_gain/candidates/000"
    )
    report = json.loads((directory / "assessment.json").read_text())
    tree = parse(Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text())
    named = units_named_by_failing_checks(report)
    assert set(named) == {("U1", 3), ("R1", 1), ("C2", 1)}
    proposals = symbol_nudge_proposals(tree, report)
    assert {tuple(p.target.values()) for p in proposals} == set(named)
    first = next(p for p in proposals if p.target == {"reference": "U1", "unit": 3})
    assert first.action["operation"] == "move_units"
    assert first.action["units"] == [{"reference": "U1", "unit": 3}]
    assert all(abs(p.action["dx_mm"]) + abs(p.action["dy_mm"]) in (1.27, 2.54) for p in proposals)


@pytest.fixture(scope="module")
def dual_buffer(tmp_path_factory):
    from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine

    if not os.environ.get("AI_KICAD_APPRUN"):
        pytest.skip("set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun")
    engine = NativeSchematicEngine(
        json.loads((ROOT / "fixtures/m2b/dual_buffer.json").read_text()),
        Path(os.environ["AI_KICAD_APPRUN"]),
        structured_refusals=True,
        **V9_FLAGS,
    )
    start = tmp_path_factory.mktemp("dual_buffer") / "000"
    start.mkdir()
    source = engine.initial(start)
    return engine, source, engine.assess(source, start)


def _origins(path: Path) -> dict:
    return {(i["reference"], i["unit"]): i["origin"] for i in _instances(parse(path.read_text()))}


@KICAD
def test_move_units_moves_only_the_named_unit_of_a_dual_op_amp(dual_buffer, tmp_path):
    engine, source, assessment = dual_buffer
    assert all(value == "PASS" for value in assessment.report["checks"].values())
    action = ACTION_ADAPTER.validate_python(
        {
            "operation": "move_units",
            "units": [{"reference": "U1", "unit": 1}],
            "dx_mm": 2.54,
            "dy_mm": 0,
        }
    )
    moved = engine.apply(source, tmp_path / "001", [action])
    before, after = _origins(source), _origins(moved)
    assert [key for key in before if before[key] != after[key]] == [("U1", 1)]
    assert after[("U1", 1)][0] - before[("U1", 1)][0] == 2_540_000
    checks = engine.assess(moved, tmp_path / "001", render=False).report["checks"]
    assert checks["erc"] == "PASS" and checks["electrical_equivalence"] == "PASS"


@KICAD
def test_nudge_entries_keep_connectivity_and_pass_collision_checks(dual_buffer, tmp_path):
    """Move U1C (the dual op-amp's power unit) 3.81 mm down: its text then fails
    field_owner_association and its supply symbols touch other items. Every nudge on the
    menu must keep ERC and netlist equivalence and pass the collision checks."""
    engine, source, _ = dual_buffer
    shift = ACTION_ADAPTER.validate_python(
        {
            "operation": "move_units",
            "units": [{"reference": "U1", "unit": 3}],
            "dx_mm": 0,
            "dy_mm": 3.81,
        }
    )
    moved = engine.apply(source, tmp_path / "001", [shift])
    assessment = engine.assess(moved, tmp_path / "001")
    failing = {name for name, value in assessment.report["checks"].items() if value != "PASS"}
    assert failing == {"field_owner_association", "power_symbol_clearance"}
    menu = engine.edit_menu(assessment, tmp_path / "menu", MenuPolicy(), ValidationCache())
    nudges = [entry for entry in menu["entries"] if entry["class"] == "symbol_nudge"]
    assert nudges, menu["record"]
    assert {entry["target"]["reference"] for entry in nudges} == {"U1"}
    assert {entry["target"]["unit"] for entry in nudges} == {3}
    scratch = {}
    for path in (tmp_path / "menu").glob("*/assessment.json"):
        report = json.loads(path.read_text())
        scratch["sha256:" + report["schematic_sha256"]] = report["checks"]
    for entry in nudges:
        checks = scratch[entry["scratch_revision"]]
        for name in ("erc", "electrical_equivalence", "observed_layout", "field_separation"):
            assert checks[name] == "PASS", (entry["description"], name)
        assert entry["fixes"]
        assert entry["action"]["operation"] == "move_units"


@KICAD
def test_malformed_reference_list_is_refused_with_a_structured_reason(dual_buffer, tmp_path):
    engine, source, _ = dual_buffer
    action = ACTION_ADAPTER.validate_python(
        {"operation": "move_symbols", "references": ["U1", "unit", "3"], "dx_mm": 1.27, "dy_mm": 0}
    )
    with pytest.raises(ValueError, match=r"^invalid_request: malformed reference list") as error:
        engine.apply(source, tmp_path / "001", [action])
    assert "'unit', '3' are not a part reference" in str(error.value)
    assert "(reference, unit)" in str(error.value)
    # Without the v10 profile the editor keeps its earlier message.
    engine.structured_refusals = False
    try:
        with pytest.raises(ValueError, match="move_symbols references not found"):
            engine.apply(source, tmp_path / "002", [action])
    finally:
        engine.structured_refusals = True
