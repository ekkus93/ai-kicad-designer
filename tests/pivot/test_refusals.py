"""Structured refusals, equivalent requests and batch rules (REVIEWER_LOOP_SPEC.md R4)."""

import json
import os
from pathlib import Path
import shutil

import pytest

from ai_kicad.pivot.edit_menu import (
    classify_editor_error,
    equivalent_action,
    equivalent_edit,
)
from ai_kicad.pivot.schematic_review import (
    MenuReviewBatch,
    SchematicAssessment,
    SchematicReview,
    SchematicReviewBatch,
    run_schematic_review,
)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "fixtures/pivot/experiments"
PASSING = {"native_tools": "PASS", "erc": "PASS", "electrical_equivalence": "PASS"}
BASE_QUALITY = {
    "wire_length_mm": 200.0,
    "rail_detour_mm": 0,
    "bends": 4,
    "perimeter_paths": [],
    "perimeter_length_mm": 0,
    "text_clearance_mm": 1.0,
    "field_ownership_mm": 2.0,
    "page_offset": 0.1,
    "occupied_area_fraction": 0.2,
    "power_symbols": {},
}


def move(reference="R1", x=5.08, y=10.0, unit=1):
    return {
        "operation": "move_field",
        "reference": reference,
        "unit": unit,
        "field": "Value",
        "x_mm": x,
        "y_mm": y,
        "angle": 0,
    }


class Engine:
    """Text drawings. `x=99` moves are no-ops, `BREAK` moves break ERC, rail edits on REF
    cannot be routed, and every edit adds 50 mm of wire. R1's value at x=5.08 fixes
    field_locality."""

    def __init__(self, menu=None):
        self.applied, self.menu = [], menu

    def _write(self, directory, text):
        path = directory / "project" / "test.kicad_sch"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def initial(self, directory):
        return self._write(directory, "start")

    def assess(self, schematic, directory, render=True):
        image = directory / "review.png"
        image.write_bytes(b"png")
        text = schematic.read_text()
        checks = dict(
            PASSING,
            erc="FAIL" if "BREAK" in text else "PASS",
            field_locality="PASS" if "R1@5.08" in text else "FAIL",
        )
        quality = dict(BASE_QUALITY, wire_length_mm=200.0 + 50 * text.count(";"))
        return SchematicAssessment(schematic, [image], {"checks": checks, "quality": quality})

    def apply(self, schematic, directory, actions):
        self.applied.append([a.model_dump(mode="json") for a in actions])
        text = schematic.read_text()
        for action in actions:
            if action.operation == "connect_rail":
                raise ValueError(
                    "no obstacle-free native wire route joins the remaining REF groups"
                )
            if action.operation == "move_field" and action.x_mm == 99:
                raise ValueError(
                    f"move_field for {action.reference}.Value made no change; "
                    "choose a different position"
                )
            if action.operation == "move_field" and action.x_mm == 98:
                return self._write(directory, text)
            tag = getattr(action, "reference", None) or "sheet"
            text += f";{tag}@{getattr(action, 'x_mm', '')}"
            if action.operation == "move_field" and action.reference == "BREAK":
                text += " BREAK"
        return self._write(directory, text)

    def edit_menu(self, assessment, directory, policy, cache, thresholds=None):
        return self.menu or {"entries": [], "record": {}}


def entry(n, action):
    return {
        "id": f"field_relocation-{n}",
        "class": "field_relocation",
        "target": {"reference": action["reference"], "unit": 1, "field": "Value"},
        "description": f"move {action['reference']} value to x={action['x_mm']}",
        "fixes": ["field_locality"],
        "gains": [],
        "predicted_delta": None,
        "action": action,
        "scratch_revision": "sha256:x",
    }


MENU = {
    "entries": [entry(n, move(x=x)) for n, x in ((1, 5.08), (2, 7.62), (3, 12.7), (4, 15.24))],
    "record": {},
}


class Reviewer:
    identity = {"backend": "test"}

    def __init__(self, replies, model=SchematicReview):
        self.replies, self.feedback, self.review_model = list(replies), [], model

    def review(self, assessment, feedback, record):
        self.feedback.append(feedback)
        reply = self.replies.pop(0)
        if callable(reply):
            reply = reply(feedback)
        return json.dumps(
            {
                "base_revision": assessment.revision,
                "issues": ["layout"] if reply.get("actions") else [],
                "rationale": "r",
                "decision": "revise" if reply.get("actions") else "needs_help",
                "actions": [],
                **reply,
            }
        )


