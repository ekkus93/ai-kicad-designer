"""Run the complete five-build M2g2 qualification matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import subprocess
import sys
import time

from ai_kicad.m2a import ROOT
from ai_kicad.m2b_build import build


PROTECTED_ROOTS = (
    "fixtures/m2blind",
    "fixtures/m2blind_v3",
    "fixtures/m2blind_v4",
    "fixtures/m2blind_v5",
    "fixtures/m2d1",
    "fixtures/m2e1",
    "fixtures/m2e1a",
    "fixtures/m2f2",
)


def _cases() -> list[tuple[str, Path, str]]:
    return [
        *[
            (f"v2-{index}", ROOT / f"fixtures/m2blind/ir/H{index}.json", "known-v2")
            for index in range(1, 9)
        ],
        *[
            (
                f"v3-{index}",
                ROOT / f"fixtures/m2blind_v3/ir/V3-{index}.json",
                "valid-known-v3",
            )
            for index in range(1, 8)
        ],
        (
            "v3-8-corrected",
            ROOT / "fixtures/m2e1a/ir/regulator_timer_led_corrected.json",
            "corrected-known-v3",
        ),
        *[
            (
                f"v4-{index}",
                ROOT / f"fixtures/m2blind_v4/ir/V4-{index}.json",
                "known-v4",
            )
            for index in range(1, 9)
        ],
        *[
            (f"m2e1-{path.stem}", path, "m2e1-probe")
            for path in sorted((ROOT / "fixtures/m2e1/ir").glob("*.json"))
        ],
        *[
            (f"m2f2-{path.stem}", path, "m2f2-probe")
            for path in sorted((ROOT / "fixtures/m2f2/ir").glob("*.json"))
        ],
        *[
            (
                f"v5-{index}",
                ROOT / f"fixtures/m2blind_v5/ir/V5-{index}.json",
                "known-v5-regression",
            )
            for index in range(1, 9)
        ],
        *[
            (case_id, ROOT / f"fixtures/m2g2/probes/{case_id}.json", "m2g2-probe")
            for case_id in (
                "dual_regulator_mixed_loads",
                "passive_two_level_fanout",
                "timer_split_filtered_gain_indicator",
            )
        ],
        (
            "passive_two_level_fanout_long_fields",
            ROOT / "fixtures/m2g2/probes/passive_two_level_fanout_long_fields.json",
            "m2g2-stress-long-fields",
        ),
        (
            "timer_split_filtered_gain_indicator_unit_exchange",
            ROOT / "fixtures/m2g2/probes/timer_split_filtered_gain_indicator_unit_exchange.json",
            "m2g2-stress-unit-exchange",
        ),
    ]


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
        "layout_attempts": _json(run / "reports/layout_attempts.json"),
        "svg_normalized_sha256": _normalized_svg(next((run / "renders/schematic").glob("*.svg"))),
        "manifest_checks": _json(run / "reports/manifest.json")["checks"],
    }


def _erc_violations(erc: dict) -> int:
    return sum(len(sheet["violations"]) for sheet in erc["sheets"])


def _preservation_audit() -> dict:
    changed = subprocess.check_output(
        ["git", "status", "--short", "--", *PROTECTED_ROOTS],
        cwd=ROOT,
        text=True,
    ).splitlines()
    paths = subprocess.check_output(
        ["git", "ls-files", "--", *PROTECTED_ROOTS], cwd=ROOT, text=True
    ).splitlines()
    head = hashlib.sha256()
    worktree = hashlib.sha256()
    for relative in paths:
        encoded = relative.encode() + b"\0"
        head.update(encoded)
        head.update(subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT))
        worktree.update(encoded)
        worktree.update((ROOT / relative).read_bytes())
    return {
        "roots": list(PROTECTED_ROOTS),
        "tracked_file_count": len(paths),
        "head_aggregate_sha256": head.hexdigest(),
        "worktree_aggregate_sha256": worktree.hexdigest(),
        "changed_paths": changed,
        "pass": not changed and head.digest() == worktree.digest(),
    }


def _anti_overfitting_audit() -> dict:
    forbidden = re.compile(
        r"V5-[1-8]|dual_regulator_mixed_loads|passive_two_level_fanout|"
        r"timer_split_filtered_gain_indicator|corpus\.v6|cp[-_ ]?sat|ortools",
        re.IGNORECASE,
    )
    findings = []
    for path in sorted((ROOT / "src/ai_kicad").glob("m2*.py")):
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if forbidden.search(line):
                findings.append(f"{path.relative_to(ROOT)}:{line_number}:{line.strip()}")
    return {
        "scope": "active M2 production modules",
        "forbidden_patterns": forbidden.pattern,
        "findings": findings,
        "pass": not findings,
        "cp_sat_introduced": any(
            "sat" in finding.lower() or "ortools" in finding.lower() for finding in findings
        ),
    }


def _build(design: Path, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    return build(
        argparse.Namespace(
            design=design,
            target="schematic",
            assets_lock=ROOT / "fixtures/m2b/assets.lock.json",
            toolchain_lock=ROOT / "fixtures/m1a/toolchain.lock.json",
            policy_lock=ROOT / "fixtures/m1a/policy.lock.json",
            out=destination,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "fixtures/m2g2/qualification")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty qualification directory: {output}")
    if args.runs != 5:
        raise SystemExit("M2g2 qualification requires exactly five runs")
    output.mkdir(parents=True, exist_ok=True)

    results = []
    for case_id, design, classification in _cases():
        runs = []
        signatures = []
        for index in range(1, 6):
            destination = output / case_id / f"run{index}"
            started = time.perf_counter()
            rc = _build(design, destination)
            elapsed = time.perf_counter() - started
            actual = destination if rc == 0 else destination.with_name(destination.name + ".failed")
            record = {
                "run": index,
                "returncode": rc,
                "path": str(actual.relative_to(ROOT)),
                "failure": _json(actual / "reports/failure.json") if rc else None,
                "runtime_seconds": round(elapsed, 6),
            }
            if rc == 0:
                signature = _signature(actual)
                signatures.append(signature)
                record.update(
                    electrical_status=signature["electrical"]["status"],
                    electrical_diagnostics=signature["electrical"]["diagnostics"],
                    erc_violation_count=_erc_violations(signature["erc"]),
                    layout=signature["layout"],
                    attempt_count=len(signature["layout_attempts"]),
                )
            runs.append(record)
        reproducible = len(signatures) == 5 and all(
            signature == signatures[0] for signature in signatures[1:]
        )
        gates_pass = len(signatures) == 5 and all(
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
            "accepted": gates_pass and reproducible,
            "reproducible": reproducible,
            "runs": runs,
            "signature": signatures[0] if signatures else None,
        }
        results.append(result)
        print(json.dumps({"id": case_id, "accepted": result["accepted"]}), flush=True)

    invalid_design = ROOT / "fixtures/m2blind_v3/ir/V3-8.json"
    invalid_destination = output / "v3-8-invalid" / "run1"
    invalid_rc = _build(invalid_design, invalid_destination)
    invalid_actual = (
        invalid_destination
        if invalid_rc == 0
        else invalid_destination.with_name(invalid_destination.name + ".failed")
    )
    invalid = {
        "id": "v3-8-invalid",
        "design": str(invalid_design.relative_to(ROOT)),
        "returncode": invalid_rc,
        "accepted_as_negative": invalid_rc != 0,
        "failure": _json(invalid_actual / "reports/failure.json") if invalid_rc else None,
    }
    preservation = _preservation_audit()
    anti_overfitting = _anti_overfitting_audit()
    successful_runs = [run for result in results for run in result["runs"] if not run["returncode"]]
    metric_names = (
        "observed_content_width_mm",
        "observed_content_height_mm",
        "observed_wire_length_mm",
        "observed_feedback_span_mm",
        "observed_motif_fragmentation_mm",
        "observed_support_locality_mm",
        "observed_page_utilization",
        "layout_attempt_count",
        "layout_repair_count",
    )
    worst_metrics = {
        metric: max(
            (
                {"case": result["id"], "run": run["run"], "value": run["layout"].get(metric)}
                for result in results
                for run in result["runs"]
                if not run["returncode"] and isinstance(run["layout"].get(metric), (int, float))
            ),
            key=lambda item: item["value"],
            default=None,
        )
        for metric in metric_names
    }
    envelope_prediction_errors = [
        {
            "case": result["id"],
            "predicted_width_mm": result["signature"]["layout"]["final_content_width_mm"],
            "observed_width_mm": result["signature"]["layout"]["observed_content_width_mm"],
            "width_delta_mm": round(
                result["signature"]["layout"]["observed_content_width_mm"]
                - result["signature"]["layout"]["final_content_width_mm"],
                6,
            ),
            "predicted_height_mm": result["signature"]["layout"]["final_content_height_mm"],
            "observed_height_mm": result["signature"]["layout"]["observed_content_height_mm"],
            "height_delta_mm": round(
                result["signature"]["layout"]["observed_content_height_mm"]
                - result["signature"]["layout"]["final_content_height_mm"],
                6,
            ),
        }
        for result in results
        if result["signature"]
    ]
    payload = {
        "schema_version": "m2g2.qualification.1",
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
        "anti_overfitting": anti_overfitting,
        "engineering_inspection": {
            "status": "pending_human",
            "scope": [
                "support association",
                "feedback and timing clarity",
                "fanout tracing",
                "required field readability",
            ],
        },
        "negative": invalid,
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "positive_base_cases": sum(
            not item["classification"].startswith("m2g2-stress") for item in results
        ),
        "stress_cases": sum(item["classification"].startswith("m2g2-stress") for item in results),
        "total": len(results),
        "builds": len(results) * 5 + 1,
        "summary": {
            "worst_metrics": worst_metrics,
            "envelope_prediction_errors": envelope_prediction_errors,
            "maximum_absolute_envelope_prediction_error_mm": max(
                (
                    max(abs(item["width_delta_mm"]), abs(item["height_delta_mm"]))
                    for item in envelope_prediction_errors
                ),
                default=0,
            ),
            "maximum_repair_count": max(
                (run["layout"]["layout_repair_count"] for run in successful_runs), default=0
            ),
            "runtime_seconds": round(
                sum(run["runtime_seconds"] for result in results for run in result["runs"]), 6
            ),
        },
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "accepted": payload["accepted"],
                "total": payload["total"],
                "positive_base_cases": payload["positive_base_cases"],
                "stress_cases": payload["stress_cases"],
                "builds": payload["builds"],
                "negative_accepted": invalid["accepted_as_negative"],
                "historical_preservation": preservation["pass"],
                "anti_overfitting": anti_overfitting["pass"],
            }
        )
    )
    if (
        payload["accepted"] != payload["total"]
        or not invalid["accepted_as_negative"]
        or not preservation["pass"]
        or not anti_overfitting["pass"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
