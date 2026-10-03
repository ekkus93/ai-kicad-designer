"""Native source-marker clearance must be measured and independently observed."""

import re

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2_compose import _source_marker_placement
from ai_kicad.m2_geometry import label_text_rect
from ai_kicad.m2b import assets, check_observed_layout


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


def test_independent_observer_rejects_source_glyph_over_label(tmp_path):
    definition = assets()["power:PWR_FLAG"].definition
    definition = re.sub(r'\(symbol\s+"PWR_FLAG"', '(symbol "power:PWR_FLAG"', definition, count=1)
    schematic = tmp_path / "overlap.kicad_sch"
    schematic.write_text(
        "(kicad_sch (lib_symbols " + definition + ") "
        '(symbol (lib_id "power:PWR_FLAG") (at 50.8 50.8 0) (unit 1) '
        '(property "Reference" "#FLG01" (at 50.8 50.8 0) (hide yes)) '
        '(property "Value" "PWR_FLAG" (at 50.8 53.34 0) (hide yes))))'
    )
    # The independent observer measures the embedded glyph, not the planner's box.
    observed = {"labels": [("VPLUS", (50_800_000, 50_800_000))]}
    with pytest.raises(InputError, match="observed source glyph overlaps label"):
        check_observed_layout(schematic, observed, {})
