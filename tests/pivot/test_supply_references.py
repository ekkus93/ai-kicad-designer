"""Supply-to-reference capacitors (spec R7.4, B12, per the 2026-11-16 reviewed solution §D)."""

import glob
import json
from pathlib import Path

from ai_kicad.pivot.supply_blocks import capacitor_distances, reference_nets
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "fixtures/pivot/experiments/rail_localization_v11_2026-11-17_run1"
FILES = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}


def _design(components, nets):
    return {
        "components": [{"id": c, "refdes": c, "asset": a} for c, a in components],
        "nets": [{"id": n, "members": m} for n, m in nets],
    }


def test_b12_vref_capacitors_are_supply_to_reference_with_nets_unchanged():
    """dual_rail_reference: C1 from VPLUS and C2 from VMINUS both go to the VREF divider
    midpoint, not a return rail. Both are recognised, local and direct, and keep VREF."""
    design = json.loads(FILES["dual_rail_reference"].read_text())
    text = Path(glob.glob(str(RUN / "dual_rail_reference/project/*.kicad_sch"))[0]).read_text()
    rows = {r["capacitor"]: r for r in capacitor_distances(design, text)}
    assert set(rows) == {"C1", "C2"}
    assert (rows["C1"]["net"], rows["C1"]["serves"]) == ("VPLUS", "U1.8")
    assert (rows["C2"]["net"], rows["C2"]["serves"]) == ("VMINUS", "U1.4")
    for row in rows.values():
        assert row["return_net"] == "VREF" and row["return_kind"] == "reference"
        assert row["direct"] and row["distance_mm"] <= 25.4
    # Every check passes on that drawing: the nets are exactly the intended ones.
    report = json.loads((RUN / "dual_rail_reference/assessment.json").read_text())
    assert report["checks"]["electrical_equivalence"] == "PASS"


def test_a_single_supply_mid_rail_divider_is_a_reference():
    """A second, non-ground example: VMID halfway between VCC and GND through R1 and R2."""
    design = _design(
        [("R1", "Device:R"), ("R2", "Device:R"), ("C1", "Device:C"), ("R3", "Device:R")],
        [
            ("VCC", [["R1", "1"], ["C1", "1"]]),
            ("VMID", [["R1", "2"], ["R2", "1"], ["C1", "2"], ["R3", "1"]]),
            ("GND", [["R2", "2"]]),
            ("SIG", [["R3", "2"]]),
        ],
    )
    assert reference_nets(design, {"VCC", "GND"}) == {"VMID"}


def test_a_signal_through_one_resistor_or_between_one_rail_is_not_a_reference():
    design = _design(
        [("R1", "Device:R"), ("R2", "Device:R")],
        [
            ("VCC", [["R1", "1"], ["R2", "1"]]),
            ("NODE", [["R1", "2"], ["R2", "2"]]),
            ("SIG", []),
        ],
    )
    # Both resistors reach the same rail: a pull-up, not a divider.
    assert reference_nets(design, {"VCC", "GND"}) == set()


def test_rail_capacitors_stay_rail_capacitors():
    for name in ("dual_buffer", "linear_regulator", "timer_astable"):
        design = json.loads(FILES[name].read_text())
        text = Path(glob.glob(str(RUN / name / "project/*.kicad_sch"))[0]).read_text()
        assert {r["return_kind"] for r in capacitor_distances(design, text)} == {"rail"}
