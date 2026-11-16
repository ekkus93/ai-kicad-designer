"""Functional blocks placed as units under brief v11 (REVIEWER_LOOP_SPEC.md R7.2)."""

import glob
import json
import os
from pathlib import Path

import pytest

from ai_kicad.pivot.blocks import partition, return_connector_distances
from ai_kicad.pivot.schematic_description import _instances
from ai_kicad.sexpr import parse
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/drawings"
FILES = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}


def _drawn(directory: Path) -> list:
    return parse(Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text())


def _roles(name: str, tree: list) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for block in partition(json.loads(FILES[name].read_text()), tree):
        roles.setdefault(block["role"], []).append(
            "+".join(f"{m[0]}/{m[1]}" for m in block["members"])
        )
    return roles


EXPECTED = {
    "rc_lowpass": {"passives": ["C1/1+R1/1"]},
    "led_series": {"indicator": ["D1/1+R1/1"]},
    "dual_buffer": {"amplifier": ["U1/1"], "parked": ["U1/2"], "power_unit": ["C1/1+C2/1+U1/3"]},
    "dual_rail_reference": {
        "amplifier": ["U1/1"],
        "parked": ["U1/2"],
        "power_unit": ["C1/1+C2/1+U1/3"],
        "passives": ["R1/1+R2/1"],
    },
    "rc_to_buffer": {"amplifier": ["C3/1+R1/1+U1/1"], "parked": ["U1/2"]},
    "sallen_key": {"amplifier": ["C3/1+C4/1+R2/1+U1/1"], "parked": ["U1/2"]},
    "linear_regulator": {
        "regulator": ["C1/1+C2/1+U1/1"],
        "power_interface": ["J1/1", "J2/1", "J3/1"],
    },
    "timer_astable": {
        "timer": ["C1/1+C2/1+R1/1+R2/1+U1/1"],
        "power_interface": ["J1/1", "J3/1"],
        "signal_interface": ["J2/1"],
    },
    "reference_555_led_flasher_v8": {"indicator": ["D1/1+R3/1"]},
}


@pytest.mark.parametrize("name", sorted(FILES))
def test_every_corpus_design_partitions_every_part_once(name):
    tree = _drawn(BASELINE / name)
    blocks = partition(json.loads(FILES[name].read_text()), tree)
    members = [tuple(m) for block in blocks for m in block["members"]]
    drawn = {(i["reference"], i["unit"]) for i in _instances(tree)}
    assert sorted(members) == sorted(drawn)
    for role, groups in EXPECTED.get(name, {}).items():
        assert sorted(_roles(name, tree)[role]) == sorted(groups), role


def test_return_connector_distance_is_reported():
    tree = _drawn(BASELINE / "linear_regulator")
    (row,) = return_connector_distances(json.loads(FILES["linear_regulator"].read_text()), tree)
    assert row["connector"] == "J3" and row["returns"] == ["REF"]
    assert row["distance_mm"] > 15.24


V11 = ["rc_to_buffer", "dual_rail_reference", "sallen_key", "linear_regulator", "timer_astable"]


@pytest.fixture(scope="module")
def v11(tmp_path_factory):
    if not os.environ.get("AI_KICAD_APPRUN"):
        pytest.skip("set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun")
    from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService

    service = NativeSchematicReviewService(
        Path(os.environ["AI_KICAD_APPRUN"]),
        "m",
        review_brief=ROOT / "fixtures/pivot/schematic_review_brief_v11.json",
    )
    root = tmp_path_factory.mktemp("blocks")
    drawn = {}
    for name in V11:
        directory = root / name
        directory.mkdir()
        engine = service.engine(FILES[name])
        source = engine.initial(directory)
        report = engine.assess(source, directory).report
        drawn[name] = (parse(source.read_text()), report, directory)
    return drawn


