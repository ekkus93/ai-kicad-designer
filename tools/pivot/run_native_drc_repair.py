"""Inject and repair a real KiCad DRC track-width fault on a disposable board."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.pivot.fabrication import sha256
from ai_kicad.pivot.native import inspect_board
from ai_kicad.pivot.cli import _model_from_fixture
from tools.pivot.experiment_paths import create_experiment_dir


def drc(cli: Path, board: Path, output: Path, env: dict[str, str]) -> dict:
    result = subprocess.run(
        [str(cli), "pcb", "drc", "--format", "json", "--output", str(output), str(board)],
        cwd=board.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(output.read_text())


def execute(root: Path, experiment_id: str, cli: Path) -> Path:
    output = create_experiment_dir(root, experiment_id)
    source = root / "fixtures/pivot/reference_555_led_flasher_v1/native_project"
    project = output / "workspace"
    reports = output / "reports"
    project.mkdir()
    reports.mkdir()
    for name in (
        "Reference555LedFlasher.kicad_pro",
        "Reference555LedFlasher.kicad_sch",
        "Reference555LedFlasher.kicad_pcb",
        "NE555D.kicad_sym",
        "sym-lib-table",
        "fp-lib-table",
    ):
        shutil.copy2(source / name, project / name)
    shutil.copytree(source / "footprints", project / "footprints")
    original = project / "Reference555LedFlasher.kicad_pcb"
    original_hash = sha256(original)
    candidate = project / "fault-candidate.kicad_pcb"
    board_text = original.read_text()
    modified, replacements = re.subn(r"\(width 0\.2\)", "(width 0.15)", board_text, count=1)
    if replacements != 1:
        raise RuntimeError("expected one 0.20 mm track width to inject")
    candidate.write_text(modified)
    injected_hash = sha256(candidate)
    config = output / "config/kicad/10.0"
    config.mkdir(parents=True)
    shutil.copy2(root / "fixtures/m2a/sym-lib-table", config / "sym-lib-table")
    env = dict(os.environ)
    env.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(output / "config")})
    injected = drc(cli, candidate, reports / "drc-injected.json", env)
    violation_types = [item.get("type") for item in injected.get("violations", [])]
    if "track_width" not in violation_types:
        raise RuntimeError(f"fault injection did not produce track_width DRC: {violation_types}")
    repair_text, repaired_count = re.subn(r"\(width 0\.15\)", "(width 0.2)", modified, count=1)
    if repaired_count != 1:
        raise RuntimeError("bounded repair could not locate its exact injected width")
    candidate.write_text(repair_text)
    repaired_hash = sha256(candidate)
    repaired = drc(cli, candidate, reports / "drc-repaired.json", env)
    if repaired.get("violations") or repaired.get("unconnected_items"):
        raise RuntimeError("bounded DRC repair did not clear the gate")
    if sha256(original) != original_hash or repaired_hash != original_hash:
        raise RuntimeError("repair altered the known-good board or failed exact restoration")
    model = _model_from_fixture(root / "fixtures/pivot/reference_555_led_flasher_v1")
    observation = inspect_board(model, candidate)
    if observation["status"] != "PASS":
        raise RuntimeError("independent pin/pad/copper observer rejected repaired board")
    report = {
        "schema_version": "native-drc-repair.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "source_board_sha256": original_hash,
        "fault_candidate_sha256": injected_hash,
        "repaired_candidate_sha256": repaired_hash,
        "fault_types": violation_types,
        "fault_violation_count": len(injected.get("violations", [])),
        "repair_actions": [
            "restore the uniquely injected 0.15 mm track to the profile 0.20 mm minimum"
        ],
        "repaired_drc_violations": len(repaired.get("violations", [])),
        "repaired_unconnected_items": len(repaired.get("unconnected_items", [])),
        "independent_board_observer": observation,
        "known_good_source_unchanged": sha256(original) == original_hash,
        "repaired_candidate_matches_known_good": repaired_hash == original_hash,
        "toolchain": {
            "kicad_cli_sha256": sha256(cli),
            "fault_call": [str(cli), "pcb", "drc", "--format", "json"],
            "repair_call": [str(cli), "pcb", "drc", "--format", "json"],
        },
    }
    (output / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    print(execute(Path(__file__).resolve().parents[2], args.experiment_id, args.cli.resolve()))


if __name__ == "__main__":
    main()
