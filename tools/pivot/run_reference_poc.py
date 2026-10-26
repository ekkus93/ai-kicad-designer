"""Produce and independently verify the reference board review package."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.fabrication import (
    deterministic_zip,
    inspect_fabrication,
    sha256,
    verify_review_package,
    write_manifest,
)
from ai_kicad.pivot.native import inspect_board, inspect_schematic
from ai_kicad.pivot.model import DesignModel
from ai_kicad.pivot.backend import DIRECT_PILOT_MANIFEST
from ai_kicad.pivot.controller import Phase, WorkflowController
from ai_kicad.pivot.direct_backend import DirectKiCadBackend
from ai_kicad.pivot.mcp_server import MCPServer
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.verify_native_project import verify_native_project


def call(command: list[str], cwd: Path, environment: dict[str, str]) -> dict:
    started = time.monotonic()
    result = subprocess.run(
        command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=180
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }


def mcp_call(server: MCPServer, name: str, arguments: dict, request_id: int) -> dict:
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    if "error" in response:
        raise RuntimeError(f"MCP {name} failed: {response['error']}")
    return response["result"]["structuredContent"]


def _violations(report: dict, key: str = "violations") -> list:
    if "sheets" in report:
        return [item for sheet in report["sheets"] for item in sheet.get(key, [])]
    return report.get(key, [])


def _dfm(board_report: dict, fabrication_report: dict, profile: dict, drill_report: dict) -> dict:
    minimums = profile["design_minimums"]
    actual_drills = [
        value for item in fabrication_report["drills"] for value in item["tools_mm"].values()
    ]
    checks = {
        "board_dimensions": all(
            abs(actual - expected) <= 0.001
            for actual, expected in zip(
                fabrication_report["outline_mm"],
                [profile["board"]["width_mm"], profile["board"]["height_mm"]],
                strict=True,
            )
        ),
        "track_width": board_report["metrics"]["min_track_width_mm"] >= minimums["track_width_mm"],
        "drill_diameter": min(actual_drills) >= minimums["plated_hole_drill_mm"],
        "native_drc": not _violations(drill_report)
        and not drill_report.get("unconnected_items", []),
        "copper_connectivity": set(board_report["copper_connectivity"].values()) == {True},
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "manufacturing_readiness": "BLOCKED_PENDING_UNVERIFIED_RULES_AND_OWNER_REVIEW"
        if profile["unsupported_or_order_dependent"]
        else "PROFILE_RULES_PASS_PENDING_OWNER_REVIEW",
        "checks": checks,
        "profile_id": profile["profile_id"],
        "unsupported_or_order_dependent": profile["unsupported_or_order_dependent"],
    }


def execute(
    root: Path,
    experiment_id: str,
    cli: Path,
    fixture_path: Path = Path("fixtures/pivot/reference_555_led_flasher_v1"),
) -> Path:
    output = create_experiment_dir(root, experiment_id)
    workspace = output / "editable_project"
    fabrication = output / "fabrication"
    reports = output / "reports"
    previews = output / "previews"
    for directory in (workspace, reports, previews):
        directory.mkdir()
    fixture = (root / fixture_path).resolve()
    if not fixture.is_relative_to((root / "fixtures/pivot").resolve()):
        raise ValueError("fixture must remain under fixtures/pivot")
    source = fixture / "native_project"
    if errors := verify_native_project(source):
        raise RuntimeError(f"native project fixture failed verification: {errors}")
    for name in (
        "Reference555LedFlasher.kicad_pro",
        "Reference555LedFlasher.kicad_sch",
        "Reference555LedFlasher.kicad_pcb",
        "NE555D.kicad_sym",
        "sym-lib-table",
        "fp-lib-table",
    ):
        shutil.copy2(source / name, workspace / name)
    shutil.copytree(source / "footprints", workspace / "footprints")
    reference_model = _model_from_fixture(fixture)
    profile = load_json(root / "fixtures/pivot/profiles/jlcpcb_2layer_reference_v1.json")
    model_payload = reference_model.model_dump(mode="json")
    model_payload["parent_revision"] = reference_model.revision_id
    model_payload["manufacturing_profile"].update(
        {
            "profile_id": profile["profile_id"],
            "min_track_mm": profile["design_minimums"]["track_width_mm"],
            "min_clearance_mm": profile["design_minimums"]["clearance_mm"],
            "min_drill_mm": profile["design_minimums"]["plated_hole_drill_mm"],
            "min_via_diameter_mm": profile["design_minimums"]["via_diameter_mm"],
            "copper_to_edge_mm": profile["design_minimums"]["copper_to_routed_edge_mm"],
            "qualification_status": "fabricator_vetted",
            "source": profile["source"],
        }
    )
    native_sources = {
        f"editable_project/{path.relative_to(workspace)}": path
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }
    model_payload["native_artifacts"] = {
        relative: sha256(path) for relative, path in native_sources.items()
    }
    model_payload["revision_id"] = "sha256:" + "0" * 64
    provisional = DesignModel.model_validate(model_payload)
    model_payload["revision_id"] = provisional.content_revision()
    model = DesignModel.model_validate(model_payload)
    model.require_revision_match()
    (workspace / "design-model.json").write_text(model.model_dump_json(indent=2) + "\n")
    config = output / "config/kicad/10.0"
    config.mkdir(parents=True)
    shutil.copy2(root / "fixtures/m2a/sym-lib-table", config / "sym-lib-table")
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(output / "config")})
    schematic = workspace / "Reference555LedFlasher.kicad_sch"
    board = workspace / "Reference555LedFlasher.kicad_pcb"
    # This P0-P4 reference flow predates the visual-review gate and records no visual
    # acceptance; its evidence makes no claim about schematic readability.
    controller = WorkflowController(
        output / "workflow",
        backend=DirectKiCadBackend(output, cli, environment),
        require_visual_schematic_review=False,
    )
    native_revision = controller.revisions.commit(
        model,
        native_sources,
        expected_revision=None,
        idempotency_key=f"native-design:{model.revision_id}",
    )
    controller.set_revision(model.design_id, native_revision)
    mcp = MCPServer(controller)
    tool_invocations = []

    def gate_and_transition(gate_name: str, target: Phase, call_id: int) -> None:
        controller.record_gate(gate_name, "PASS", native_revision)
        tool_invocations.append(
            {
                "tool": "request_phase_transition",
                "response": mcp_call(
                    mcp,
                    "request_phase_transition",
                    {
                        "expected_revision": native_revision,
                        "target_phase": target,
                        "idempotency_key": f"phase:{target}",
                    },
                    call_id,
                ),
            }
        )

    controller.record_gate("requirements_explicit", "PASS", native_revision)
    tool_invocations.append(
        {
            "tool": "request_phase_transition",
            "response": mcp_call(
                mcp,
                "request_phase_transition",
                {
                    "expected_revision": native_revision,
                    "target_phase": Phase.CIRCUIT_DESIGN,
                    "idempotency_key": "phase:CIRCUIT_DESIGN",
                },
                1,
            ),
        }
    )
    gate_and_transition("circuit_design_validated", Phase.SCHEMATIC, 2)
    erc_response = mcp_call(
        mcp,
        "run_erc",
        {
            "source": "editable_project/Reference555LedFlasher.kicad_sch",
            "output": "reports/erc.json",
        },
        3,
    )
    erc = erc_response["report"]
    (reports / "erc.json").write_text(json.dumps(erc, indent=2) + "\n")
    if _violations(erc):
        raise RuntimeError("ERC failed; inspect retained report")
    commands = [
        [
            str(cli),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(reports / "netlist.xml"),
            str(schematic),
        ],
        [
            str(cli),
            "pcb",
            "render",
            "--output",
            str(previews / "board-top.png"),
            "--side",
            "top",
            str(board),
        ],
        [
            str(cli),
            "pcb",
            "render",
            "--output",
            str(previews / "board-bottom.png"),
            "--side",
            "bottom",
            str(board),
        ],
    ]
    calls = [call(command, workspace, environment) for command in commands]
    version_call = call([str(cli), "version"], workspace, environment)
    calls.insert(0, version_call)
    if any(item["returncode"] != 0 for item in calls):
        raise RuntimeError("real KiCad command failed; inspect retained call log")
    schematic_report = inspect_schematic(
        load_json(fixture / "design.json"), schematic, reports / "netlist.xml"
    )
    board_report = inspect_board(model, board)
    if schematic_report["status"] != "pass":
        raise RuntimeError("independent schematic equivalence failed")
    gate_and_transition("schematic_validated", Phase.FOOTPRINTS, 4)
    if board_report["status"] != "PASS":
        raise RuntimeError("independent footprint and pin-pad mapping failed")
    gate_and_transition("footprints_validated", Phase.PCB_PLACEMENT, 5)
    gate_and_transition("placement_validated", Phase.PCB_ROUTING, 6)
    drc_response = mcp_call(
        mcp,
        "run_drc",
        {
            "source": "editable_project/Reference555LedFlasher.kicad_pcb",
            "output": "reports/drc.json",
        },
        7,
    )
    drc = drc_response["report"]
    (reports / "drc.json").write_text(json.dumps(drc, indent=2) + "\n")
    if (
        _violations(drc)
        or drc.get("unconnected_items")
        or not all(board_report["copper_connectivity"].values())
    ):
        raise RuntimeError("native DRC/copper graph failed")
    gate_and_transition("pcb_validated", Phase.MANUFACTURING_REVIEW, 8)
    export_response = mcp_call(
        mcp,
        "prepare_fabrication_package",
        {
            "source": "editable_project/Reference555LedFlasher.kicad_pcb",
            "output": "fabrication",
            "expected_revision": native_revision,
            "idempotency_key": f"fabrication:{native_revision}",
        },
        9,
    )
    tool_invocations.append({"tool": "run_erc", "response": erc_response})
    tool_invocations.append({"tool": "run_drc", "response": drc_response})
    tool_invocations.append({"tool": "prepare_fabrication_package", "response": export_response})
    fabrication_report = inspect_fabrication(
        fabrication, profile["board"]["width_mm"], profile["board"]["height_mm"]
    )
    dfm = _dfm(board_report, fabrication_report, profile, drc)
    gates = {
        "erc": not _violations(erc),
        "schematic_equivalence": schematic_report["status"] == "pass",
        "board_equivalence_and_connectivity": board_report["status"] == "PASS",
        "drc": not _violations(drc) and not drc.get("unconnected_items", []),
        "gerber_drill": fabrication_report["status"] == "PASS",
        "dfm": dfm["status"] == "PASS",
        "previews": all(
            (previews / name).stat().st_size > 1000
            for name in ("board-top.png", "board-bottom.png")
        ),
    }
    verification = {
        "schema_version": "reference-poc-verification.v1",
        "revision_id": model.revision_id,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "readiness_state": "PACKAGE_READY_FOR_REVIEW" if all(gates.values()) else "BLOCKED",
        "gates": gates,
        "schematic": schematic_report,
        "board": board_report,
        "fabrication": fabrication_report,
        "dfm": dfm,
    }
    (reports / "verification_report.json").write_text(json.dumps(verification, indent=2) + "\n")
    call_log = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "kicad_cli_sha256": sha256(cli),
        "backend_manifest": DIRECT_PILOT_MANIFEST.model_dump(mode="json"),
        "mcp_tools": tool_invocations,
        "controller_state": controller._state(),
        "calls": calls,
        "elapsed_seconds": round(sum(item["elapsed_seconds"] for item in calls), 6),
        "source_hashes": {
            str(path.relative_to(source)): sha256(path)
            for path in sorted(source.rglob("*"))
            if path.is_file()
        },
    }
    (reports / "call_log.json").write_text(json.dumps(call_log, indent=2) + "\n")
    write_manifest(
        output,
        model.revision_id,
        {"verification_report_sha256": sha256(reports / "verification_report.json"), **gates},
        profile["unsupported_or_order_dependent"]
        + ["No order, assembly, power-on measurement or physical test has occurred."],
        {
            "kicad_cli_sha256": sha256(cli),
            "kicad_cli_version": version_call["stdout"].strip(),
            "backend_manifest": DIRECT_PILOT_MANIFEST.model_dump(mode="json"),
            "native_artifact_hashes": model.native_artifacts,
            "fabrication_profile_sha256": sha256(
                root / "fixtures/pivot/profiles/jlcpcb_2layer_reference_v1.json"
            ),
            "canonical_model_revision": model.revision_id,
        },
    )
    package_hash = deterministic_zip(output, output / "review-package.zip")
    (output / "package.sha256").write_text(package_hash + "  review-package.zip\n")
    with tempfile.TemporaryDirectory(prefix="pivot-review-clean-") as temporary:
        verify_review_package(output / "review-package.zip", Path(temporary) / "extracted")
    controller.record_gate("package_ready_for_review", "PASS", native_revision)
    ready_transition = mcp_call(
        mcp,
        "request_phase_transition",
        {
            "expected_revision": native_revision,
            "target_phase": Phase.REVIEW_READY,
            "idempotency_key": f"phase:REVIEW_READY:{native_revision}",
        },
        10,
    )
    tool_invocations.append({"tool": "request_phase_transition", "response": ready_transition})
    call_log["mcp_tools"] = tool_invocations
    call_log["controller_state"] = controller._state()
    (reports / "call_log.json").write_text(json.dumps(call_log, indent=2) + "\n")
    write_manifest(
        output,
        model.revision_id,
        {"verification_report_sha256": sha256(reports / "verification_report.json"), **gates},
        profile["unsupported_or_order_dependent"]
        + ["No order, assembly, power-on measurement or physical test has occurred."],
        {
            "kicad_cli_sha256": sha256(cli),
            "kicad_cli_version": version_call["stdout"].strip(),
            "backend_manifest": DIRECT_PILOT_MANIFEST.model_dump(mode="json"),
            "native_artifact_hashes": model.native_artifacts,
            "fabrication_profile_sha256": sha256(
                root / "fixtures/pivot/profiles/jlcpcb_2layer_reference_v1.json"
            ),
            "canonical_model_revision": model.revision_id,
        },
    )
    package_hash = deterministic_zip(output, output / "review-package.zip")
    (output / "package.sha256").write_text(package_hash + "  review-package.zip\n")
    with tempfile.TemporaryDirectory(prefix="pivot-review-clean-final-") as temporary:
        verify_review_package(output / "review-package.zip", Path(temporary) / "extracted")
    if verification["status"] != "PASS":
        raise RuntimeError("reference POC gates failed")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("fixtures/pivot/reference_555_led_flasher_v1"),
        help="hash-locked reference fixture under fixtures/pivot",
    )
    args = parser.parse_args()
    print(
        execute(
            Path(__file__).resolve().parents[2],
            args.experiment_id,
            args.cli.resolve(),
            args.fixture,
        )
    )


if __name__ == "__main__":
    main()
