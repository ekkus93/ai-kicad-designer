"""R2 quality measures (docs/pivot/REVIEWER_LOOP_SPEC.md R2)."""

import glob
import json
from pathlib import Path

import pytest

from ai_kicad.pivot.quality_measures import (
    DEFAULT_QUALITY_THRESHOLDS,
    compare_quality,
    count_bends,
    measure_quality,
    perimeter_paths,
    quality_overlay,
)
from ai_kicad.pivot.review_status import corpus_status_fields
from ai_kicad.pivot.schematic_review import SchematicAssessment, run_schematic_review
from ai_kicad.sexpr import parse

EXPERIMENTS = Path(__file__).resolve().parents[2] / "fixtures/pivot/experiments"
MM = 1_000_000


def _candidate(run: str, design: str, candidate: str) -> tuple[dict, dict]:
    directory = EXPERIMENTS / run / design / "candidates" / candidate
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    report = json.loads((directory / "assessment.json").read_text())
    return measure_quality(parse(text), text, report), report


RESISTOR = """(symbol "Device:R"
    (symbol "R_0_1" (rectangle (start -1.016 -2.54) (end 1.016 2.54)))
    (symbol "R_1_1"
      (pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
      (pin passive line (at 0 -3.81 90) (length 1.27) (name "~") (number "2"))))"""


def _sheet(wires: list[tuple[float, float, float, float]]) -> list:
    parts = "".join(
        f'(symbol (lib_id "Device:R") (at {x} 50 0) (unit 1)'
        f' (property "Reference" "R{n}" (at {x + 2.54} 50 0))'
        f' (property "Value" "10k" (at {x - 2.54} 50 0)))'
        for n, x in ((1, 50), (2, 120))
    )
    drawn = "".join(f"(wire (pts (xy {a} {b}) (xy {c} {d})))" for a, b, c, d in wires)
    return parse(f"(kicad_sch (lib_symbols {RESISTOR}) {parts} {drawn})")


def test_perimeter_rule_flags_a_route_skirting_the_parts():
    # R1 and R2 top pins (y 46.19) joined by a loop up to y 30, above both parts.
    loop = _sheet([(50, 46.19, 50, 30), (50, 30, 120, 30), (120, 30, 120, 46.19)])
    found = perimeter_paths(loop, DEFAULT_QUALITY_THRESHOLDS)
    assert found == [
        {"side": "top", "length_mm": 70.0, "from_mm": [50.0, 30.0], "to_mm": [120.0, 30.0]}
    ]


def test_perimeter_rule_ignores_wires_between_pins_and_short_edge_runs():
    # A straight wire along the parts' pin row stays inside the symbol core.
    straight = _sheet([(50, 53.81, 120, 53.81)])
    assert perimeter_paths(straight, DEFAULT_QUALITY_THRESHOLDS) == []
    # A loop above the parts that is shorter than 50.8 mm does not qualify.
    short = _sheet([(50, 46.19, 50, 40), (50, 40, 90, 40)])
    assert perimeter_paths(short, DEFAULT_QUALITY_THRESHOLDS) == []


def test_bends_merge_collinear_segments_and_skip_tees():
    segments = [
        ((0, 0), (10 * MM, 0)),
        ((10 * MM, 0), (20 * MM, 0)),  # straight continuation: no bend
        ((20 * MM, 0), (20 * MM, 10 * MM)),  # corner: one bend
        ((10 * MM, 0), (10 * MM, -5 * MM)),  # tee at (10, 0): no bend
    ]
    assert count_bends(segments) == 1


def test_hand_counted_rc_lowpass():
    """Counted by hand from the wire listing of this drawing (2026-11-14):
    IN 53.34 mm, 2 corners; OUT 44.45 mm, 0 corners (a tee at C1); REF 100.33 mm, 3 corners;
    REF runs 53.34 mm along the bottom below every part."""
    quality, _report = _candidate(
        "review_loop_corpus_v3_2026-11-12_qwen35_256k_run1", "rc_lowpass", "000"
    )
    assert quality["wire_length_mm"] == pytest.approx(198.12)
    assert quality["bends"] == 5
    assert [(p["side"], p["length_mm"]) for p in quality["perimeter_paths"]] == [("bottom", 53.34)]
    assert quality["rail_detour_mm"] == 0  # rc_lowpass asserts no rails


