"""Run and verify the revision-bound initial placement plan with KiCad 10."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.native import inspect_board
from ai_kicad.pivot.placement import apply_placement, load_plan
from ai_kicad.sexpr import children, one, parse
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.verify_native_project import verify_native_project


def run(root: Path, experiment_id: str) -> Path:
    fixture = root / "fixtures/pivot/reference_555_led_flasher_v1"
    native = fixture / "native_project"
    if errors := verify_native_project(native):
        raise RuntimeError(f"native placement fixture failed verification: {errors}")
    output = create_experiment_dir(root, experiment_id)
    shutil.copy2(native / "Reference555LedFlasher.kicad_pro", output)
    shutil.copy2(native / "fp-lib-table", output)
    shutil.copytree(native / "footprints", output / "footprints")
    board = output / "Reference555LedFlasher.kicad_pcb"
    model = _model_from_fixture(fixture)
    placement = apply_placement(
        native / "placement_source.kicad_pcb",
        board,
        load_plan(fixture / "placement-plan.v1.json"),
        expected_revision=model.revision_id,
    )
    cli = Path("/home/phil/Applications/kicad-10.0.6/kicad-cli")
    drc_path = output / "placement-drc.json"
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "TZ": "UTC"})
    drc = subprocess.run(
        [str(cli), "pcb", "drc", "--severity-all", "--format", "json", "-o", str(drc_path), str(board)],
        capture_output=True,
        text=True,
        timeout=180,
        env=environment,
        check=False,
    )
    if not drc_path.is_file():
        raise RuntimeError(f"KiCad DRC did not write a report: {drc.stderr}")
    drc_report = json.loads(drc_path.read_text())
    observed = inspect_board(model, board)
    root_expr = parse(board.read_text())
    positions = {}
    for footprint in children(root_expr, "footprint"):
        reference = next(item[2] for item in children(footprint, "property") if item[1] == "Reference")
        at = one(footprint, "at")
        positions[reference] = [float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0]
    expected = {
        reference: [value["x_mm"], value["y_mm"], value["rotation_deg"]]
        for reference, value in placement["placements"].items()
    }
    report = {
        "schema_version": "deterministic-placement-assessment.v1",
        "revision_id": model.revision_id,
        "source_board_sha256": placement["source_board_sha256"],
        "candidate_board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
        "kicad_cli": str(cli),
        "kicad_cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
        "placement_readback_exact": positions == expected,
        "native_instance_and_pin_pad_net_partition": {
            "unmatched_partitions": observed["unmatched_partitions"],
            "footprint_mismatches": observed["footprint_mismatches"],
            "component_references": observed["component_references"],
        },
        "placement_drc": {
            "returncode": drc.returncode,
            "violations": drc_report.get("violations", []),
            "unconnected_items": drc_report.get("unconnected_items", []),
            "unconnected_items_expected": "placement source intentionally has no routed copper",
        },
        "result": "PASS"
        if drc.returncode == 0
        and not drc_report.get("violations")
        and positions == expected
        and not observed["unmatched_partitions"]
        and not observed["footprint_mismatches"]
        else "FAIL",
        "limitations": [
            "Placement-stage board is intentionally unrouted; unconnected-item findings are expected.",
            "A zero-error placement DRC does not claim route completeness or fabrication readiness.",
        ],
    }
    (output / "placement-assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["result"] != "PASS":
        raise RuntimeError(f"placement assessment failed; evidence retained at {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[2], args.experiment_id))


if __name__ == "__main__":
    main()
