"""Isolated ngspice transient runner for explicitly supported analog fragments."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class SpiceError(RuntimeError):
    pass


def simulate_rc_charge(
    ngspice: Path,
    workspace: Path,
    *,
    supply_v: float,
    resistance_ohm: float,
    capacitance_f: float,
    stop_s: float,
) -> dict:
    if min(supply_v, resistance_ohm, capacitance_f, stop_s) <= 0:
        raise SpiceError("simulation inputs must be positive")
    workspace.mkdir(parents=True, exist_ok=False)
    netlist = workspace / "rc-charge.cir"
    output = workspace / "timing.dat"
    netlist.write_text(
        "RC timing charge\n"
        f"V1 vcc 0 {supply_v}\n"
        f"R1 vcc timing {resistance_ohm}\n"
        f"C1 timing 0 {capacitance_f} ic=0\n"
        f".tran {stop_s / 2000} {stop_s} uic\n"
        ".control\n"
        "set filetype=ascii\n"
        "run\n"
        f"wrdata {output} time v(timing)\n"
        "quit\n"
        ".endc\n"
        ".end\n"
    )
    result = subprocess.run(
        [str(ngspice), "-b", str(netlist)],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode or not output.is_file():
        raise SpiceError(result.stderr or result.stdout)
    samples = []
    for line in output.read_text().splitlines():
        values = [float(value) for value in line.split()]
        samples.append((values[0], values[-1]))
    threshold = supply_v * 2 / 3
    crossing = next((time for time, voltage in samples if voltage >= threshold), None)
    if crossing is None:
        raise SpiceError("transient did not reach two-thirds threshold")
    return {
        "schema_version": "spice-transient.v1",
        "status": "PASS",
        "ngspice_sha256": hashlib.sha256(ngspice.read_bytes()).hexdigest(),
        "netlist_sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
        "sample_count": len(samples),
        "two_thirds_crossing_s": crossing,
        "analytical_crossing_s": -resistance_ohm * capacitance_f * __import__("math").log(1 / 3),
        "limitations": [
            "This verifies the passive timing-node charge fragment, not the complete NE555 macro-model.",
            "Parasitics, temperature, component distributions and physical behavior are not modeled.",
        ],
    }
