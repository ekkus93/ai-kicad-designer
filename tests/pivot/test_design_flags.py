"""Report-only design-review flags (REVIEWER_LOOP_SPEC.md R7.6)."""

import json

import pytest

from ai_kicad.pivot.design_flags import _ohms, design_review_flags
from ai_kicad.pivot.schematic_review import SchematicAssessment, run_schematic_review
from tools.pivot.run_review_loop_corpus import CORPUS

DESIGNS = {
    (path.parent.name if path.name == "design.json" else path.stem): json.loads(path.read_text())
    for path in CORPUS
}
EXPECTED = {
    "timer_supply_bypass_missing": {
        "timer_astable",
        "reference_555_led_flasher_v8",
        "timer_astable_gnd",
    },
    "divider_reference": {"dual_rail_reference"},
    "regulator_datasheet_checks_unrecorded": {"linear_regulator"},
    "opamp_swing_unverified": {
        "dual_buffer",
        "dual_rail_reference",
        "inverting_gain",
        "noninverting_gain",
        "rc_to_buffer",
        "sallen_key",
    },
}


@pytest.mark.parametrize("flag", sorted(EXPECTED))
def test_each_flag_appears_exactly_on_its_designs(flag):
    found = {
        name
        for name, design in DESIGNS.items()
        if any(item["flag"] == flag for item in design_review_flags(design))
    }
    assert found == EXPECTED[flag]


def test_divider_reports_its_thevenin_impedance():
    (divider,) = [
        item
        for item in design_review_flags(DESIGNS["dual_rail_reference"])
        if item["flag"] == "divider_reference"
    ]
    assert divider["parts"] == ["R1", "R2"] and divider["net"] == "VREF"
    assert divider["thevenin_ohms"] == 5000.0


def test_a_555_with_a_supply_bypass_is_not_flagged():
    design = json.loads(json.dumps(DESIGNS["timer_astable"]))
    design["components"].append(
        {"id": "bypass", "refdes": "C9", "asset": "Device:C", "value": "100n"}
    )
    for net in design["nets"]:
        if net["id"] == "VCC":
            net["members"].append(["bypass", "1"])
        if net["id"] == "REF":
            net["members"].append(["bypass", "2"])
    assert not any(
        item["flag"] == "timer_supply_bypass_missing" for item in design_review_flags(design)
    )


def test_resistance_values():
    assert _ohms("10k") == 10_000 and _ohms("4k7") == 4_700 and _ohms("1M") == 1e6
    assert _ohms("470") == 470 and _ohms("12.4k precision") is None


class Engine:
    def initial(self, directory):
        path = directory / "project" / "t.kicad_sch"
        path.parent.mkdir(parents=True)
        path.write_text("x")
        return path

    def assess(self, schematic, directory):
        image = directory / "i.png"
        image.write_bytes(b"png")
        flags = [{"flag": "timer_supply_bypass_missing", "parts": ["U1"], "detail": "d"}]
        checks = {"native_tools": "PASS", "erc": "PASS", "electrical_equivalence": "PASS"}
        return SchematicAssessment(
            schematic, [image], {"checks": checks, "design_review_flags": flags}
        )

    def apply(self, schematic, directory, actions):
        raise AssertionError("no edits")


class Reviewer:
    identity = {"backend": "test"}

    def review(self, assessment, feedback, record):
        return json.dumps(
            {
                "base_revision": assessment.revision,
                "decision": "accept",
                "issues": [],
                "actions": [],
                "rationale": "r",
            }
        )


def test_flags_are_reported_without_affecting_acceptance_or_design_status(tmp_path):
    result = run_schematic_review(Engine(), Reviewer(), tmp_path / "run")
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    assert result["design_review_flags"][0]["flag"] == "timer_supply_bypass_missing"
    assert result["status_levels"]["DESIGN_REQUIREMENTS_CHECKED"]["status"] == "PENDING"


@pytest.mark.skipif(
    not __import__("os").environ.get("AI_KICAD_APPRUN"),
    reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun",
)
def test_native_assessment_carries_the_flags_and_no_check_changes(tmp_path):
    import os
    from pathlib import Path

    from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService

    root = Path(__file__).resolve().parents[2]
    service = NativeSchematicReviewService(
        Path(os.environ["AI_KICAD_APPRUN"]),
        "m",
        review_brief=root / "fixtures/pivot/schematic_review_brief_v10.json",
    )
    engine = service.engine(root / "fixtures/m2b/linear_regulator.json")
    source = engine.initial(tmp_path)
    report = engine.assess(source, tmp_path).report
    assert [item["flag"] for item in report["design_review_flags"]] == [
        "regulator_datasheet_checks_unrecorded"
    ]
    assert "design_review_flags" not in report["checks"]
    assert all(value == "PASS" for value in report["checks"].values())
