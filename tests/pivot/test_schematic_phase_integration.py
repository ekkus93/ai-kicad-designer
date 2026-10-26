"""The schematic image-review loop as a revision-bound SCHEMATIC-phase controller tool."""

import json
from pathlib import Path

import pytest

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.controller import NotAuthorized, Phase, WorkflowController
from ai_kicad.pivot.mcp_server import MCPServer
from ai_kicad.pivot.revisions import StaleRevision

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"


class FakeReview:
    timeout_seconds = 5.0

    def __init__(self, status: str, accepted: str | None = None):
        self.status, self.accepted, self.calls = status, accepted, []

    def review(self, design: Path, output: Path) -> dict:
        self.calls.append((design, output))
        output.mkdir(parents=True)
        result = {
            "status": self.status,
            "reason": "fake loop",
            "accepted_schematic": self.accepted,
        }
        (output / "result.json").write_text(json.dumps(result))
        return result


def controller_in_schematic(tmp_path, service) -> tuple[WorkflowController, str]:
    controller = WorkflowController(tmp_path / "workspace", schematic_review=service)
    model = _model_from_fixture(FIXTURE)
    revision = controller.revisions.commit(
        model, {}, expected_revision=None, idempotency_key="initialize"
    )
    controller.set_revision(model.design_id, revision)
    state = controller._state()
    state["phase"] = Phase.SCHEMATIC
    controller._save_state(state)
    (controller.workspace / "design.json").write_text("{}")
    return controller, revision


def review(controller, revision, output="review-1", key="review-1"):
    return controller.dispatch(
        "review_schematic",
        {
            "design": "design.json",
            "output": output,
            "expected_revision": revision,
            "idempotency_key": key,
        },
    )


def to_footprints(controller, revision):
    return controller.dispatch(
        "request_phase_transition",
        {
            "expected_revision": revision,
            "target_phase": Phase.FOOTPRINTS,
            "idempotency_key": f"footprints-{len(controller._state()['idempotency'])}",
        },
    )


def test_accepted_loop_records_revision_bound_visual_gate_and_unlocks_footprints(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/002/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    response = review(controller, revision)
    gate = controller._state()["gates"]["schematic_visual_review"]
    assert response["status"] == "PASS"
    assert gate["status"] == "PASS" and gate["revision_id"] == revision
    assert gate["accepted_schematic"].endswith("review-1/candidates/002/project/Design.kicad_sch")
    assert len(service.calls) == 1
    controller.record_gate("schematic_validated", "PASS", revision)
    assert to_footprints(controller, revision)["phase"] == Phase.FOOTPRINTS


@pytest.mark.parametrize("status", ["NEEDS_HELP", "NO_PROGRESS", "LIMIT_REACHED", "TOOL_ERROR"])
def test_unaccepted_loop_blocks_downstream_even_with_electrical_gate(tmp_path, status):
    controller, revision = controller_in_schematic(tmp_path, FakeReview(status))
    assert review(controller, revision)["status"] == "FAIL"
    controller.record_gate("schematic_validated", "PASS", revision)
    with pytest.raises(NotAuthorized, match="schematic_visual_review"):
        to_footprints(controller, revision)
    assert controller._state()["unresolved_issues"][-1]["gate"] == "schematic_visual_review"


def test_electrical_gate_is_still_required_after_visual_acceptance(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    review(controller, revision)
    with pytest.raises(NotAuthorized, match="schematic_validated"):
        to_footprints(controller, revision)


def test_visual_gate_from_previous_revision_does_not_authorize_transition(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    review(controller, revision)
    newer = "sha256:" + "2" * 64
    controller.set_revision(controller._state()["design_id"], newer)
    controller.record_gate("schematic_validated", "PASS", newer)
    with pytest.raises(NotAuthorized, match="schematic_visual_review"):
        to_footprints(controller, newer)


def test_review_rejects_stale_revision_and_is_hidden_outside_schematic_phase(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    with pytest.raises(StaleRevision):
        review(controller, "sha256:" + "1" * 64)
    state = controller._state()
    state["phase"] = Phase.CIRCUIT_DESIGN
    controller._save_state(state)
    assert "review_schematic" not in {tool["name"] for tool in controller.visible_tools()}
    with pytest.raises(NotAuthorized):
        review(controller, revision, output="review-2", key="review-2")
    assert service.calls == []


def test_review_output_must_be_new_and_inside_workspace(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    (controller.workspace / "taken").mkdir()
    for output in ("taken", "../escape"):
        with pytest.raises(Exception, match="already exists|escapes"):
            review(controller, revision, output=output, key=f"review-{output}")
    assert service.calls == []


def test_review_tool_is_listed_and_callable_through_mcp(tmp_path):
    service = FakeReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    server = MCPServer(controller)
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert "review_schematic" in {tool["name"] for tool in listed["result"]["tools"]}
    called = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "review_schematic",
                "arguments": {
                    "design": "design.json",
                    "output": "review-mcp",
                    "expected_revision": revision,
                    "idempotency_key": "review-mcp",
                },
            },
        }
    )
    assert "error" not in called
    assert controller._state()["gates"]["schematic_visual_review"]["status"] == "PASS"


def test_mcp_transport_waits_for_a_review_longer_than_the_default_call_timeout(tmp_path):
    import time

    class SlowReview(FakeReview):
        timeout_seconds = 5.0

        def review(self, design: Path, output: Path) -> dict:
            time.sleep(0.5)
            return super().review(design, output)

    service = SlowReview("ACCEPTED_FOR_REVIEW", "candidates/000/project/Design.kicad_sch")
    controller, revision = controller_in_schematic(tmp_path, service)
    server = MCPServer(controller, call_timeout_seconds=0.1)
    called = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "review_schematic",
                "arguments": {
                    "design": "design.json",
                    "output": "review-slow",
                    "expected_revision": revision,
                    "idempotency_key": "review-slow",
                },
            },
        }
    )
    assert "error" not in called
    assert not (controller.revisions.root / ".writer-lease").exists()
