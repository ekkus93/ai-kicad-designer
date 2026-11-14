"""R1 status levels and edit outcomes (docs/pivot/REVIEWER_LOOP_SPEC.md R1)."""

import json
from pathlib import Path

from ai_kicad.pivot.review_status import (
    LEVELS,
    broken_connectivity,
    corpus_status_fields,
    edit_outcome,
    ignored_erc_checks,
    run_primary_effect,
    status_levels,
)
from ai_kicad.pivot.schematic_review import SchematicAssessment, run_schematic_review

EXPERIMENTS = Path(__file__).resolve().parents[2] / "fixtures/pivot/experiments"
FULL = {
    "native_tools": "PASS",
    "erc": "PASS",
    "electrical_equivalence": "PASS",
    "observed_layout": "PASS",
    "field_locality": "PASS",
}


def _report(run: str, design: str, candidate: str) -> dict:
    return json.loads(
        (EXPERIMENTS / run / design / "candidates" / candidate / "assessment.json").read_text()
    )


def test_levels_use_their_named_checks():
    levels = status_levels({"checks": FULL}, model_verdict="accept", model_accepted=True)
    assert tuple(levels) == LEVELS
    assert levels["NATIVE_VALID"] == {"status": "PASS", "basis": {"native_tools": "PASS"}}
    assert levels["ELECTRICALLY_EQUIVALENT"]["basis"] == {
        "electrical_equivalence": "PASS",
        "erc": "PASS",
    }
    assert set(levels["PRESENTATION_PASS"]["basis"]) == {"observed_layout", "field_locality"}
    assert levels["MODEL_ACCEPTED"]["status"] == "PASS"
    for name in ("QUALITY_NOT_WORSE", "DESIGN_REQUIREMENTS_CHECKED", "HUMAN_REVIEWED"):
        assert levels[name]["status"] == "PENDING"


def test_erc_failure_alone_fails_electrical_equivalence():
    checks = dict(FULL, erc="FAIL")
    levels = status_levels({"checks": checks}, model_verdict=None, model_accepted=False)
    assert levels["ELECTRICALLY_EQUIVALENT"]["status"] == "FAIL"
    assert levels["MODEL_ACCEPTED"] == {"status": "PENDING", "basis": "not reviewed"}


def test_missing_evidence_is_pending_not_pass():
    levels = status_levels(
        {"checks": {"native_tools": "PASS", "erc": "PASS"}},
        model_verdict="revise",
        model_accepted=False,
    )
    assert levels["ELECTRICALLY_EQUIVALENT"]["status"] == "PENDING"
    assert levels["ELECTRICALLY_EQUIVALENT"]["basis"]["electrical_equivalence"] == "MISSING"
    assert levels["PRESENTATION_PASS"]["status"] == "PENDING"
    assert levels["MODEL_ACCEPTED"] == {"status": "FAIL", "basis": {"decision": "revise"}}
    assert status_levels({}, model_verdict=None, model_accepted=False)["NATIVE_VALID"][
        "status"
    ] == ("PENDING")


def test_historical_rc_corrupted_regeneration_is_a_functional_repair():
    run = "schematic_review_loop_2026-10-25_run1"
    before, after = _report(run, "rc_corrupted", "000"), _report(run, "rc_corrupted", "001")
    outcome = edit_outcome(before, after, disposition="KEPT")
    assert outcome == {
        "primary_effect": "FUNCTIONAL_REPAIR",
        "quality_overlay": None,
        "disposition": "KEPT",
        "reason_class": None,
    }


def test_historical_inverting_gain_field_move_is_a_presentation_fix():
    run = "review_loop_corpus_v3_2026-10-31_qwen35_32k_run1"
    first = edit_outcome(
        _report(run, "inverting_gain", "000"),
        _report(run, "inverting_gain", "001"),
        disposition="KEPT",
    )
    fixing = edit_outcome(
        _report(run, "inverting_gain", "001"),
        _report(run, "inverting_gain", "003"),
        disposition="KEPT",
    )
    assert first["primary_effect"] == "LAYOUT_CHANGE"
    assert fixing["primary_effect"] == "PRESENTATION_FIX"
    assert run_primary_effect([first, fixing]) == "PRESENTATION_FIX"