def test_october_rc_to_buffer_regression_reports_worse():
    """review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer 000 -> accepted 004: the wire
    grows 547 -> 880 mm and VPLUS/VMINUS are routed around the drawing."""
    run = "review_loop_corpus_2026-10-26_qwen_run1"
    before, report_before = _candidate(run, "rc_to_buffer", "000")
    after, report_after = _candidate(run, "rc_to_buffer", "004")
    # Hand-checked against the protected observer's independent counts.
    assert before["wire_length_mm"] == report_before["layout"]["observed_wire_length_mm"]
    assert after["wire_length_mm"] == report_after["layout"]["observed_wire_length_mm"]
    assert (before["bends"], after["bends"]) == (21, 29)
    # Hand-checked from the wire listing: VMINUS along the bottom and left, VPLUS on top.
    assert sorted((p["side"], p["length_mm"]) for p in after["perimeter_paths"]) == [
        ("bottom", 100.33),
        ("left", 66.04),
        ("top", 118.11),
    ]
    comparison = compare_quality(before, after)
    assert not comparison["not_worse"]
    assert {"wire_length_mm", "bends", "perimeter_paths", "rail_detour_mm"} <= set(
        comparison["worse"]
    )


def test_inverting_gain_field_fix_is_not_worse():
    run = "review_loop_corpus_v3_2026-10-31_qwen35_32k_run1"
    before, _ = _candidate(run, "inverting_gain", "001")
    after, _ = _candidate(run, "inverting_gain", "003")
    comparison = compare_quality(before, after)
    assert comparison["not_worse"]
    assert quality_overlay("PRESENTATION_FIX", comparison) is None


BASE = {
    "wire_length_mm": 200.0,
    "rail_detour_mm": 10.0,
    "bends": 10,
    "perimeter_paths": [],
    "perimeter_length_mm": 0,
    "text_clearance_mm": 1.5,
    "field_ownership_mm": 2.0,
    "page_offset": 0.1,
    "occupied_area_fraction": 0.2,
    "power_symbols": {"orphaned": [], "ambiguous": [], "redundant": [], "colliding": []},
}


@pytest.mark.parametrize(
    ("change", "worse"),
    [
        ({"wire_length_mm": 212.6}, set()),  # +12.6 mm: under the 12.7 mm floor
        ({"wire_length_mm": 212.8}, {"wire_length_mm"}),
        ({"rail_detour_mm": 15.0}, set()),  # +5.0 mm: under max(5.08, 1.0)
        ({"rail_detour_mm": 15.2}, {"rail_detour_mm"}),
        ({"bends": 12}, set()),
        ({"bends": 13}, {"bends"}),
        ({"text_clearance_mm": 0.9}, set()),
        ({"text_clearance_mm": 0.8}, {"text_clearance_mm"}),
        ({"field_ownership_mm": 0.8}, set()),
        ({"field_ownership_mm": 0.7}, {"field_ownership_mm"}),
        ({"page_offset": 0.13}, set()),
        ({"page_offset": 0.14}, {"page_offset"}),
        ({"perimeter_length_mm": 20.0}, set()),
        ({"perimeter_length_mm": 26.0}, {"perimeter_paths"}),
        (
            {"power_symbols": dict(BASE["power_symbols"], orphaned=["#PWR01"])},
            {"power_symbols_orphaned"},
        ),
    ],
)
def test_thresholds(change, worse):
    assert set(compare_quality(BASE, dict(BASE, **change))["worse"]) == worse


def test_power_symbol_count_alone_is_never_worse():
    before = dict(BASE, power_symbols=dict(BASE["power_symbols"], per_rail={"VCC": 1}))
    after = dict(BASE, power_symbols=dict(BASE["power_symbols"], per_rail={"VCC": 4}))
    assert compare_quality(before, after)["not_worse"]


def test_overlays():
    worse = {"not_worse": False, "worse": {"bends": {}}}
    assert quality_overlay("PRESENTATION_FIX", worse) == "LOCAL_FIX_ONLY"
    assert quality_overlay("FUNCTIONAL_REPAIR", worse) == "LOCAL_FIX_ONLY"
    assert quality_overlay("LAYOUT_CHANGE", worse) == "QUALITY_REGRESSION"
    assert quality_overlay("LAYOUT_CHANGE", None) is None


