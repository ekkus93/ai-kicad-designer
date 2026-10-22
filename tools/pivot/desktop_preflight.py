"""Record a migrated host without rewriting the historical toolchain lock."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from tools.check_m2h2_locked_toolchain import inspect_lock, runner_platform
from tools.pivot.experiment_paths import create_experiment_dir


def capture(root: Path, appdir: Path, experiment_id: str) -> Path:
    """Require all six original file hashes before issuing a separate host lock."""
    original_path = root / "fixtures/m1a/toolchain.lock.json"
    original_bytes = original_path.read_bytes()
    original = json.loads(original_bytes)
    host_lock = copy.deepcopy(original)
    appdir = appdir.resolve(strict=True)
    for section in ("executables", "libraries"):
        for item in host_lock[section]:
            item["path"] = str(appdir / Path(item["path"]).relative_to("/tmp/AppDir"))
    host_lock["platform"] = runner_platform()
    relocated_result = inspect_lock(host_lock, host_lock["platform"])
    original_result = inspect_lock(original, host_lock["platform"])
    output = create_experiment_dir(root, experiment_id)
    report = {
        "schema_version": "pivot-desktop-preflight.v1",
        "source_commit": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "historical_lock_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "historical_lock_result": original_result,
        "desktop_identity_result": relocated_result,
        "historical_lock_unchanged": original_path.read_bytes() == original_bytes,
        "scope": "New desktop runtime only; does not qualify the historical locked runner.",
    }
    (output / "preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    if not relocated_result["ok"]:
        raise RuntimeError(f"KiCad binary identity failed; see {output / 'preflight.json'}")
    (output / "desktop-toolchain.lock.json").write_text(json.dumps(host_lock, indent=2) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appdir", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    print(capture(Path(__file__).resolve().parents[2], args.appdir, args.experiment_id))


if __name__ == "__main__":
    main()