def run(tmp_path, replies, *, model=SchematicReview, menu=MENU, **options):
    engine, reviewer = Engine(menu), Reviewer(replies, model)
    options.setdefault("edit_mode", "free_form_experimental")
    result = run_schematic_review(
        engine,
        reviewer,
        tmp_path / "run",
        structured_refusals=True,
        refusal_grid_mm=1.27,
        **options,
    )
    return engine, reviewer, result


def refusal(feedback):
    return json.loads(feedback)["refusal"]


STOP = {"decision": "needs_help"}


def test_connectivity_refusal_reports_checks_and_alternatives(tmp_path):
    _engine, reviewer, result = run(tmp_path, [{"actions": [move("BREAK")]}, STOP])
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "connectivity"
    assert item["evidence"] == {"erc": {"before": "PASS", "after": "FAIL"}}
    assert 1 <= len(item["alternatives"]) <= 3
    assert item["alternatives"][0]["action"]["operation"] == "move_field"
    assert result["iterations"][0]["refusal"] == item


def test_no_change_refusal(tmp_path):
    _engine, reviewer, _ = run(tmp_path, [{"actions": [move(x=98)]}, STOP])
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "no_change"
    assert item["evidence"]["revision"].startswith("sha256:")


def test_quality_refusal_in_enforcement_mode(tmp_path):
    _engine, reviewer, _ = run(
        tmp_path, [{"actions": [move("R2", x=40.0)]}, STOP], quality_rollback=True
    )
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "quality"
    assert item["evidence"]["wire_length_mm"] == {"before": 200.0, "after": 250.0}


def test_infeasible_route_refusal(tmp_path):
    rail = {"operation": "connect_rail", "net": "REF", "replace_existing": True}
    _engine, reviewer, _ = run(tmp_path, [{"actions": [rail]}, STOP])
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "infeasible_route"
    assert "no obstacle-free" in item["evidence"]["editor"]


def test_invalid_request_refusal_in_menu_only_mode(tmp_path):
    _engine, reviewer, _ = run(tmp_path, [{"actions": [move()]}, STOP], edit_mode="menu_only")
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "invalid_request"
    assert item["evidence"]["offered"] == [f"field_relocation-{n}" for n in range(1, 5)]
    # In menu-only mode alternatives are menu IDs, without raw actions.
    assert item["alternatives"] and "action" not in item["alternatives"][0]


def test_repeat_refusal_stops_without_running_the_editor(tmp_path):
    engine, _reviewer, result = run(
        tmp_path, [{"actions": [move(x=99)]}, {"actions": [move(x=99)]}]
    )
    assert result["status"] == "NO_PROGRESS"
    second = result["iterations"][1]["refusal"]
    assert second["reason_class"] == "repeat"
    assert "made no change" in second["evidence"]["earlier"]
    assert len(engine.applied) == 1


def test_budget_exhausted_notice(tmp_path):
    menu = dict(MENU, record={"budget_exhausted": "native validation limit reached"})
    _engine, _reviewer, result = run(tmp_path, [STOP], menu=menu)
    notice = result["iterations"][0]["menu_notice"]
    assert notice["reason_class"] == "budget_exhausted"
    assert "native validation limit reached" in notice["message"]


def test_equivalent_coordinate_edit_on_the_same_drawing_is_a_repeat(tmp_path):
    engine, _reviewer, result = run(
        tmp_path, [{"actions": [move(x=99)]}, {"actions": [move(x=99 + 1.27)]}]
    )
    assert result["iterations"][1]["refusal"]["reason_class"] == "repeat"
    assert len(engine.applied) == 1
    # Two grid steps away is a different request, and the editor runs.
    engine, _reviewer, result = run(
        tmp_path / "b", [{"actions": [move(x=99)]}, {"actions": [move(x=99 - 2.54)]}, STOP]
    )
    assert len(engine.applied) == 2


