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
    clear_label_pin_numbers_text,
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


def fields(tree: list, reference: str, unit: int = 1) -> dict[str, tuple[str, tuple[int, int]]]:
    symbol = next(
        item
        for item in children(tree, "symbol")
        if int(one(item, "unit")[1]) == unit
        and any(p[1] == "Reference" and p[2] == reference for p in children(item, "property"))
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
        body = bodies[(reference, 1)]
        for name_, (value, (x, y)) in new.items():
            assert y == old[name_][1][1], "text keeps its vertical position"
            assert x < old[name_][1][0], "text moves toward the part"
            box = _field_box((x, y), value)
            # At least the body gap clear of the body, and well under the old distance.
            assert box[0] >= body[2] + BODY_GAP
            assert box[0] - body[2] <= old[name_][1][0] - body[2]
            assert not any(
                _overlaps(box, item) for item in _obstacles(tightened, after, (reference, 1))
            )


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
        body, kind = bodies[(reference, 1)]
        assert kind == "connector" and reference in moved
        centre = ((body[0] + body[2]) / 2, (body[1] + body[3]) / 2)

        def spread(points):
            return sum(abs(x - centre[0]) + abs(y - centre[1]) for x, y in points)

        before = [tuple(v * 1e6 for v in point) for point in moved[reference]["from_mm"].values()]
        placed = [point for _value, point in fields(after, reference).values()]
        assert spread(placed) < spread(before)
        for value, point in fields(after, reference).values():
            box = _field_box(point, value)
            assert not any(
                _overlaps(box, item) for item in _obstacles(tightened, after, (reference, 1))
            )


@pytest.mark.parametrize(
    "name",
    ["dual_buffer", "dual_rail_reference", "noninverting_gain", "rc_to_buffer", "sallen_key"],
)
def test_op_amp_power_unit_text_reads_as_its_own(tmp_path, name):
    """The body-less V+/V- unit's text moves beside it, not near a neighbouring part."""
    from ai_kicad.pivot.field_layout import _label_bodies
    from ai_kicad.pivot.schematic_fields import measure_field_association

    text = compiled_text(name, tmp_path)
    before = parse(text)
    power_units = [
        part for part, (_box, kind) in _label_bodies(before).items() if kind == "power_unit"
    ]
    assert power_units, "the op-amp supply unit is recognised"
    tightened, moves = tighten_vertical_fields_text(text)
    after = parse(tightened)
    moved = {(move["reference"], move["unit"]) for move in moves}
    for part in power_units:
        assert part in moved
        witnesses = [
            item
            for item in measure_field_association(after)["witnesses"]
            if (item["reference"], item["unit"]) == part
        ]
        assert witnesses == []
        for value, point in fields(after, *part).values():
            box = _field_box(point, value)
            assert not any(_overlaps(box, item) for item in _obstacles(tightened, after, part))
    # Other units of the same part keep their text where it was.
    for symbol in children(before, "symbol"):
        reference = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        unit = int(one(symbol, "unit")[1])
        if (reference, unit) not in moved and not reference.startswith("#"):
            assert fields(before, reference, unit) == fields(after, reference, unit)


def test_tightening_is_idempotent(tmp_path):
    once, _moves = tighten_vertical_fields_text(compiled_text("timer_astable", tmp_path))
    twice, moves = tighten_vertical_fields_text(once)
    assert twice == once and moves == []


def test_moved_text_stays_inside_the_observers_page_area(tmp_path):
    """led_reverse_supply's J1 sits near the top; its text must not move past the margin."""
    # The protected observer's A4 content area (m2b_observation), in nm.
    page = (20_320_000, 25_400_000, 276_680_000, 184_600_000)
    _tightened, moves = tighten_vertical_fields_text(compiled_text("led_reverse_supply", tmp_path))
    assert "J1" in {move["reference"] for move in moves}
    for move in moves:
        for x, y in move["to_mm"].values():
            x, y = round(x * 1e6), round(y * 1e6)
            assert page[0] <= x <= page[2]
            assert page[1] <= y <= page[3]


CORPUS_RUN = ROOT / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-11-01_qwen35_32k_run2"


def _labels(text: str) -> list[tuple[str, tuple[int, int]]]:
    from ai_kicad.m2a_core import _nm

    return [
        (label[1], (_nm(one(label, "at")[1]), _nm(one(label, "at")[2])))
        for label in children(parse(text), "label")
    ]


def _number_gap(text: str, name: str, point: tuple[int, int]) -> int:
    from ai_kicad.m2_geometry import label_text_rect
    from ai_kicad.pivot.power_symbols import _pin_number_boxes

    box = label_text_rect(name, point)
    return min(
        max(box[0] - b[2], b[0] - box[2], box[1] - b[3], b[1] - box[3])
        for _owner, b in _pin_number_boxes(text, parse(text))
    )


@pytest.mark.parametrize(
    "design", ["dual_buffer", "noninverting_gain", "rc_to_buffer", "sallen_key"]
)
def test_vminus_label_moves_off_the_connector_pin_number(design):
    """The VMINUS label's text, 0.14 mm from pin number 4, moves out along a longer stub."""
    from ai_kicad.m2a_core import _nm
    from ai_kicad.pivot.power_symbols import _wire_segments

    text = next((CORPUS_RUN / design / "candidates/000/project").glob("*.kicad_sch")).read_text()
    before = [item for item in _labels(text) if item[0] == "VMINUS"]
    flags_before = {
        (_nm(one(s, "at")[1]), _nm(one(s, "at")[2]))
        for s in children(parse(text), "symbol")
        if one(s, "lib_id")[1] == "power:PWR_FLAG"
    }
    # The connector's label, on the stub end it shares with a flag.
    crowded = [
        item for item in before if item[1] in flags_before and _number_gap(text, *item) < 635_000
    ]
    assert len(crowded) == 1
    name, old = crowded[0]

    moved, moves = clear_label_pin_numbers_text(text)

    vminus = [m for m in moves if m["label"] == "VMINUS"]
    assert len(vminus) == 1
    new = tuple(round(v * 1_000_000) for v in vminus[0]["to_mm"])
    assert new[1] == old[1] and new[0] < old[0]
    assert (name, new) in _labels(moved) and (name, old) not in _labels(moved)
    assert _number_gap(moved, name, new) >= 635_000
    # The stub is lengthened to the new anchor and the flag on its end moves with the label.
    assert any({first, second} == {new, old} for first, second in _wire_segments(parse(moved)))
    flags_after = {
        (_nm(one(s, "at")[1]), _nm(one(s, "at")[2]))
        for s in children(parse(moved), "symbol")
        if one(s, "lib_id")[1] == "power:PWR_FLAG"
    }
    assert flags_after == flags_before - {old} | {new}


@pytest.mark.parametrize(
    "design", ["timer_astable", "timer_astable_gnd", "led_series", "rc_lowpass", "linear_regulator"]
)
def test_labels_clear_of_pin_numbers_stay_where_drawn(design):
    text = next((CORPUS_RUN / design / "candidates/000/project").glob("*.kicad_sch")).read_text()
    assert clear_label_pin_numbers_text(text) == (text, [])


@pytest.mark.parametrize("design", sorted(p.name for p in CORPUS_RUN.iterdir() if p.is_dir()))
def test_lengthened_label_stub_touches_only_its_own_wire(design):
    """A moved label's new stub must not reach another wire; on inverting_gain the
    VPLUS rail runs one grid step outside the VMINUS stub, so that label cannot move."""
    from ai_kicad.m2_geometry import point_on_segment
    from ai_kicad.pivot.power_symbols import _wire_segments

    text = next((CORPUS_RUN / design / "candidates/000/project").glob("*.kicad_sch")).read_text()
    original = _wire_segments(parse(text))
    _moved, moves = clear_label_pin_numbers_text(text)
    for move in moves:
        old = tuple(round(v * 1_000_000) for v in move["from_mm"])
        new = tuple(round(v * 1_000_000) for v in move["to_mm"])
        step = 1_270_000 if new[0] > old[0] else -1_270_000
        for x in range(old[0] + step, new[0] + step, step):
            assert not any(point_on_segment((x, old[1]), *segment) for segment in original)
    if design == "inverting_gain":
        assert "VMINUS" not in {move["label"] for move in moves}
