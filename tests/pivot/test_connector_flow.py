"""Connector orientation and signal flow under brief v11 (REVIEWER_LOOP_SPEC.md R7.1)."""

import glob
import json
import os
from pathlib import Path

import pytest

from ai_kicad.pivot.connector_flow import _place, _split_wire
from ai_kicad.pivot.net_detours import pin_pair_detours
from ai_kicad.pivot.quality_measures import compare_quality
from ai_kicad.pivot.schematic_description import _instances
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1"
CONNECTOR = """(kicad_sch (lib_symbols (symbol "Connector_Generic:Conn_01x01"
  (symbol "Conn_01x01_1_1" (rectangle (start -1.27 1.27) (end 1.27 -1.27))
    (pin passive line (at -5.08 0 0) (length 3.81) (name "Pin_1") (number "1")))))
  (symbol (lib_id "Connector_Generic:Conn_01x01") (at 50 50 0) (unit 1)
    (property "Reference" "J1" (at 55 48.5 0)) (property "Value" "In" (at 55 51.5 0))
    (pin "1" (uuid "a")))
  (wire (pts (xy 10 10) (xy 30 10)) (stroke (width 0) (type default)) (uuid "w1")))"""


def _pin(text):
    (item,) = [i for i in _instances(parse(text)) if i["reference"] == "J1"]
    return item["pins"][0]["point"]


def test_mirroring_flips_the_pin_and_reflects_the_text():
    assert _pin(CONNECTOR) == (44_920_000, 50_000_000)
    mirrored = _place(CONNECTOR, "J1", True, None)
    assert _pin(mirrored) == (55_080_000, 50_000_000)
    symbol = next(s for s in children(parse(mirrored), "symbol"))
    assert one(symbol, "mirror")[1] == "y"
    reference = next(p for p in children(symbol, "property") if p[1] == "Reference")
    assert float(one(reference, "at")[1]) == 45.0
    moved = _place(CONNECTOR, "J1", True, (80_010_000, 60_960_000))
    assert _pin(moved) == (80_010_000, 60_960_000)
    # Mirroring twice restores the original orientation.
    assert "(mirror" not in _place(mirrored, "J1", True, None)


def test_wire_is_split_where_a_flag_sits():
    split = _split_wire(
        CONNECTOR, ((10_000_000, 10_000_000), (30_000_000, 10_000_000)), (12_540_000, 10_000_000)
    )
    wires = [
        [(float(xy[1]), float(xy[2])) for xy in children(one(wire, "pts"), "xy")]
        for wire in children(parse(split), "wire")
    ]
    assert wires == [[(10.0, 10.0), (12.54, 10.0)], [(12.54, 10.0), (30.0, 10.0)]]


DESIGNS = {
    "B03": "linear_regulator",
    "B04": "led_long_text",
    "B05": "reference_555_led_flasher_v8",
    "B06": "rc_lowpass",
    "B08": "led_reverse_supply",
    "B10": "timer_astable_gnd",
    "B11": "led_series",
    "B13": "rc_highpass",
    "B15": "timer_astable",
}


@pytest.fixture(scope="module")
def v11(tmp_path_factory):
    if not os.environ.get("AI_KICAD_APPRUN"):
        pytest.skip("set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun")
    from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
    from tools.pivot.run_review_loop_corpus import CORPUS

    service = NativeSchematicReviewService(
        Path(os.environ["AI_KICAD_APPRUN"]),
        "m",
        review_brief=ROOT / "fixtures/pivot/schematic_review_brief_v11.json",
    )
    files = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}
    drawn = {}
    root = tmp_path_factory.mktemp("v11")
    for code, name in DESIGNS.items():
        directory = root / name
        directory.mkdir()
        engine = service.engine(files[name])
        source = engine.initial(directory)
        report = engine.assess(source, directory).report
        presentation = json.loads((directory / "presentation.json").read_text())
        drawn[code] = (source.read_text(), report, presentation)
    return drawn


def _rows(text, report):
    return pin_pair_detours(parse(text), report["terminal_inventory"])


def _pair(rows, net, pins):
    return next(r for r in rows if r["net"] == net and sorted(r["pins"]) == sorted(pins))


@pytest.mark.parametrize("code", sorted(DESIGNS))
def test_every_regenerated_drawing_passes_every_check(v11, code):
    _text, report, _presentation = v11[code]
    assert all(value == "PASS" for value in report["checks"].values()), report["checks"]


@pytest.mark.parametrize("code", ["B04", "B08", "B11"])
def test_no_connector_u_turn_without_a_recorded_constraint(v11, code):
    text, report, presentation = v11[code]
    kept = {
        item["connector"]
        for item in presentation["connector_flow"]
        if not item.get("change") and item.get("kept_because")
    }
    for row in _rows(text, report):
        for pin in row["u_turn_at"]:
            if pin.startswith("J") and row["excess_mm"] > 2.54:
                assert pin.split(".")[0] in kept, row


def test_regulator_input_left_and_output_right(v11):
    text, _report, _presentation = v11["B03"]
    parts = {i["reference"]: i for i in _instances(parse(text))}
    left, right = parts["U1"]["body"][0], parts["U1"]["body"][2]
    assert parts["J1"]["body"][2] < left and parts["C1"]["body"][2] < left
    assert parts["J2"]["body"][0] > right and parts["C2"]["body"][0] > right


@pytest.mark.parametrize("code", ["B05", "B10", "B15"])
def test_555_output_reaches_its_connector_without_wrapping(v11, code):
    text, report, _presentation = v11[code]
    row = _pair(_rows(text, report), "OUT", ["J2.1", "U1.3"])
    assert row["excess_mm"] <= 2.54 and not row["leaves_part_box"], row


@pytest.mark.parametrize("code", ["B06", "B13"])
def test_rated_good_filters_are_not_made_worse(v11, code):
    text, report, _presentation = v11[code]
    design = DESIGNS[code]
    directory = BASELINE / "drawings" / design
    old_text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    old_report = json.loads((directory / "assessment.json").read_text())
    assert compare_quality(old_report["quality"], report["quality"])["not_worse"]
    old = sum(r["excess_mm"] for r in _rows(old_text, old_report))
    new = sum(r["excess_mm"] for r in _rows(text, report))
    assert new <= old
