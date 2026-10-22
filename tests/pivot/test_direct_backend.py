import shutil
import json
import hashlib
from pathlib import Path

import pytest

from ai_kicad.pivot.backend import BackendError
from ai_kicad.pivot.controller import Phase, WorkflowController
from ai_kicad.pivot.direct_backend import DirectKiCadBackend
from ai_kicad.pivot.mcp_server import MCPServer
from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.native import board_component_inventory


ROOT = Path(__file__).resolve().parents[2]
CLI = Path("/home/phil/Applications/kicad-10.0.6/AppDir/bin/kicad-cli")
SOURCE = ROOT / "fixtures/pivot/experiments/reference_poc_2026-10-22_run7/editable_project"
DESKTOP_TOOLCHAIN = (
    ROOT
    / "fixtures/pivot/experiments/desktop_preflight_2026-10-22_run1/desktop-toolchain.lock.json"
)


def backend_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    shutil.copytree(SOURCE, workspace / "source")
    return DirectKiCadBackend(workspace, CLI), workspace


def test_create_project_exact_readback_and_transaction_dry_run(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    result = backend.call("create_project", {"source": "source", "destination": "candidate"})
    assert result["status"] == "PASS" and result["hashes"]
    schematic = workspace / "candidate/Reference555LedFlasher.kicad_sch"
    before = schematic.read_bytes()
    marker = '(property "Value" "NE555D" (at 171.45 97.79 0)'
    result = backend.call(
        "apply_schematic_transaction",
        {
            "source": "candidate/Reference555LedFlasher.kicad_sch",
            "changes": [
                {
                    "old": marker,
                    "new": '(property "Value" "NE555D-probe" (at 171.45 97.79 0)',
                }
            ],
            "dry_run": True,
        },
    )
    assert result["status"] == "PLAN_VALID" and schematic.read_bytes() == before
    with pytest.raises(BackendError, match="escapes"):
        backend.call("run_drc", {"source": "../board.kicad_pcb", "output": "x.json"})


def test_mcp_create_schematic_runs_locked_compiler_erc_and_independent_netlist(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    shutil.copytree(fixture, workspace / "input")
    shutil.copy2(DESKTOP_TOOLCHAIN, workspace / "input/desktop-toolchain.lock.json")
    model = _model_from_fixture(fixture)
    (workspace / "input/design-model.v1.json").write_text(model.model_dump_json(indent=2) + "\n")
    controller = WorkflowController(workspace, backend=backend)
    controller.set_revision(model.design_id, model.revision_id)
    state = controller._state()
    state["phase"] = Phase.SCHEMATIC
    controller._save_state(state)
    request = {
        "design": "input/design.json",
        "bom": "input/bom.json",
        "footprint_lock": "input/footprint_assets.lock.json",
        "board_profile": "input/board_profile.json",
        "design_model": "input/design-model.v1.json",
        "toolchain_lock": "input/desktop-toolchain.lock.json",
        "output": "generated/schematic",
        "expected_revision": model.revision_id,
        "idempotency_key": "create-schematic-v1",
    }
    response = MCPServer(controller).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_schematic", "arguments": request},
        }
    )
    assert "result" in response, response
    result = response["result"]["structuredContent"]
    assert result["status"] == "PASS"
    assert result["independent_observation"]["status"] == "pass"
    assert result["schematic_sha256"]
    generated = workspace / request["output"]
    assert (generated / "pivot-schematic-evidence.json").is_file()
    assert json.loads((generated / "reports/erc.json").read_text())["kicad_version"] == "10.0.6"


def test_real_kicad_drc_is_accessible_through_mcp_controller(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    controller = WorkflowController(workspace, backend=backend)
    state = controller._state()
    state["phase"] = Phase.PCB_ROUTING
    controller._save_state(state)
    server = MCPServer(controller)
    envelope = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "run_drc",
                "arguments": {
                    "source": "source/Reference555LedFlasher.kicad_pcb",
                    "output": "reports/real-drc.json",
                },
            },
        }
    )
    structured = envelope["result"]["structuredContent"]
    assert structured["status"] == "PASS"
    assert not structured["report"]["violations"]
    assert not structured["report"]["unconnected_items"]


