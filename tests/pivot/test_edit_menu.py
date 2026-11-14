"""The pre-checked edit menu and choose_edit (docs/pivot/REVIEWER_LOOP_SPEC.md R3)."""

import json
import os
from pathlib import Path
import shutil

import pytest

from ai_kicad.pivot.edit_menu import (
    MenuPolicy,
    Proposal,
    ValidationCache,
    build_menu,
    canonical_action,
)
from ai_kicad.pivot.schematic_review import (
    MenuReview,
    SchematicAssessment,
    SchematicReview,
    run_schematic_review,
)

PASSING = {"native_tools": "PASS", "erc": "PASS", "electrical_equivalence": "PASS"}


class Assessment:
    def __init__(self, revision, checks, **report):
        self.revision = revision
        self.report = {"checks": checks, **report}


def _base():
    return Assessment("sha256:base", dict(PASSING, field_locality="FAIL"))


def _proposal(n, edit_class="field_relocation", cost=None):
    return Proposal(
        edit_class=edit_class,
        action={"operation": "move_field", "reference": f"R{n}", "x_mm": float(n)},
        target={"reference": f"R{n}", "unit": 1, "field": "Value"},
        addresses=["field_locality"],
        cost=float(n if cost is None else cost),
        description=f"move R{n}",
    )


def _fixing(action):
    return Assessment("sha256:" + action["reference"], dict(PASSING, field_locality="PASS"))


def test_caps_per_class_and_in_total():
    proposals = [_proposal(n) for n in range(6)] + [
        _proposal(n, edit_class=f"class_{n % 4}") for n in range(10, 22)
    ]
    policy = MenuPolicy(geometric_proposals=40, native_validations=40)
    menu = build_menu(_base(), proposals, _fixing, policy, ValidationCache())
    classes = [entry["class"] for entry in menu["entries"]]
    assert len(classes) == 8
    assert max(classes.count(name) for name in set(classes)) <= 3


def test_geometric_screen_considers_at_most_the_cap():
    screened = []

    def precheck(proposal):
        screened.append(proposal)
        return True

    policy = MenuPolicy(per_class=8, total=8, geometric_proposals=12, native_validations=40)
    menu = build_menu(
        _base(),
        [_proposal(n) for n in range(30)],
        _fixing,
        policy,
        ValidationCache(),
        precheck=precheck,
    )
    assert len(screened) == 12
    assert menu["record"]["proposals_considered"] == 12
    assert menu["record"]["proposals_generated"] == 30


def test_native_validation_cap_shows_the_verified_subset():
    validated = []

    def validate(action):
        validated.append(action)
        return _fixing(action)

    policy = MenuPolicy(per_class=8, total=8, native_validations=2)
    menu = build_menu(
        _base(), [_proposal(n) for n in range(5)], validate, policy, ValidationCache()
    )
    assert len(validated) == 2 and len(menu["entries"]) == 2
    assert menu["record"]["budget_exhausted"] == "native validation limit reached"
    assert menu["record"]["native_validations"] == 2


def test_time_budget_stops_validation():
    ticks = iter([0.0, 0.0, 25.0, 25.0, 25.0, 25.0])
    menu = build_menu(
        _base(),
        [_proposal(n) for n in range(3)],
        _fixing,
        MenuPolicy(per_class=8),
        ValidationCache(),
        clock=lambda: next(ticks),
    )
    assert len(menu["entries"]) == 1
    assert menu["record"]["budget_exhausted"] == "menu time budget reached"


def test_only_natively_valid_fixing_entries_are_shown():
    outcomes = {
        "R0": Assessment("sha256:R0", dict(PASSING, erc="FAIL", field_locality="PASS")),
        "R1": Assessment("sha256:base", dict(PASSING, field_locality="FAIL")),
        "R2": Assessment("sha256:R2", dict(PASSING, field_locality="PASS", observed_layout="FAIL")),
        "R3": Assessment("sha256:R3", dict(PASSING, field_locality="FAIL", observed_layout="PASS")),
        "R4": Assessment("sha256:R4", dict(PASSING, field_locality="PASS", observed_layout="PASS")),
    }

    def validate(action):
        if action["reference"] == "R5":
            raise ValueError("no such field")
        return outcomes[action["reference"]]

    base = Assessment("sha256:base", dict(PASSING, field_locality="FAIL", observed_layout="PASS"))
    menu = build_menu(
        base,
        [_proposal(n) for n in range(6)],
        validate,
        MenuPolicy(per_class=8),
        ValidationCache(),
    )
    assert [entry["target"]["reference"] for entry in menu["entries"]] == ["R4"]
    reasons = {item["action"]["reference"]: item["reason"] for item in menu["record"]["rejected"]}
    assert reasons == {
        "R0": "breaks erc",
        "R1": "no change",
        "R2": "makes observed_layout fail",
        "R3": "resolves nothing a failing check reports",
        "R5": "editor refused: no such field",
    }
    entry = menu["entries"][0]
    assert entry["id"] == "field_relocation-1"
    assert entry["fixes"] == ["field_locality"]
    assert entry["target"] == {"reference": "R4", "unit": 1, "field": "Value"}
    assert entry["scratch_revision"] == "sha256:R4"
    assert "predicted_delta" in entry


