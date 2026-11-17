"""Drawing conventions under brief v11 (spec R7.5, task P6-011q)."""

import glob
import json
from pathlib import Path

import pytest

from ai_kicad.pivot.supply_blocks import power_block_directions
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "fixtures/pivot/experiments/text_clearance_v11_2026-11-17_run1"
FILES = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}


def _text(name: str) -> str:
    return Path(glob.glob(str(RUN / name / "project/*.kicad_sch"))[0]).read_text()


@pytest.mark.parametrize("name", ["timer_astable", "timer_astable_gnd"])
def test_ic_return_symbols_point_down(name):
    """B10 and B15: the ground/REF symbol under U1 pointed right in v10; every return
    symbol of the power block now points down."""
    design = json.loads(FILES[name].read_text())
    returns = [r for r in power_block_directions(design, _text(name)) if r["role"] == "return"]
    assert returns and all(tuple(r["direction"]) == (0, 1) for r in returns), returns


CONVENTIONS = ROOT / "fixtures/pivot/experiments/conventions_v11_2026-11-17_run2"


def _report(name: str) -> dict:
    return json.loads((CONVENTIONS / name / "assessment.json").read_text())


def _presentation(name: str) -> dict:
    return json.loads((CONVENTIONS / name / "presentation.json").read_text())


def _sheet(name: str) -> str:
    return Path(glob.glob(str(CONVENTIONS / name / "project/*.kicad_sch"))[0]).read_text()


def test_a_divider_midpoint_is_labelled_with_connectivity_unchanged():
    """B12: VREF, the R1/R2 midpoint, carries a local label of its own name, and KiCad's
    netlist and ERC are unchanged (every check passes)."""
    from ai_kicad.sexpr import children, parse

    labels = [node[1] for node in children(parse(_sheet("dual_rail_reference")), "label")]
    assert "VREF" in labels
    report = _report("dual_rail_reference")
    assert all(value == "PASS" for value in report["checks"].values()), report["checks"]


@pytest.mark.parametrize(
    "name",
    ["dual_buffer", "dual_rail_reference", "inverting_gain", "noninverting_gain", "sallen_key"],
)
def test_parked_units_are_noted_unused(name):
    from ai_kicad.sexpr import children, parse

    notes = [node[1] for node in children(parse(_sheet(name)), "text")]
    assert notes.count("unused") == 1
    moves = [m for m in _presentation(name)["convention_moves"] if "part" in m]
    assert [m["part"] for m in moves] == ["U1 unit 2"] and moves[0]["change"]
    assert all(value == "PASS" for value in _report(name)["checks"].values())


def test_the_regulator_return_jog_is_straightened_with_connectivity_unchanged():
    """ChatGPT's v11 regulator review: U1 pin 2 went right 1.27 mm, down, and back left
    onto the REF bus. It now drops straight onto the bus; KiCad's netlist and ERC are
    unchanged, and wire length and bends fell."""
    from ai_kicad.pivot.readability_checks import _segments
    from ai_kicad.sexpr import parse

    cleanup = _presentation("linear_regulator")["wire_cleanup"]
    assert cleanup["hooks"], cleanup
    inventory = _report("linear_regulator")["terminal_inventory"]
    (pin,) = [t for t in inventory if (t["reference"], t["pin"]) == ("U1", "2")]
    x = round(pin["x_mm"] * 1e6)
    segments = _segments(parse(_sheet("linear_regulator")))
    # The wire leaving pin 2 runs straight down from it.
    leaving = [s for s in segments if (x, round(pin["y_mm"] * 1e6)) in s]
    assert len(leaving) == 1 and leaving[0][0][0] == leaving[0][1][0] == x, leaving
    report = _report("linear_regulator")
    assert all(value == "PASS" for value in report["checks"].values()), report["checks"]
    old = json.loads((RUN / "linear_regulator" / "assessment.json").read_text())["quality"]
    assert report["quality"]["bends"] < old["bends"]
    assert report["quality"]["wire_length_mm"] < old["wire_length_mm"]


def test_cleanup_never_brings_text_close_to_a_wire():
    """led_reverse_supply: straightening its hooks would bring text 0.42 mm from a wire,
    so they are refused and recorded."""
    cleanup = _presentation("led_reverse_supply")["wire_cleanup"]
    assert any("text would be" in reason for reason in cleanup["refused"]), cleanup
    assert _report("led_reverse_supply")["quality"]["text_clearance_mm"] >= 1.27


def test_a_quantity_value_with_words_is_reported_and_the_design_is_unchanged():
    design_text = FILES["led_long_text"].read_text()
    report = _report("led_long_text")
    flags = [f for f in report["design_review_flags"] if f["flag"] == "value_mixes_words"]
    assert [f["parts"] for f in flags] == [["R123"]]
    assert FILES["led_long_text"].read_text() == design_text
