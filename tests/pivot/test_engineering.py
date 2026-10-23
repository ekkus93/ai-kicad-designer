import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.engineering import (
    CatalogPart,
    CircuitRequirements,
    AssemblyPlacement,
    RequirementError,
    SUPPORTED_DOMAINS,
    astable_555,
    decoupling_capacitance,
    export_through_hole_assembly,
    export_kicad_smt_assembly,
    export_smt_assembly,
    led_resistor,
    regulator_thermal,
    resistor_power,
    select_part,
)
from ai_kicad.pivot.spice import simulate_rc_charge


ROOT = Path(__file__).resolve().parents[2]
NGSPICE = Path("/home/phil/Applications/ngspice-42/AppDir/usr/bin/ngspice")


def test_typed_requirements_reject_unsafe_unknowns_and_bad_ranges():
    with pytest.raises(ValidationError, match="nominal"):
        CircuitRequirements(
            function="timer",
            supply_nominal_v=20.0,
            supply_min_v=4.0,
            supply_max_v=10.0,
            output_load_ma=1.0,
            environment="bench",
            safety_class="benign-low-voltage",
            assumptions=[],
            unresolved=[],
        )
    with pytest.raises(ValidationError, match="safety-critical"):
        CircuitRequirements(
            function="mains control",
            supply_nominal_v=120,
            supply_min_v=100,
            supply_max_v=130,
            output_load_ma=1,
            environment="unknown",
            safety_class="high-voltage",
            assumptions=[],
            unresolved=["isolation class"],
        )


def test_catalog_exact_selection_rejects_package_pinout_and_voltage_negatives():
    data = json.loads((ROOT / "fixtures/pivot/catalog/reference_parts.v1.json").read_text())
    catalog = [CatalogPart.model_validate(item) for item in data["parts"]]
    timer = select_part(
        catalog,
        category="timer",
        package="PDIP-8",
        minimum_voltage_v=5.25,
        required_pin_map={str(index): str(index) for index in range(1, 9)},
    )
    assert timer.mpn == "NE555P"
    assert timer.supplier_mappings[0].supplier_part_number == "296-NE555P-ND"
    assert timer.supplier_mappings[0].checked_on == "2026-10-22"
    resistor = select_part(
        catalog,
        category="resistor",
        package="Axial DIN0207, 7.62mm lead pitch",
        minimum_power_w=0.25,
        required_resistance_ohm=10_000,
    )
    assert resistor.mpn == "CFR-25JB-52-10K"
    capacitor = select_part(
        catalog,
        category="capacitor",
        package="Radial 3.81mm x 2.54mm, 2.54mm lead pitch",
        minimum_voltage_v=5.25,
        required_capacitance_f=10e-9,
        required_dielectric="X7R",
        required_polarity="nonpolar",
    )
    assert capacitor.mpn == "C315C103K5R5TA"
    incomplete_approved = dict(data["parts"][0], supplier_mappings=[])
    with pytest.raises(ValidationError, match="dated supplier mapping"):
        CatalogPart.model_validate(incomplete_approved)
    with pytest.raises(RequirementError, match="unsupported"):
        select_part(catalog, category="timer", package="SOIC-8")
    with pytest.raises(RequirementError, match="unsupported"):
        select_part(catalog, category="timer", package="PDIP-8", minimum_voltage_v=20)
    with pytest.raises(RequirementError, match="unsupported"):
        select_part(
            catalog,
            category="resistor",
            package="Axial DIN0207, 7.62mm lead pitch",
            minimum_power_w=0.5,
            required_resistance_ohm=10_000,
        )
    with pytest.raises(RequirementError, match="unsupported"):
        select_part(
            catalog,
            category="capacitor",
            package="Radial 5.0mm diameter x 11.0mm, 5.0mm lead pitch",
            required_polarity="bipolar",
        )