def test_validations_are_cached_by_base_revision_and_action():
    calls = []

    def validate(action):
        calls.append(action)
        return _fixing(action)

    cache = ValidationCache(context="brief-v10")
    proposals = [_proposal(n) for n in range(3)]
    build_menu(_base(), proposals, validate, MenuPolicy(), cache)
    again = build_menu(_base(), proposals, validate, MenuPolicy(), cache)
    assert len(calls) == 3
    assert again["record"]["native_validations"] == 0 and again["record"]["cache_hits"] == 3
    other = Assessment("sha256:changed", dict(PASSING, field_locality="FAIL"))
    build_menu(other, proposals, validate, MenuPolicy(), cache)
    assert len(calls) == 6
    assert canonical_action({"b": 1.00001, "a": [2.0]}) == canonical_action({"a": [2.0], "b": 1.0})


class MenuEngine:
    """Candidate 000 fails field_locality; moving R1's value to x=5.08 fixes it."""

    def __init__(self):
        self.applied, self.menus = [], 0

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
        fixed = "x=5.08" in schematic.read_text()
        checks = dict(PASSING, field_locality="PASS" if fixed else "FAIL")
        return SchematicAssessment(schematic, [image], {"checks": checks})

    def apply(self, schematic, directory, actions):
        self.applied.append([action.model_dump(mode="json") for action in actions])
        text = schematic.read_text() + "".join(
            f";{a.operation} {getattr(a, 'reference', '')} x={getattr(a, 'x_mm', '')}"
            for a in actions
        )
        return self._write(directory, text)

    def edit_menu(self, assessment, directory, policy, cache, thresholds=None):
        from ai_kicad.pivot.schematic_review import ACTION_ADAPTER

        self.menus += 1
        counter = iter(range(100))

        def validate(action):
            step = directory / f"{next(counter):03d}"
            parsed = ACTION_ADAPTER.validate_python(action)
            return self.assess(self.apply(assessment.schematic, step, [parsed]), step, False)

        proposals = [
            Proposal(
                "field_relocation",
                {
                    "operation": "move_field",
                    "reference": "R1",
                    "unit": 1,
                    "field": "Value",
                    "x_mm": x,
                    "y_mm": 10.0,
                    "angle": 0,
                },
                {"reference": "R1", "unit": 1, "field": "Value"},
                ["field_locality"],
                x,
                f"move R1 Value to x={x}",
            )
            for x in (3.81, 5.08)
        ]
        return build_menu(assessment, proposals, validate, policy, cache)


class MenuReviewer:
    identity = {"backend": "test"}

    def __init__(self, replies, model=MenuReview):
        self.replies, self.inputs, self.review_model = iter(replies), [], model

    def review(self, assessment, feedback, record):
        self.inputs.append((assessment.menu, feedback))
        reply = {
            "base_revision": assessment.revision,
            "decision": "accept",
            "issues": [],
            "actions": [],
            "rationale": "r",
        }
        reply.update(next(self.replies))
        return json.dumps(reply)


CHOOSE = {
    "decision": "revise",
    "issues": ["R1 value detached"],
    "actions": [{"operation": "choose_edit", "id": "field_relocation-1"}],
}


def test_chosen_entry_matches_its_scratch_result(tmp_path):
    engine, reviewer = MenuEngine(), MenuReviewer([CHOOSE, {}])
    result = run_schematic_review(engine, reviewer, tmp_path / "run", edit_mode="menu_only")
    menu = reviewer.inputs[0][0]
    assert [entry["id"] for entry in menu["entries"]] == ["field_relocation-1"]
    assert menu["record"]["rejected"][0]["reason"] == "resolves nothing a failing check reports"
    first = result["iterations"][0]
    assert first["menu_choices"] == ["field_relocation-1"]
    assert first["menu_choice"]["matches_scratch"] is True
    assert first["edit_outcome"]["primary_effect"] == "PRESENTATION_FIX"
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
    assert (tmp_path / "run/menus/000/menu.json").is_file()
    assert first["menu"]["record"]["native_validations"] == 2


