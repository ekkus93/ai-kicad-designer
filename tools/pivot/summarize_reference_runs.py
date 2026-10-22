"""Verify and summarize clean reference POC repetitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from ai_kicad.pivot.fabrication import verify_review_package


def summarize(root: Path, run_numbers: list[int]) -> dict:
    runs = []
    for number in run_numbers:
        run_root = root / f"fixtures/pivot/experiments/reference_poc_2026-10-22_run{number}"
        report = json.loads((run_root / "reports/verification_report.json").read_text())
        call_log = json.loads((run_root / "reports/call_log.json").read_text())
        manifest = json.loads((run_root / "fabrication_manifest.json").read_text())
        package_line = (run_root / "package.sha256").read_text().split()
        package = run_root / "review-package.zip"
        package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
        if not package_line or package_line[0] != package_sha:
            raise ValueError(f"run {number}: package checksum mismatch")
        with tempfile.TemporaryDirectory(prefix="poc-clean-extract-") as extraction:
            verify_review_package(package, Path(extraction) / "clean")
        images = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((run_root / "previews").glob("*.png"))
        }
        if report["status"] != "PASS" or not all(report["gates"].values()):
            raise ValueError(f"run {number}: one or more verification gates failed")
        if report["revision_id"] != manifest["revision_id"]:
            raise ValueError(f"run {number}: manifest and report revisions differ")
        runs.append(
            {
                "run": number,
                "status": report["status"],
                "readiness_state": report["readiness_state"],
                "revision_id": report["revision_id"],
                "gates": report["gates"],
                "track_count": report["board"]["metrics"]["track_count"],
                "track_length_mm": report["board"]["metrics"]["track_length_mm"],
                "via_count": report["board"]["metrics"]["via_count"],
                "native_drc_violation_count": len(
                    call_log["mcp_tools"][7]["response"]["report"].get("violations", [])
                ),
                "mcp_tool_call_count": len(call_log["mcp_tools"]),
                "elapsed_seconds": call_log["elapsed_seconds"],
                "preview_sha256": images,
                "package_sha256": package_sha,
                "clean_extraction": "PASS",
            }
        )
    semantic_fields = (
        "status",
        "readiness_state",
        "revision_id",
        "gates",
        "track_count",
        "track_length_mm",
        "via_count",
        "native_drc_violation_count",
        "preview_sha256",
    )
    reference = runs[0]
    mismatches = {
        field: [run["run"] for run in runs if run[field] != reference[field]]
        for field in semantic_fields
        if any(run[field] != reference[field] for run in runs[1:])
    }
    return {
        "schema_version": "reference-poc-repeatability.v2",
        "runs": runs,
        "stable_semantics": "PASS" if not mismatches else "FAIL",
        "semantic_mismatches": mismatches,
        "permitted_nondeterminism": [
            "ZIP/package SHA may vary when generated timestamps or report timestamps vary.",
            "Elapsed time varies with host load and process startup.",
            "Package SHA is still recorded and verified independently for each run.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    summary = summarize(root, args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "stable_semantics": summary["stable_semantics"]}))
    if summary["stable_semantics"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
