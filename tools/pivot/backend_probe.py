"""Record bounded, explicit MCP capability probes without an LLM judge."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.pivot.benchmark_runner import McpStdio
from tools.pivot.experiment_paths import create_experiment_dir


def inventory(path: Path) -> dict[str, str]:
    return {
        str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file() and not item.is_symlink()
    }


async def probe(args: argparse.Namespace) -> Path:
    root = Path(__file__).resolve().parents[2]
    experiment = create_experiment_dir(root, args.experiment_id)
    workspace = experiment / "workspace"
    shutil.copytree(args.project, workspace)
    before = inventory(workspace)
    config = experiment / "konnect.toml"
    config.write_text(
        f"kicad_cli = {json.dumps(str(args.cli.resolve()))}\n"
        f"project_dir = {json.dumps(str(workspace))}\n"
        'log_level = "warn"\n' + (f"ipc_address = {json.dumps(args.ipc)}\n" if args.ipc else "")
    )
    gui = None
    gui_log = None
    if args.gui_launcher:
        boards = list(workspace.glob("*.kicad_pcb"))
        if len(boards) != 1:
            raise ValueError("GUI probe requires exactly one native board")
        gui_log = (experiment / "gui.log").open("wb")
        gui = await asyncio.create_subprocess_exec(
            "dbus-run-session",
            "--",
            str(args.gui_launcher),
            "pcbnew",
            str(boards[0]),
            stdout=gui_log,
            stderr=gui_log,
        )
        await asyncio.sleep(3)
    client = McpStdio(
        [str(args.server.resolve()), "--config", str(config)], workspace, dict(os.environ)
    )
    records: list[dict] = []
    started = time.monotonic()
    try:
        initialized = await client.start(args.timeout)
        (experiment / "initialize.json").write_text(json.dumps(initialized, indent=2) + "\n")
        calls = [{"name": "load_toolset", "arguments": {"name": name}} for name in args.toolset]
        if args.plan:
            # The explicit caller-owned probe plan is data; no shell interpolation occurs.
            calls += json.loads(args.plan.read_text().replace("{workspace}", str(workspace)))
        for call in calls:
            call_started = time.monotonic()
            try:
                response = await client.request("tools/call", call, args.timeout)
                record = {"request": call, "response": response}
            except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
                record = {"request": call, "exception": type(exc).__name__, "detail": str(exc)}
            record["elapsed_seconds"] = time.monotonic() - call_started
            record["workspace_hashes"] = inventory(workspace)
            records.append(record)
            (experiment / "calls.json").write_text(json.dumps(records, indent=2) + "\n")
            if "exception" in record:
                break  # An uncertain mutation is never blindly retried.
        listing = await client.request("tools/list", {}, args.timeout)
        (experiment / "tools.json").write_text(json.dumps(listing, indent=2) + "\n")
    finally:
        exit_code = await client.close()
        if gui is not None and gui.returncode is None:
            gui.terminate()
            try:
                await asyncio.wait_for(gui.wait(), 5)
            except TimeoutError:
                gui.kill()
                await gui.wait()
        if gui_log is not None:
            gui_log.close()
        (experiment / "stderr.log").write_text("\n".join(client.stderr_lines) + "\n")
        after = inventory(workspace)
        summary = {
            "schema_version": "pivot-backend-probe.v1",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "server_sha256": hashlib.sha256(args.server.read_bytes()).hexdigest(),
            "elapsed_seconds": time.monotonic() - started,
            "exit_code": exit_code,
            "before": before,
            "after": after,
            "changed_inputs": [
                name for name, digest in before.items() if after.get(name) != digest
            ],
            "scope": "Raw capability observations; independent native checks are required.",
        }
        (experiment / "probe.json").write_text(json.dumps(summary, indent=2) + "\n")
    return experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--toolset", action="append", default=[])
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--ipc")
    parser.add_argument("--gui-launcher", type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    print(asyncio.run(probe(args)))


if __name__ == "__main__":
    main()
