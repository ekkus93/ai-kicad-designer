"""Close parallel runs of different nets (spec R7.4, report-only)."""

import glob
import json
from pathlib import Path

import pytest

from ai_kicad.pivot.parallel_exposure import parallel_exposure
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
RUN3 = ROOT / "fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run3"


def _wire(a, b):
    return f"(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})))"


def _pin(net, x, y):
    return {"reference": "U1", "pin": net, "net": net, "x_mm": x, "y_mm": y}


def _sheet(*wires):
    return parse(f"(kicad_sch (lib_symbols) {' '.join(wires)})")


def test_a_long_run_beside_a_neighbouring_pin_is_sustained():
    """Two pins 2.54 mm apart whose wires both run 5.08 mm straight up."""
    tree = _sheet(_wire((10, 50), (10, 44.92)), _wire((12.54, 50), (12.54, 44.92)))
    (row,) = parallel_exposure(tree, [_pin("A", 10, 50), _pin("B", 12.54, 50)])
    assert row["nets"] == ["A", "B"] and row["sustained"]
    # The first 1.27 mm of each wire leaves its pin by necessity and is not counted.
    assert row["exposure_mm"] == pytest.approx(3.81)


def test_an_unavoidable_pin_exit_that_turns_away_is_not_counted():
    """The same pins, but A's wire turns away after one grid step: nothing is exposed."""
    tree = _sheet(
        _wire((10, 50), (10, 48.73)),
        _wire((10, 48.73), (2.38, 48.73)),
        _wire((12.54, 50), (12.54, 48.73)),
        _wire((12.54, 48.73), (20.16, 48.73)),
    )
    assert parallel_exposure(tree, [_pin("A", 10, 50), _pin("B", 12.54, 50)]) == []


def test_wires_of_one_net_and_distant_wires_are_not_counted():
    tree = _sheet(_wire((10, 50), (10, 40)), _wire((15.08, 50), (15.08, 40)))
    assert parallel_exposure(tree, [_pin("A", 10, 50), _pin("B", 15.08, 50)]) == []
    tree = _sheet(_wire((10, 50), (10, 40)), _wire((12.54, 50), (12.54, 40)))
    assert parallel_exposure(tree, [_pin("A", 10, 50), _pin("A", 12.54, 50)]) == []


@pytest.mark.parametrize(
    "name", ["reference_555_led_flasher_v8", "timer_astable", "timer_astable_gnd"]
)
def test_the_555_control_capacitor_run_beside_vcc_is_flagged(name):
    """ChatGPT's 2026-11-16 flasher review: C2's CONT wire runs beside pin 8's VCC."""
    directory = RUN3 / name
    tree = parse(Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text())
    inventory = json.loads((directory / "assessment.json").read_text())["terminal_inventory"]
    rows = {tuple(r["nets"]): r for r in parallel_exposure(tree, inventory)}
    assert rows[("CONT", "VCC")]["sustained"], rows


@pytest.mark.parametrize("name", ["led_series", "rc_lowpass", "linear_regulator"])
def test_designs_without_close_runs_report_none(name):
    directory = RUN3 / name
    tree = parse(Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text())
    inventory = json.loads((directory / "assessment.json").read_text())["terminal_inventory"]
    assert [r for r in parallel_exposure(tree, inventory) if r["sustained"]] == []


def test_the_capacitor_route_search_is_bounded_and_records_its_outcome():
    """R7.4 bounded search: at most 12 cheap candidates and 3 native assessments, with the
    counts, time and refusals recorded. Around the 555's top edge every route that turns
    away from pin 8 meets pin 4's or pin 8's VCC symbol, so the outcome is a documented
    no-safe-improvement and the drawing is kept."""
    from ai_kicad.pivot import supply_blocks
    from tools.pivot.run_review_loop_corpus import CORPUS

    files = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}
    directory = RUN3 / "timer_astable"
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    inventory = json.loads((directory / "assessment.json").read_text())["terminal_inventory"]
    nets = {(t["reference"], t["pin"]): t["net"] for t in inventory}
    design = json.loads(files["timer_astable"].read_text())
    (row,) = supply_blocks.capacitor_distances(design, text)
    native_calls = []
    candidate, label, record = supply_blocks._try_dogleg(
        text,
        design,
        row,
        nets,
        lambda _text: None,
        lambda _text, _tolerate=None: True,
        lambda c: native_calls.append(c) or None,
        frozenset(),
    )
    assert record["exposure_mm_before"] == pytest.approx(3.81)
    assert record["geometric"] <= supply_blocks.DOGLEG_GEOMETRIC_BUDGET
    assert record["native"] <= supply_blocks.DOGLEG_NATIVE_BUDGET
    assert len(native_calls) == record["native"]
    assert candidate is None and label is None and record["refused"]
    assert "seconds" in record and record["structural"] > 0