def test_menu_only_refuses_free_form_edits(tmp_path):
    move = {
        "operation": "move_field",
        "reference": "R1",
        "unit": 1,
        "field": "Value",
        "x_mm": 5.08,
        "y_mm": 10.0,
        "angle": 0,
    }
    free = {"decision": "revise", "issues": ["R1 value detached"], "actions": [move]}
    engine = MenuEngine()
    reviewer = MenuReviewer([free, {"decision": "needs_help"}], model=SchematicReview)
    result = run_schematic_review(engine, reviewer, tmp_path / "run", edit_mode="menu_only")
    first = result["iterations"][0]
    assert first["refusal"]["reason_class"] == "invalid_request"
    assert "free-form edits (move_field) are refused in menu-only mode" in reviewer.inputs[1][1]
    # Only the menu's two scratch validations ran the editor.
    assert len(engine.applied) == 2


def test_unknown_menu_id_is_refused(tmp_path):
    bad = dict(CHOOSE, actions=[{"operation": "choose_edit", "id": "field_relocation-9"}])
    reviewer = MenuReviewer([bad, {"decision": "needs_help"}])
    run_schematic_review(MenuEngine(), reviewer, tmp_path / "run", edit_mode="menu_only")
    assert "no edit-menu entry field_relocation-9" in reviewer.inputs[1][1]
    assert "offered ids are ['field_relocation-1']" in reviewer.inputs[1][1]


def test_free_form_mode_builds_no_menu(tmp_path):
    engine = MenuEngine()
    reviewer = MenuReviewer([{"decision": "needs_help"}], model=SchematicReview)
    run_schematic_review(engine, reviewer, tmp_path / "run")
    assert engine.menus == 0 and reviewer.inputs[0][0] is None


@pytest.mark.skipif(
    not os.environ.get("AI_KICAD_APPRUN"),
    reason="set AI_KICAD_APPRUN to the KiCad 10.0.6 AppRun",
)
def test_native_menu_for_a_detached_power_unit_label(tmp_path):
    """review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain 000: U1C's reference
    and value fail field_owner_association. Every menu entry must pass native ERC and
    netlist equivalence in scratch, and choosing one must reproduce its scratch result."""
    from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine

    root = Path(__file__).resolve().parents[2]
    source = (
        root
        / "fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1"
        / "inverting_gain/candidates/000/project/InvertingGain.kicad_sch"
    )

    class FromCandidate(NativeSchematicEngine):
        def initial(self, directory):
            (directory / "project").mkdir(parents=True)
            target = directory / "project" / source.name
            shutil.copyfile(source, target)
            return target

    engine = FromCandidate(
        json.loads((root / "fixtures/m2b/inverting_gain.json").read_text()),
        Path(os.environ["AI_KICAD_APPRUN"]),
        power_symbol_rails=True,
    )
    reviewer = MenuReviewer([CHOOSE, {"decision": "needs_help"}])
    result = run_schematic_review(engine, reviewer, tmp_path / "run", edit_mode="menu_only")
    menu = json.loads((tmp_path / "run/menus/000/menu.json").read_text())
    assert menu["entries"], menu["record"]
    record = menu["record"]
    assert record["native_validations"] <= 8 and record["proposals_considered"] <= 12
    assert record["kicad_invocations"] == 3 * record["native_validations"]
    assert record["seconds"] < 20
    assert record["budget_exhausted"] in (None, "native validation limit reached")
    scratch = tmp_path / "run/menus/000/scratch"
    by_revision = {}
    for assessment in scratch.glob("*/assessment.json"):
        report = json.loads(assessment.read_text())
        by_revision["sha256:" + report["schematic_sha256"]] = report["checks"]
    for entry in menu["entries"]:
        if entry["class"] == "field_relocation":
            assert entry["target"]["reference"] == "U1" and entry["target"]["unit"] == 3
        checks = by_revision[entry["scratch_revision"]]
        assert checks["erc"] == "PASS" and checks["electrical_equivalence"] == "PASS"
        assert entry["fixes"]
    first = result["iterations"][0]
    assert first["menu_choice"]["matches_scratch"] is True
    assert first["edit_outcome"]["disposition"] == "KEPT"


def _fake_ollama(monkeypatch, sent):
    from ai_kicad.pivot.schematic_review import OllamaSchematicReviewer

    def request(self, path, payload=None):
        if path == "/api/show":
            return {"capabilities": ["vision"]}
        if path == "/api/tags":
            return {"models": [{"name": "m", "digest": "d"}]}
        if path == "/api/version":
            return {"version": "0"}
        sent.append(payload)
        return {"message": {"content": "{}"}, "done_reason": "stop"}

    monkeypatch.setattr(OllamaSchematicReviewer, "_request", request)
    return OllamaSchematicReviewer