class Engine:
    """Each edit adds 50 mm of wire; `fixing` decides whether it also fixes field_locality."""

    def __init__(self, fixing: bool):
        self.fixing, self.applied = fixing, 0

    def _write(self, directory, text):
        path = directory / "project" / "test.kicad_sch"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def initial(self, directory):
        return self._write(directory, "candidate-0")

    def assess(self, schematic, directory):
        image = directory / "review.png"
        image.write_bytes(b"png")
        number = int(schematic.read_text().split("-")[1])
        fixed = self.fixing and number > 0
        checks = {
            "native_tools": "PASS",
            "erc": "PASS",
            "electrical_equivalence": "PASS",
            "field_locality": "PASS" if fixed or not self.fixing else "FAIL",
        }
        quality = dict(BASE, wire_length_mm=200.0 + 50 * number)
        return SchematicAssessment(schematic, [image], {"checks": checks, "quality": quality})

    def apply(self, schematic, directory, actions):
        self.applied += 1
        return self._write(directory, f"candidate-{self.applied}")


class Reviewer:
    identity = {"backend": "test"}

    def __init__(self, decisions):
        self.decisions, self.feedback = iter(decisions), []

    def review(self, assessment, feedback, record):
        self.feedback.append(feedback)
        decision = next(self.decisions)
        reply = {
            "base_revision": assessment.revision,
            "decision": decision,
            "issues": [],
            "actions": [],
            "rationale": "r",
        }
        if decision == "revise":
            reply["issues"] = ["crowded"]
            reply["actions"] = [
                {"operation": "move_symbols", "references": ["R1"], "dx_mm": 2.54, "dy_mm": 0}
            ]
        return json.dumps(reply)


def test_worse_neutral_edit_is_kept_and_labelled_by_default(tmp_path):
    result = run_schematic_review(
        Engine(fixing=False), Reviewer(["revise", "accept"]), tmp_path / "run"
    )
    outcome = result["iterations"][0]["edit_outcome"]
    assert outcome["disposition"] == "KEPT"
    assert outcome["primary_effect"] == "LAYOUT_CHANGE"
    assert outcome["quality_overlay"] == "QUALITY_REGRESSION"
    assert result["iterations"][0]["quality_delta"]["deltas"]["wire_length_mm"] == 50.0
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    assert result["status_levels"]["QUALITY_NOT_WORSE"]["status"] == "FAIL"
    assert result["quality_rollback"] is False
    fields = corpus_status_fields(result)
    assert fields["edit_overlays"] == {"QUALITY_REGRESSION": 1}
    assert fields["quality_worse"] == ["wire_length_mm"]
    assert fields["quality_delta"]["wire_length_mm"] == 50.0


def test_fix_that_makes_quality_worse_is_local_fix_only(tmp_path):
    result = run_schematic_review(
        Engine(fixing=True), Reviewer(["revise", "accept"]), tmp_path / "run"
    )
    outcome = result["iterations"][0]["edit_outcome"]
    assert outcome["primary_effect"] == "PRESENTATION_FIX"
    assert outcome["quality_overlay"] == "LOCAL_FIX_ONLY"


def test_enforcement_mode_rolls_back_a_worse_neutral_edit(tmp_path):
    reviewer = Reviewer(["revise", "accept"])
    result = run_schematic_review(
        Engine(fixing=False), reviewer, tmp_path / "run", quality_rollback=True
    )
    first = result["iterations"][0]
    assert first["edit_outcome"]["disposition"] == "ROLLED_BACK"
    assert first["edit_outcome"]["reason_class"] == "quality"
    assert "wire_length_mm worse" in reviewer.feedback[1]
    assert result["accepted_schematic"].endswith("000/project/test.kicad_sch")
    assert result["status_levels"]["QUALITY_NOT_WORSE"]["status"] == "PASS"


def test_enforcement_mode_keeps_a_worse_fix(tmp_path):
    result = run_schematic_review(
        Engine(fixing=True), Reviewer(["revise", "accept"]), tmp_path / "run", quality_rollback=True
    )
    assert result["iterations"][0]["edit_outcome"]["disposition"] == "KEPT"
    assert result["iterations"][0]["edit_outcome"]["quality_overlay"] == "LOCAL_FIX_ONLY"