def test_revision_bound_placement_is_executable_through_mcp(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    source = fixture / "native_project/placement_source.kicad_pcb"
    copied_source = workspace / "placement_source.kicad_pcb"
    shutil.copy2(source, copied_source)
    plan = json.loads((fixture / "placement-plan.v1.json").read_text())
    model = _model_from_fixture(fixture)
    controller = WorkflowController(workspace, backend=backend)
    controller.set_revision(model.design_id, model.revision_id)
    state = controller._state()
    state["phase"] = Phase.PCB_PLACEMENT
    controller._save_state(state)
    original = copied_source.read_bytes()
    request = {
        "source": "placement_source.kicad_pcb",
        "output": "placed/Reference555LedFlasher.kicad_pcb",
        "plan": plan,
        "expected_revision": model.revision_id,
        "idempotency_key": "placement-v1",
    }
    server = MCPServer(controller)
    envelope = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "apply_placements", "arguments": request},
        }
    )
    assert "result" in envelope, envelope
    response = envelope["result"]["structuredContent"]
    replay_envelope = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "apply_placements", "arguments": request},
        }
    )
    assert "result" in replay_envelope, replay_envelope
    replay = replay_envelope["result"]["structuredContent"]
    assert response["status"] == "PASS" and response["mutation_occurred"]
    assert replay == response
    assert copied_source.read_bytes() == original
    assert (workspace / request["output"]).is_file()


def test_pin_pad_footprint_hash_and_pin_one_checks_are_executable_through_mcp(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    model = _model_from_fixture(fixture)
    (workspace / "design-model.json").write_text(model.model_dump_json(indent=2) + "\n")
    controller = WorkflowController(workspace, backend=backend)
    controller.set_revision(model.design_id, model.revision_id)
    state = controller._state()
    state["phase"] = Phase.FOOTPRINTS
    controller._save_state(state)
    response = MCPServer(controller).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "verify_pin_pad_map",
                "arguments": {
                    "design_model": "design-model.json",
                    "footprint_root": "source/footprints",
                },
            },
        }
    )["result"]["structuredContent"]
    assert response["status"] == "PASS"
    assert response["revision_id"] == model.revision_id
    assert len(response["components"]) == len(model.components) == 10
    assert all(item["mapped_pin_count"] == item["required_pin_count"] for item in response["components"])


def _unassigned_model_and_requests(fixture, workspace):
    approved = _model_from_fixture(fixture)
    assignments = []
    payload = approved.model_dump(mode="json")
    for component in payload["components"]:
        assignments.append(
            {
                "component_id": component["component_id"],
                "footprint": component["footprint"],
                "pin_pad_map": component["pin_pad_map"],
            }
        )
        component["footprint"] = None
        component["footprint_sha256"] = None
        component["pin_pad_map"] = []
    payload["revision_id"] = "sha256:" + "0" * 64
    unassigned = type(approved).model_validate(payload)
    payload["revision_id"] = unassigned.content_revision()
    unassigned = type(approved).model_validate(payload)
    model_path = workspace / "unassigned-model.json"
    model_path.write_text(unassigned.model_dump_json(indent=2) + "\n")
    return approved, unassigned, assignments, model_path


