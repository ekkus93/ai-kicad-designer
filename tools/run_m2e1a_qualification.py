"""Run the bounded M2e1a valid-regression and corrected-fixture qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import subprocess
import sys

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2b_build import build


HISTORICAL_V3_8_SHA256 = "4e0c1f1634a23870b5e50990da49e7f1696113f9544587677c8346a520ffdf1a"


def _cases() -> list[tuple[str, Path, str]]:
    return [
        *[
            (f"v2-{index}", ROOT / f"fixtures/m2blind/ir/H{index}.json", "valid-v2")
            for index in range(1, 9)
        ],
        *[
            (f"v3-{index}", ROOT / f"fixtures/m2blind_v3/ir/V3-{index}.json", "valid-v3")
            for index in range(1, 8)
        ],
        *[
            (f"probe-{path.stem}", path, "original-m2e1-probe")
            for path in sorted((ROOT / "fixtures/m2e1/ir").glob("*.json"))
        ],
        (
            "corrected-regulator-timer-led",
            ROOT / "fixtures/m2e1a/ir/regulator_timer_led_corrected.json",
            "corrected-v3-8-equivalent",
        ),
    ]


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(str(item.relative_to(path)).encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _normalized_svg(path: Path) -> str:
    return hashlib.sha256(
        re.sub(r"<title>.*?</title>", "<title/>", path.read_text()).encode()
    ).hexdigest()


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


def _historical_validation(output: Path) -> dict:
    path = ROOT / "fixtures/m2blind_v3/ir/V3-8.json"
    digest = _sha(path)
    if digest != HISTORICAL_V3_8_SHA256:
        raise RuntimeError("historical V3-8 preservation hash differs")
    try:
        validate(_json(path), assets())
    except InputError as exc:
        message = str(exc)
    else:
        raise RuntimeError("historical V3-8 unexpectedly passed power-source validation")
    required = ("POWER_ASSERTION_DRIVER_CONFLICT", "POWER_SOURCE_ASSERTION_REQUIRED")
    if any(code not in message for code in required):
        raise RuntimeError("historical V3-8 did not produce both required diagnostics")
    record = {
        "status": "invalid_authored_power",
        "path": str(path.relative_to(ROOT)),
        "sha256": digest,
        "diagnostic": message,
        "compiler_repair_attempted": False,
        "layout_attempted": False,
    }
    validation_dir = output / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    (validation_dir / "historical-v3-8-invalid.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "fixtures/m2e1a/qualification")
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    historical = _historical_validation(output)
    results = []
    for case_id, design, classification in _cases():
        runs = []
        signatures = []
        for index in range(1, 6):
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
            runs.append(
                {
                    "run": index,
                    "returncode": rc,
                    "path": str(actual.relative_to(ROOT)),
                    "failure": _json(actual / "reports/failure.json") if rc else None,
                }
            )
            if rc == 0:
                signatures.append(_signature(actual))
        reproducible = len(signatures) == 5 and all(
            signature == signatures[0] for signature in signatures[1:]
        )
        results.append(
            {
                "id": case_id,
                "classification": classification,
                "design": str(design.relative_to(ROOT)),
                "design_sha256": _sha(design),
                "accepted": all(run["returncode"] == 0 for run in runs) and reproducible,
                "reproducible": reproducible,
                "runs": runs,
                "signature": signatures[0] if signatures else None,
            }
        )
    protected_paths = [
        ROOT / "fixtures/m2blind_v3/corpus.v3.json",
        ROOT / "fixtures/m2blind_v3/ir/V3-8.json",
        ROOT / "fixtures/m2blind_v3/automated_results.json",
        ROOT / "fixtures/m2blind_v3/SUMMARY.md",
        ROOT / "fixtures/m2e1/SUMMARY.md",
    ]
    source_files = sorted((ROOT / "src/ai_kicad").glob("*.py"))
    payload = {
        "schema_version": "m2e1a.qualification.1",
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
        "historical_v3_8_validation": historical,
        "preserved_file_sha256": {
            str(path.relative_to(ROOT)): _sha(path) for path in protected_paths
        },
        "preserved_failed_v3_8_tree_sha256": _tree_sha(ROOT / "fixtures/m2e1/qualification/v3-8"),
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "total": len(results),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"accepted": payload["accepted"], "total": payload["total"]}))
    if payload["accepted"] != payload["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
