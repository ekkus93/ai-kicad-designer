"""Acceptance is joint, revision-bound and requires review of the edited images."""

import base64
import json

import pytest

from ai_kicad.pivot.schematic_review import (
    MoveField,
    OllamaSchematicReviewer,
    SchematicAssessment,
    TranslateSheet,
    run_schematic_review,
)
from ai_kicad.pivot.schematic_review_native import (
    NativeSchematicEngine,
    edit_schematic_text,
    field_collision_witnesses,
)
from ai_kicad.sexpr import one, parse


class Engine:
    def __init__(self, outcomes=(False, True), *, repeat=False):
        self.outcomes = outcomes
        self.repeat = repeat
        self.applied = 0
        self.assessed = []

    def initial(self, directory):
        project = directory / "project"
        project.mkdir()
        source = project / "test.kicad_sch"
        source.write_text("candidate-0")
        return source

    def assess(self, schematic, directory):
        self.assessed.append(schematic)
        image = directory / "render.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + schematic.read_bytes())
        passed = self.outcomes[min(len(self.assessed) - 1, len(self.outcomes) - 1)]
        return SchematicAssessment(
            schematic, [image], {"checks": {"electrical": "PASS" if passed else "FAIL"}}
        )

    def apply(self, schematic, directory, actions):
        self.applied += 1
        project = directory / "project"
        project.mkdir(parents=True)
        target = project / schematic.name
        target.write_text(schematic.read_text() if self.repeat else f"candidate-{self.applied}")
        return target


class Reviewer:
    identity = {"model": "test-reviewer"}

    def __init__(self, replies):
        self.replies = iter(replies)
        self.inputs = []

    def review(self, assessment, feedback, record):
        self.inputs.append((assessment.revision, assessment.images[0].read_bytes(), feedback))
        reply = {
            "base_revision": assessment.revision,
            "decision": "accept",
            "issues": [],
            "actions": [],
            "rationale": "Inspected image and checks.",
        }
        reply.update(next(self.replies))
        return json.dumps(reply)


REVISION = {
    "decision": "revise",
    "issues": ["overlap"],
    "actions": [{"operation": "regenerate_schematic"}],
}


def test_repairs_and_rereviews_new_image_before_acceptance(tmp_path):
    engine, reviewer = Engine(), Reviewer([REVISION, {}])
    result = run_schematic_review(engine, reviewer, tmp_path / "run")
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    assert len(engine.assessed) == 2
    assert reviewer.inputs[0][0] != reviewer.inputs[1][0]
    assert reviewer.inputs[0][1] != reviewer.inputs[1][1]
    assert len(result["iterations"]) == 2
    assert engine.assessed[0].read_text() == "candidate-0"
    assert result["accepted_schematic"].endswith("001/project/test.kicad_sch")
    assert result["human_electrical_review"] == "PENDING"


@pytest.mark.parametrize("reply", [{}, {"issues": ["still crowded"]}, REVISION])
def test_no_acceptance_with_failed_checks_or_pending_edits(tmp_path, reply):
    engine, reviewer = Engine((False,)), Reviewer([reply])
    result = run_schematic_review(engine, reviewer, tmp_path / "run", max_reviews=1)
    assert result["accepted_schematic"] is None
    assert result["status"] == "LIMIT_REACHED"
    assert engine.applied == 0


def test_stale_review_is_rejected_and_feedback_returned(tmp_path):
    reviewer = Reviewer([{"base_revision": "sha256:" + "0" * 64}, {}])
    result = run_schematic_review(Engine((True,)), reviewer, tmp_path / "run")
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    assert "stale model review" in reviewer.inputs[1][2]
    assert len(result["iterations"]) == 2


def test_regression_preserves_best_passing_candidate_without_accepting_it(tmp_path):
    result = run_schematic_review(
        Engine((True, False)),
        Reviewer([REVISION, {}]),
        tmp_path / "run",
        max_reviews=2,
    )
    assert result["accepted_schematic"] is None
    assert result["best_passing_schematic"].endswith("000/project/test.kicad_sch")


def test_repeated_candidate_stops_without_false_convergence(tmp_path):
    result = run_schematic_review(
        Engine(repeat=True),
        Reviewer([REVISION]),
        tmp_path / "run",
    )
    assert result["status"] == "NO_PROGRESS"
    assert result["accepted_schematic"] is None


def test_model_token_budget_cannot_be_overridden_by_acceptance(tmp_path):
    class ExpensiveReviewer(Reviewer):
        def review(self, assessment, feedback, record):
            raw = super().review(assessment, feedback, record)
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({"response": {"prompt_eval_count": 11}}))
            return raw

    result = run_schematic_review(
        Engine((True,)),
        ExpensiveReviewer([{}]),
        tmp_path / "run",
        max_model_tokens=10,
    )
    assert result["status"] == "LIMIT_REACHED"
    assert result["accepted_schematic"] is None
    assert result["model_tokens"] == 11


