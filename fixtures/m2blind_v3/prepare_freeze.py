"""Create the one-time M2d2 implementation and environment freeze.

This script is evaluation infrastructure only.  It does not import or alter the
compiler and must be run before authoring the corpus.v3 inputs.
"""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item.decode() for item in output.split(b"\0") if item]


def evidence_tree(relative: str) -> dict[str, object]:
    base = ROOT / relative
    files = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {
        "file_count": len(files),
        "canonical_file_map_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": files,
    }


def main() -> None:
    if (HERE / "corpus.v3.json").exists() or (HERE / "ir").exists():
        raise SystemExit("refusing to freeze after V3 corpus/IR authoring")

    tracked = tracked_files()
    prefixes = (
        "src/ai_kicad/",
        "tests/",
        "fixtures/m1a/assets/",
        "fixtures/m2a/assets/",
    )
    exact = {
        "pyproject.toml",
        "requirements.lock",
        "fixtures/m1a/assets.lock.json",
        "fixtures/m1a/assets_nc.lock.json",
        "fixtures/m1a/drafting.v1.json",
        "fixtures/m1a/policy.lock.json",
        "fixtures/m1a/toolchain.lock.json",
        "fixtures/m1a/divider.json",
        "fixtures/m1a/divider_nc.json",
        "fixtures/m1a/sym-lib-table",
        "fixtures/m2a/assets.lock.json",
        "fixtures/m2a/dual_buffer.json",
        "fixtures/m2a/sym-lib-table",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/EVALUATION_PLAN.md",
        "docs/SCHEMATIC_LAYOUT_SPEC.md",
        "docs/CIRCUIT_IR_SPEC.md",
        "docs/KICAD_INTEGRATION_SPEC.md",
    }
    behavior_files = sorted(
        path
        for path in tracked
        if path in exact or path.startswith(prefixes) or path.startswith("fixtures/m2b/")
    )

    toolchain = json.loads((ROOT / "fixtures/m1a/toolchain.lock.json").read_text())
    external = {}
    for entry in [*toolchain["executables"], *toolchain.get("libraries", [])]:
        path = Path(entry["path"])
        external[entry["id"]] = {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": sha256(path) if path.is_file() else None,
            "locked_sha256": entry["file_sha256"],
            "matches_lock": path.is_file() and sha256(path) == entry["file_sha256"],
            **({"version": entry["version"]} if "version" in entry else {}),
        }

    cpu_model = "unknown"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break

    freeze = {
        "schema_version": "m2d2.implementation-freeze.v1",
        "evaluation": "M2d2 — corpus.v3 frozen blind composition qualification",
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
        "files": {path: sha256(ROOT / path) for path in behavior_files},
        "file_count": len(behavior_files),
        "locks": {
            "requirements": sha256(ROOT / "requirements.lock"),
            "toolchain": sha256(ROOT / "fixtures/m1a/toolchain.lock.json"),
            "policy": sha256(ROOT / "fixtures/m1a/policy.lock.json"),
            "drafting": sha256(ROOT / "fixtures/m1a/drafting.v1.json"),
            "m1_assets": sha256(ROOT / "fixtures/m1a/assets.lock.json"),
            "m2a_assets": sha256(ROOT / "fixtures/m2a/assets.lock.json"),
            "m2b_assets": sha256(ROOT / "fixtures/m2b/assets.lock.json"),
        },
        "toolchain": {
            "lock": toolchain,
            "external_files": external,
        },
        "active_asset_files": {
            path: sha256(ROOT / path) for path in behavior_files if path.endswith(".kicad_sym")
        },
        "historical_evidence_before": {
            "fixtures/m2blind": evidence_tree("fixtures/m2blind"),
            "fixtures/m2d1": evidence_tree("fixtures/m2d1"),
        },
    }
    output = HERE / "implementation_freeze.json"
    output.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    (HERE / "implementation_freeze.sha256").write_text(
        f"{sha256(output)}  implementation_freeze.json\n"
    )
    print(f"froze {len(behavior_files)} tracked behavior/evaluation files")
    print(sha256(output))


if __name__ == "__main__":
    main()
