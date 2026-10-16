"""Inspect downloaded final qualification evidence without promoting planned labels."""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
import subprocess
from pathlib import Path

from m2h2_final_artifact_audit_helpers import (
    _defect_total,
    _fresh_case_directory,
    _hard_defects,
    baseline_regression_diagnostics,
    case_detail,
    comparative_baseline,
    conductor_accounting,
    digest,
    graph_distances,
    identity_errors,
    placement_classes,
    render_chunks,
    union_length,
    verify_emitted_conductors,
)
from run_m2h2_structural_audit import audit_paths

from ai_kicad.m2a import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--interactions", type=Path, required=True)
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--emit-renders", action="store_true")
    args = parser.parse_args()
    errors = []
    qualification = json.loads((args.qualification / "results.json").read_text())
    errors.extend(identity_errors(qualification))
    if qualification.get("accepted") != 56 or qualification.get("total") != 56:
        errors.append("56-positive matrix incomplete")
    if qualification.get("negative_v3_8_accepted") is not True:
        errors.append("V3-8 negative not proved")
    for audit in ("historical_preservation", "anti_overfitting"):
        if qualification.get(audit, {}).get("pass") is not True:
            errors.append(f"{audit} did not pass")
    negative = json.loads(
        (args.qualification / "v3-8-invalid/run1.failed/reports/failure.json").read_text()
    )
    if negative.get("status") != "invalid" or not all(
        item in negative.get("message", "")
        for item in ("POWER_ASSERTION_DRIVER_CONFLICT", "POWER_SOURCE_ASSERTION_REQUIRED")
    ):
        errors.append("V3-8 exact authored electrical-precondition rejection absent")
    details = []
    for case in qualification["results"]:
        if len(case["runs"]) != 5 or not case["accepted"] or not case["reproducible"]:
            errors.append(f"base case not qualified: {case['id']}")
        if case["accepted"]:
            details.append(
                case_detail(
                    "base",
                    case["id"],
                    case["signature"],
                    args.qualification / case["id"] / "run1",
                    ROOT / case["design"],
                )
            )
        if args.emit_renders and case["accepted"]:
            render_chunks(
                args.qualification, "base__" + case["id"], args.qualification / case["id"]
            )
    summaries = {}
    for group in ("i1", "i2", "i3", "i4", "i5", "i6"):
        payload = json.loads((args.interactions / group / "results.json").read_text())
        errors.extend(f"{group}: {error}" for error in identity_errors(payload))
        if payload.get("accepted") != payload.get("total"):
            errors.append(f"incomplete interaction group: {group}")
        if payload.get("runner_sha256") != digest(ROOT / "tools/run_m2h2_i1.py"):
            errors.append(f"stale interaction runner: {group}")
        records = []
        for case in payload["results"]:
            if len(case["runs"]) != 5 or not case["accepted"] or not case["reproducible"]:
                errors.append(f"interaction not qualified: {group}/{case['id']}")
            record = {
                "case": case["id"],
                "cell": case.get("cell"),
                "selected_triple": case.get("selected_triple"),
                "accepted": case["accepted"],
                "reproducible": case["reproducible"],
                "observed_structural_class": case.get("observed_structural_class"),
                "runs": [run["path"] for run in case["runs"]],
            }
            if group == "i3" and case["runs"][0].get("signature"):
                record["observed_placement_classes"] = placement_classes(
                    case["runs"][0]["signature"]
                )
                record["class_coverage_status"] = "requires_final_band_class_reconciliation"
            if case["accepted"]:
                signature = case["runs"][0]["signature"]
                record["observed_placement_classes"] = placement_classes(signature)
                details.append(
                    case_detail(
                        group,
                        case["id"],
                        signature,
                        args.interactions / group / case["id"] / "run1",
                        ROOT / "fixtures/m2h2/interaction" / group / (case["id"] + ".json"),
                    )
                )
                if args.emit_renders:
                    render_chunks(
                        args.interactions / group,
                        group + "__" + case["id"],
                        args.interactions / group / case["id"],
                    )
            records.append(record)
            print(
                json.dumps(
                    {"kind": "m2h2.artifact-case-audit.1", "group": group, **record},
                    separators=(",", ":"),
                ),
                flush=True,
            )
        summaries[group] = {
            "git_head": payload.get("git_head"),
            "accepted": payload["accepted"],
            "total": payload["total"],
            "records": records,
        }
    structural = []
    for path in sorted(args.structural.glob("*/results.json")):
        payload = json.loads(path.read_text())
        errors.extend(identity_errors(payload))
        if (
            not payload.get("accepted")
            or not payload.get("reproducible")
            or len(payload["runs"]) != 5
        ):
            errors.append(f"structural case not qualified: {path.parent.name}")
        if payload.get("runner_sha256") != digest(
            ROOT / "tools/run_m2h2_structural_alternative.py"
        ):
            errors.append("stale structural runner")
        record = {"case": path.parent.name, **payload}
        structural.append(record)
        print(
            json.dumps(
                {
                    "kind": "m2h2.structural-case-audit.1",
                    "case": path.parent.name,
                    "accepted": payload["accepted"],
                    "reproducible": payload["reproducible"],
                    "required_class": payload["required_class"],
                    "classes": [
                        {key: run[key] for key in ("all_bands", "active_core_bands", "interleaved")}
                        for run in payload["runs"]
                    ],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        if args.emit_renders:
            render_chunks(path.parent.parent, "structural__" + path.parent.name, path.parent)
    required_structural_cases = {
        "a0_multiple",
        "a0_interleaved",
        "a1_multiple",
        "a1_interleaved",
        "a2_one",
        "a2_interleaved",
        "three_amplifier_one_band",
        "a3_interleaved",
        "a3_one",
    }
    observed_structural_cases = {item["case"] for item in structural}
    if observed_structural_cases != required_structural_cases or len(structural) != 9:
        errors.append("nine distinct required structural alternative cases must qualify")
    structural_audit = audit_paths([ROOT / "src/ai_kicad"])
    if not structural_audit["pass"]:
        errors.append("structural anti-overfitting audit failed")
    dependency_text = "\n".join(
        (ROOT / path).read_text() for path in ("pyproject.toml", "requirements.lock")
    )
    if re.search(r"cp[-_ ]?sat|ortools", dependency_text, re.IGNORECASE):
        errors.append("forbidden solver dependency")
    document_paths = [
        ROOT / "docs" / name
        for name in (
            "M2_GENERALIZATION_REMEDIATION_SPEC.md",
            "M2H2_FINALIZATION_SPEC_2026-09-27.md",
            "M2H2_FINALIZATION_TODO_2026-09-27.md",
            "M2H2_HANDOFF_2026-09-27.md",
        )
    ]
    document_paths.append(ROOT / "fixtures/m2h2/STATUS.md")
    link_errors = []
    link_count = 0
    for document in document_paths:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            target = target.split("#", 1)[0]
            if not target or "://" in target:
                continue
            link_count += 1
            if not (document.parent / target).exists():
                link_errors.append(f"{document.relative_to(ROOT)}: {target}")
    errors.extend(f"broken link: {item}" for item in link_errors)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    baseline_comparison = comparative_baseline(
        args.qualification, args.interactions, args.structural
    )
    for name, passed in baseline_comparison["criteria"].items():
        if not passed:
            errors.append(f"comparative baseline criterion failed: {name}")
    print(
        json.dumps(
            {
                "kind": "m2h2.baseline-comparison.1",
                "passed": baseline_comparison["passed"],
                "case_count": baseline_comparison["case_count"],
                "missing_cases": baseline_comparison["missing_cases"],
                "totals": baseline_comparison["totals"],
                "criteria": baseline_comparison["criteria"],
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    print(
        json.dumps(
            {
                "kind": "m2h2.baseline-regression-diagnostics.1",
                **baseline_regression_diagnostics(baseline_comparison["cases"]),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )

    metrics = {}
    for detail in details:
        for name, value in detail["layout"].items():
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and (name not in metrics or value > metrics[name]["value"])
            ):
                metrics[name] = {
                    "group": detail["group"],
                    "case": detail["case"],
                    "value": value,
                }
    report = {
        "details": details,
        "worst_metrics": metrics,
        "negative": negative,
        "structural": structural,
        "structural_anti_overfitting": structural_audit,
        "link_audit": {"links_checked": link_count, "errors": link_errors},
        "cp_sat_dependency_absent": not bool(
            re.search(r"cp[-_ ]?sat|ortools", dependency_text, re.IGNORECASE)
        ),
        "historical_preservation": qualification["historical_preservation"],
        "anti_overfitting": qualification["anti_overfitting"],
        "baseline_comparison": baseline_comparison,
        "schema_version": "m2h2.final-artifact-audit.1",
        "qualification_head": qualification["git_head"],
        "source_sha256": qualification["source_sha256"],
        "groups": summaries,
        "errors": errors,
        "machine_evidence_valid": not errors,
        "M2h2": "INCOMPLETE",
        "remaining_gates": [
            "actual I3 band classes and structural alternatives",
            "selected triple invariant reconciliation",
            "fresh engineering render inspection",
            "final audit/TODO closure",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    encoded = base64.b64encode(gzip.compress(args.out.read_bytes(), mtime=0)).decode()
    chunks = [encoded[index : index + 1000] for index in range(0, len(encoded), 1000)]
    for index, chunk in enumerate(chunks):
        print(
            json.dumps(
                {
                    "kind": "m2h2.report-transfer.1",
                    "index": index,
                    "total": len(chunks),
                    "sha256": digest(args.out),
                    "data": chunk,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
    print(
        json.dumps(
            {
                "kind": "m2h2.artifact-audit-outcome.1",
                "errors": errors,
                "machine_evidence_valid": not errors,
                "worst_metrics": metrics,
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    if errors:
        raise SystemExit(1)


__all__ = [
    "_defect_total",
    "_fresh_case_directory",
    "_hard_defects",
    "baseline_regression_diagnostics",
    "case_detail",
    "comparative_baseline",
    "conductor_accounting",
    "digest",
    "graph_distances",
    "identity_errors",
    "main",
    "placement_classes",
    "render_chunks",
    "union_length",
    "verify_emitted_conductors",
]

if __name__ == "__main__":
    main()