def test_without_the_v10_grid_only_identical_edits_repeat(tmp_path):
    engine, reviewer = (
        Engine(MENU),
        Reviewer([{"actions": [move(x=99)]}, {"actions": [move(x=100.27)]}, STOP]),
    )
    run_schematic_review(engine, reviewer, tmp_path / "run")
    assert len(engine.applied) == 2
    # Free-form briefs keep their plain-text feedback.
    assert reviewer.feedback[1].startswith("edit refused: move_field for R1.Value made no change")


def test_equivalence_rules():
    assert equivalent_action(move(x=5.08), move(x=6.35), 1.27)
    assert not equivalent_action(move(x=5.08), move(x=7.62), 1.27)
    assert not equivalent_action(move(x=5.08), move(x=5.08, unit=2), 1.27)
    rail = {"operation": "connect_rail", "net": "REF", "replace_existing": True}
    assert equivalent_action(rail, dict(rail), 1.27)
    assert not equivalent_action(rail, dict(rail, replace_existing=False), 1.27)
    assert not equivalent_action(rail, dict(rail, net="VCC"), 1.27)
    units = {
        "operation": "move_units",
        "units": [{"reference": "U1", "unit": 3}],
        "dx_mm": 1.27,
        "dy_mm": 0,
    }
    assert equivalent_action(units, dict(units, dx_mm=2.54), 1.27)
    assert not equivalent_action(units, dict(units, units=[{"reference": "U1", "unit": 1}]), 1.27)
    assert not equivalent_edit([move()], [move(), move()], 1.27)
    assert classify_editor_error("connect_rail made no change; VCC is wired") == "no_change"
    assert classify_editor_error("no clear position for a VPLUS power symbol") == "infeasible_route"
    assert classify_editor_error("move_field must identify one existing reference/unit") == (
        "invalid_request"
    )


def test_independent_batch_commits_each_safe_edit(tmp_path):
    batch = {"actions": [move(x=5.08), move("BREAK")]}
    _engine, reviewer, result = run(
        tmp_path, [batch, STOP], model=SchematicReviewBatch, max_reviews=3
    )
    first = result["iterations"][0]
    assert first["applied_actions"] == [1] and first["bundle"] is False
    feedback = json.loads(reviewer.feedback[1])
    assert feedback["applied_actions"] == [1]
    assert feedback["refusal"]["reason_class"] == "connectivity"
    assert result["iterations"][1]["revision"] != first["revision"]


def test_dependent_bundle_commits_all_or_none(tmp_path):
    menu = {
        "entries": [entry(1, move(x=5.08)), entry(2, move("BREAK"))],
        "record": {},
    }
    bundle = {
        "bundle": True,
        "actions": [
            {"operation": "choose_edit", "id": "field_relocation-1"},
            {"operation": "choose_edit", "id": "field_relocation-2"},
        ],
    }
    _engine, reviewer, result = run(
        tmp_path, [bundle, STOP], model=MenuReviewBatch, menu=menu, edit_mode="menu_only"
    )
    first = result["iterations"][0]
    assert first["applied_actions"] == [] and first["bundle"] is True
    assert [o["disposition"] for o in first["edit_outcomes"]] == ["ROLLED_BACK", "ROLLED_BACK"]
    assert refusal(reviewer.feedback[1])["reason_class"] == "connectivity"
    # Nothing was committed: the next review sees the same drawing.
    assert result["iterations"][1]["revision"] == first["revision"]


KICAD = pytest.mark.skipif(
    not os.environ.get("AI_KICAD_APPRUN"),
    reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun",
)


def _replay(tmp_path, run, design, candidate, replies, **flags):
    """Start the loop from a historical candidate with a scripted reviewer."""
    from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine

    source = next(
        (EXPERIMENTS / run / design / "candidates" / candidate / "project").glob("*.kicad_sch")
    )
    name = json.loads((ROOT / f"fixtures/m2b/{design}.json").read_text())

    class FromCandidate(NativeSchematicEngine):
        def initial(self, directory):
            (directory / "project").mkdir(parents=True)
            target = directory / "project" / source.name
            shutil.copyfile(source, target)
            return target

    engine = FromCandidate(
        name, Path(os.environ["AI_KICAD_APPRUN"]), structured_refusals=True, **flags
    )
    reviewer = Reviewer(replies)
    result = run_schematic_review(
        engine,
        reviewer,
        tmp_path / "run",
        edit_mode="free_form_experimental",
        structured_refusals=True,
        refusal_grid_mm=1.27,
    )
    return reviewer, result


