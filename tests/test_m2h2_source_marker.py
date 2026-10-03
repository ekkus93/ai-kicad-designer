"""Native source-marker clearance must be measured and independently observed."""

import pytest

import json

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT, observe
from ai_kicad.m2_compose import _source_marker_placement
from ai_kicad.m2_geometry import label_text_rect
from ai_kicad.m2b import assets, check_observed_layout, validate


def test_source_marker_uses_locked_body_and_clear_orientation():
    body = assets()["power:PWR_FLAG"].bodies[0]
    point = (50_800_000, 50_800_000)
    label = label_text_rect("VPLUS", point)
    chosen, angle, rectangle = _source_marker_placement([point], body, [label])
    assert chosen == point
    assert angle == 180
    assert rectangle == (49_784_000, 50_800_000, 51_816_000, 53_340_000)
    with pytest.raises(InputError, match="COMPOSE_SOURCE_GLYPH_CLEARANCE"):
        _source_marker_placement([point], body, [label, rectangle])


def test_independent_observer_rejects_source_glyph_over_label():
    # Preserve the historical native schematic/XML as a real-byte counterexample.
    root = ROOT / "fixtures/m2b/qualification/noninverting_gain"
    schematic = next((root / "project").glob("*.kicad_sch"))
    observed = observe(schematic, root / "reports/netlist.xml")
    design = validate(
        json.loads((ROOT / "fixtures/m2b/noninverting_gain.json").read_text()), assets()
    )
    with pytest.raises(InputError, match="observed source glyph overlaps label"):
        check_observed_layout(schematic, observed, design)


def test_source_marker_never_rotates_into_its_attached_wire():
    body = assets()["power:PWR_FLAG"].bodies[0]
    point = (50_800_000, 50_800_000)
    wires = [(point, (50_800_000, 54_610_000))]
    with pytest.raises(InputError, match="COMPOSE_SOURCE_GLYPH_CLEARANCE"):
        _source_marker_placement([point], body, [label_text_rect("VPLUS", point)], wires)
    other = (70_000_000, 50_800_000)
    chosen, _, _ = _source_marker_placement(
        [point, other], body, [label_text_rect("VPLUS", point)], wires
    )
    assert chosen == other


def test_independent_observer_rejects_wire_entering_attached_source_glyph(tmp_path):
    import re

    definition = re.sub(
        r'\(symbol\s+"PWR_FLAG"',
        '(symbol "power:PWR_FLAG"',
        assets()["power:PWR_FLAG"].definition,
        count=1,
    )
    schematic = tmp_path / "wire_entry.kicad_sch"
    schematic.write_text(
        "(kicad_sch (lib_symbols " + definition + ") "
        '(symbol (lib_id "power:PWR_FLAG") (at 50.8 50.8 180) (unit 1) '
        '(property "Reference" "#FLG01" (at 50.8 50.8 0) (hide yes)) '
        '(property "Value" "PWR_FLAG" (at 50.8 53.34 0) (hide yes))))'
    )
    point = (50_800_000, 50_800_000)
    observed = {
        "labels": [],
        "wires": [(point, (50_800_000, 54_610_000))],
        "pin_positions": {("#FLG01", "1"): point},
        "nets": {"VPLUS": [("#FLG01", "1")]},
        "junctions": [],
        "occurrences": {("#FLG01", 1): {"lib": "power:PWR_FLAG", "properties": {}}},
    }
    with pytest.raises(InputError, match="observed wire through source glyph"):
        check_observed_layout(schematic, observed, {"components": [], "relationships": []})
