import json
import os
from pathlib import Path

import pytest

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.controller import (
    BudgetExceeded,
    ControllerError,
    NotAuthorized,
    Phase,
    UnsupportedTool,
    WorkflowController,
)
from ai_kicad.pivot.revisions import StaleRevision


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"


def initialized(tmp_path, budget=100):
    controller = WorkflowController(tmp_path / "workspace", operation_budget=budget)
    model = _model_from_fixture(FIXTURE)
    revision = controller.revisions.commit(
        model, {}, expected_revision=None, idempotency_key="initialize"
    )
    controller.set_revision(model.design_id, revision)
    return controller, revision


def transition(controller, revision, target, required_gate):
    controller.record_gate(required_gate, "PASS", revision)
    return controller.dispatch(
        "request_phase_transition",
        {
            "expected_revision": revision,
            "target_phase": target,
            "idempotency_key": f"transition-{target}",
        },
    )


def test_phase_and_task_visibility_has_small_schema_inventory(tmp_path):
    controller, _ = initialized(tmp_path)
    names = {tool["name"] for tool in controller.visible_tools()}
    assert "define_requirements" in names
    assert "prepare_fabrication_package" not in names
    scoped = controller.visible_tools({"define_requirements"})
    requirement_schema = next(
        item["inputSchema"] for item in scoped if item["name"] == "define_requirements"
    )
    assert requirement_schema["$id"].endswith("define_requirements.v1.json")
    assert requirement_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "description" in requirement_schema["properties"]
    assert {tool["name"] for tool in scoped} == {
        "create_checkpoint",
        "define_requirements",
        "get_capabilities",
        "get_design_state",
        "get_validation_report",
        "request_phase_transition",
        "rollback_to_checkpoint",
    }
    full_inventory = [
        {"name": tool.name, "inputSchema": tool.schema} for tool in controller.tools.values()
    ]
    assert len(json.dumps(scoped)) < len(json.dumps(full_inventory))


def test_unimplemented_domain_tool_is_explicitly_unsupported(tmp_path):
    controller, revision = initialized(tmp_path)
    state = controller._state()
    state["phase"] = Phase.CIRCUIT_DESIGN
    controller._save_state(state)
    before = controller._state()["operations"]
    with pytest.raises(UnsupportedTool, match="not implemented"):
        controller.dispatch(
            "edit_circuit_graph",
            {"expected_revision": revision, "idempotency_key": "unsupported"},
        )
    assert controller._state()["operations"] == before


def test_forged_hidden_call_and_stale_write_are_rejected(tmp_path):
    controller, revision = initialized(tmp_path)
    with pytest.raises(NotAuthorized):
        controller.dispatch(
            "prepare_fabrication_package",
            {"expected_revision": revision, "idempotency_key": "forged"},
        )
    assert controller.dispatch("get_design_state", {})["revision_id"] == revision
    with pytest.raises(StaleRevision):
        controller.dispatch(
            "define_requirements",
            {
                "description": "stale request",
                "expected_revision": "sha256:" + "1" * 64,
                "idempotency_key": "stale",
            },
        )


def test_phase_transitions_require_revision_bound_gate_and_backward_invalidates(tmp_path):
    controller, revision = initialized(tmp_path)
    with pytest.raises(NotAuthorized, match="requirements_explicit"):
        controller.dispatch(
            "request_phase_transition",
            {
                "expected_revision": revision,
                "target_phase": Phase.CIRCUIT_DESIGN,
                "idempotency_key": "missing-gate",
            },
        )
    transition(controller, revision, Phase.CIRCUIT_DESIGN, "requirements_explicit")
    transition(controller, revision, Phase.SCHEMATIC, "circuit_design_validated")
    with pytest.raises(NotAuthorized, match="schematic_visual_review"):
        transition(controller, revision, Phase.FOOTPRINTS, "schematic_validated")
    controller.record_gate("schematic_visual_review", "PASS", revision)
    transition(controller, revision, Phase.FOOTPRINTS, "schematic_validated")
    response = controller.dispatch(
        "request_phase_transition",
        {
            "expected_revision": revision,
            "target_phase": Phase.CIRCUIT_DESIGN,
            "idempotency_key": "backward",
        },
    )
    assert response["phase"] == Phase.CIRCUIT_DESIGN
    assert "schematic_validated" not in controller._state()["gates"]
    assert "schematic_visual_review" not in controller._state()["gates"]
    with pytest.raises(NotAuthorized, match="skip"):
        controller.dispatch(
            "request_phase_transition",
            {
                "expected_revision": revision,
                "target_phase": Phase.PCB_ROUTING,
                "idempotency_key": "skip",
            },
        )


def test_dry_run_idempotency_checkpoint_rollback_and_restart_handoff(tmp_path):
    controller, revision = initialized(tmp_path)
    before = controller._state()
    response = controller.dispatch(
        "create_checkpoint",
        {
            "expected_revision": revision,
            "name": "dry-run-checkpoint",
            "dry_run": True,
            "idempotency_key": "plan",
        },
    )
    assert not response["mutation_occurred"]
    assert controller._state()["revision_id"] == before["revision_id"]
    controller.dispatch(
        "create_checkpoint",
        {
            "expected_revision": revision,
            "name": "known-good",
            "idempotency_key": "checkpoint",
        },
    )
    handoff = controller.persist_handoff("continue schematic")
    restarted = WorkflowController(controller.workspace)
    assert restarted.persist_handoff("continue schematic")["revision_id"] == revision
    assert json.loads(restarted.handoff_path.read_text())["task"] == "continue schematic"
    assert handoff["revision_id"] == revision


def test_security_budget_replay_and_redaction(tmp_path):
    controller, revision = initialized(tmp_path, budget=2)
    with pytest.raises(ControllerError, match="escapes"):
        controller.confined_path("../outside")
    target = controller.workspace / "target"
    target.write_text("x")
    link = controller.workspace / "link"
    os.symlink(target, link)
    with pytest.raises(ControllerError, match="symlink"):
        controller.confined_path("link", must_exist=True)
    request = {
        "expected_revision": revision,
        "name": "security-test",
        "dry_run": True,
        "idempotency_key": "same",
        "api_token": "do-not-log",
    }
    # The always-on checkpoint tool rejects extra args, so use a test tool with
    # an explicit schema to prove redaction and replay without a real mutation.
    from ai_kicad.pivot.controller import Tool

    controller.tools["checkpoint_probe"] = Tool(
        "checkpoint_probe",
        None,
        True,
        {
            "type": "object",
            "properties": {
                "expected_revision": {"type": ["string", "null"]},
                "idempotency_key": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "api_token": {"type": "string"},
            },
            "required": ["expected_revision", "idempotency_key"],
        },
        lambda _: {"status": "probe"},
    )
    from ai_kicad.pivot.controller import PHASE_TOOLS, Phase

    PHASE_TOOLS[Phase.REQUIREMENTS].add("checkpoint_probe")
    try:
        first = controller.dispatch("checkpoint_probe", request)
        second = controller.dispatch("checkpoint_probe", request)
    finally:
        PHASE_TOOLS[Phase.REQUIREMENTS].remove("checkpoint_probe")
    assert first == second
    assert "do-not-log" not in controller.trace_path.read_text()
    controller.dispatch("get_design_state", {})
    with pytest.raises(BudgetExceeded):
        controller.dispatch("get_design_state", {})