def test_reference_catalog_covers_bom_and_keeps_unsourced_supply_unapproved():
    data = json.loads((ROOT / "fixtures/pivot/catalog/reference_parts.v1.json").read_text())
    bom = json.loads((ROOT / "fixtures/pivot/reference_555_led_flasher_v1/bom.json").read_text())
    footprint_lock = json.loads(
        (
            ROOT / "fixtures/pivot/reference_555_led_flasher_v1/footprint_assets.lock.json"
        ).read_text()
    )
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    locked_footprints = {
        f"{asset['library']}:{asset['footprint']}": asset for asset in footprint_lock["assets"]
    }
    catalog = {part.mpn: part for part in map(CatalogPart.model_validate, data["parts"])}
    assert set(catalog) == {item["mpn"] for item in bom["items"]}
    for item in bom["items"]:
        part = catalog[item["mpn"]]
        assert part.footprint == item["footprint"]
        asset = locked_footprints[part.footprint]
        footprint_bytes = (fixture / asset["path"]).read_bytes()
        assert hashlib.sha256(footprint_bytes).hexdigest() == asset["sha256"]
        assert part.pin_map == item["symbol_pin_to_pad"]
        assert len(part.datasheet_sha256) == 64
        assert (not part.approved) or part.supplier_mappings
    bipolar = catalog["ECEA1CN100UE"]
    assert not bipolar.approved
    assert not bipolar.supplier_mappings
    with pytest.raises(RequirementError, match="unsupported"):
        select_part(
            list(catalog.values()),
            category="capacitor",
            package=bipolar.package,
            required_capacitance_f=10e-6,
            required_polarity="bipolar",
        )


def test_reference_calculations_and_boundaries():
    timing = astable_555(10_000, 47_000, 10e-6)
    assert timing["frequency_hz"] == pytest.approx(1.386, rel=0.01)
    led = led_resistor(5.25, 2.0, 1000, 0.25)
    assert led["status"] == "PASS" and led["current_a"] == pytest.approx(0.00325)
    with pytest.raises(RequirementError):
        led_resistor(2.0, 2.0, 1000, 0.25)
    assert resistor_power(0.001, 47_000, 0.25)["status"] == "PASS"
    thermal = regulator_thermal(12, 5, 0.1, 50, 25)
    assert thermal["dissipation_w"] == pytest.approx(0.7)
    assert thermal["estimated_junction_c"] == pytest.approx(60)
    assert decoupling_capacitance(0.1, 1e-3, 0.5)["minimum_ideal_capacitance_f"] == pytest.approx(
        200e-6
    )


def test_real_ngspice_transient_matches_analytical_limit(tmp_path):
    report = simulate_rc_charge(
        NGSPICE,
        tmp_path / "spice",
        supply_v=5.0,
        resistance_ohm=57_000,
        capacitance_f=10e-6,
        stop_s=1.2,
    )
    assert report["status"] == "PASS"
    assert report["two_thirds_crossing_s"] == pytest.approx(
        report["analytical_crossing_s"], abs=0.002
    )


def test_through_hole_assembly_scope_and_domain_manifest(tmp_path):
    verification = json.loads(
        (
            ROOT
            / "fixtures/pivot/experiments/reference_poc_2026-10-22_run7/reports/verification_report.json"
        ).read_text()
    )
    bom = json.loads((ROOT / "fixtures/pivot/reference_555_led_flasher_v1/bom.json").read_text())
    result = export_through_hole_assembly(verification["board"], bom, tmp_path / "assembly")
    assert result["centroid"] == "UNSUPPORTED" and result["paste"] == "UNSUPPORTED"
    assert SUPPORTED_DOMAINS["rf"] == "unsupported"