SCHEMATIC = """(kicad_sch (version 20250114)
 (lib_symbols (symbol "Device:R" (property "Reference" "R" (at 0 0 0))))
 (wire (pts (xy 10 20) (xy 20 20)))
 (junction (at 20 20)) (label "OUT" (at 20 20 0))
 (symbol (lib_id "Device:R") (at 20 30 90) (unit 1)
   (property "Reference" "R1" (at 25 30 0))
   (property "Value" "10k" (at 25 33 0))
   (pin "1" (uuid "abc"))))"""


def test_field_edit_preserves_library_and_electrical_geometry():
    moved = edit_schematic_text(
        SCHEMATIC,
        [
            MoveField(
                operation="move_field",
                reference="R1",
                unit=1,
                field="Value",
                x_mm=28.0,
                y_mm=34.0,
                angle=0,
            )
        ],
    )
    before, after = parse(SCHEMATIC), parse(moved)
    assert one(before, "lib_symbols") == one(after, "lib_symbols")
    assert one(before, "wire") == one(after, "wire")
    symbol = one(after, "symbol")
    assert one(symbol, "at") == ["at", "20", "30", "90"]
    assert one(symbol, "pin") == one(one(before, "symbol"), "pin")
    assert '"10k" (at 28.000000 34.000000 0)' in moved
    with pytest.raises(ValueError, match="existing reference"):
        edit_schematic_text(
            SCHEMATIC,
            [
                MoveField(
                    operation="move_field",
                    reference="R9",
                    unit=1,
                    field="Reference",
                    x_mm=1.0,
                    y_mm=2.0,
                    angle=0,
                )
            ],
        )


def test_invalid_native_edit_is_atomic(tmp_path):
    source = tmp_path / "source.kicad_sch"
    source.write_text(SCHEMATIC)
    engine = NativeSchematicEngine.__new__(NativeSchematicEngine)
    with pytest.raises(ValueError, match="existing reference"):
        engine.apply(
            source,
            tmp_path / "candidate",
            [
                MoveField(
                    operation="move_field",
                    reference="R999",
                    unit=1,
                    field="Value",
                    x_mm=20.0,
                    y_mm=20.0,
                    angle=0,
                )
            ],
        )
    assert source.read_text() == SCHEMATIC
    assert not (tmp_path / "candidate").exists()
    assert not list(tmp_path.glob(".review-edit-*"))


def test_field_collision_gate_includes_fields_on_same_symbol():
    upright = SCHEMATIC.replace("(at 25 30 0)", "(at 25 30 90)").replace(
        "(at 25 33 0)", "(at 25 33 90)"
    )
    assert not field_collision_witnesses(parse(upright))
    corrupted = upright.replace('"Value" "10k" (at 25 33 90)', '"Value" "10k" (at 25 30 90)')
    assert field_collision_witnesses(parse(corrupted)) == [["R1:1.Reference", "R1:1.Value"]]


def test_translation_moves_conductors_and_properties_but_not_library():
    source = SCHEMATIC.replace('"10k"', '"10k (at 5 6)"')
    moved = edit_schematic_text(
        source,
        [
            TranslateSheet(
                operation="translate_sheet",
                dx_mm=2.54,
                dy_mm=-2.54,
            )
        ],
    )
    before, after = parse(SCHEMATIC), parse(moved)
    assert one(before, "lib_symbols") == one(after, "lib_symbols")
    assert one(one(after, "junction"), "at")[1:] == ["22.540000", "17.460000"]
    assert one(one(after, "symbol"), "at")[1:] == ["22.540000", "27.460000", "90"]
    assert "(xy 12.540000 17.460000)" in moved
    assert '"Value" "10k (at 5 6)" (at 27.540000 30.460000 0)' in moved


def test_vision_adapter_sends_actual_images_and_schema(tmp_path, monkeypatch):
    calls = []

    def request(self, path, payload=None):
        calls.append((path, payload))
        return {
            "/api/show": {"capabilities": ["vision", "completion"]},
            "/api/tags": {"models": [{"name": "vision:test", "digest": "123"}]},
            "/api/version": {"version": "test"},
            "/api/chat": {"message": {"content": "{}"}, "done_reason": "stop"},
        }[path]

    monkeypatch.setattr(OllamaSchematicReviewer, "_request", request)
    reviewer = OllamaSchematicReviewer("vision:test")
    project = tmp_path / "project"
    project.mkdir()
    schematic, image = project / "test.kicad_sch", tmp_path / "preview.png"
    schematic.write_text(SCHEMATIC)
    image.write_bytes(b"\x89PNG\r\n\x1a\nimage-content")
    reviewer.review(
        SchematicAssessment(schematic, [image], {"checks": {"erc": "PASS"}}),
        "",
        tmp_path / "review.json",
    )
    payload = calls[-1][1]
    assert base64.b64decode(payload["messages"][1]["images"][0]) == image.read_bytes()
    assert payload["format"]["properties"]["base_revision"]
    assert payload["options"]["num_ctx"] == 16384
    log = json.loads((tmp_path / "review.json").read_text())
    assert log["images"][0]["sha256"]
    assert "image-content" not in json.dumps(log)


def test_vision_adapter_refuses_nonlocal_endpoint():
    with pytest.raises(ValueError, match="local Ollama"):
        OllamaSchematicReviewer("model", endpoint="https://example.com")