def test_historical_noninverting_gain_merge_is_rolled_back_for_connectivity():
    run = "review_loop_corpus_2026-10-27_qwen35_256k_run1"
    before = _report(run, "noninverting_gain", "003")
    after = _report(run, "noninverting_gain", "004")
    broken = broken_connectivity(before, after)
    assert broken == ["electrical_equivalence", "erc", "native_tools"]
    outcome = edit_outcome(before, after, disposition="ROLLED_BACK", reason_class="connectivity")
    assert outcome["primary_effect"] is None and outcome["reason_class"] == "connectivity"
    assert ignored_erc_checks(before) == [
        "footprint_filter",
        "four_way_junction",
        "simulation_model_issue",
        "single_global_label",
    ]


class Engine:
    """Candidate 000 fails field_locality; each edit fixes it; ERC ignores one category."""

    def __init__(self):
        self.applied = 0

    def _write(self, directory: Path, text: str) -> Path:
        path = directory / "project" / "test.kicad_sch"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def initial(self, directory):
        return self._write(directory, "candidate-0")

    def assess(self, schematic, directory):
        image = directory / "review.png"
        image.write_bytes(b"png")
        checks = dict(FULL, field_locality="PASS" if self.applied else "FAIL")
        erc = {"ignored_checks": [{"key": "four_way_junction", "description": "x"}]}
        return SchematicAssessment(schematic, [image], {"checks": checks, "erc": erc})

    def apply(self, schematic, directory, actions):
        self.applied += 1
        return self._write(directory, f"candidate-{self.applied}")


class Reviewer:
    identity = {"backend": "test"}

    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def review(self, assessment, feedback, record):
        decision = next(self.decisions)
        reply = {
            "base_revision": assessment.revision,
            "decision": decision,
            "issues": [],
            "actions": [],
            "rationale": "r",
        }
        if decision == "revise":
            reply["issues"] = ["detached value"]
            reply["actions"] = [
                {
                    "operation": "move_field",
                    "reference": "R1",
                    "field": "Value",
                    "unit": 1,
                    "angle": 0,
                    "x_mm": 1,
                    "y_mm": 2,
                }
            ]
        return json.dumps(reply)


def test_loop_result_reports_levels_for_current_initial_and_best(tmp_path):
    result = run_schematic_review(Engine(), Reviewer(["revise", "accept"]), tmp_path / "run")
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    reported = result["candidates_reported"]
    assert result["status_levels"] == reported["current"]["levels"]
    assert reported["current"]["schematic"] == "candidates/001/project/test.kicad_sch"
    assert reported["initial"]["schematic"] == "candidates/000/project/test.kicad_sch"
    assert reported["best_passing"]["revision"] == reported["current"]["revision"]
    assert result["status_levels"]["MODEL_ACCEPTED"]["status"] == "PASS"
    assert result["status_levels"]["PRESENTATION_PASS"]["status"] == "PASS"
    initial = reported["initial"]["levels"]
    assert initial["PRESENTATION_PASS"]["status"] == "FAIL"
    assert initial["MODEL_ACCEPTED"] == {"status": "FAIL", "basis": {"decision": "revise"}}
    assert result["iterations"][0]["edit_outcome"]["primary_effect"] == "PRESENTATION_FIX"
    assert result["run_primary_effect"] == "PRESENTATION_FIX"
    assert result["erc_ignored_checks"] == ["four_way_junction"]
    assert result["accepted_for_review_implies"] == [
        "ELECTRICALLY_EQUIVALENT",
        "PRESENTATION_PASS",
        "MODEL_ACCEPTED",
    ]


def test_unaccepted_run_describes_the_last_committed_candidate(tmp_path):
    result = run_schematic_review(Engine(), Reviewer(["needs_help"]), tmp_path / "run")
    assert result["status"] == "NEEDS_HELP"
    current = result["candidates_reported"]["current"]
    assert current["schematic"] == "candidates/000/project/test.kicad_sch"
    assert result["status_levels"]["MODEL_ACCEPTED"]["status"] == "FAIL"
    assert result["candidates_reported"]["best_passing"] is None
    assert result["run_primary_effect"] is None


def test_corpus_summary_fields_compress_levels_and_count_dispositions(tmp_path):
    result = run_schematic_review(Engine(), Reviewer(["revise", "accept"]), tmp_path / "run")
    fields = corpus_status_fields(result)
    assert fields["status_levels"]["MODEL_ACCEPTED"] == "PASS"
    assert fields["status_levels"]["HUMAN_REVIEWED"] == "PENDING"
    assert fields["run_primary_effect"] == "PRESENTATION_FIX"
    assert fields["edit_dispositions"] == {"KEPT": 1}
    assert corpus_status_fields({"status": "TOOL_ERROR", "iterations": []})["status_levels"] is None
