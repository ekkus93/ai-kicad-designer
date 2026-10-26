"""Independent geometric gate for grossly misassociated symbol fields."""

from pathlib import Path

from ai_kicad.pivot.schematic_fields import measure_field_association
from ai_kicad.pivot.schematic_review_native import MoveField, edit_schematic_text
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]
RC_SCHEMATIC = (
    ROOT
    / "fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/inputs/pristine_rc"
    / "project/DevstralV4RcLowpass1kHz.kicad_sch"
)
TIMER_SCHEMATIC = (
    ROOT
    / "fixtures/pivot/reference_555_led_flasher_v8/native_project"
    / "Reference555LedFlasher.kicad_sch"
)


def test_association_gate_accepts_current_rc_and_timer_layouts() -> None:
    for path in (RC_SCHEMATIC, TIMER_SCHEMATIC):
        report = measure_field_association(parse(path.read_text()))
        assert report["witnesses"] == []


def test_association_gate_catches_value_moved_to_neighboring_connector() -> None:
    text = edit_schematic_text(
        RC_SCHEMATIC.read_text(),
        [
            MoveField(
                operation="move_field",
                reference="C1",
                unit=1,
                field="Value",
                x_mm=99.0,
                y_mm=47.5,
                angle=0,
            )
        ],
    )
    report = measure_field_association(parse(text))
    witness = next(
        item
        for item in report["witnesses"]
        if item["reference"] == "C1" and item["field"] == "Value"
    )
    assert witness["nearest_other_reference"] == "J2"
    assert witness["owner_advantage_mm"] > report["minimum_owner_advantage_mm"]


def test_association_gate_rejects_invalid_margin() -> None:
    import pytest

    with pytest.raises(ValueError, match="finite and nonnegative"):
        measure_field_association(parse(RC_SCHEMATIC.read_text()), float("nan"))


def test_move_field_rejects_noop_coordinate_with_repairable_feedback() -> None:
    import pytest

    current = parse(RC_SCHEMATIC.read_text())
    # The fixture's current C1 value coordinate is read from its serialized property.
    symbol = next(
        item
        for item in children(current, "symbol")
        if next(prop[2] for prop in children(item, "property") if prop[1] == "Reference") == "C1"
    )
    value = next(prop for prop in children(symbol, "property") if prop[1] == "Value")
    at = one(value, "at")
    with pytest.raises(ValueError, match="made no change; choose a different position"):
        edit_schematic_text(
            RC_SCHEMATIC.read_text(),
            [
                MoveField(
                    operation="move_field",
                    reference="C1",
                    unit=1,
                    field="Value",
                    x_mm=float(at[1]),
                    y_mm=float(at[2]),
                    angle=int(float(at[3])),
                )
            ],
        )
