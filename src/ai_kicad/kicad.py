"""KiCad 10.0.6 headless subprocess boundary."""

import json
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import subprocess
import time

from .assets import sha256
from .ir import InputError, load_json


class ToolFailure(RuntimeError):
    pass


def validate_toolchain(path: Path, python_lock: Path) -> Path:
    lock = load_json(path)
    if (
        set(lock)
        != {
            "schema_version",
            "platform",
            "executables",
            "python_lock_sha256",
            "configuration_digest",
            "environment",
        }
        or lock["schema_version"] != "m1.1"
    ):
        raise InputError("unsupported toolchain lock")
    if lock["python_lock_sha256"] != sha256(python_lock.read_bytes()):
        raise InputError("Python dependency lock hash mismatch")
    for requirement in python_lock.read_text().splitlines():
        package, pinned = requirement.split("==", 1)
        try:
            installed = version(package)
        except PackageNotFoundError as exc:
            raise InputError(f"missing Python dependency: {package}") from exc
        if installed != pinned:
            raise InputError(f"Python dependency {package}: expected {pinned}, found {installed}")
    if lock["environment"] != {"locale": "C", "timezone": "UTC"}:
        raise InputError("unsupported KiCad environment")
    entries = {item["id"]: item for item in lock["executables"]}
    if set(entries) != {"kicad-cli", "kicad-cli-binary"}:
        raise InputError("missing KiCad launcher or binary identity")
    for item in entries.values():
        executable = Path(item["path"])
        if (
            not executable.is_absolute()
            or not executable.is_file()
            or sha256(executable.read_bytes()) != item["file_sha256"]
            or item["version"] != "10.0.6"
        ):
            raise InputError("KiCad 10.0.6 executable identity mismatch")
    config_table = Path(__file__).resolve().parents[2] / "fixtures/m1a/sym-lib-table"
    if sha256(config_table.read_bytes()) != lock["configuration_digest"]:
        raise InputError("KiCad configuration hash mismatch")
    launcher = Path(entries["kicad-cli"]["path"])
    version_probe = subprocess.run(
        [str(launcher), "kicad-cli", "version"], capture_output=True, text=True, timeout=30
    )
    if version_probe.returncode or version_probe.stdout.strip() != "10.0.6":
        raise ToolFailure(
            f"locked KiCad version probe failed: {version_probe.stdout} {version_probe.stderr}"
        )
    return launcher


def run_headless(schematic: Path, launcher: Path, stage: Path) -> tuple[Path, Path, list[Path]]:
    reports = stage / "reports"
    raw = reports / "raw"
    renders = stage / "renders" / "schematic"
    config = stage / "config"
    for directory in (raw, renders, config):
        directory.mkdir(parents=True, exist_ok=True)
    netlist = reports / "netlist.xml"
    erc = reports / "erc.json"
    commands = [
        (
            "netlist",
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(netlist),
                str(schematic),
            ],
            netlist,
        ),
        (
            "erc",
            [
                "sch",
                "erc",
                "--format",
                "json",
                "--severity-all",
                "--exit-code-violations",
                "-o",
                str(erc),
                str(schematic),
            ],
            erc,
        ),
        ("svg", ["sch", "export", "svg", "-o", str(renders), str(schematic)], None),
    ]
    table = Path(__file__).resolve().parents[2] / "fixtures/m1a/sym-lib-table"
    configured = config / "kicad" / "10.0"
    configured.mkdir(parents=True, exist_ok=True)
    (configured / "sym-lib-table").write_bytes(table.read_bytes())
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(config)})
    start = time.time_ns()
    for label, args, output in commands:
        invocation = [str(launcher), "kicad-cli", *args]
        try:
            result = subprocess.run(
                invocation, capture_output=True, text=True, env=environment, timeout=90
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ToolFailure(f"{label} invocation failed: {exc}") from exc
        (raw / f"{label}.json").write_text(
            json.dumps(
                {
                    "argv": invocation,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            )
            + "\n"
        )
        if output is not None and (
            not output.is_file() or not output.stat().st_size or output.stat().st_mtime_ns < start
        ):
            raise ToolFailure(f"{label} report missing, empty or stale")
        if label != "erc" and result.returncode:
            raise ToolFailure(f"{label} failed with exit {result.returncode}: {result.stderr}")
        if label == "erc" and result.returncode not in (0, 5):
            raise ToolFailure(f"ERC tool failed with exit {result.returncode}: {result.stderr}")
    try:
        erc_data = json.loads(erc.read_text())
    except ValueError as exc:
        raise ToolFailure("malformed ERC report") from exc
    if not isinstance(erc_data, dict):
        raise ToolFailure("invalid ERC report schema")
    svgs = sorted(renders.glob("*.svg"))
    if not svgs or any(not svg.stat().st_size for svg in svgs):
        raise ToolFailure("SVG export missing or empty")
    return netlist, erc, svgs
