"""Falsify the native long-field rotation missed by planner-only metrics."""

import re
import sys
from pathlib import Path
import pytest
from ai_kicad.ir import InputError
from ai_kicad.m2b import assets, check_observed_layout, validate
from ai_kicad.m2_compose import compose_with_evidence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from make_m2h2_i6 import text_support, text_branch  # noqa: E402


@pytest.mark.parametrize(
    "factory,arg",
    [
        (text_support, "0"),
        (text_support, "1-2"),
        (text_support, "3+"),
        (text_branch, 1),
        (text_branch, 2),
        (text_branch, 3),
    ],
)
def test_long_passive_native_orientation_matches_measured_horizontal_fields(factory, arg):
    design, _ = factory("long", arg)
    scene, _ = compose_with_evidence(validate(design, assets()), assets())
    for component in design["components"]:
        if component["asset"] in {"Device:R", "Device:C"} and len(component["value"]) > 4:
            key = (component["id"], 1)
            assert scene.text_angles.get(key, 0) == scene.angles.get(key, 0) % 180


def test_independent_observer_rejects_long_native_rotated_value_on_resistor(tmp_path):
    definition = re.sub(
        r'\(symbol\s+"R"', '(symbol "Device:R"', assets()["Device:R"].definition, count=1
    )
    schematic = tmp_path / "long_field.kicad_sch"
    schematic.write_text(
        "(kicad_sch (lib_symbols " + definition + ") "
        '(symbol (lib_id "Device:R") (at 100 100 90) (unit 1) '
        '(property "Reference" "R1" (at 100 93.65 0) (effects (font (size 1.27 1.27)))) '
        '(property "Value" "R12345678901234567890123" (at 100 96.19 0) (effects (font (size 1.27 1.27))))))'
    )
    observed = {
        "labels": [],
        "wires": [],
        "pin_positions": {},
        "nets": {},
        "junctions": [],
        "occurrences": {},
    }
    with pytest.raises(InputError, match="observed required field overlaps body/label"):
        check_observed_layout(schematic, observed, {"components": [], "relationships": []})


def test_compensated_horizontal_native_value_does_not_cross_worksheet(tmp_path):
    definition = re.sub(
        r'\(symbol\s+"R"', '(symbol "Device:R"', assets()["Device:R"].definition, count=1
    )
    schematic = tmp_path / "horizontal_field.kicad_sch"
    schematic.write_text(
        "(kicad_sch (lib_symbols " + definition + ") "
        '(symbol (lib_id "Device:R") (at 170 155 90) (unit 1) '
        '(property "Reference" "R1" (at 179 157.46 90) (effects (font (size 1.27 1.27)))) '
        '(property "Value" "R12345678901234567890123" (at 179 160 90) (effects (font (size 1.27 1.27))))))'
    )
    observed = {
        "labels": [],
        "wires": [],
        "pin_positions": {},
        "nets": {},
        "junctions": [],
        "occurrences": {
            ("R1", 1): {
                "lib": "Device:R",
                "properties": {
                    "Reference": {
                        "position": (179_000_000, 157_460_000),
                        "value": "R1",
                        "hidden": False,
                    },
                    "Value": {
                        "position": (179_000_000, 160_000_000),
                        "value": "R12345678901234567890123",
                        "hidden": False,
                    },
                },
            }
        },
    }
    check_observed_layout(schematic, observed, {"components": [], "relationships": []})
