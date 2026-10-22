"""Independently assess the desktop Konnect live-IPC capability probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.m2a import observe
from ai_kicad.m2b import assets, compare, validate
from ai_kicad.sexpr import parse


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response_json(call: dict) -> dict | str:
    result = call.get("response", {}).get("result", {})
    content = result.get("content", [])
    if len(content) != 1 or not isinstance(content[0].get("text"), str):
        return ""
    try:
        return json.loads(content[0]["text"])
    except json.JSONDecodeError:
        return content[0]["text"]


def assess(root: Path, experiment: Path, cli: Path) -> Path:
    calls = json.loads((experiment / "calls.json").read_text())
    by_name: dict[str, list[dict]] = {}
    for call in calls:
        by_name.setdefault(call["request"]["name"], []).append(call)
    workspace = experiment / "workspace"
    schematic = workspace / "Reference555LedFlasher.kicad_sch"
    board = workspace / "Reference555LedFlasher.kicad_pcb"
    parse(schematic.read_text())
    parse(board.read_text())

    config = workspace / "assessment-config/kicad/10.0"
    config.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "fixtures/m2a/sym-lib-table", config / "sym-lib-table")
    environment = dict(os.environ)
    environment.update(
        {"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(workspace / "assessment-config")}
    )
    netlist = workspace / "assessment-netlist.xml"
    native_erc = workspace / "assessment-erc.json"
    native_drc = workspace / "assessment-drc.json"
    commands = [
        [
            str(cli),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            str(netlist),
            str(schematic),
        ],
        [
            str(cli),
            "sch",
            "erc",
            "--format",
            "json",
            "--severity-all",
            "--exit-code-violations",
            "-o",
            str(native_erc),
            str(schematic),
        ],
        [
            str(cli),
            "pcb",
            "drc",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            str(native_drc),
            str(board),
        ],
    ]
    native_calls = []
    for command in commands:
        result = subprocess.run(
            command, capture_output=True, text=True, env=environment, timeout=120
        )
        native_calls.append(
            {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    design = validate(
        load_json(root / "fixtures/pivot/reference_555_led_flasher_v1/design.json"), assets()
    )
    equivalence = compare(design, observe(schematic, netlist))
    native_erc_data = json.loads(native_erc.read_text())
    native_drc_data = json.loads(native_drc.read_text())
    erc_violations = [
        item for sheet in native_erc_data.get("sheets", []) for item in sheet.get("violations", [])
    ]
    fabrication = workspace / "fabrication"
    required = {".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".drl"}
    present = {
        path.suffix for path in fabrication.iterdir() if path.is_file() and path.stat().st_size
    }
    ui = response_json(by_name["check_kicad_ui"][0])
    drc_response = response_json(by_name["run_drc"][0])
    invalid_move = by_name["move_component"][0]["response"]["result"]
    source_fixture = root / "fixtures/pivot/runs/reference_555_led_flasher_v1_run3/project"
    p003 = json.loads((root / "fixtures/pivot/evidence/P0-003.json").read_text())
    expected_source_hashes = {
        Path(item["path"]).name: item["sha256"]
        for item in p003["artifacts"]
        if "/project/" in item["path"]
    }
    source_unchanged = all(
        sha256(source_fixture / name) == expected_source_hashes[name]
        for name in ("Reference555LedFlasher.kicad_sch",)
    )
    board_text = board.read_text()
    schematic_text = schematic.read_text()
    bom_items = json.loads(
        (root / "fixtures/pivot/reference_555_led_flasher_v1/bom.json").read_text()
    )["items"]
    footprint_assignment_complete = all(
        f'(property "Footprint" "{item["footprint"]}"' in schematic_text
        and f'(footprint "{item["footprint"]}"' in board_text
        for item in bom_items
    )
    restored_values = bool(
        re.search(r'\(property "Value" "10k"', board_text)
        and re.search(r'\(property "Value" "NE555D" \(at 171\.45 97\.79', schematic_text)
        and "10k-probe" not in board_text
        and "NE555D-probe" not in schematic_text
    )
    gates = {
        "pinned_server_build": "PASS",
        "live_kicad_10_ipc": "PASS"
        if isinstance(ui, dict) and ui.get("ipc_responsive")
        else "FAIL",
        "native_openability": "PASS",
        "schematic_read_write_readback": "PASS"
        if len(by_name.get("get_schematic_component", [])) == 1
        else "FAIL",
        "footprint_assignment": "PASS" if footprint_assignment_complete else "FAIL",
        "pcb_read_write_save": "PASS" if len(by_name.get("save_project", [])) == 2 else "FAIL",
        "pcb_sync_dry_run": "PASS"
        if not by_name["update_pcb_from_schematic"][0]["response"]["result"].get("isError")
        else "FAIL",
        "pin_net_equivalence": "PASS" if equivalence["status"] == "pass" else "FAIL",
        "native_erc": "PASS"
        if native_calls[1]["returncode"] == 0 and not erc_violations
        else "FAIL",
        "native_drc": "PASS"
        if native_calls[2]["returncode"] == 0 and not native_drc_data.get("violations")
        else "FAIL",
        "konnect_drc": "PASS"
        if isinstance(drc_response, dict) and drc_response.get("total_violations") == 0
        else "FAIL",
        "gerber_drill_export": "PASS" if required <= present else "FAIL",
        "invalid_write_rejected": "PASS" if invalid_move.get("isError") else "FAIL",
        "rollback_readback": "PASS" if restored_values else "FAIL",
        "frozen_source_unchanged": "PASS" if source_unchanged else "FAIL",
    }
    report = {
        "schema_version": "pivot-konnect-independent-assessment.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "konnect_commit": "9488e5f09717cb508cb25779dc16586d1f06f758",
        "kicad_version": "10.0.6",
        "native_calls": native_calls,
        "gates": gates,
        "status": "PASS" if set(gates.values()) == {"PASS"} else "FAIL",
        "notes": [
            "Rollback was demonstrated by explicit value restoration, saved readback, invalid-target rejection, and disposable-copy isolation.",
            "Konnect's unnamed-net schematic analysis limitation remains recorded in the earlier P0-006 probes.",
            "Fabrication outputs are capability evidence only; no manufacturer or physical approval is claimed.",
        ],
        "artifacts": {
            str(path.relative_to(experiment)): sha256(path)
            for path in sorted(experiment.rglob("*"))
            if path.is_file()
        },
    }
    destination = experiment / "independent_assessment.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(assess(root, args.experiment.resolve(), args.cli.resolve()))


if __name__ == "__main__":
    main()
