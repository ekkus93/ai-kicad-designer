"""Probe the isolated KiCad development headless IPC server."""

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

from pivot.experiment_paths import create_experiment_dir


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--launcher", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = create_experiment_dir(root, args.experiment_id)
    workspace = output / "workspace"
    source = root / "fixtures/pivot/runs/reference_555_led_flasher_v1_run3/project"
    shutil.copytree(source, workspace)
    socket = Path(f"/tmp/kicad-pivot-dev-{os.getpid()}.sock")
    locked = json.loads((root / "fixtures/m1a/toolchain.lock.json").read_text())
    locked_before = {
        item["id"]: sha256(Path(item["path"]))
        for section in ("executables", "libraries")
        for item in locked[section]
    }
    command = [
        str(args.launcher.resolve()),
        "kicad-cli",
        "api-server",
        "--socket",
        str(socket),
        str(workspace / "Reference555LedFlasher.kicad_sch"),
    ]
    log = (output / "server.log").open("wb")
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            if socket.exists():
                break
            if process.poll() is not None:
                raise RuntimeError("development API server exited before creating its socket")
            time.sleep(0.05)
        else:
            raise TimeoutError("development API socket did not appear")

        from kipy import KiCad

        client = KiCad(socket_path=f"ipc://{socket}", client_name="ai-kicad-pivot-probe")
        client.ping()
        version = repr(client.get_version())
        api_version = repr(client.get_api_version())
        schematic = client.get_schematic()
        symbols = schematic.get_symbols()
        original_values = {symbol.reference: symbol.value for symbol in symbols}
        original_net_count = len(schematic.get_netlist())
        timer = next(symbol for symbol in symbols if symbol.reference == "U1")

        dropped = schematic.begin_commit()
        timer.value = "NE555D-dropped-probe"
        schematic.update_items(timer)
        schematic.drop_commit(dropped)
        value_after_drop = next(
            symbol.value for symbol in schematic.get_symbols() if symbol.reference == "U1"
        )

        applied = schematic.begin_commit()
        timer = next(symbol for symbol in schematic.get_symbols() if symbol.reference == "U1")
        timer.value = "NE555D-applied-probe"
        schematic.update_items(timer)
        schematic.push_commit(applied, "isolated development API probe")
        value_after_push = next(
            symbol.value for symbol in schematic.get_symbols() if symbol.reference == "U1"
        )

        restored = schematic.begin_commit()
        timer = next(symbol for symbol in schematic.get_symbols() if symbol.reference == "U1")
        timer.value = original_values["U1"]
        schematic.update_items(timer)
        schematic.push_commit(restored, "restore probe value")
        schematic.save()
        final_values = {symbol.reference: symbol.value for symbol in schematic.get_symbols()}
        final_net_count = len(schematic.get_netlist())
        unsupported = []
        try:
            client.get_board()
        except Exception as exc:  # Exact API error is part of the capability inventory.
            unsupported.append(
                {
                    "operation": "get_board_without_loaded_board",
                    "error": type(exc).__name__,
                    "detail": str(exc),
                }
            )

        gates = {
            "headless_server_started": "PASS",
            "version_identified": "PASS" if version.startswith("10.99.0") else "FAIL",
            "schematic_read": "PASS" if set(original_values) >= {"U1", "R1", "R2"} else "FAIL",
            "netlist_read": "PASS" if original_net_count == 7 else "FAIL",
            "dropped_batch_not_applied": "PASS"
            if value_after_drop == original_values["U1"]
            else "FAIL",
            "pushed_batch_readback": "PASS"
            if value_after_push == "NE555D-applied-probe"
            else "FAIL",
            "restored_and_saved": "PASS" if final_values == original_values else "FAIL",
            "connectivity_preserved": "PASS" if final_net_count == original_net_count else "FAIL",
        }
        report = {
            "schema_version": "pivot-kicad-development-probe.v1",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_commit": subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip(),
            "command": command,
            "binary_sha256": sha256(args.launcher),
            "version": version,
            "api_version": api_version,
            "python_binding_version": "0.9.0.dev0",
            "python_binding_api_commit": "dcadf9baa30d43d7d1b3d0342345f05ec0da26e1",
            "original_values": original_values,
            "value_after_drop": value_after_drop,
            "value_after_push": value_after_push,
            "final_values": final_values,
            "original_net_count": original_net_count,
            "final_net_count": final_net_count,
            "unsupported": unsupported,
            "gates": gates,
            "status": "PASS" if set(gates.values()) == {"PASS"} else "FAIL",
            "scope": "Isolated KiCad 10.99 development snapshot; this is not a released KiCad 11 compatibility claim.",
        }
        (output / "capability_inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        locked_after = {
            item["id"]: sha256(Path(item["path"]))
            for section in ("executables", "libraries")
            for item in locked[section]
        }
        (output / "locked_kicad_integrity.json").write_text(
            json.dumps(
                {
                    "before": locked_before,
                    "after": locked_after,
                    "unchanged": locked_before == locked_after,
                    "expected": {
                        item["id"]: item["file_sha256"]
                        for section in ("executables", "libraries")
                        for item in locked[section]
                    },
                },
                indent=2,
            )
            + "\n"
        )
    print(output)


if __name__ == "__main__":
    main()