LED = ("review_loop_corpus_v3_2026-10-31_qwen35_32k_run2", "led_reverse_supply", "003")
LED_REVISION = "sha256:7a3ad94a430b902fcd2fb169fa68e7fa45895428f8bbc70ecd34597d5a978903"
NONINVERTING = ("review_loop_corpus_2026-10-27_qwen35_256k_run1", "noninverting_gain", "003")
NONINVERTING_REVISION = "sha256:3242f0507e645255d05d3c6a296738ce1408f1aa2d8e139a0b851562c1fbd3ca"
# The logged October reply that the model repeated until the run stopped.
J1_NO_OP = {
    "operation": "move_field",
    "reference": "J1",
    "unit": 1,
    "field": "Value",
    "x_mm": 45.37,
    "y_mm": 27.725,
    "angle": 0,
}


@KICAD
def test_replay_led_reverse_supply_no_op_stops_after_one_refusal_with_an_alternative(tmp_path):
    reviewer, result = _replay(
        tmp_path, *LED, [{"actions": [J1_NO_OP]}, {"actions": [J1_NO_OP]}], power_symbol_rails=True
    )
    first, second = result["iterations"][:2]
    assert first["revision"] == LED_REVISION
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "no_change"
    assert 1 <= len(item["alternatives"]) <= 3
    assert all(alt["action"]["reference"] == "J1" for alt in item["alternatives"])
    assert second["refusal"]["reason_class"] == "repeat"
    assert result["status"] == "NO_PROGRESS" and len(result["iterations"]) == 2


@KICAD
def test_replay_wrong_unit_request_is_an_invalid_request(tmp_path):
    reviewer, result = _replay(
        tmp_path,
        *LED,
        [{"actions": [dict(J1_NO_OP, unit=2, x_mm=50.8)]}, STOP],
        power_symbol_rails=True,
    )
    assert result["iterations"][0]["revision"] == LED_REVISION
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "invalid_request"
    assert "must identify one existing reference/unit" in item["evidence"]["editor"]
    assert result["status"] == "NEEDS_HELP"


@KICAD
def test_replay_zero_length_route_is_an_invalid_request(tmp_path):
    route = {
        "operation": "add_wire_path",
        "net": "REF",
        "from_ref": "C2",
        "from_pin": "1",
        "to_ref": "C1",
        "to_pin": "2",
        "waypoints": [{"x_mm": 125.73, "y_mm": 93.98}],
    }
    reviewer, result = _replay(
        tmp_path, *NONINVERTING, [{"actions": [route]}, STOP], power_symbol_rails=True
    )
    assert result["iterations"][0]["revision"] == NONINVERTING_REVISION
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "invalid_request"
    assert "repeats waypoint" in item["evidence"]["editor"]


@KICAD
def test_replay_unsafe_net_merge_is_rolled_back_and_an_alternative_recovers(tmp_path):
    """The 2026-10-27 move_symbols(U1, dx -1.27 mm) merged REF and VMINUS. It is rolled back
    with the failing checks; the scripted reviewer then takes the first alternative."""
    merge = {"operation": "move_symbols", "references": ["U1"], "dx_mm": -1.27, "dy_mm": 0}

    def take_alternative(feedback):
        options = refusal(feedback)["alternatives"]
        return {"actions": [options[0]["action"]]} if options else STOP

    reviewer, result = _replay(
        tmp_path,
        *NONINVERTING,
        [{"actions": [merge]}, take_alternative, STOP],
        power_symbol_rails=True,
    )
    first = result["iterations"][0]
    assert first["revision"] == NONINVERTING_REVISION
    item = refusal(reviewer.feedback[1])
    assert item["reason_class"] == "connectivity"
    assert item["evidence"]["electrical_equivalence"] == {"before": "PASS", "after": "FAIL"}
    if item["alternatives"]:
        assert result["iterations"][1]["edit_outcome"]["disposition"] == "KEPT"