def test_menu_only_reviewer_sends_the_menu_and_a_choose_edit_schema(monkeypatch, tmp_path):
    sent = []
    reviewer_class = _fake_ollama(monkeypatch, sent)
    reviewer = reviewer_class("m", menu_only=True, max_actions=4)
    schematic = tmp_path / "test.kicad_sch"
    schematic.write_text("drawing")
    image = tmp_path / "page.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    assessment = SchematicAssessment(schematic, [image], {"checks": {}})
    assessment.menu = {
        "entries": [
            {
                "id": "field_relocation-1",
                "class": "field_relocation",
                "target": {"reference": "R1", "unit": 1, "field": "Value"},
                "description": "move R1 Value right of its body",
                "fixes": ["field_locality"],
                "predicted_delta": None,
                "action": {"operation": "move_field"},
                "scratch_revision": "sha256:x",
            }
        ]
    }
    reviewer.review(assessment, "", tmp_path / "record.json")
    request = sent[0]
    handoff = json.loads(request["messages"][1]["content"])
    assert handoff["edit_menu"][0]["id"] == "field_relocation-1"
    assert "action" not in handoff["edit_menu"][0]
    assert "Free-form edits are refused" in request["messages"][0]["content"]
    action_schema = request["format"]["$defs"]
    assert set(action_schema) == {"ChooseEdit"}
    assert reviewer.identity["menu_only"] is True


def test_free_form_reviewer_prompt_and_schema_are_unchanged(monkeypatch, tmp_path):
    sent = []
    reviewer = _fake_ollama(monkeypatch, sent)("m")
    assert "ChooseEdit" not in json.dumps(reviewer.review_model.model_json_schema())


def test_optional_entries_only_when_every_check_passes_and_at_most_two():
    quality = {
        "wire_length_mm": 500.0,
        "rail_detour_mm": 0,
        "bends": 10,
        "perimeter_paths": [],
        "perimeter_length_mm": 0,
        "text_clearance_mm": 1.0,
        "field_ownership_mm": 2.0,
        "page_offset": 0.1,
        "occupied_area_fraction": 0.2,
        "power_symbols": {},
    }
    base = Assessment("sha256:base", dict(PASSING), quality=quality)

    def shorter(action):
        return Assessment(
            "sha256:" + action["reference"],
            dict(PASSING),
            quality=dict(quality, wire_length_mm=400.0),
        )

    optional = [
        Proposal("rail_symbol", {"reference": f"N{n}"}, {"net": f"N{n}"}, [], n, "d")
        for n in range(4)
    ]
    menu = build_menu(base, optional, shorter, MenuPolicy(), ValidationCache())
    assert len(menu["entries"]) == 2
    assert all(
        entry["optional"] and entry["gains"] == ["wire_length_mm"] for entry in menu["entries"]
    )
    # With a failing check, entries that address nothing are not offered.
    failing = Assessment("sha256:base", dict(PASSING, field_locality="FAIL"), quality=quality)
    assert build_menu(failing, optional, shorter, MenuPolicy(), ValidationCache())["entries"] == []

    # An optional edit with no measured gain is not offered.
    def same(action):
        return Assessment("sha256:x" + action["reference"], dict(PASSING), quality=quality)

    menu = build_menu(base, optional, same, MenuPolicy(), ValidationCache())
    assert menu["entries"] == []
    assert menu["record"]["rejected"][0]["reason"] == "optional edit shows no measured quality gain"


def test_rail_proposals_name_the_failing_rails():
    from ai_kicad.pivot.edit_menu import rail_proposals

    report = {
        "checks": {"rail_presentation": "PASS", "power_symbol_clearance": "FAIL"},
        "intended_circuit": {"power_assertions": [{"net": "VCC"}, {"net": "REF"}]},
        "readability_witnesses": {},
    }
    proposals = rail_proposals(report)
    assert {(p.action["operation"], p.target["net"]) for p in proposals} == {
        ("use_power_symbols", "REF"),
        ("use_power_symbols", "VCC"),
        ("connect_rail", "REF"),
        ("connect_rail", "VCC"),
    }
    assert all(p.addresses == ["power_symbol_clearance"] for p in proposals)
    assert all("power_symbol_clearance" in p.must_pass for p in proposals)


class EmptyMenuEngine(MenuEngine):
    def assess(self, schematic, directory, render=True):
        image = directory / "review.png"
        image.write_bytes(b"png")
        return SchematicAssessment(schematic, [image], {"checks": dict(PASSING)})

    def edit_menu(self, assessment, directory, policy, cache, thresholds=None):
        self.menus += 1
        return {"entries": [], "record": {"native_validations": 0}}


def test_model_may_accept_with_an_empty_menu(tmp_path):
    reviewer = MenuReviewer([{}])
    result = run_schematic_review(
        EmptyMenuEngine(), reviewer, tmp_path / "run", edit_mode="menu_only"
    )
    assert reviewer.inputs[0][0]["entries"] == []
    assert result["status"] == "ACCEPTED_FOR_REVIEW"
