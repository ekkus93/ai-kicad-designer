"""Exercise the phase-gated router candidate import using real KiCad 10 DRC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.controller import Phase, WorkflowController
from ai_kicad.pivot.direct_backend import DirectKiCadBackend
from ai_kicad.pivot.mcp_server import MCPServer
from tools.pivot.experiment_paths import create_experiment_dir


def _call(server: MCPServer, name: str, arguments: dict, call_id: int) -> dict:
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    if "error" in response:
        raise RuntimeError(f"MCP {name} failed: {response['error']}")
    return response["result"]["structuredContent"]


def execute(root: Path, experiment_id: str) -> Path:
    fixture = root / "fixtures/pivot/reference_555_led_flasher_v1"
    native = fixture / "native_project"
    output = create_experiment_dir(root, experiment_id)
    for name in ("Reference555LedFlasher.kicad_pro", "fp-lib-table"):
        shutil.copy2(native / name, output / name)
    shutil.copytree(native / "footprints", output / "footprints")
    shutil.copytree(native / "footprints", output / "router_candidate/footprints")
    candidate = output / "router_candidate/Reference555LedFlasher.kicad_pcb"
    shutil.copy2(native / "Reference555LedFlasher.kicad_pcb", candidate)
    shutil.copy2(native / "Reference555LedFlasher.kicad_pro", candidate.parent)
    shutil.copy2(native / "fp-lib-table", candidate.parent)
    (output / "design-model.json").write_text(
        _model_from_fixture(fixture).model_dump_json(indent=2) + "\n"
    )
    model = _model_from_fixture(fixture)
    source = output / "placement_source.kicad_pcb"
    shutil.copy2(native / "placement_source.kicad_pcb", source)
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "TZ": "UTC"})
    cli = Path("/home/phil/Applications/kicad-10.0.6/AppDir/bin/kicad-cli")
    # Router-import probe only; it predates and makes no claim about visual schematic review.
    controller = WorkflowController(
        output / "workflow",
        backend=DirectKiCadBackend(output, cli, environment),
        require_visual_schematic_review=False,
    )
    with controller.revisions.writer("router-import-probe"):
        revision = controller.revisions.commit(
            model,
            {},
            expected_revision=None,
            idempotency_key=f"router-probe:{model.revision_id}",
        )
    controller.set_revision(model.design_id, revision)
    server = MCPServer(controller)
    invocation = []
    gates = [
        ("requirements_explicit", Phase.CIRCUIT_DESIGN),
        ("circuit_design_validated", Phase.SCHEMATIC),
        ("schematic_validated", Phase.FOOTPRINTS),
        ("footprints_validated", Phase.PCB_PLACEMENT),
    ]
    for index, (gate, target) in enumerate(gates, start=1):
        controller.record_gate(gate, "PASS", revision)
        invocation.append(
            _call(
                server,
                "request_phase_transition",
                {
                    "expected_revision": revision,
                    "target_phase": target,
                    "idempotency_key": f"phase:{target}",
                },
                index,
            )
        )
    placement = _call(
        server,
        "apply_placements",
        {
            "source": "placement_source.kicad_pcb",
            "output": "placement/Reference555LedFlasher.kicad_pcb",
            "plan": json.loads((fixture / "placement-plan.v1.json").read_text()),
            "expected_revision": revision,
            "idempotency_key": "placement:reference-plan-v1",
        },
        5,
    )
    invocation.append(placement)
    controller.record_gate("placement_validated", "PASS", revision)
    invocation.append(
        _call(
            server,
            "request_phase_transition",
            {
                "expected_revision": revision,
                "target_phase": Phase.PCB_ROUTING,
                "idempotency_key": "phase:PCB_ROUTING",
            },
            6,
        )
    )
    route = _call(
        server,
        "route_nets",
        {
            "source": "placement/Reference555LedFlasher.kicad_pcb",
            "candidate": "router_candidate/Reference555LedFlasher.kicad_pcb",
            "output": "routed/Reference555LedFlasher.kicad_pcb",
            "design_model": "design-model.json",
            "drc_report": "reports/router-import-drc.json",
            "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "expected_revision": revision,
            "idempotency_key": "route-import:external-router-candidate-v1",
        },
        7,
    )
    invocation.append(route)
    report = {
        "schema_version": "router-import-probe.v1",
        "design_revision": revision,
        "router_candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "candidate_source": "locked native routed reference board; ProductOfAmerica/Freerouting evidence is separately retained",
        "tool_invocations": invocation,
        "route_import": route,
        "result": "PASS"
        if route["status"] == "PASS"
        and route["observer"]["status"] == "PASS"
        and not route["drc"]["violations"]
        and not route["drc"]["unconnected_items"]
        else "FAIL",
        "scope_limit": "This validates safe import of a complete router candidate; the direct backend does not claim a general-purpose autorouting engine.",
    }
    path = output / "router-import-assessment.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    if report["result"] != "PASS":
        raise RuntimeError(f"router candidate failed; evidence retained at {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    print(execute(Path(__file__).resolve().parents[2], args.experiment_id))


if __name__ == "__main__":
    main()
