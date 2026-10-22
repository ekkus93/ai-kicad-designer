"""Geometry-independent contracts for reusable schematic field placement."""

import json
from pathlib import Path

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2b_layout import Draft, _place_all_component_text_slots
from ai_kicad.m2_text_layout import (
    candidate_text_anchors,
    first_clear_text_anchor,
    property_envelopes,
    readable_property_angle,
    readable_property_angles,
)
from ai_kicad.m2a import PITCH
from ai_kicad.m2b import assets, validate
from ai_kicad.m2a import Asset


def test_rotated_symbol_property_text_stays_page_readable() -> None:
    assert [readable_property_angle(angle) for angle in (0, 90, 180, 270)] == [0, 90, 0, 90]
    assert readable_property_angles({("diode", 1): 90, ("connector", 1): 270, ("passive", 1): 0}) == {
        ("diode", 1): 90,
        ("connector", 1): 90,
    }


def test_candidate_search_moves_around_wire_and_is_deterministic() -> None:
    origin = (100 * PITCH, 100 * PITCH)
    preferred = (origin[0] + 8 * PITCH, origin[1] - 2 * PITCH)
    candidates = candidate_text_anchors(origin, preferred)
    blocked = property_envelopes("R1", "1k", preferred)
    selected = first_clear_text_anchor(
        candidates,
        lambda anchor: property_envelopes("R1", "1k", anchor),
        obstacles=(),
        wires=(((blocked[0][0] - PITCH, preferred[1]), (blocked[0][2] + PITCH, preferred[1])),),
    )
    assert selected is not None
    assert selected != preferred
    assert selected == first_clear_text_anchor(
        candidates,
        lambda anchor: property_envelopes("R1", "1k", anchor),
        obstacles=(),
        wires=(((blocked[0][0] - PITCH, preferred[1]), (blocked[0][2] + PITCH, preferred[1])),),
    )


def test_long_values_expand_the_text_envelope() -> None:
    short = property_envelopes("R1", "1k", (0, 0))[1]
    long = property_envelopes("R1", "WP7113ID", (0, 0))[1]
    assert long[2] - long[0] > short[2] - short[0]


def test_symbol_body_geometry_and_longest_field_drive_nearby_slots() -> None:
    body = (0, 0, 10 * PITCH, 10 * PITCH)
    origin = (5 * PITCH, 5 * PITCH)
    short = candidate_text_anchors(origin, origin, body=body, longest_field="R1")
    long = candidate_text_anchors(origin, origin, body=body, longest_field="WP7113ID")
    short_body_slots = short[-4:]
    long_body_slots = long[-4:]
    assert short_body_slots[0][1] < body[1]
    assert long_body_slots[1][0] > short_body_slots[1][0]
    selected = first_clear_text_anchor(
        short[1:],
        lambda anchor: property_envelopes("R1", "1k", anchor),
        obstacles=(body,),
        wires=(),
    )
    assert selected is not None and selected != origin


def test_multiline_reference_value_pair_is_rejected_when_fixed_line_spacing_overlaps() -> None:
    candidates = candidate_text_anchors((10 * PITCH, 10 * PITCH), (10 * PITCH, 2 * PITCH))
    assert first_clear_text_anchor(
        candidates,
        lambda anchor: property_envelopes("R1", "Long\nvalue", anchor),
        obstacles=(),
        wires=(),
    ) is None


def test_composed_rotated_led_fields_are_page_readable() -> None:
    root = Path(__file__).resolve().parents[1]
    locked_assets = assets()
    design = validate(json.loads((root / "fixtures/m2b/led_series.json").read_text()), locked_assets)
    scene, _evidence = compose_with_evidence(design, locked_assets)
    led = next(component for component in design["components"] if component["asset"] == "Device:LED")
    occurrence = (led["id"], 1)
    assert scene.angles[occurrence] in (90, 270)
    assert scene.text_angles[occurrence] == 90


def test_nonpassive_component_fields_move_away_from_a_neighbouring_symbol() -> None:
    design = {
        "components": [
            {"id": "active", "refdes": "U1", "value": "Timer", "asset": "Example:Timer"},
            {"id": "neighbor", "refdes": "D1", "value": "LED", "asset": "Example:Timer"},
        ]
    }
    resolved = {
        "Example:Timer": Asset("Example:Timer", "", {1: ()}, {1: (-PITCH, -PITCH, PITCH, PITCH)})
    }
    origin = (40 * PITCH, 40 * PITCH)
    preferred = (40 * PITCH, 32 * PITCH)
    draft = Draft(
        design,
        resolved,
        {("active", 1): origin, ("neighbor", 1): preferred},
        {},
        [],
        [],
        [],
        [],
        {("active", 1): preferred, ("neighbor", 1): (60 * PITCH, 60 * PITCH)},
    )
    _place_all_component_text_slots(design, draft)
    assert draft.text_positions[("active", 1)] != preferred
