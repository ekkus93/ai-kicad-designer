"""Inspect downloaded final qualification evidence without promoting planned labels."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

from ai_kicad.m2a import ROOT


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_errors(payload: dict) -> list[str]:
    errors = []
    hashes = payload.get("source_sha256", {})
    expected_modules = {
        str(path.relative_to(ROOT)) for path in (ROOT / "src/ai_kicad").glob("*.py")
    }
    if set(hashes) != expected_modules:
        errors.append("production module hash inventory mismatch")
    if not hashes:
        errors.append("missing source hashes")
    for relative, expected in hashes.items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            errors.append(f"stale source: {relative}")
    for field, relative in (
        ("toolchain_lock_sha256", "fixtures/m1a/toolchain.lock.json"),
        ("asset_lock_sha256", "fixtures/m2b/assets.lock.json"),
        ("policy_lock_sha256", "fixtures/m1a/policy.lock.json"),
    ):
        if payload.get(field) != digest(ROOT / relative):
            errors.append(f"stale lock: {relative}")
    return errors


def placement_classes(signature: dict) -> dict:
    composition = signature.get("composition", {})
    blocks = {block["id"]: block for block in composition.get("blocks", [])}
    placed = [
        (blocks[item["fragment"]], item["placed_envelope"])
        for item in composition.get("variants", [])
        if item["fragment"] in blocks and blocks[item["fragment"]]["kind"] != "interface"
    ]
    active_kinds = {
        "timer",
        "power_stage",
        "buffer",
        "noninverting_amplifier",
        "inverting_amplifier",
        "sallen_key",
    }
    cores = [
        (block, box)
        for block, box in placed
        if block["kind"] in active_kinds and not block.get("unused")
    ]

    def count_bands(items):
        bands = []
        for top in sorted({box[1] for _, box in items}):
            if not bands or top - bands[-1] > 5_080_000:
                bands.append(top)
        return len(bands)

    backfill = [
        [first["id"], second["id"]]
        for index, (first, a) in enumerate(placed)
        for second, b in placed[index + 1 :]
        if abs(a[1] - b[1]) > 5_080_000
        and max(a[1], b[1]) < min(a[3], b[3])
        and (a[2] <= b[0] or b[2] <= a[0])
    ]
    return {
        "active_core_count": len(cores),
        "all_noninterface_bands": count_bands(placed),
        "active_core_bands": count_bands(cores),
        "backfill_pairs": backfill,
        "placements": [
            {
                "fragment": block["id"],
                "kind": block["kind"],
                "unused": block.get("unused"),
                "envelope_nm": box,
            }
            for block, box in placed
        ],
    }


def render_chunks(root: Path, case_id: str, case_dir: Path) -> None:
    svgs = sorted((case_dir / "run1/renders/schematic").glob("*.svg"))
    if len(svgs) != 1:
        raise ValueError(f"{case_id}: expected one real KiCad render, got {len(svgs)}")
    data = svgs[0].read_bytes()
    encoded = base64.b64encode(gzip.compress(data, mtime=0)).decode()
    chunks = [encoded[index : index + 1000] for index in range(0, len(encoded), 1000)]
    for index, chunk in enumerate(chunks):
        print(
            json.dumps(
                {
                    "kind": "m2h2.render-transfer.1",
                    "case": case_id,
                    "root": str(root),
                    "index": index,
                    "total": len(chunks),
                    "svg_sha256": hashlib.sha256(data).hexdigest(),
                    "data": chunk,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )


def union_length(segments):
    """Independent interval union charges overlapping local/global segments once."""
    lines = {}
    for a, b in segments:
        if a == b:
            continue
        if a[0] == b[0]:
            key, interval = ("v", a[0]), sorted((a[1], b[1]))
        elif a[1] == b[1]:
            key, interval = ("h", a[1]), sorted((a[0], b[0]))
        else:
            raise ValueError("non-orthogonal conductor")
        lines.setdefault(key, []).append(interval)
    total = 0
    for intervals in lines.values():
        start, end = sorted(intervals)[0]
        for low, high in sorted(intervals)[1:]:
            if low > end:
                total += end - start
                start, end = low, high
            else:
                end = max(end, high)
        total += end - start
    return total


def case_detail(group, case_id, signature):
    composition = signature["composition"]
    layout = signature["layout"]
    lengths = []
    for tree in composition["canonical_trees"]:
        global_segments = [
            segment
            for route in composition["routes"]
            if route["net"] == tree["net"]
            for segment in route["segments"]
        ]
        full = union_length(tree["segments"])
        global_length = union_length(global_segments)
        if full != tree["length_nm"] or union_length(tree["segments"] + global_segments) != full:
            raise ValueError(f"{group}/{case_id}: invalid conductor accounting")
        lengths.append(
            {
                "net": tree["net"],
                "canonical_union_nm": full,
                "global_union_nm": global_length,
                "local_residual_nm": full - global_length,
                "accounting": "global union charged first; local residual excludes shared intervals",
            }
        )
    detail = {
        "group": group,
        "case": case_id,
        "layout": layout,
        "net_lengths": lengths,
        "terminal_inventory_count": composition["obligation_certificate"][
            "terminal_inventory_count"
        ],
        "net_graph_witnesses": composition["obligation_certificate"]["net_graph_witnesses"],
        "structural_search": composition["structural_search"],
        "candidate_selection": composition["candidate_selection"],
        "variants": composition["variants"],
        "budgets": composition["budgets"],
        "best_rejected_candidate": composition["best_rejected_candidate"],
        "prediction_observation_deltas_mm": {
            axis: layout.get(f"observed_content_{axis}_mm", 0)
            - layout.get(f"final_content_{axis}_mm", 0)
            for axis in ("width", "height")
        },
    }
    print(
        json.dumps(
            {
                "kind": "m2h2.detailed-case-audit.1",
                "group": group,
                "case": case_id,
                "net_lengths": lengths,
                "budgets": composition["budgets"],
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    return detail


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
            details.append(case_detail("base", case["id"], case["signature"]))
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
                details.append(case_detail(group, case["id"], signature))
                if args.emit_renders and (group == "i3" or case.get("selected_triple")):
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
    if len(structural) != 6:
        errors.append("six structural alternative cases required")
    metrics = {}
    for detail in details:
        for name, value in detail["layout"].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if name not in metrics or value > metrics[name]["value"]:
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
        "historical_preservation": qualification["historical_preservation"],
        "anti_overfitting": qualification["anti_overfitting"],
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


if __name__ == "__main__":
    main()