@pytest.mark.parametrize("name", V11)
def test_v11_blocks_pass_every_check_in_signal_order_without_intrusions(v11, name):
    _tree, report, directory = v11[name]
    assert all(value == "PASS" for value in report["checks"].values()), report["checks"]
    assert report["block_layout"]["signal_order_witnesses"] == []
    assert report["block_layout"]["intrusions"] == []
    presentation = json.loads((directory / "presentation.json").read_text())
    assert presentation["blocks"], "the partition is recorded with the drawing"


def _gap(tree, first, second):
    units = {(i["reference"], i["unit"]): i for i in _instances(tree)}
    a, b = units[first]["body"], units[second]["body"]
    box = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
    between = [
        key
        for key, item in units.items()
        if key[0] != first[0]
        and box[0] < (item["body"][0] + item["body"][2]) / 2 < box[2]
        and box[1] < (item["body"][1] + item["body"][3]) / 2 < box[3]
    ]
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3], 0) / 1e6, between


@pytest.mark.parametrize("name", ["rc_to_buffer", "dual_rail_reference", "sallen_key"])
def test_parked_unit_sits_next_to_its_active_sibling(v11, name):
    """B09, B12, B14: nothing lies between the parked unit B and the active unit A, and
    they are nearer than in the v10 baseline (63.5, 109.2 and 36.8 mm)."""
    tree, _report, directory = v11[name]
    gap, between = _gap(tree, ("U1", 1), ("U1", 2))
    old, _ = _gap(_drawn(BASELINE / name), ("U1", 1), ("U1", 2))
    assert between == [] and gap < old and gap <= 40.64, (gap, old, between)
    moves = json.loads((directory / "presentation.json").read_text())["block_moves"]
    assert any(m.get("block") == "parked" and m.get("change") for m in moves)


@pytest.mark.parametrize("name", ["linear_regulator", "timer_astable"])
def test_return_connector_joins_its_power_interface(v11, name):
    """The L7805 regulator and the 555 timer: J3 moves, as one unit with its REF symbol,
    power flag and private wires, to sit with the supply connector J1."""
    tree, report, directory = v11[name]
    (row,) = report["return_connector_distances"]
    assert row["connector"] == "J3" and row["nearest_interface_part"] == "J1"
    assert row["distance_mm"] <= 17.78
    moves = json.loads((directory / "presentation.json").read_text())["block_moves"]
    (move,) = [m for m in moves if m.get("block") == "power_interface"]
    assert move["change"] and move["with"] == "J1"
    # Its REF symbol and power flag moved with it: still on its pin's private wiring,
    # and the netlist and ERC are unchanged (every check passes, above).
    assert report["checks"]["electrical_equivalence"] == "PASS"
    assert report["checks"]["erc"] == "PASS"


def test_an_indicator_is_driven_by_its_signal_net_never_a_rail():
    """2026-11-16 regression: the LED flasher's R3/D1 block was aimed at R1 on the VCC rail
    (the last pin checked), where its OUT net could not be routed. A rail never drives a
    block; the driver is U1 pin 3 on OUT."""
    from ai_kicad.pivot.block_moves import indicator_drive

    directory = (
        ROOT
        / "fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run2"
        / "reference_555_led_flasher_v8"
    )
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    report = json.loads((directory / "assessment.json").read_text())
    nets = {(t["reference"], t["pin"]): t["net"] for t in report["terminal_inventory"]}
    design = json.loads(FILES["reference_555_led_flasher_v8"].read_text())
    rails = frozenset(item["net"] for item in design["power_assertions"])
    net, driver, own_pin = indicator_drive(text, nets, [("D1", 1), ("R3", 1)], rails)
    assert net == "OUT" and (driver["reference"], driver["pin"]) == ("U1", "3")
    assert own_pin == ("D1", "1")
    # R3 alone touches VCC and LED_A: its driver is D1 on LED_A, never the VCC rail.
    net, driver, _own = indicator_drive(text, nets, [("R3", 1)], rails)
    assert net == "LED_A" and driver["reference"] == "D1"
