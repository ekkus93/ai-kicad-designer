"""Reference/value text of vertical two-pin parts sits beside the part body."""

import json
from pathlib import Path

import pytest

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a_artifacts import emit
from ai_kicad.m2b import assets, validate
from ai_kicad.pivot.field_layout import (
    BODY_GAP,
    _field_box,
    _obstacles,
    _vertical_bodies,
    tighten_vertical_fields_text,
)
from ai_kicad.pivot.power_symbols import _overlaps
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]


def compiled_text(name: str, directory: Path) -> str:
    resolved = assets()
    source = ROOT / "fixtures/m2b" / f"{name}.json"
    if not source.is_file():
        source = ROOT / "fixtures/pivot" / name / "design.json"
    design = validate(json.loads(source.read_text()), resolved)
    scene, _composition = compose_with_evidence(design, resolved)
    return emit(design, resolved, scene, directory).read_text()


def fields(tree: list, reference: str) -> dict[str, tuple[str, tuple[int, int]]]:
    symbol = next(
        item
        for item in children(tree, "symbol")
        if any(p[1] == "Reference" and p[2] == reference for p in children(item, "property"))
    )
    return {
        prop[1]: (
            prop[2],
            (round(float(one(prop, "at")[1]) * 1e6), round(float(one(prop, "at")[2]) * 1e6)),
        )
        for prop in children(symbol, "property")
        if prop[1] in {"Reference", "Value"}
    }


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("timer_astable", {"R1", "R2", "C1", "C2"}),
        ("reference_555_led_flasher_v8", {"R1", "R2", "R3", "C1", "C2", "D1"}),
        ("rc_lowpass", {"C1"}),
    ],
)
def test_vertical_part_text_moves_beside_the_body(tmp_path, name, expected):
    text = compiled_text(name, tmp_path)
    before = parse(text)
    tightened, moves = tighten_vertical_fields_text(text)
    after = parse(tightened)
    assert expected <= {move["reference"] for move in moves}
    bodies = _vertical_bodies(after)
    for reference in expected:
        old, new = fields(before, reference), fields(after, reference)
        body = bodies[reference]
        for name_, (value, (x, y)) in new.items():
            assert y == old[name_][1][1], "text keeps its vertical position"
            assert x < old[name_][1][0], "text moves toward the part"
            box = _field_box((x, y), value)
            # At least the body gap clear of the body, and well under the old distance.
            assert box[0] >= body[2] + BODY_GAP
            assert box[0] - body[2] <= old[name_][1][0] - body[2]
            assert not any(_overlaps(box, item) for item in _obstacles(tightened, after, reference))


def test_parts_with_pins_on_several_sides_are_left_alone(tmp_path):
    text = compiled_text("timer_astable", tmp_path)
    tightened, _moves = tighten_vertical_fields_text(text)
    assert fields(parse(text), "U1") == fields(parse(tightened), "U1")


@pytest.mark.parametrize("name", ["timer_astable", "reference_555_led_flasher_v8"])
def test_connector_text_moves_next_to_the_connector(tmp_path, name):
    from ai_kicad.pivot.field_layout import _label_bodies

    text = compiled_text(name, tmp_path)
    tightened, moves = tighten_vertical_fields_text(text)
    after = parse(tightened)
    bodies = _label_bodies(after)
    moved = {move["reference"]: move for move in moves}
    for reference in ("J1", "J2", "J3"):
        body, kind = bodies[reference]
        assert kind == "connector" and reference in moved
        centre = ((body[0] + body[2]) / 2, (body[1] + body[3]) / 2)

        def spread(points):
            return sum(abs(x - centre[0]) + abs(y - centre[1]) for x, y in points)

        before = [tuple(v * 1e6 for v in point) for point in moved[reference]["from_mm"].values()]
        placed = [point for _value, point in fields(after, reference).values()]
        assert spread(placed) < spread(before)
        for value, point in fields(after, reference).values():
            box = _field_box(point, value)
            assert not any(_overlaps(box, item) for item in _obstacles(tightened, after, reference))


def test_tightening_is_idempotent(tmp_path):
    once, _moves = tighten_vertical_fields_text(compiled_text("timer_astable", tmp_path))
    twice, moves = tighten_vertical_fields_text(once)
    assert twice == once and moves == []
