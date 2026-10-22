"""Run KiCad and independent observers on a cleanly extracted review ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.fabrication import inspect_fabrication, verify_review_package
from ai_kicad.pivot.native import inspect_board, inspect_schematic


def _run(cli: Path, args: list[str], root: Path, env: dict[str, str]) -> dict:
    result = subprocess.run(
        [str(cli), *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return {
        "command": [str(cli), *args],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def verify(package: Path, cli: Path) -> dict:
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="review-zip-clean-open-") as directory:
        extraction = Path(directory) / "project"
        extracted = verify_review_package(package, extraction)
        project = extraction / "editable_project"
        schematic = project / "Reference555LedFlasher.kicad_sch"
        board = project / "Reference555LedFlasher.kicad_pcb"
        reports = extraction / "clean-open-reports"
        reports.mkdir()
        environment = dict(os.environ)
        environment.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(Path(directory) / "config")})
        commands = [
            _run(cli, ["sch", "erc", "--format", "json", "--output", str(reports / "erc.json"), str(schematic)], extraction, environment),
            _run(cli, ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(reports / "netlist.xml"), str(schematic)], extraction, environment),
            _run(cli, ["pcb", "drc", "--severity-all", "--format", "json", "--output", str(reports / "drc.json"), str(board)], extraction, environment),
        ]
        erc = json.loads((reports / "erc.json").read_text())
        drc = json.loads((reports / "drc.json").read_text())
        schematic_observer = inspect_schematic(
            load_json(root / "fixtures/pivot/reference_555_led_flasher_v1/design.json"),
            schematic,
            reports / "netlist.xml",
        )
        board_observer = inspect_board(
            _model_from_fixture(root / "fixtures/pivot/reference_555_led_flasher_v1"), board
        )
        fabrication = inspect_fabrication(
            extraction / "fabrication", 50.0, 35.0
        )
        erc_violations = [
            violation
            for sheet in erc.get("sheets", [])
            for violation in sheet.get("violations", [])
        ]
        result = {
            "schema_version": "clean-review-extract-validation.v1",
            "package_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
            "clean_extraction": "PASS" if extracted else "FAIL",
            "kicad_cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
            "commands": commands,
            "erc_violation_count": len(erc_violations),
            "drc_violation_count": len(drc.get("violations", [])),
            "unconnected_item_count": len(drc.get("unconnected_items", [])),
            "schematic_observer": schematic_observer,
            "board_observer": board_observer,
            "fabrication_observer": fabrication,
            "status": "PASS"
            if all(command["returncode"] == 0 for command in commands)
            and not erc_violations
            and not drc.get("violations")
            and not drc.get("unconnected_items")
            and schematic_observer["status"] == "pass"
            and board_observer["status"] == "PASS"
            and fabrication["status"] == "PASS"
            else "FAIL",
        }
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--cli",
        type=Path,
        default=Path("/home/phil/Applications/kicad-10.0.6/AppDir/bin/kicad-cli"),
    )
    args = parser.parse_args()
    report = verify(args.package, args.cli.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