def test_footprint_assignment_is_revision_bound_and_atomic_through_mcp(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    approved, unassigned, assignments, model_path = _unassigned_model_and_requests(fixture, workspace)
    controller = WorkflowController(workspace, backend=backend)
    controller.set_revision(unassigned.design_id, unassigned.revision_id)
    state = controller._state()
    state["phase"] = Phase.FOOTPRINTS
    controller._save_state(state)
    request = {
        "design_model": model_path.name,
        "footprint_root": "source/footprints",
        "output": "assigned/design-model.json",
        "assignments": assignments,
        "expected_revision": unassigned.revision_id,
        "idempotency_key": "assign-footprints-v1",
    }
    server = MCPServer(controller)
    envelope = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "assign_footprints", "arguments": request},
        }
    )
    assert "result" in envelope, envelope
    response = envelope["result"]["structuredContent"]
    replay_envelope = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "assign_footprints", "arguments": request},
        }
    )
    assert "result" in replay_envelope, replay_envelope
    replay = replay_envelope["result"]["structuredContent"]
    saved = type(approved).model_validate_json((workspace / request["output"]).read_text())
    assert response["status"] == "PASS" and response["fully_assigned"]
    assert response["new_revision_id"] == saved.revision_id
    assert saved.parent_revision == unassigned.revision_id
    assert saved.components == approved.components
    assert controller._state()["revision_id"] == saved.revision_id
    assert replay == response


def test_footprint_assignment_rejects_wrong_pin_one_without_candidate(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    approved, unassigned, assignments, model_path = _unassigned_model_and_requests(fixture, workspace)
    del approved
    assignments[0]["pin_pad_map"][0]["pad"] = "999"
    with pytest.raises(BackendError, match="pin 1"):
        backend.call(
            "assign_footprints",
            {
                "design_model": model_path.name,
                "footprint_root": "source/footprints",
                "output": "assigned/design-model.json",
                "assignments": assignments,
                "expected_revision": unassigned.revision_id,
            },
        )
    assert not (workspace / "assigned/design-model.json").exists()


def test_schematic_to_pcb_sync_candidate_import_is_executable_through_mcp(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    model = _model_from_fixture(fixture)
    model_path = workspace / "design-model.json"
    model_path.write_text(model.model_dump_json(indent=2) + "\n")
    shutil.copy2(fixture / "design.json", workspace / "design.json")
    shutil.copy2(fixture / "bom.json", workspace / "bom.json")
    shutil.copy2(fixture / "footprint_assets.lock.json", workspace / "footprint_assets.lock.json")
    shutil.copy2(fixture / "board_profile.json", workspace / "board_profile.json")
    controller = WorkflowController(workspace, backend=backend)
    controller.set_revision(model.design_id, model.revision_id)
    state = controller._state()
    state["phase"] = Phase.FOOTPRINTS
    controller._save_state(state)
    candidate = workspace / "source/Reference555LedFlasher.kicad_pcb"
    request = {
        "schematic": "source/Reference555LedFlasher.kicad_sch",
        "source_design": "design.json",
        "bom": "bom.json",
        "footprint_lock": "footprint_assets.lock.json",
        "board_profile": "board_profile.json",
        "candidate": "source/Reference555LedFlasher.kicad_pcb",
        "output": "synced/Reference555LedFlasher.kicad_pcb",
        "design_model": "design-model.json",
        "netlist": "reports/sync-netlist.xml",
        "drc_report": "reports/sync-drc.json",
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "expected_revision": model.revision_id,
        "idempotency_key": "sync-v1",
    }
    result = MCPServer(controller).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "sync_pcb", "arguments": request},
        }
    )["result"]["structuredContent"]
    assert result["status"] == "PASS"
    assert result["mutation_occurred"]
    assert result["capability"]["support"] == "experimental"
    assert result["schematic"]["status"] == "pass"
    assert result["board"]["status"] == "PASS"
    assert not result["drc"]["violations"]
    assert (workspace / request["output"]).read_bytes() == candidate.read_bytes()


