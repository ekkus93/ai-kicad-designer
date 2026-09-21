"""Run and summarize five clean M2e1 regression/development builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import subprocess
import sys

from ai_kicad.m2a import ROOT
from ai_kicad.m2b_build import build


def _cases() -> list[tuple[str, Path, str]]:
    return [
        *[
            (f"v2-{index}", ROOT / f"fixtures/m2blind/ir/H{index}.json", "known-v2")
            for index in range(1, 9)
        ],
        *[
            (f"v3-{index}", ROOT / f"fixtures/m2blind_v3/ir/V3-{index}.json", "known-v3")
            for index in range(1, 9)
        ],
        *[
            (f"dev-{path.stem}", path, "development")
            for path in sorted((ROOT / "fixtures/m2e1/ir").glob("*.json"))
        ],
    ]


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_svg(path: Path) -> str:
    return hashlib.sha256(
        re.sub(r"<title>.*?</title>", "<title/>", path.read_text()).encode()
    ).hexdigest()


def _successful_signature(run: Path) -> dict:
    project = next((run / "project").glob("*.kicad_sch"))
    pro = project.with_suffix(".kicad_pro")
    erc = _json(run / "reports/erc.json")
    erc.pop("date", None)
    erc.pop("source", None)
    return {
        "schematic_sha256": _sha(project),
        "project_sha256": _sha(pro),
        "electrical": _json(run / "reports/electrical.json"),
        "erc": erc,
        "layout": _json(run / "reports/layout.json"),
        "composition": _json(run / "reports/composition.json"),
        "svg_normalized_sha256": _normalized_svg(next((run / "renders/schematic").glob("*.svg"))),
        "manifest_checks": _json(run / "reports/manifest.json")["checks"],
    }


def _failure_signature(run: Path) -> dict:
    signature = {"failure": _json(run / "reports/failure.json")}
    erc_path = run / "reports/erc.json"
    if erc_path.exists():
        erc = _json(erc_path)
        erc.pop("date", None)
        erc.pop("source", None)
        signature["erc"] = erc
    return signature


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "fixtures/m2e1/qualification")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for case_id, design, classification in _cases():
        runs = []
        signatures = []
        failure_signatures = []
        for index in range(1, 6):
            destination = args.out / case_id / f"run{index}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            rc = build(
                argparse.Namespace(
                    design=design,
                    target="schematic",
                    assets_lock=ROOT / "fixtures/m2b/assets.lock.json",
                    toolchain_lock=ROOT / "fixtures/m1a/toolchain.lock.json",
                    policy_lock=ROOT / "fixtures/m1a/policy.lock.json",
                    out=destination,
                )
            )
            actual = destination if rc == 0 else destination.with_name(destination.name + ".failed")
            failure = None
            if rc:
                failure = _json(actual / "reports/failure.json")
                failure_signatures.append(_failure_signature(actual))
            else:
                signatures.append(_successful_signature(actual))
            runs.append(
                {
                    "run": index,
                    "returncode": rc,
                    "path": str(actual.relative_to(ROOT)),
                    "failure": failure,
                }
            )
        reproducible = (
            len(signatures) == 5 and all(item == signatures[0] for item in signatures[1:])
        ) or (
            len(failure_signatures) == 5
            and all(item == failure_signatures[0] for item in failure_signatures[1:])
        )
        results.append(
            {
                "id": case_id,
                "classification": classification,
                "design": str(design.relative_to(ROOT)),
                "design_sha256": _sha(design),
                "accepted": all(item["returncode"] == 0 for item in runs) and reproducible,
                "reproducible": reproducible,
                "runs": runs,
                "signature": signatures[0] if signatures else failure_signatures[0],
            }
        )
    source_files = sorted((ROOT / "src/ai_kicad").glob("*.py"))
    payload = {
        "schema_version": "m2e1.qualification.1",
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": platform.platform(),
        "toolchain_lock_sha256": _sha(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "asset_lock_sha256": _sha(ROOT / "fixtures/m2b/assets.lock.json"),
        "policy_lock_sha256": _sha(ROOT / "fixtures/m1a/policy.lock.json"),
        "source_sha256": {str(path.relative_to(ROOT)): _sha(path) for path in source_files},
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "total": len(results),
    }
    (args.out / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"accepted": payload["accepted"], "total": payload["total"]}))


if __name__ == "__main__":
    main()
