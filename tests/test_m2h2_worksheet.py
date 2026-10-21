"""Falsify native worksheet collisions without trusting planner geometry."""

import re

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2b import assets, check_observed_layout


def test_independent_observer_rejects_native_field_in_title_block(tmp_path):
    definition = re.sub(
        r'\(symbol\s+"C"', '(symbol "Device:C"', assets()["Device:C"].definition, count=1
    )
    schematic = tmp_path / "worksheet_field.kicad_sch"
    schematic.write_text(
        "(kicad_sch (lib_symbols " + definition + ") "
        '(symbol (lib_id "Device:C") (at 100 100 0) (unit 1) '
        '(property "Reference" "C5" (at 110 95 0) (effects (font (size 1.27 1.27)))) '
        '(property "Value" "10u" (at 179.07 166.37 0) (effects (font (size 1.27 1.27))))))'
    )
    observed = {
        "labels": [],
        "wires": [],
        "pin_positions": {},
        "nets": {},
        "junctions": [],
        "occurrences": {
            ("C5", 1): {
                "lib": "Device:C",
                "properties": {
                    "Reference": {
                        "position": (110_000_000, 95_000_000),
                        "value": "C5",
                        "hidden": False,
                    },
                    "Value": {
                        "position": (179_070_000, 166_370_000),
                        "value": "10u",
                        "hidden": False,
                    },
                },
            }
        },
    }
    with pytest.raises(InputError, match="observed content overlaps worksheet title block"):
        check_observed_layout(schematic, observed, {"components": [], "relationships": []})
