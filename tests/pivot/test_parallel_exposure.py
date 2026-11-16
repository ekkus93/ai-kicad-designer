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
