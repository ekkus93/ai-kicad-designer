"""Inspect downloaded final qualification evidence without promoting planned labels."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import heapq
import re
import subprocess

from ai_kicad.m2a import ROOT, observe
from ai_kicad.m2b import assets
from analyze_m2h2_historical_composition import (
    _design_paths as historical_design_paths,
    analyze_case as analyze_native_composition,
    build_report as build_historical_composition_report,
)
from run_m2h2_structural_audit import audit_paths


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
    encoded = base64.b64encode(data).decode()
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
                    "encoding": "base64-svg",
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


def graph_distances(segments, source, terminals):
    points = {tuple(point) for segment in segments for point in segment} | set(terminals)
    graph = {point: {} for point in points}
    for a, b in segments:
        axis = 1 if a[0] == b[0] else 0
        fixed = 1 - axis
        nodes = sorted(
            (
                point
                for point in points
                if point[fixed] == a[fixed]
                and min(a[axis], b[axis]) <= point[axis] <= max(a[axis], b[axis])
            ),
            key=lambda point: point[axis],
        )
        for first, second in zip(nodes, nodes[1:]):
            distance = abs(first[axis] - second[axis])
            graph[first][second] = graph[second][first] = distance
    distances = {source: 0}
    queue = [(0, source)]
    while queue:
        distance, point = heapq.heappop(queue)
        if distance != distances[point]:
            continue
        for target, weight in graph.get(point, {}).items():
            proposal = distance + weight
            if proposal < distances.get(target, float("inf")):
                distances[target] = proposal
                heapq.heappush(queue, (proposal, target))
    return distances


def conductor_accounting(canonical, proposed_global, reported_length, pruned_count):
    """Charge only emitted intervals; router proposals can have pruned leaves."""
    full = union_length(canonical)
    if full != reported_length:
        raise ValueError("canonical length differs from independent interval union")
    proposed = union_length(proposed_global)
    # Inclusion/exclusion gives the interval intersection without trusting route
    # provenance or charging proposal-only leaves as emitted conductor.
    emitted_global = full + proposed - union_length(canonical + proposed_global)
    removed = proposed - emitted_global
    if removed and not pruned_count:
        raise ValueError("proposal-only conductor has no pruning witness")
    return {
        "canonical_union_nm": full,
        "global_union_nm": emitted_global,
        "local_residual_nm": full - emitted_global,
        "proposed_global_union_nm": proposed,
        "pruned_proposal_union_nm": removed,
        "pruned_leaf_count": pruned_count,
        "accounting": "emitted global intersection charged first; local residual excludes shared intervals; pruned router proposals are reported separately",
    }


def verify_emitted_conductors(canonical_trees, observed_wires):
    def normalized(segments):
        return sorted(tuple(sorted(tuple(point) for point in segment)) for segment in segments)

    canonical = [segment for tree in canonical_trees for segment in tree["segments"]]
    if normalized(canonical) != normalized(observed_wires):
        raise ValueError("canonical conductor inventory differs from emitted schematic bytes")


def _fresh_case_directory(
    case: str, qualification: Path, interactions: Path, structural: Path
) -> Path | None:
    if case.startswith("base__"):
        return qualification / case.split("__", 1)[1]
    if case.startswith("structural__"):
        return structural / case.split("__", 1)[1]
    if "__" in case:
        group, case_id = case.split("__", 1)
        if group in {"i1", "i2", "i3", "i4", "i5", "i6"}:
            return interactions / group / case_id
    return None


def _hard_defects(record: dict) -> dict[str, int]:
    repeated = record["repeated_structure"]
    return {
        "stage_order_inversions": int(record["flow_order"]["stage_order_inversions"]),
        "interface_side_violations": len(record["interface_flow"]["interface_side_violations"]),
        "local_label_disconnects": len(record["routing"]["local_label_disconnects"]),
        "page_low_utilization": int(bool(record["page"].get("low_utilization"))),
        "page_edge_bias": int(bool(record["page"].get("edge_bias"))),
        "repeated_out_of_tolerance": int(
            repeated["applicable"] and not repeated["within_frozen_tolerance"]
        ),
    }


def _defect_total(record: dict) -> int:
    return sum(_hard_defects(record).values())


def baseline_regression_diagnostics(pairs: list[dict], limit: int = 24) -> dict:
    """Rank independent current-vs-historical regressions without relaxing a gate."""
    ranked = []
    for record in pairs:
        historic = record["historical"]
        fresh = record["fresh"]
        increased_hard = {
            name: record["fresh_hard_defects"][name] - count
            for name, count in record["historical_hard_defects"].items()
            if record["fresh_hard_defects"][name] > count
        }
        fragmentation = round(
            fresh["fragmentation_total_mm"] - historic["fragmentation_total_mm"], 4
        )
        detours = fresh["u_shaped_detours"] - historic["u_shaped_detours"]
        branch = round(fresh["branch_inconsistency_mm"] - historic["branch_inconsistency_mm"], 4)
        unresolved_hard = bool(
            record["historical_hard_defect_total"] and record["fresh_hard_defect_total"]
        )
        repeated_fail = not fresh["repeated_within_tolerance"]
        if not (
            unresolved_hard
            or increased_hard
            or repeated_fail
            or fragmentation > 0
            or detours > 0
            or branch > 0
        ):
            continue
        ranked.append(
            {
                "case": record["case"],
                "unresolved_hard": unresolved_hard,
                "historical_hard_defects": record["historical_hard_defects"],
                "fresh_hard_defects": record["fresh_hard_defects"],
                "increased_hard": increased_hard,
                "repeated_out_of_tolerance": repeated_fail,
                "fragmentation_delta_mm": fragmentation,
                "u_shaped_detours_delta": detours,
                "branch_inconsistency_delta_mm": branch,
                "historical_interface_violations": historic["interface_side_violations"],
                "fresh_interface_violations": fresh["interface_side_violations"],
                "historical_edge_bias": historic["edge_bias"],
                "fresh_edge_bias": fresh["edge_bias"],
            }
        )
    ranked.sort(
        key=lambda item: (
            -len(item["increased_hard"]),
            -int(item["unresolved_hard"]),
            -int(item["repeated_out_of_tolerance"]),
            -(
                max(item["u_shaped_detours_delta"], 0)
                + max(item["branch_inconsistency_delta_mm"], 0)
            ),
            item["case"],
        )
    )
    # Independently rank worst metric contributions. The hard-defect priority
    # list above can bury the cases driving a corpus-wide aesthetic regression.
    # The ranking is diagnostic only; no acceptance criterion is relaxed.
    by_metric = {}
    for metric in (
        "fragmentation_total_mm",
        "u_shaped_detours",
        "branch_inconsistency_mm",
    ):
        worsened = sorted(
            (
                {
                    "case": pair["case"],
                    "historical": pair["historical"][metric],
                    "fresh": pair["fresh"][metric],
                    "delta": round(
                        pair["fresh"][metric] - pair["historical"][metric], 4
                    ),
                }
                for pair in pairs
                if pair["fresh"][metric] > pair["historical"][metric]
            ),
            key=lambda item: (-item["delta"], item["case"]),
        )
        by_metric[metric] = {
            "worsened_case_count": len(worsened),
            "total_positive_delta": round(
                sum(item["delta"] for item in worsened), 4
            ),
            "omitted_count": max(0, len(worsened) - limit),
            "worst_cases": worsened[:limit],
        }
    mixed = next((item for item in pairs if item["case"] == "i4__b2_mixed"), None)
    return {
        "affected_count": len(ranked),
        "omitted_count": max(0, len(ranked) - limit),
        "ranked_cases": ranked[:limit],
        "by_metric": by_metric,
        "i4": mixed,
    }


def comparative_baseline(qualification: Path, interactions: Path, structural: Path) -> dict:
    baseline = build_historical_composition_report()
    designs = historical_design_paths()
    resolved = assets()
    pairs = []
    missing = []
    for historical in sorted(baseline["cases"], key=lambda item: item["case"]):
        case = historical["case"]
        directory = _fresh_case_directory(case, qualification, interactions, structural)
        svgs = (
            sorted((directory / "run1/renders/schematic").glob("*.svg"))
            if directory is not None
            else []
        )
        design = designs.get(case)
        if directory is None or design is None or len(svgs) != 1:
            missing.append(case)
            continue
        fresh = analyze_native_composition(case, design, svgs[0].read_bytes(), resolved)
        pairs.append(
            {
                "case": case,
                "historical_svg_sha256": historical["svg_sha256"],
                "fresh_svg_sha256": fresh["svg_sha256"],
                "historical_hard_defects": _hard_defects(historical),
                "fresh_hard_defects": _hard_defects(fresh),
                "historical_hard_defect_total": _defect_total(historical),
                "fresh_hard_defect_total": _defect_total(fresh),
                "historical": {
                    "stage_order_inversions": historical["flow_order"]["stage_order_inversions"],
                    "interface_side_violations": len(
                        historical["interface_flow"]["interface_side_violations"]
                    ),
                    "fragmentation_total_mm": historical["functional_fragmentation"][
                        "total_intra_block_span_mm"
                    ],
                    "edge_bias": historical["page"].get("edge_bias"),
                    "low_utilization": historical["page"].get("low_utilization"),
                    "u_shaped_detours": historical["routing"]["u_shaped_detours"],
                    "branch_inconsistency_mm": historical["routing"][
                        "sibling_branch_geometry_inconsistency_mm"
                    ],
                    "repeated_within_tolerance": historical["repeated_structure"][
                        "within_frozen_tolerance"
                    ],
                },
                "fresh": {
                    "stage_order_inversions": fresh["flow_order"]["stage_order_inversions"],
                    "interface_side_violations": len(
                        fresh["interface_flow"]["interface_side_violations"]
                    ),
                    "fragmentation_total_mm": fresh["functional_fragmentation"][
                        "total_intra_block_span_mm"
                    ],
                    "edge_bias": fresh["page"].get("edge_bias"),
                    "low_utilization": fresh["page"].get("low_utilization"),
                    "u_shaped_detours": fresh["routing"]["u_shaped_detours"],
                    "branch_inconsistency_mm": fresh["routing"][
                        "sibling_branch_geometry_inconsistency_mm"
                    ],
                    "repeated_within_tolerance": fresh["repeated_structure"][
                        "within_frozen_tolerance"
                    ],
                },
            }
        )

    def total(side: str, field: str) -> float:
        return sum(float(item[side][field]) for item in pairs)

    historical_stage = total("historical", "stage_order_inversions")
    fresh_stage = total("fresh", "stage_order_inversions")
    historical_interfaces = total("historical", "interface_side_violations")
    fresh_interfaces = total("fresh", "interface_side_violations")
    historical_fragmentation = total("historical", "fragmentation_total_mm")
    fresh_fragmentation = total("fresh", "fragmentation_total_mm")
    historical_uturns = total("historical", "u_shaped_detours")
    fresh_uturns = total("fresh", "u_shaped_detours")
    historical_branch = total("historical", "branch_inconsistency_mm")
    fresh_branch = total("fresh", "branch_inconsistency_mm")
    historical_edge_bias = sum(bool(item["historical"]["edge_bias"]) for item in pairs)
    fresh_edge_bias = sum(bool(item["fresh"]["edge_bias"]) for item in pairs)
    historical_low_util = sum(bool(item["historical"]["low_utilization"]) for item in pairs)
    fresh_low_util = sum(bool(item["fresh"]["low_utilization"]) for item in pairs)

    i4 = next((item for item in pairs if item["case"] == "i4__b2_mixed"), None)
    criteria = {
        "complete_case_coverage": not missing
        and len(pairs) == baseline["provenance"]["native_svg_count"],
        "baseline_hard_defects_cleared": all(
            item["historical_hard_defect_total"] == 0 or item["fresh_hard_defect_total"] == 0
            for item in pairs
        ),
        "no_new_hard_defects_on_previously_clean_cases": all(
            item["historical_hard_defect_total"] != 0 or item["fresh_hard_defect_total"] == 0
            for item in pairs
        ),
        "individual_hard_defects_never_worsen": all(
            all(
                item["fresh_hard_defects"][key] <= value
                for key, value in item["historical_hard_defects"].items()
            )
            for item in pairs
        ),
        "stage_order_improves_or_remains_zero": (
            fresh_stage == 0 if historical_stage == 0 else fresh_stage < historical_stage
        ),
        "interface_side_metrics_improve": (
            fresh_interfaces == 0
            if historical_interfaces == 0
            else fresh_interfaces < historical_interfaces
        ),
        "functional_fragmentation_nonworsening": fresh_fragmentation <= historical_fragmentation,
        "page_bias_nonworsening": (
            fresh_edge_bias <= historical_edge_bias and fresh_low_util <= historical_low_util
        ),
        "routing_aesthetics_nonworsening": (
            fresh_uturns <= historical_uturns and fresh_branch <= historical_branch + 1e-6
        ),
        "repeated_structure_within_frozen_tolerance": all(
            item["fresh"]["repeated_within_tolerance"] for item in pairs
        ),
        "i4_specific_improvement": bool(
            i4
            and i4["fresh_hard_defect_total"] < i4["historical_hard_defect_total"]
            and i4["fresh"]["interface_side_violations"] == 0
            and not i4["fresh"]["edge_bias"]
            and i4["fresh"]["u_shaped_detours"] <= i4["historical"]["u_shaped_detours"]
            and i4["fresh"]["branch_inconsistency_mm"]
            <= i4["historical"]["branch_inconsistency_mm"] + 1e-6
        ),
    }
    return {
        "schema_version": "m2h2.comparative-native-baseline.1",
        "historical_qualification_sha": baseline["provenance"]["historical_qualification_sha"],
        "historical_inventory_sha256": baseline["provenance"]["inventory_sha256"],
        "case_count": len(pairs),
        "missing_cases": missing,
        "totals": {
            "stage_order_inversions": {
                "historical": historical_stage,
                "fresh": fresh_stage,
            },
            "interface_side_violations": {
                "historical": historical_interfaces,
                "fresh": fresh_interfaces,
            },
            "functional_fragmentation_total_mm": {
                "historical": historical_fragmentation,
                "fresh": fresh_fragmentation,
            },
            "edge_bias_case_count": {
                "historical": historical_edge_bias,
                "fresh": fresh_edge_bias,
            },
            "low_utilization_case_count": {
                "historical": historical_low_util,
                "fresh": fresh_low_util,
            },
            "u_shaped_detours": {
                "historical": historical_uturns,
                "fresh": fresh_uturns,
            },
            "branch_inconsistency_mm": {
                "historical": historical_branch,
                "fresh": fresh_branch,
            },
        },
        "criteria": criteria,
        "passed": all(criteria.values()),
        "cases": pairs,
    }


def case_detail(group, case_id, signature, directory, design_path):
    composition = signature["composition"]
    layout = signature["layout"]
    schematic = next((directory / "project").glob("*.kicad_sch"))
    observed = observe(schematic, directory / "reports/netlist.xml")
    verify_emitted_conductors(composition["canonical_trees"], observed["wires"])
    design = json.loads(design_path.read_text())
    refs = {part["id"]: part["refdes"] for part in design["components"]}
    obligations = composition["obligation_certificate"]["semantic_obligations"]
    roles = {item["id"]: item for item in obligations["presentation_nets"]}
    lengths = []
    for tree in composition["canonical_trees"]:
        global_segments = [
            segment
            for route in composition["routes"]
            if route["net"] == tree["net"]
            for segment in route["segments"]
        ]
        accounting = conductor_accounting(
            tree["segments"],
            global_segments,
            tree["length_nm"],
            layout.get("pruned_route_leaves", {}).get(tree["net"], 0),
        )
        full = accounting["canonical_union_nm"]
        role = roles.get(tree["net"], {})
        points = {
            tuple(observed["pin_positions"][(refs[component], pin)])
            for component, pin in role.get("terminals", [])
            if component in refs
        }
        lower = (
            (
                max(point[0] for point in points)
                - min(point[0] for point in points)
                + max(point[1] for point in points)
                - min(point[1] for point in points)
            )
            if points
            else 0
        )
        explicit = role.get("explicit_geometry_required", False)
        sources = {
            tuple(observed["pin_positions"][(refs[component], pin)])
            for port in obligations["ports"]
            if port["net"] == tree["net"] and port["fragment"] in role.get("producer_fragments", [])
            for component, pin in port["terminals"]
            if component in refs
        }
        path_lengths = (
            [graph_distances(tree["segments"], source, points) for source in sources]
            if explicit
            else []
        )
        worst = max(
            (distances.get(point, -1) for distances in path_lengths for point in points),
            default=None,
        )
        lengths.append(
            {
                "net": tree["net"],
                **accounting,
                "terminal_count": len(points),
                "terminal_bbox_lower_bound_nm": lower if explicit else None,
                "routed_to_bound_ratio": full / lower if explicit and lower else None,
                "worst_explicit_source_consumer_path_nm": worst,
                "source_count": len(sources),
            }
        )
    detail = {
        "group": group,
        "case": case_id,
        "layout": layout,
        "net_lengths": lengths,
        "physical_component_count": len(refs),
        "observed_terminal_count": sum(len(members) for members in observed["nets"].values()),
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


if __name__ == "__main__":
    main()