def test_pcbway_smt_bom_centroid_and_rotation_negatives(tmp_path):
    placements = [
        AssemblyPlacement(
            reference="R1",
            x_mm=10.25,
            y_mm=4.5,
            side="Top",
            rotation_deg=90,
            footprint="R_0603_1608Metric",
        ),
        AssemblyPlacement(
            reference="C1",
            x_mm=12,
            y_mm=5,
            side="Bottom",
            rotation_deg=270,
            footprint="C_0603_1608Metric",
        ),
    ]
    bom = [
        {"reference": "R1", "quantity": 1, "mpn": "RC0603", "footprint": "R_0603_1608Metric"},
        {"reference": "C1", "quantity": 1, "mpn": "CC0603", "footprint": "C_0603_1608Metric"},
    ]
    report = export_smt_assembly(placements, bom, tmp_path / "valid")
    assert report["status"] == "PASS" and report["placement_count"] == 2
    assert "Bottom,270.00" in (tmp_path / "valid/centroid.csv").read_text()
    with pytest.raises(ValidationError):
        AssemblyPlacement(
            reference="R1", x_mm=0, y_mm=0, side="Top", rotation_deg=360, footprint="x"
        )
    wrong = [dict(bom[0], quantity=2), bom[1]]
    with pytest.raises(RequirementError, match="quantity"):
        export_smt_assembly(placements, wrong, tmp_path / "wrong")


def test_native_kicad_smt_export_binds_position_paste_and_drawing_to_board(tmp_path):
    board = tmp_path / "assembly.kicad_pcb"
    board.write_text(
        '(kicad_pcb (footprint "Resistor_SMD:R_0603_1608Metric" (property "Reference" "R1")))'
    )
    bom = [
        {
            "reference": "R1",
            "quantity": 1,
            "mpn": "RC0603",
            "footprint": "Resistor_SMD:R_0603_1608Metric",
        }
    ]

    def fake_cli(command, **_kwargs):
        if "pos" in command:
            output = Path(command[command.index("--output") + 1])
            output.write_text(
                "Ref,Val,Package,PosX,PosY,Rot,Side\n"
                "R1,10k,R_0603_1608Metric,10.2500,4.5000,-90.0,bottom\n"
            )
        elif "gerbers" in command:
            output = Path(command[command.index("--output") + 1])
            (output / "assembly-F_Paste.gbr").write_text("%FSLAX46Y46*%\n%LPD*%\n")
        else:
            Path(command[command.index("--output") + 1]).write_bytes(b"%PDF-1.5 test")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("ai_kicad.pivot.engineering.subprocess.run", side_effect=fake_cli) as cli:
        report = export_kicad_smt_assembly(["kicad-cli"], board, bom, tmp_path / "package")

    assert report["status"] == "PASS"
    assert report["placement_count"] == 1
    assert report["paste"] == ["paste/assembly-F_Paste.gbr"]
    assert report["assembly_drawing"] == "assembly.pdf"
    centroid = (tmp_path / "package/centroid.csv").read_text()
    assert "R1,10.2500mm,4.5000mm,Bottom,270.00" in centroid
    assert len(report["output_sha256"]) == 4
    assert len(cli.call_args_list) == 3


def test_native_kicad_smt_export_rejects_footprint_mismatch_before_promotion(tmp_path):
    board = tmp_path / "assembly.kicad_pcb"
    board.write_text('(kicad_pcb (footprint "R_0603_1608Metric" (property "Reference" "R1")))')
    bom = [
        {
            "reference": "R1",
            "quantity": 1,
            "mpn": "RC0603",
            "footprint": "C_0603_1608Metric",
        }
    ]

    def fake_cli(command, **_kwargs):
        output = Path(command[command.index("--output") + 1])
        output.write_text(
            "Ref,Val,Package,PosX,PosY,Rot,Side\n"
            "R1,10k,R_0603_1608Metric,10.2500,4.5000,90.0,Front\n"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("ai_kicad.pivot.engineering.subprocess.run", side_effect=fake_cli):
        with pytest.raises(RequirementError, match="footprint differs"):
            export_kicad_smt_assembly(["kicad-cli"], board, bom, tmp_path / "package")
    assert not (tmp_path / "package").exists()
