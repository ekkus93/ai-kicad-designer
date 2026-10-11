"""Fail closed before locked KiCad qualification if pinned binaries disappear.

This preflight never installs a substitute toolchain or changes the pinned lock.
It only inspects the runner, byte hashes and executable version.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "fixtures/m1a/toolchain.lock.json"


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runner_platform() -> dict[str, str | None]:
    cpu_model = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        None,
    )
    return {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_model": cpu_model,
    }


def inspect_lock(lock: dict, current: dict) -> dict:
    """Produce machine-readable, exact-hash runner diagnostics; never waive a mismatch."""
    mismatches: list[dict] = []
    for field, expected in lock["platform"].items():
        if current.get(field) != expected:
            mismatches.append(
                {"id": f"platform.{field}", "expected": expected, "actual": current.get(field)}
            )
    files = []
    for section in ("executables", "libraries"):
        for entry in lock[section]:
            path = Path(entry["path"])
            expected = entry["file_sha256"]
            actual = sha256_file(path)
            files.append({"section": section, "id": entry["id"], "path": str(path),
                          "present": actual is not None, "sha256_matches": actual == expected})
            if actual != expected:
                mismatches.append(
                    {"id": entry["id"], "path": str(path), "expected_sha256": expected,
                     "actual_sha256": actual}
                )
    launcher = Path(lock["executables"][0]["path"])
    if sha256_file(launcher) == lock["executables"][0]["file_sha256"]:
        try:
            probe = subprocess.run(
                [str(launcher), "kicad-cli", "version"],
                check=False, capture_output=True, text=True, timeout=30,
            )
            expected_version = lock["executables"][0]["version"]
            if probe.returncode != 0 or probe.stdout.strip() != expected_version:
                mismatches.append(
                    {"id": "version_probe", "expected": expected_version,
                     "returncode": probe.returncode, "actual": probe.stdout.strip()}
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            mismatches.append({"id": "version_probe", "error": type(exc).__name__})
    return {"kind": "m2h2.locked-toolchain-preflight.1",
            "ok": not mismatches, "files": files, "mismatches": mismatches}


def main() -> int:
    lock = json.loads(LOCK.read_text())
    result = inspect_lock(lock, runner_platform())
    print("LOCKED_KICAD_TOOLCHAIN_PREFLIGHT=" + json.dumps(result, sort_keys=True))
    if not result["ok"]:
        print("LOCKED_KICAD_TOOLCHAIN_UNAVAILABLE: Restore exactly the byte-pinned "
              "KiCad 10.0.6 files specified in fixtures/m1a/toolchain.lock.json "
              "before retrying; do not weaken hashes or substitute an unverified build.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
