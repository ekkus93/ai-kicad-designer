"""Create the one-time M2f1 implementation/environment freeze before V4 authoring."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HISTORICAL = (
    "fixtures/m2blind",
    "fixtures/m2blind_v3",
    "fixtures/m2d1",
    "fixtures/m2e1",
    "fixtures/m2e1a",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_map(base: Path) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def map_digest(files: dict[str, str]) -> str:
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def main() -> None:
    forbidden = [HERE / "corpus.v4.json", HERE / "ir"]
    if any(path.exists() for path in forbidden):
        raise SystemExit("refusing to freeze after V4 corpus/IR authoring")

    tracked_raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    tracked = sorted(item.decode() for item in tracked_raw.split(b"\0") if item)
    tracked_files = {path: sha256(ROOT / path) for path in tracked}
    toolchain_path = ROOT / "fixtures/m1a/toolchain.lock.json"
    toolchain = json.loads(toolchain_path.read_text())
    external = {}
    for entry in [*toolchain["executables"], *toolchain.get("libraries", [])]:
        path = Path(entry["path"])
        actual = sha256(path) if path.is_file() else None
        external[entry["id"]] = {
            "path": str(path),
            "version": entry.get("version"),
            "exists": path.is_file(),
            "sha256": actual,
            "locked_sha256": entry["file_sha256"],
            "matches_lock": actual == entry["file_sha256"],
        }

    cpu_model = "unknown"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break

    history = {}
    for relative in HISTORICAL:
        files = file_map(ROOT / relative)
        history[relative] = {
            "file_count": len(files),
            "canonical_file_map_sha256": map_digest(files),
            "files": files,
        }

    locks = {
        "requirements": "requirements.lock",
        "pyproject": "pyproject.toml",
        "toolchain": "fixtures/m1a/toolchain.lock.json",
        "policy": "fixtures/m1a/policy.lock.json",
        "drafting": "fixtures/m1a/drafting.v1.json",
        "m1_assets": "fixtures/m1a/assets.lock.json",
        "m1_nc_assets": "fixtures/m1a/assets_nc.lock.json",
        "m2a_assets": "fixtures/m2a/assets.lock.json",
        "m2b_assets": "fixtures/m2b/assets.lock.json",
    }
    freeze = {
        "schema_version": "m2f1.implementation-freeze.v1",
        "evaluation": "M2f1 — corpus.v4 frozen blind qualification",
        "hash_algorithm": "sha256",
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status_porcelain_before_freeze": subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            text=True,
        ).splitlines(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "cache_tag": sys.implementation.cache_tag,
        },
        "platform": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_model": cpu_model,
            "os_release": Path("/etc/os-release").read_text(),
        },
        "environment_contract": {
            "locale": toolchain["environment"]["locale"],
            "timezone": toolchain["environment"]["timezone"],
            "host_timezone": os.environ.get("TZ", "America/Los_Angeles (session context)"),
        },
        "tracked_files": tracked_files,
        "tracked_file_count": len(tracked_files),
        "behavior_affecting_scope": "all tracked repository files at freeze time",
        "locks": {name: {"path": path, "sha256": sha256(ROOT / path)} for name, path in locks.items()},
        "toolchain": {"lock": toolchain, "external_files": external},
        "active_asset_files": {
            path: digest
            for path, digest in tracked_files.items()
            if path.endswith((".kicad_sym", ".lock.json")) and "assets" in path
        },
        "historical_evidence_before": history,
    }
    output = HERE / "implementation_freeze.json"
    output.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    (HERE / "implementation_freeze.sha256").write_text(
        f"{sha256(output)}  implementation_freeze.json\n"
    )
    print(json.dumps({"tracked": len(tracked_files), "sha256": sha256(output)}))


if __name__ == "__main__":
    main()
