"""Geometry-independent contracts for reusable schematic field placement."""

import json
from pathlib import Path

from ai_kicad.m2a_artifacts import emit, verify_serialized_scene
from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a import PITCH, Asset, Scene, certify_scene_geometry
from ai_kicad.m2b_layout import Draft, _place_all_component_text_slots
from ai_kicad.m2_text_layout import (
    MAX_LOCAL_SEARCH_RADIUS,
    candidate_text_anchors,
    first_clear_text_anchor,
    property_envelopes,
    property_page_angle,
    property_positions,
    readable_property_angle,
    readable_property_angles,
    text_extents,
)
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_transform import transform_library_point


def test_rotated_symbol_property_text_stays_page_readable() -> None:
    assert [readable_property_angle(angle) for angle in (0, 90, 180, 270)] == [0, 90, 0, 90]
    assert readable_property_angles(
        {("diode", 1): 90, ("connector", 1): 270, ("passive", 1): 0}
    ) == {
        ("diode", 1): 90,
        ("connector", 1): 90,
    }
    assert [property_page_angle(angle) for angle in (0, 90, 180, 270)] == [0, 0, 0, 0]


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


def test_candidate_search_expands_to_configured_block_local_limit() -> None:
    origin = (20 * PITCH, 20 * PITCH)
    candidates = candidate_text_anchors(origin, origin)
    assert (origin[0] + MAX_LOCAL_SEARCH_RADIUS * PITCH, origin[1]) in candidates


def test_multiline_value_gets_an_independent_collision_free_anchor() -> None:
    anchor = (10 * PITCH, 10 * PITCH)
    reference_position, value_position = property_positions("R1", "Long\nvalue", anchor)
    assert reference_position == anchor
    assert value_position[0] == anchor[0]
    assert value_position[1] > anchor[1] + 2 * PITCH
    reference_envelope, value_envelope = property_envelopes("R1", "Long\nvalue", anchor)
    assert reference_envelope[3] < value_envelope[1]
    rotated_reference, rotated_value = property_envelopes("R1", "Long\nvalue", anchor, 90)
    assert text_extents("Long\nvalue", 90) == tuple(reversed(text_extents("Long\nvalue")))
    assert rotated_reference[3] < rotated_value[1]

    candidates = candidate_text_anchors(anchor, (10 * PITCH, 2 * PITCH))
    assert (
        first_clear_text_anchor(
            candidates,
            lambda anchor: property_envelopes("R1", "Long\nvalue", anchor),
            obstacles=(),
            wires=(),
        )
        is not None
    )


def test_multiline_value_anchor_survives_kicad_serialization(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    locked_assets = assets()
    source = json.loads((root / "fixtures/m2b/led_series.json").read_text())
    source["components"][0]["value"] = "Long\nLED value"
    design = validate(source, locked_assets)
    scene, _evidence = compose_with_evidence(design, locked_assets)
    schematic = emit(design, locked_assets, scene, tmp_path)
    verify_serialized_scene(design, scene, schematic)


def test_mirrored_connector_pin_route_round_trips_through_native_scene(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    locked_assets = assets()
    design = validate(
        json.loads((root / "fixtures/m2b/led_long_text.json").read_text()), locked_assets
    )
    composed, _evidence = compose_with_evidence(design, locked_assets)
    connector = next(component for component in design["components"] if component["id"] == "source")
    occurrence = (connector["id"], 1)
    pin = locked_assets[connector["asset"]].units[1][0]
    origin = composed.positions[occurrence]
    old_dx, old_dy = transform_library_point(pin.x, pin.y, composed.angles.get(occurrence, 0))
    old_pin = (origin[0] + old_dx, origin[1] + old_dy)
    new_dx, new_dy = transform_library_point(pin.x, pin.y, composed.angles.get(occurrence, 0), "y")
    new_pin = (origin[0] + new_dx, origin[1] + new_dy)
    wires = [
        tuple(new_pin if point == old_pin else point for point in segment)
        for segment in composed.wires
    ]
    labels = [(name, new_pin if point == old_pin else point) for name, point in composed.labels]
    mirrors = {occurrence: "y"}
    draft = Draft(
        design,
        locked_assets,
        dict(composed.positions),
        dict(composed.angles),
        list(wires),
        list(composed.wire_nets),
        labels,
        list(composed.junctions),
        dict(composed.text_positions),
        mirrors,
    )
    _place_all_component_text_slots(design, draft)
    assert draft.point(connector["id"], pin.number) == new_pin
    assert new_pin in {point for segment in draft.wires for point in segment}
    mirrored = certify_scene_geometry(
        Scene(
            draft.positions,
            draft.wires,
            draft.wire_nets,
            draft.labels,
            draft.junctions,
            dict(composed.metrics),
            draft.angles,
            draft.text_positions,
            dict(composed.text_angles),
            mirrors=mirrors,
        )
    )
    schematic = emit(design, locked_assets, mirrored, tmp_path)
    verify_serialized_scene(design, mirrored, schematic)
    assert "(mirror y)" in schematic.read_text()


def test_mirror_transform_applies_before_symbol_rotation() -> None:
    assert transform_library_point(3, 5, 0, "x") == (3, 5)
    assert transform_library_point(3, 5, 0, "y") == (-3, -5)
    assert transform_library_point(3, 5, 90, "y") == (-5, 3)


def test_draft_pin_positions_follow_mirror_transform() -> None:
    resistor = assets()["Device:R"]
    design = {"components": [{"id": "resistor", "asset": "Device:R"}]}
    origin = (40 * PITCH, 40 * PITCH)
    draft = Draft(design, {"Device:R": resistor}, {}, {}, [], [], [], [], {})
    draft.add("resistor", *origin, mirror="x")
    pin = resistor.units[1][0]
    dx, dy = transform_library_point(pin.x, pin.y, 0, "x")
    assert draft.point("resistor", pin.number) == (origin[0] + dx, origin[1] + dy)


def test_composed_rotated_led_fields_are_page_readable() -> None:
    root = Path(__file__).resolve().parents[1]
    locked_assets = assets()
    design = validate(
        json.loads((root / "fixtures/m2b/led_series.json").read_text()), locked_assets
    )
    scene, _evidence = compose_with_evidence(design, locked_assets)
    led = next(
        component for component in design["components"] if component["asset"] == "Device:LED"
    )
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
