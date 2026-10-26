"""Demonstrate the visual review loop as the controller's SCHEMATIC-phase tool over MCP.

For each design, a fresh controller workspace is advanced to SCHEMATIC, the loop runs
through ``tools/call review_schematic`` with the native KiCad engine and a local vision
model, and the FOOTPRINTS transition is requested. ``schematic_validated`` is recorded
only from the accepted candidate's own independent ERC/electrical-equivalence results.
Upstream REQUIREMENTS/CIRCUIT_DESIGN gates are recorded by this harness without
evaluation; they are outside this demonstration and are labeled as such.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.controller import NotAuthorized, Phase, WorkflowController
from ai_kicad.pivot.mcp_server import MCPServer
from ai_kicad.pivot.schematic_review import file_hash, write_json
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
from tools.pivot.experiment_paths import create_experiment_dir

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"


def call(server: MCPServer, name: str, arguments: dict, request_id: int) -> dict:
    return server.handle(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )


def demonstrate(design_name: str, service: NativeSchematicReviewService, root: Path) -> dict:
    workspace = root / design_name
    controller = WorkflowController(workspace, schematic_review=service)
    model = _model_from_fixture(FIXTURE)
    revision = controller.revisions.commit(
        model, {}, expected_revision=None, idempotency_key="demo-initialize"
    )
    controller.set_revision(model.design_id, revision)
    server = MCPServer(controller)
    log = []
    for gate, target in (
        ("requirements_explicit", Phase.CIRCUIT_DESIGN),
        ("circuit_design_validated", Phase.SCHEMATIC),
    ):
        controller.record_gate(gate, "PASS", revision)
        log.append(
            {
                "upstream_gate_recorded_without_evaluation": gate,
                "transition": call(
                    server,
                    "request_phase_transition",
                    {
                        "expected_revision": revision,
                        "target_phase": target,
                        "idempotency_key": f"to-{target}",
                    },
                    len(log) + 1,
                ),
            }
        )
    shutil.copy2(ROOT / "fixtures/m2b" / f"{design_name}.json", workspace / "design.json")
    listed = server.handle({"jsonrpc": "2.0", "id": 90, "method": "tools/list"})
    review = call(
        server,
        "review_schematic",
        {
            "design": "design.json",
            "output": "schematic-review",
            "expected_revision": revision,
            "idempotency_key": "review-1",
        },
        91,
    )
    gate = controller._state()["gates"].get("schematic_visual_review", {})
    electrical = None
    if gate.get("status") == "PASS":
        accepted = Path(gate["accepted_schematic"])
        assessment = json.loads((accepted.parent.parent / "assessment.json").read_text())
        electrical = {
            name: assessment["checks"][name]
            for name in ("native_tools", "erc", "electrical_equivalence")
        }
        if all(value == "PASS" for value in electrical.values()):
            controller.record_gate("schematic_validated", "PASS", revision)
    try:
        transition = controller.dispatch(
            "request_phase_transition",
            {
                "expected_revision": revision,
                "target_phase": Phase.FOOTPRINTS,
                "idempotency_key": "to-FOOTPRINTS",
            },
        )
    except NotAuthorized as error:
        transition = {"status": "DENIED", "reason": str(error)}
    result = json.loads((workspace / "schematic-review/result.json").read_text())
    return {
        "design": design_name,
        "revision_id": revision,
        "review_schematic_listed_in_schematic_phase": "review_schematic"
        in {tool["name"] for tool in listed["result"]["tools"]},
        "mcp_review_error": review.get("error"),
        "loop_status": result["status"],
        "loop_reason": result["reason"],
        "reviews": len(result["iterations"]),
        "model_tokens": result.get("model_tokens"),
        "visual_gate": gate,
        "electrical_checks_of_accepted_candidate": electrical,
        "footprints_transition": transition,
        "final_phase": controller._state()["phase"],
        "upstream_log": log,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--designs", nargs="+", default=["rc_lowpass", "linear_regulator"])
    parser.add_argument(
        "--review-brief", type=Path, default=ROOT / "fixtures/pivot/schematic_review_brief_v2.json"
    )
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    service = NativeSchematicReviewService(
        args.kicad_apprun, args.model, review_brief=args.review_brief
    )
    results = [demonstrate(name, service, root) for name in args.designs]
    summary = {
        "schema_version": "schematic-phase-demo.v1",
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "controller_sha256": file_hash(ROOT / "src/ai_kicad/pivot/controller.py"),
        "service_sha256": file_hash(ROOT / "src/ai_kicad/pivot/schematic_review_service.py"),
        "model": args.model,
        "review_brief": str(args.review_brief.relative_to(ROOT)),
        "results": results,
        "locked_host_qualification": False,
        "human_readability_review": "PENDING",
    }
    write_json(root / "summary.json", summary)
    for item in results:
        print(item["design"], item["loop_status"], item["footprints_transition"].get("status"))


if __name__ == "__main__":
    main()
