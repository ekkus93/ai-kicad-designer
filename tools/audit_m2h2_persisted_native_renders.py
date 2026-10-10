"""Inventory persisted, source-matched native renders without GitHub artifact uploads.

This is a deterministic *inspection transport* and byte-hash manifest. It is
not a visual-engineering acceptance oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from run_m2g2_qualification import _normalized_svg
from run_m2h2_final_artifact_audit import identity_errors, render_chunks

REQUIRED_STRUCTURAL = frozenset(
    {
        "a0_multiple",
        "a0_interleaved",
        "a1_multiple",
        "a1_interleaved",
        "a2_one",
        "a2_interleaved",
        "a3_one",
        "a3_interleaved",
        "three_amplifier_one_band",
    }
)
GROUPS = ("i1", "i2", "i3", "i4", "i5", "i6")


def inventory_case(root: Path, name: str, runs: list[dict]) -> dict:
    """Require five distinct native KiCad renders and hash all actual bytes."""
    if len(runs) != 5:
        raise ValueError(f"{name}: expected five qualification runs")
    renders = []
    for index in range(1, 6):
        run = root / f"run{index}"
        if not run.is_dir():
            raise ValueError(f"{name}: missing run{index}")
        svgs = sorted((run / "renders/schematic").glob("*.svg"))
        if len(svgs) != 1:
            raise ValueError(f"{name}: run{index} has {len(svgs)} SVGs, expected 1")
        data = svgs[0].read_bytes()
        if not data.lstrip().startswith((b"<?xml", b"<svg")) or b"<svg" not in data:
            raise ValueError(f"{name}: run{index} is not native SVG content")
        renders.append(
            {
                "run": index,
                "path": str(svgs[0]),
                "sha256": hashlib.sha256(data).hexdigest(),
                "normalized_svg_sha256": _normalized_svg(svgs[0]),
                "size_bytes": len(data),
            }
        )
    return {
        "case": name,
        "renders": renders,
        "byte_identical": len({record["sha256"] for record in renders}) == 1,
        "normalized_identical": len({record["normalized_svg_sha256"] for record in renders}) == 1,
    }


def require_identity(payload: dict, source_sha: str, context: str) -> None:
    errors = identity_errors(payload)
    if payload.get("git_head") != source_sha:
        errors.append(f"source identity mismatch: {payload.get('git_head')}")
    if errors:
        raise ValueError(f"{context}: " + "; ".join(errors))


def collect(root: Path, source_sha: str) -> dict:
    qualification = json.loads((root / "qualification/results.json").read_text())
    require_identity(qualification, source_sha, "qualification")
    if (
        qualification.get("total") != 56
        or qualification.get("accepted") != 56
        or qualification.get("negative_v3_8_accepted") is not True
    ):
        raise ValueError("base 56-case qualification or V3-8 rejection missing")
    records = []
    seen = set()
    for case in qualification["results"]:
        name = "base__" + case["id"]
        if name in seen or not case["accepted"] or not case["reproducible"]:
            raise ValueError(f"{name}: missing or duplicate qualified case")
        seen.add(name)
        records.append(inventory_case(root / "qualification" / case["id"], name, case["runs"]))
    if len(records) != 56:
        raise ValueError("base case inventory must contain exactly 56 cases")

    groups = {}
    for group in GROUPS:
        result = json.loads((root / "interactions" / group / "results.json").read_text())
        require_identity(result, source_sha, group)
        if result["accepted"] != result["total"] or result["total"] != len(result["results"]):
            raise ValueError(f"{group}: qualification count mismatch")
        groups[group] = len(result["results"])
        for case in result["results"]:
            name = group + "__" + case["id"]
            if name in seen or not case["accepted"] or not case["reproducible"]:
                raise ValueError(f"{name}: missing or duplicate qualified case")
            seen.add(name)
            records.append(
                inventory_case(root / "interactions" / group / case["id"], name, case["runs"])
            )

    observed_structural = set()
    for path in sorted((root / "structural").glob("*/results.json")):
        result = json.loads(path.read_text())
        name = path.parent.name
        require_identity(result, source_sha, "structural " + name)
        if not result["accepted"] or not result["reproducible"]:
            raise ValueError(f"{name}: structural qualification not accepted")
        if name in observed_structural:
            raise ValueError(f"{name}: duplicate structural class")
        observed_structural.add(name)
        records.append(inventory_case(path.parent, "structural__" + name, result["runs"]))
    if observed_structural != REQUIRED_STRUCTURAL:
        raise ValueError(
            f"structural case mismatch: missing={sorted(REQUIRED_STRUCTURAL - observed_structural)}"
            f" unexpected={sorted(observed_structural - REQUIRED_STRUCTURAL)}"
        )

    return {
        "schema_version": "m2h2.persisted-native-render-inventory.1",
        "qualification_head": source_sha,
        "acceptance_status": "NOT_VISUALLY_INSPECTED",
        "base_cases": 56,
        "interaction_cases": groups,
        "structural_cases": len(observed_structural),
        "total_cases": len(records),
        "total_svg_files": sum(len(record["renders"]) for record in records),
        "byte_identical_cases": sum(record["byte_identical"] for record in records),
        "normalized_identical_cases": sum(record["normalized_identical"] for record in records),
        "cases": sorted(records, key=lambda record: record["case"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--emit-case", default="")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha must be an exact lowercase 40-character SHA")
    report = collect(args.root, args.source_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out.exists():
        if args.out.read_text() != rendered:
            raise ValueError("existing manifest differs: preserve prior evidence")
    else:
        args.out.write_text(rendered)
    print(
        json.dumps(
            {
                "kind": "m2h2.persisted-native-render-summary.1",
                **{key: value for key, value in report.items() if key != "cases"},
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    for record in report["cases"]:
        print(
            json.dumps(
                {
                    "kind": "m2h2.native-render-hash.1",
                    "case": record["case"],
                    "sha256": [render["sha256"] for render in record["renders"]],
                    "normalized_svg_sha256": [
                        render["normalized_svg_sha256"] for render in record["renders"]
                    ],
                    "byte_identical": record["byte_identical"],
                    "normalized_identical": record["normalized_identical"],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
    if args.emit_case:
        candidates = {item["case"] for item in report["cases"]}
        if args.emit_case not in candidates:
            raise ValueError(f"unknown exact qualified case: {args.emit_case}")
        prefix, case = args.emit_case.split("__", 1)
        if prefix == "base":
            directory = args.root / "qualification" / case
        elif prefix == "structural":
            directory = args.root / "structural" / case
        else:
            directory = args.root / "interactions" / prefix / case
        render_chunks(args.root, args.emit_case, directory)


if __name__ == "__main__":
    main()
