"""Run M2f2 regressions and five-build changed-output qualification."""

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


PROTECTED_ROOTS = (
    "fixtures/m2blind",
    "fixtures/m2blind_v3",
    "fixtures/m2blind_v4",
    "fixtures/m2d1",
    "fixtures/m2e1",
)


def _cases() -> list[tuple[str, Path, str, int]]:
    prior = [
        *[
            (f"v2-{index}", ROOT / f"fixtures/m2blind/ir/H{index}.json", "known-v2", 1)
            for index in range(1, 9)
        ],
        *[
            (
                f"v3-{index}",
                ROOT / f"fixtures/m2blind_v3/ir/V3-{index}.json",
                "valid-known-v3",
                1,
            )
            for index in range(1, 8)
        ],
        (
            "v3-8-corrected",
            ROOT / "fixtures/m2e1a/ir/regulator_timer_led_corrected.json",
            "corrected-known-v3",
            1,
        ),
        *[
            (f"m2e1-{path.stem}", path, "m2e1-probe", 1)
            for path in sorted((ROOT / "fixtures/m2e1/ir").glob("*.json"))
        ],
    ]
    changed = [
        *[
            (
                f"v4-{index}",
                ROOT / f"fixtures/m2blind_v4/ir/V4-{index}.json",
                "known-v4-regression",
                5,
            )
            for index in range(1, 9)
        ],
        *[
            (f"probe-{path.stem}", path, "m2f2-probe", 5)
            for path in sorted((ROOT / "fixtures/m2f2/ir").glob("*.json"))
        ],
    ]
    return prior + changed


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_svg(path: Path) -> str:
    normalized = re.sub(r"<title>.*?</title>", "<title/>", path.read_text())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _signature(run: Path) -> dict:
    schematic = next((run / "project").glob("*.kicad_sch"))
    project = schematic.with_suffix(".kicad_pro")
    erc = _json(run / "reports/erc.json")
    erc.pop("date", None)
    erc.pop("source", None)
    return {
        "schematic_sha256": _sha(schematic),
        "project_sha256": _sha(project),
        "electrical": _json(run / "reports/electrical.json"),
        "erc": erc,
        "layout": _json(run / "reports/layout.json"),
        "composition": _json(run / "reports/composition.json"),
        "svg_normalized_sha256": _normalized_svg(next((run / "renders/schematic").glob("*.svg"))),
        "manifest_checks": _json(run / "reports/manifest.json")["checks"],
    }


def _erc_violations(erc: dict) -> int:
    return sum(len(sheet["violations"]) for sheet in erc["sheets"])


def _historical_v4_schematic(case_id: str) -> Path:
    ordinal = case_id.rsplit("-", 1)[1]
    root = ROOT / "fixtures/m2blind_v4/runs" / f"V4-{ordinal}"
    run = root / ("run1.failed" if ordinal == "7" else "run1")
    return next((run / "project").glob("*.kicad_sch"))


def _preservation_audit() -> dict:
    changed = subprocess.check_output(
        ["git", "status", "--short", "--", *PROTECTED_ROOTS],
        cwd=ROOT,
        text=True,
    ).splitlines()
    return {"roots": list(PROTECTED_ROOTS), "changed_paths": changed, "pass": not changed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "fixtures/m2f2/qualification")
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty qualification directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    results = []
    for case_id, design, classification, run_count in _cases():
        runs = []
        signatures = []
        for index in range(1, run_count + 1):
            destination = output / case_id / f"run{index}"
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
            run_record = {
                "run": index,
                "returncode": rc,
                "path": str(actual.relative_to(ROOT)),
                "failure": _json(actual / "reports/failure.json") if rc else None,
            }
            if rc == 0:
                signature = _signature(actual)
                signatures.append(signature)
                run_record.update(
                    electrical_status=signature["electrical"]["status"],
                    electrical_diagnostics=signature["electrical"]["diagnostics"],
                    erc_violation_count=_erc_violations(signature["erc"]),
                    layout=signature["layout"],
                )
            runs.append(run_record)
        reproducible = len(signatures) == run_count and all(
            signature == signatures[0] for signature in signatures[1:]
        )
        gates_pass = bool(signatures) and all(
            run["returncode"] == 0
            and run["electrical_status"] == "pass"
            and not run["electrical_diagnostics"]
            and run["erc_violation_count"] == 0
            for run in runs
        )
        result = {
            "id": case_id,
            "classification": classification,
            "design": str(design.relative_to(ROOT)),
            "design_sha256": _sha(design),
            "run_count": run_count,
            "accepted": gates_pass and reproducible,
            "reproducible": reproducible,
            "runs": runs,
            "signature": signatures[0] if signatures else None,
        }
        if classification == "known-v4-regression" and signatures:
            old = _historical_v4_schematic(case_id)
            result["historical_schematic_sha256"] = _sha(old)
            result["schematic_changed_from_frozen_v4"] = (
                result["historical_schematic_sha256"] != signatures[0]["schematic_sha256"]
            )
        results.append(result)
        print(json.dumps({"id": case_id, "accepted": result["accepted"]}), flush=True)

    preservation = _preservation_audit()
    payload = {
        "schema_version": "m2f2.qualification.1",
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
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha(path)
            for path in sorted((ROOT / "src/ai_kicad").glob("*.py"))
        },
        "historical_preservation": preservation,
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "total": len(results),
        "builds": sum(item["run_count"] for item in results),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "accepted": payload["accepted"],
                "total": payload["total"],
                "builds": payload["builds"],
                "historical_preservation": preservation["pass"],
            }
        )
    )
    if payload["accepted"] != payload["total"] or not preservation["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
