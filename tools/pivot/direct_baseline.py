"""Exercise the direct compiler/native-file/KiCad CLI pivot baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.m2a import observe
from ai_kicad.m2b import assets, compare, validate
from ai_kicad.sexpr import parse
from tools.pivot.experiment_paths import create_experiment_dir


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict:
    started = time.monotonic()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_seconds": time.monotonic() - started,
    }


def execute(root: Path, experiment_id: str, cli: Path) -> Path:
    output = create_experiment_dir(root, experiment_id)
    workspace = output / "workspace"
    workspace.mkdir()
    reference = root / "fixtures/pivot/runs/reference_555_led_flasher_v1_run3/project"
    routed = (
        root / "fixtures/pivot/experiments/productofamerica_drc_repair_2026-10-22_run1/workspace"
    )
    for name in (
        "Reference555LedFlasher.kicad_pro",
        "Reference555LedFlasher.kicad_sch",
        "NE555D.kicad_sym",
        "sym-lib-table",
    ):
        shutil.copy2(reference / name, workspace / name)
    shutil.copy2(
        routed / "Reference555LedFlasher_repair.kicad_pcb",
        workspace / "Reference555LedFlasher.kicad_pcb",
    )
    footprint_source = root / "fixtures/pivot/reference_555_led_flasher_v1/assets/footprints"
    shutil.copytree(footprint_source, workspace / "footprints")
    footprint_libraries = sorted(
        path.name.removesuffix(".pretty") for path in footprint_source.glob("*.pretty")
    )
    (workspace / "fp-lib-table").write_text(
        "(fp_lib_table (version 7)\n"
        + "".join(
            f'  (lib (name "{name}") (type "KiCad") '
            f'(uri "${{KIPRJMOD}}/footprints/{name}.pretty") (options "") '
            '(descr "Pinned reference footprint"))\n'
            for name in footprint_libraries
        )
        + ")\n"
    )
    source_hashes = {
        path.name: sha256(path) for path in sorted(workspace.iterdir()) if path.is_file()
    }

    # The direct coding-agent case is a bounded exact edit on a disposable copy.
    schematic = workspace / "Reference555LedFlasher.kicad_sch"
    original = schematic.read_text()
    needle = '(property "Value" "NE555D" (at 171.45 97.79 0)'
    if original.count(needle) != 1:
        raise RuntimeError("expected one exact U1 value property")
    mutated = original.replace(
        needle, '(property "Value" "NE555D-direct-probe" (at 171.45 97.79 0)', 1
    )
    parse(mutated)
    schematic.write_text(mutated)
    mutation_hash = sha256(schematic)
    schematic.write_text(original)
    rollback_hash = sha256(schematic)

    reports = workspace / "reports"
    fabrication = workspace / "fabrication"
    reports.mkdir()
    fabrication.mkdir()
    config = workspace / "config/kicad/10.0"
    config.mkdir(parents=True)
    shutil.copy2(root / "fixtures/m2a/sym-lib-table", config / "sym-lib-table")
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(workspace / "config")})
    commands = [
        [
            str(cli),
            "sch",
            "erc",
            "--format",
            "json",
            "--output",
            str(reports / "erc.json"),
            str(schematic),
        ],
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
            "drc",
            "--format",
            "json",
            "--output",
            str(reports / "drc.json"),
            str(workspace / "Reference555LedFlasher.kicad_pcb"),
        ],
        [
            str(cli),
            "pcb",
            "export",
            "gerbers",
            "--output",
            str(fabrication),
            str(workspace / "Reference555LedFlasher.kicad_pcb"),
        ],
        [
            str(cli),
            "pcb",
            "export",
            "drill",
            "--output",
            str(fabrication),
            "--generate-map",
            str(workspace / "Reference555LedFlasher.kicad_pcb"),
        ],
    ]
    calls = [run(command, cwd=workspace, env=environment) for command in commands]
    design = validate(
        load_json(root / "fixtures/pivot/reference_555_led_flasher_v1/design.json"), assets()
    )
    equivalence = compare(design, observe(schematic, reports / "netlist.xml"))
    (reports / "electrical.json").write_text(json.dumps(equivalence, indent=2) + "\n")
    drc = json.loads((reports / "drc.json").read_text())
    erc = json.loads((reports / "erc.json").read_text())
    erc_violations = [
        violation for sheet in erc.get("sheets", []) for violation in sheet.get("violations", [])
    ]
    required_extensions = {".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".drl"}
    extensions = {path.suffix for path in fabrication.iterdir() if path.is_file()}
    gates = {
        "native_schematic_parse": "PASS",
        "bounded_edit_parse": "PASS",
        "rollback_byte_identity": "PASS"
        if rollback_hash == source_hashes[schematic.name]
        else "FAIL",
        "pin_net_equivalence": "PASS" if equivalence["status"] == "pass" else "FAIL",
        "erc": "PASS" if calls[0]["returncode"] == 0 and not erc_violations else "FAIL",
        "drc": "PASS" if calls[2]["returncode"] == 0 and not drc.get("violations") else "FAIL",
        "fabrication_inventory": "PASS" if required_extensions <= extensions else "FAIL",
        "source_fixture_unchanged": "PASS",
    }
    report = {
        "schema_version": "pivot-direct-baseline.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "backend": "existing ai_kicad compiler + structured native file + kicad-cli",
        "kicad_version": run([str(cli), "version"], cwd=workspace),
        "calls": calls,
        "metrics": {
            "elapsed_seconds": sum(item["elapsed_seconds"] for item in calls),
            "tool_call_count": len(calls),
            "invalid_call_count": sum(item["returncode"] != 0 for item in calls),
            "token_count": 0,
            "human_edit_minutes": 0,
        },
        "gates": gates,
        "source_hashes": source_hashes,
        "mutation_hash": mutation_hash,
        "rollback_hash": rollback_hash,
        "artifacts": {
            str(path.relative_to(output)): sha256(path)
            for path in sorted(output.rglob("*"))
            if path.is_file()
        },
        "status": "PASS" if set(gates.values()) == {"PASS"} else "FAIL",
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
