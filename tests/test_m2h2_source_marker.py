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
