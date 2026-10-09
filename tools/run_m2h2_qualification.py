"""Run M2h2's fixed positive matrix in fresh locked KiCad directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_composition_qualification_observation import observe_composition_evidence
from ai_kicad.m2_semantics import semantic_plan
from run_m2g2_qualification import (
    _anti_overfitting_audit,
    _build,
    _cases,
    _erc_violations,
    _json,
    _preservation_audit,
    _sha,
    _signature,
)


def cases() -> list[tuple[str, Path, str]]:
    previous = _cases()
    regressions = [
        (f"v6-{index}", ROOT / f"fixtures/m2blind_v6/ir/V6-{index}.json", "v6-regression")
        for index in range(1, 9)
    ]
    development = [
        (path.stem, path, "development-stress" if "long_fields" in path.stem else "development")
        for path in sorted((ROOT / "fixtures/m2h2/development").glob("dp*.json"))
        if not path.name.endswith(".expected.json")
    ]
    result = previous + regressions + development
    if len(result) != 56 or len({item[0] for item in result}) != len(result):
        raise RuntimeError("M2h2 positive inventory must contain 56 distinct cases")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    resolved = assets()
    for case_id, design, classification in cases():
        plan = semantic_plan(validate(json.loads(design.read_text()), resolved), resolved)
        signatures = []
        runs = []
        for index in range(1, 6):
            destination = output / case_id / f"run{index}"
            started = time.perf_counter()
            rc = _build(design, destination)
            actual = destination if rc == 0 else destination.with_name(destination.name + ".failed")
            record = {
                "run": index,
                "returncode": rc,
                "path": str(actual.relative_to(ROOT)),
                "runtime_seconds": round(time.perf_counter() - started, 6),
            }
            if rc == 0:
                signature = _signature(actual)
                signatures.append(signature)
                composition_observer = observe_composition_evidence(
                    plan, signature["composition"]
                ).as_dict()
                record.update(
                    electrical_status=signature["electrical"]["status"],
                    electrical_diagnostics=signature["electrical"]["diagnostics"],
                    erc_violation_count=_erc_violations(signature["erc"]),
                    serialized_scene_verified=signature["composition"]["obligation_certificate"][
                        "serialized_scene_verified"
                    ],
                    composition_observer=composition_observer,
                    layout=signature["layout"],
                )
            else:
                record["failure"] = _json(actual / "reports/failure.json")
            runs.append(record)
            print(json.dumps({"case": case_id, "run": index, "returncode": rc}), flush=True)
        reproducible = len(signatures) == 5 and all(s == signatures[0] for s in signatures[1:])
        observer_reproducible = len(runs) == 5 and all(
            run.get("composition_observer") == runs[0].get("composition_observer")
            for run in runs[1:]
        )
        accepted = reproducible and observer_reproducible and all(
            run["returncode"] == 0
            and run["electrical_status"] == "pass"
            and not run["electrical_diagnostics"]
            and run["erc_violation_count"] == 0
            and run["serialized_scene_verified"] == "pass"
            and run["composition_observer"]["passed"]
            for run in runs
        )
        results.append(
            {
                "id": case_id,
                "classification": classification,
                "design": str(design.relative_to(ROOT)),
                "design_sha256": _sha(design),
                "accepted": accepted,
                "reproducible": reproducible,
                "composition_observer_reproducible": observer_reproducible,
                "runs": runs,
                "signature": signatures[0] if signatures else None,
            }
        )
        print(
            json.dumps(
                {
                    "kind": "m2h2.qualification-case-summary.1",
                    "id": case_id,
                    "accepted": accepted,
                    "reproducible": reproducible,
                    "composition_observer_passed": all(
                        run.get("composition_observer", {}).get("passed", False)
                        for run in runs
                    ),
                    "runs": [run["path"] for run in runs],
                    "failures": [run.get("failure") for run in runs if run["returncode"]],
                    "layout": signatures[0]["layout"] if signatures else None,
                    "canonical_lengths_nm": {
                        tree["net"]: tree["length_nm"]
                        for tree in (
                            signatures[0]["composition"]["canonical_trees"] if signatures else []
                        )
                    },
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        (output / "progress.json").write_text(json.dumps(results, indent=2) + "\n")
    invalid = ROOT / "fixtures/m2blind_v3/ir/V3-8.json"
    invalid_path = output / "v3-8-invalid/run1"
    invalid_rc = _build(invalid, invalid_path)
    preservation = _preservation_audit()
    anti_overfitting = _anti_overfitting_audit()
    payload = {
        "schema_version": "m2h2.qualification.1",
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "python": sys.version,
        "toolchain_lock_sha256": _sha(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "asset_lock_sha256": _sha(ROOT / "fixtures/m2b/assets.lock.json"),
        "policy_lock_sha256": _sha(ROOT / "fixtures/m1a/policy.lock.json"),
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha(path)
            for path in sorted((ROOT / "src/ai_kicad").glob("*.py"))
        },
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "total": len(results),
        "builds": len(results) * 5 + 1,
        "negative_v3_8_accepted": invalid_rc != 0,
        "historical_preservation": preservation,
        "anti_overfitting": anti_overfitting,
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "results"},
            separators=(",", ":"),
        ),
        flush=True,
    )
    print(
        json.dumps(
            {key: payload[key] for key in ("accepted", "total", "builds", "negative_v3_8_accepted")}
        ),
        flush=True,
    )
    if payload["accepted"] != payload["total"] or invalid_rc == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
