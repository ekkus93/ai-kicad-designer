"""Brief v11 and the R7.3 per-net detour measure (REVIEWER_LOOP_SPEC.md R7, R7.3)."""

import glob
import json
import os
from pathlib import Path

import pytest

from ai_kicad.pivot.net_detours import pin_pair_detours
from ai_kicad.pivot.schematic_review_brief import (
    SchematicReviewBriefV11,
    brief_generator_layout,
    brief_review_profile,
)
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
BRIEFS = ROOT / "fixtures/pivot"
BASELINE = ROOT / "fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1"
KEY = json.loads((BASELINE / "blind_key.json").read_text())


def test_v11_keeps_v10_and_adds_the_generator_layout_steps():
    v10, v11 = (
        json.loads((BRIEFS / f"schematic_review_brief_v{n}.json").read_text()) for n in (10, 11)
    )
    assert v11["criteria"] == v10["criteria"]
    assert v11["review_profile"] == v10["review_profile"]
    assert brief_generator_layout(BRIEFS / "schematic_review_brief_v11.json").model_dump() == {
        "connector_flow": True,
        "block_placement": True,
        "supply_blocks": True,
        "conventions": True,
    }
    assert brief_review_profile(BRIEFS / "schematic_review_brief_v11.json") is not None
    for n in (9, 10):
        assert brief_generator_layout(BRIEFS / f"schematic_review_brief_v{n}.json") is None


def test_v11_schema_matches_typed_contract():
    expected = SchematicReviewBriefV11.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v11.json"
    assert json.loads((BRIEFS / "schematic_review_brief.v11.schema.json").read_text()) == expected


def test_service_passes_generator_layout_only_for_v11():
    apprun = Path("/unused/AppRun")
    v11 = NativeSchematicReviewService(
        apprun, "m", review_brief=BRIEFS / "schematic_review_brief_v11.json"
    )
    v10 = NativeSchematicReviewService(
        apprun, "m", review_brief=BRIEFS / "schematic_review_brief_v10.json"
    )
    assert v11.generator_layout["connector_flow"] is True
    assert v10.generator_layout is None


def _drawing(code: str):
    directory = BASELINE / "drawings" / KEY[code]["design"]
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    report = json.loads((directory / "assessment.json").read_text())
    return pin_pair_detours(parse(text), report["terminal_inventory"])


def _pair(rows, net, pins):
    return next(row for row in rows if row["net"] == net and sorted(row["pins"]) == sorted(pins))


@pytest.mark.parametrize(
    ("code", "net", "pins", "connector"),
    [
        ("B04", "VPLUS", ["J1.1", "R123.1"], "J1.1"),
        ("B04", "REF", ["D24.1", "J2.1"], "J2.1"),
        ("B08", "LOCAL_REF", ["J1.1", "R1.1"], "J1.1"),
        ("B08", "VNEG", ["D1.1", "J2.1"], "J2.1"),
        ("B11", "VPLUS", ["J1.1", "R1.1"], "J1.1"),
        ("B11", "REF", ["D1.1", "J2.1"], "J2.1"),
    ],
)
def test_connector_u_turns_are_flagged(code, net, pins, connector):
    """Hand-checked against the drawings' wire listings: each connector pin faces away
    from the part it feeds and its wire turns back around the connector."""
    row = _pair(_drawing(code), net, pins)
    assert connector in row["u_turn_at"]
    assert row["excess_mm"] > 2.54 and row["leaves_part_box"]


@pytest.mark.parametrize("code", ["B05", "B10", "B15"])
def test_555_output_wrap_is_flagged(code):
    row = _pair(_drawing(code), "OUT", ["J2.1", "U1.3"])
    assert row["excess_mm"] > 2.54 and row["leaves_part_box"]
    assert "U1.3" in row["u_turn_at"]


@pytest.mark.parametrize("code", ["B06", "B13"])
def test_rated_good_rc_filters_also_have_connector_u_turns(code):
    """Recorded fact (2026-11-14): B06 and B13 were rated good, yet their input and return
    connectors face away from the filter exactly as in B11. See the P6-011m note."""
    rows = _drawing(code)
    flagged = [row for row in rows if row["excess_mm"] > 2.54]
    assert {row["net"] for row in flagged} == {"IN", "REF"}
    assert all(any(pin.startswith("J") for pin in row["u_turn_at"]) for row in flagged)


def test_straight_wire_has_no_detour():
    sheet = parse("(kicad_sch (lib_symbols) (wire (pts (xy 10 10) (xy 30 10))))")
    inventory = [
        {"net": "N", "reference": "A", "pin": "1", "x_mm": 10.0, "y_mm": 10.0},
        {"net": "N", "reference": "B", "pin": "1", "x_mm": 30.0, "y_mm": 10.0},
    ]
    (row,) = pin_pair_detours(sheet, inventory)
    assert row["path_mm"] == row["manhattan_mm"] == 20.0
    assert row["excess_mm"] == 0 and row["u_turn_at"] == []


@pytest.mark.skipif(
    not os.environ.get("AI_KICAD_APPRUN"),
    reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun",
)
@pytest.mark.parametrize("design", ["rc_lowpass", "dual_buffer", "timer_astable"])
def test_v9_and_v10_drawings_are_unchanged(tmp_path, design):
    """v10 drawings regenerate byte-for-byte as the committed v10 baseline (25a319c9), and
    v9 draws the same bytes as v10 (the same generator steps)."""
    committed = Path(glob.glob(str(BASELINE / "drawings" / design / "project/*.kicad_sch"))[0])
    for version in (9, 10):
        service = NativeSchematicReviewService(
            Path(os.environ["AI_KICAD_APPRUN"]),
            "m",
            review_brief=BRIEFS / f"schematic_review_brief_v{version}.json",
        )
        directory = tmp_path / f"v{version}"
        directory.mkdir()
        drawn = service.engine(ROOT / f"fixtures/m2b/{design}.json").initial(directory)
        assert drawn.read_bytes() == committed.read_bytes(), version