def test_sync_pcb_rejects_model_drift_and_stale_net_candidate(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    model = _model_from_fixture(fixture)
    model_path = workspace / "design-model.json"
    model_path.write_text(model.model_dump_json(indent=2) + "\n")
    for filename in ("design.json", "bom.json", "footprint_assets.lock.json", "board_profile.json"):
        shutil.copy2(fixture / filename, workspace / filename)
    candidate = workspace / "source/Reference555LedFlasher.kicad_pcb"
    request = {
        "schematic": "source/Reference555LedFlasher.kicad_sch",
        "source_design": "design.json",
        "bom": "bom.json",
        "footprint_lock": "footprint_assets.lock.json",
        "board_profile": "board_profile.json",
        "candidate": "source/Reference555LedFlasher.kicad_pcb",
        "output": "sync-candidate.kicad_pcb",
        "design_model": "design-model.json",
        "netlist": "reports/sync-netlist.xml",
        "drc_report": "reports/sync-drc.json",
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "expected_revision": model.revision_id,
    }
    changed = model.model_dump(mode="json")
    changed["parent_revision"] = model.revision_id
    changed["title"] += " altered"
    changed["revision_id"] = "sha256:" + "0" * 64
    pending = type(model).model_validate(changed)
    changed["revision_id"] = pending.content_revision()
    changed_model = type(model).model_validate(changed)
    model_path.write_text(changed_model.model_dump_json(indent=2) + "\n")
    with pytest.raises(BackendError, match="do not match"):
        backend.call("sync_pcb", request | {"expected_revision": changed_model.revision_id})
    assert not (workspace / request["output"]).exists()

    model_path.write_text(model.model_dump_json(indent=2) + "\n")
    schematic_path = workspace / "source/Reference555LedFlasher.kicad_sch"
    original_schematic = schematic_path.read_text()
    assert '(label "OUT"' in original_schematic
    schematic_path.write_text(
        original_schematic.replace('(label "OUT"', '(label "REF"', 1)
    )
    with pytest.raises(BackendError, match="schematic failed independent equivalence"):
        backend.call("sync_pcb", request)
    assert not (workspace / request["output"]).exists()
    schematic_path.write_text(original_schematic)

    candidate.write_text(candidate.read_text().replace('(net "/VCC")', '(net "/REF")', 1))
    stale_request = request | {
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }
    with pytest.raises(BackendError, match="pin/pad/net identity"):
        backend.call("sync_pcb", stale_request)
    assert not (workspace / request["output"]).exists()


def test_router_candidate_import_requires_exact_geometry_netlist_and_real_drc(tmp_path):
    backend, workspace = backend_workspace(tmp_path)
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    model = _model_from_fixture(fixture)
    model_path = workspace / "design-model.json"
    model_path.write_text(model.model_dump_json(indent=2) + "\n")
    placement_source = workspace / "placement_source.kicad_pcb"
    shutil.copy2(fixture / "native_project/placement_source.kicad_pcb", placement_source)
    plan = json.loads((fixture / "placement-plan.v1.json").read_text())
    placement = backend.call(
        "apply_placements",
        {
            "source": "placement_source.kicad_pcb",
            "output": "placement/board.kicad_pcb",
            "plan": plan,
            "expected_revision": model.revision_id,
        },
    )
    assert placement["status"] == "PASS"
    candidate = workspace / "source/Reference555LedFlasher.kicad_pcb"
    candidate_before = candidate.read_bytes()
    request = {
        "source": "placement/board.kicad_pcb",
        "candidate": "source/Reference555LedFlasher.kicad_pcb",
        "output": "imported/board.kicad_pcb",
        "design_model": "design-model.json",
        "drc_report": "reports/router-import-drc.json",
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "expected_revision": model.revision_id,
    }
    response = backend.call("route_nets", request)
    assert response["status"] == "PASS"
    assert response["capability"]["support"] == "experimental"
    assert response["observer"]["status"] == "PASS"
    assert not response["drc"]["violations"]
    assert not response["drc"]["unconnected_items"]
    imported = workspace / request["output"]
    assert hashlib.sha256(imported.read_bytes()).hexdigest() == response["imported_sha256"]
    assert candidate.read_bytes() == candidate_before
    assert board_component_inventory(imported) == board_component_inventory(candidate)
