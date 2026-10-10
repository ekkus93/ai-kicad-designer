"""Characterize the frozen M2h2 native-render baseline with independent observers.

Evidence-only: verifies archived SVG hashes, reconstructs semantics from authored
fixtures, and records native geometry defects. It does not feed production search
or claim current-source qualification.
"""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_composition_tolerances import FROZEN_TOLERANCES, Complexity, tolerance_for
from ai_kicad.m2_interface_flow_composition_observer import (
    ExternalInterface,
    FlowStage,
    SIGNAL_INPUT_ROLE,
    SIGNAL_OUTPUT_ROLE,
    measure_interface_flow_composition,
)
from ai_kicad.m2_native_render_archive_materialize import load_native_baseline
from ai_kicad.m2_routing_composition_observer import measure_routing_readability
from ai_kicad.m2_semantics import semantic_plan
from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations
from run_m2h2_qualification import cases as base_cases

MANIFEST = (
    ROOT
    / "fixtures/m2h2/human_composition_baseline_2026-10-08"
    / "native_render_archive_manifest_42ab8452.json"
)
WIRE_STYLE = "stroke:#009600"
WIRE_PATH = re.compile(r"M\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+L\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s*")
MM_TO_NM = 1_000_000
ENVELOPE_CENTER_MM = (18 * 1.27 + 105.0, 23 * 1.27 + 70.0)
OWNER_LOCALITY_MM = 60.0
LOCAL_LABEL_MM = 80.0
ACTIVE_CORE_KINDS = {
    "timer",
    "power_stage",
    "buffer",
    "noninverting_amplifier",
    "inverting_amplifier",
    "sallen_key",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _svgs(root: Path, manifest: Path) -> tuple[dict[str, bytes], dict]:
    inventory, parts = load_native_baseline(root, manifest)
    expected = dict(inventory.case_hashes)
    result = {}
    for part in parts:
        for item in part["renders"]:
            svg = gzip.decompress(base64.b64decode(item["data"], validate=True))
            if _sha(svg) != expected[item["case"]]:
                raise ValueError(f"native SVG digest mismatch: {item['case']}")
            ET.fromstring(svg)
            result[item["case"]] = svg
    if set(result) != set(expected):
        raise ValueError("verified SVG set differs from frozen archive inventory")
    return result, {
        "historical_qualification_sha": inventory.qualification_head,
        "native_svg_count": inventory.render_count,
        "inventory_sha256": inventory.inventory_sha256,
    }


def _designs() -> dict[str, Path]:
    result = {f"base__{name}": path for name, path, _kind in base_cases()}
    interaction = ROOT / "fixtures/m2h2/interaction"
    for group in ("i1", "i2", "i3", "i4", "i5", "i6"):
        for path in sorted((interaction / group).glob("*.json")):
            if not path.name.endswith(".expected.json"):
                result[f"{group}__{path.stem}"] = path
    for path in sorted((interaction / "i3").glob("*.json")):
        if not path.name.endswith(".expected.json"):
            result[f"structural__{path.stem}"] = path
    return result


def _text(svg: bytes) -> dict[str, tuple[tuple[float, float], ...]]:
    values = defaultdict(list)
    for element in ET.fromstring(svg).iter():
        if element.tag.rsplit("}", 1)[-1] != "text" or not (element.text or "").strip():
            continue
        try:
            values[element.text.strip()].append(
                (float(element.attrib["x"]), float(element.attrib["y"]))
            )
        except (KeyError, ValueError):
            pass
    return {key: tuple(points) for key, points in values.items()}


# Compatibility names keep focused evidence tests independent of helper refactors.
_design_paths = _designs
_verified_svg_by_case = _svgs


def _refdes(component: dict, unit: int, resolved: dict) -> str:
    base = component["refdes"]
    if len(resolved[component["asset"]].units) <= 1:
        return base
    return f"{base}{chr(ord('A') + unit - 1)}"


def _occurrence_points(design: dict, plan, resolved: dict, text: dict) -> tuple[dict, list[str]]:
    components = {item["id"]: item for item in design["components"]}
    points = {}
    missing = []
    occurrences = sorted({item for block in plan.blocks for item in block.occurrences})
    for occurrence in occurrences:
        component_id, unit = occurrence
        component = components[component_id]
        display = _refdes(component, unit, resolved)
        candidates = text.get(display, ()) or text.get(component["refdes"], ())
        unique = tuple(sorted(set(candidates)))
        if len(unique) != 1:
            missing.append(f"{component_id}:{unit}:{display}:count={len(unique)}")
        else:
            points[occurrence] = unique[0]
    return points, missing


def _centers(design: dict, plan, resolved: dict, text: dict) -> tuple[dict, list[str], int]:
    points, missing = _occurrence_points(design, plan, resolved, text)
    centers = {}
    for block in plan.blocks:
        observed = [points[item] for item in block.occurrences if item in points]
        if observed:
            centers[block.id] = (
                sum(item[0] for item in observed) / len(observed),
                sum(item[1] for item in observed) / len(observed),
            )
    return centers, missing, len(points)


def _interfaces(plan, centers: dict) -> dict:
    interfaces = []
    for source, target, _net in inferred_passive_interface_signal_relations(plan):
        if source not in centers or target not in centers:
            continue
        if source.startswith("interface."):
            interfaces.append(ExternalInterface(source, SIGNAL_INPUT_ROLE, centers[source], target))
        elif target.startswith("interface."):
            interfaces.append(
                ExternalInterface(target, SIGNAL_OUTPUT_ROLE, centers[target], source)
            )
    stages = tuple(
        FlowStage(name, center)
        for name, center in sorted(centers.items())
        if not name.startswith("interface.")
    )
    measured = measure_interface_flow_composition(tuple(interfaces), stages, ())
    distances = []
    for item in sorted(interfaces, key=lambda value: value.interface_id):
        owner = centers.get(item.owner_stage_id)
        if owner is None:
            continue
        distances.append(
            {
                "interface_id": item.interface_id,
                "owner_stage_id": item.owner_stage_id,
                "role": item.role,
                "distance_mm": round(
                    abs(item.center[0] - owner[0]) + abs(item.center[1] - owner[1]), 6
                ),
            }
        )
    return {
        "interface_side_violations": [asdict(item) for item in measured.interface_side_violations],
        "interface_owner_distances_mm": distances,
        "interface_owner_detachments": [
            item for item in distances if item["distance_mm"] > OWNER_LOCALITY_MM
        ],
        "visual_owner_locality_limit_mm": OWNER_LOCALITY_MM,
    }


def _wires(svg: bytes):
    result = []
    for group in ET.fromstring(svg).iter():
        if group.tag.rsplit("}", 1)[-1] != "g" or WIRE_STYLE not in group.attrib.get("style", ""):
            continue
        for element in group:
            match = WIRE_PATH.fullmatch(element.attrib.get("d", "").strip())
            if element.tag.rsplit("}", 1)[-1] != "path" or match is None:
                continue
            x1, y1, x2, y2 = (float(value) for value in match.groups())
            result.append(
                (
                    (round(x1 * MM_TO_NM), round(y1 * MM_TO_NM)),
                    (round(x2 * MM_TO_NM), round(y2 * MM_TO_NM)),
                )
            )
    return tuple(result)


def _components(segments) -> dict[tuple[int, int], int]:
    graph = defaultdict(set)
    for first, second in segments:
        graph[first].add(second)
        graph[second].add(first)
    result = {}
    component = 0
    for start in sorted(graph):
        if start in result:
            continue
        pending = [start]
        while pending:
            point = pending.pop()
            if point in result:
                continue
            result[point] = component
            pending.extend(graph[point] - result.keys())
        component += 1
    return result


def _nearest(point, endpoints):
    scaled = (round(point[0] * MM_TO_NM), round(point[1] * MM_TO_NM))
    ranked = sorted((abs(scaled[0] - p[0]) + abs(scaled[1] - p[1]), p) for p in endpoints)
    return ranked[0][1] if ranked and ranked[0][0] <= 2_000_000 else None


def _label_disconnects(design: dict, plan, text: dict, segments) -> list[dict]:
    components = _components(segments)
    authored = {item["id"] for item in design["nets"]}
    signal = {item.id for item in plan.presentation_nets if item.role == "signal"}
    result = []
    for net in sorted(authored & signal):
        anchors = sorted({p for label in text.get(net, ()) if (p := _nearest(label, components))})
        for index, first in enumerate(anchors):
            for second in anchors[index + 1 :]:
                distance = (abs(first[0] - second[0]) + abs(first[1] - second[1])) / MM_TO_NM
                if distance <= LOCAL_LABEL_MM and components.get(first) != components.get(second):
                    result.append(
                        {
                            "net": net,
                            "first_anchor_mm": [first[0] / MM_TO_NM, first[1] / MM_TO_NM],
                            "second_anchor_mm": [second[0] / MM_TO_NM, second[1] / MM_TO_NM],
                            "manhattan_distance_mm": round(distance, 6),
                        }
                    )
    return result


def _page(plan, centers: dict) -> dict:
    if not centers:
        return {"observable": False}
    xs = [p[0] for p in centers.values()]
    ys = [p[1] for p in centers.values()]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    centroid = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    offset = abs(centroid[0] - ENVELOPE_CENTER_MM[0]) + abs(centroid[1] - ENVELOPE_CENTER_MM[1])
    visible = len({item for block in plan.blocks for item, _unit in block.occurrences})
    edge_count = len({(e.kind, e.source, e.target, e.net) for e in plan.edges})
    complexity = Complexity(len(plan.blocks), visible, edge_count)
    tolerance = tolerance_for(complexity)
    ratio = width * height / (210.0 * 140.0)
    return {
        "observable": True,
        "content_bbox_mm": [
            round(min(xs), 6),
            round(min(ys), 6),
            round(max(xs), 6),
            round(max(ys), 6),
        ],
        "occupied_area_ratio": round(ratio, 9),
        "centroid_offset_mm": round(offset, 6),
        "complexity": asdict(complexity),
        "tolerance": asdict(tolerance),
        "low_utilization": tolerance.minimum_occupied_ratio is not None
        and ratio < tolerance.minimum_occupied_ratio,
        "edge_bias": offset > tolerance.maximum_centroid_offset_mm,
    }


def _flow_order(plan, centers: dict) -> dict:
    by_id = {block.id: block for block in plan.blocks}
    relations = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"} and edge.source != edge.target
    }
    relations.update(
        (item.source_fragment, item.target_fragment, item.net)
        for item in plan.precedence
        if item.source_fragment != item.target_fragment
    )
    violations = []
    for source, target, net in sorted(relations):
        if source not in centers or target not in centers:
            continue
        if by_id.get(source) is None or by_id.get(target) is None:
            continue
        if by_id[source].kind == "interface" or by_id[target].kind == "interface":
            continue
        delta = centers[target][0] - centers[source][0]
        if delta < 0:
            violations.append(
                {
                    "source": source,
                    "target": target,
                    "net": net,
                    "reversal_mm": round(-delta, 6),
                }
            )
    return {
        "stage_order_inversions": len(violations),
        "cumulative_reversal_mm": round(sum(item["reversal_mm"] for item in violations), 6),
        "violations": violations,
    }


def _fragmentation(design: dict, plan, resolved: dict, text: dict) -> dict:
    points, _missing = _occurrence_points(design, plan, resolved, text)
    witnesses = []
    for block in plan.blocks:
        if block.kind == "interface":
            continue
        observed = [points[item] for item in block.occurrences if item in points]
        if len(observed) < 2:
            continue
        xs = [point[0] for point in observed]
        ys = [point[1] for point in observed]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        witnesses.append(
            {
                "block": block.id,
                "occurrence_count": len(observed),
                "manhattan_bbox_span_mm": round(span, 6),
            }
        )
    return {
        "multi_occurrence_block_count": len(witnesses),
        "total_intra_block_span_mm": round(
            sum(item["manhattan_bbox_span_mm"] for item in witnesses), 6
        ),
        "maximum_intra_block_span_mm": max(
            (item["manhattan_bbox_span_mm"] for item in witnesses), default=0.0
        ),
        "witnesses": witnesses,
    }


def _features(plan, design: dict, interface: dict, centers: dict) -> dict:
    outgoing = defaultdict(set)
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"}:
            outgoing[edge.source].add(edge.target)
    kinds = defaultdict(int)
    for block in plan.blocks:
        if block.kind != "interface":
            kinds[block.kind] += 1
    core_ys = sorted(
        centers[block.id][1]
        for block in plan.blocks
        if block.id in centers and not block.unused and block.kind in ACTIVE_CORE_KINDS
    )
    bands = []
    for y in core_ys:
        if not bands or y - bands[-1] > 5.08:
            bands.append(y)
    return {
        "linear_chain": bool(outgoing) and all(len(targets) <= 1 for targets in outgoing.values()),
        "branch_fanout": any(len(targets) > 1 for targets in outgoing.values())
        or any(edge.kind == "branch" for edge in plan.edges),
        "feedback": any(edge.kind == "feedback" for edge in plan.edges),
        "repeated_channels": max(kinds.values(), default=0) >= 3,
        "shared_rail": any(
            item.role == "distributive" and len(item.fragments) >= 2
            for item in plan.presentation_nets
        ),
        "internal_reference": any(item.internally_generated for item in plan.presentation_nets),
        "multi_output": sum(
            item["role"] == SIGNAL_OUTPUT_ROLE for item in interface["interface_owner_distances_mm"]
        )
        >= 2,
        "long_field_text": max(
            (len(str(item.get("value", ""))) for item in design["components"]), default=0
        )
        >= 24,
        "active_core_band_count": len(bands),
        "active_core_block_count": len(core_ys),
    }


def _signal_reachability(plan) -> set[tuple[str, str]]:
    outgoing = defaultdict(set)
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"} and edge.source != edge.target:
            outgoing[edge.source].add(edge.target)
    for item in plan.precedence:
        if item.source_fragment != item.target_fragment:
            outgoing[item.source_fragment].add(item.target_fragment)
    result = set()
    for source in sorted(outgoing):
        pending = list(sorted(outgoing[source]))
        seen = set()
        while pending:
            target = pending.pop()
            if target in seen:
                continue
            seen.add(target)
            result.add((source, target))
            pending.extend(sorted(outgoing.get(target, ())))
    return result


def _semantic_peer_signature(plan, block_id: str) -> tuple:
    by_id = {block.id: block for block in plan.blocks}
    block = by_id[block_id]
    incident = []
    for edge in plan.edges:
        if edge.source == block_id:
            neighbor = by_id.get(edge.target)
            incident.append(("out", edge.kind, neighbor.kind if neighbor else "unknown"))
        elif edge.target == block_id:
            neighbor = by_id.get(edge.source)
            incident.append(("in", edge.kind, neighbor.kind if neighbor else "unknown"))
    return (
        block.kind,
        tuple(sorted(port.role for port in block.ports)),
        tuple(sorted(incident)),
    )


def _repeated_alignment(plan, centers: dict, page: dict) -> dict:
    """Measure generic incomparable semantic peers against frozen band tolerance."""
    reachable = _signal_reachability(plan)
    groups = defaultdict(list)
    for block in plan.blocks:
        if block.kind == "interface" or block.unused or block.id not in centers:
            continue
        groups[_semantic_peer_signature(plan, block.id)].append(block.id)

    witnesses = []
    for signature, members in sorted(groups.items(), key=lambda item: repr(item[0])):
        ordered = sorted(members)
        if len(ordered) < 2:
            continue
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if (first, second) in reachable or (second, first) in reachable:
                    continue
                first_point, second_point = centers[first], centers[second]
                witnesses.append(
                    {
                        "members": [first, second],
                        "semantic_signature": repr(signature),
                        "x_displacement_mm": round(abs(first_point[0] - second_point[0]), 6),
                        "y_displacement_mm": round(abs(first_point[1] - second_point[1]), 6),
                        "off_axis_drift_mm": round(
                            min(
                                abs(first_point[0] - second_point[0]),
                                abs(first_point[1] - second_point[1]),
                            ),
                            6,
                        ),
                    }
                )

    tolerance = page.get("tolerance", {}).get("maximum_repeated_alignment_variance_mm")
    maximum = max((item["off_axis_drift_mm"] for item in witnesses), default=0.0)
    return {
        "applicable": bool(witnesses),
        "peer_pair_count": len(witnesses),
        "maximum_off_axis_drift_mm": maximum,
        "frozen_tolerance_mm": tolerance,
        "within_frozen_tolerance": tolerance is None or maximum <= tolerance,
        "witnesses": witnesses,
    }


def analyze_case(case: str, path: Path, svg: bytes, resolved: dict) -> dict:
    design = json.loads(path.read_text())
    plan = semantic_plan(validate(design, resolved), resolved)
    text = _text(svg)
    centers, missing, observed = _centers(design, plan, resolved, text)
    interface = _interfaces(plan, centers)
    flow_order = _flow_order(plan, centers)
    fragmentation = _fragmentation(design, plan, resolved, text)
    segments = _wires(svg)
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segments)
    routing = measure_routing_readability(segments, semantic_local_length=length)
    labels = _label_disconnects(design, plan, text, segments)
    page = _page(plan, centers)
    features = _features(plan, design, interface, centers)
    repeated = _repeated_alignment(plan, centers, page)
    record = {
        "case": case,
        "design": str(path.relative_to(ROOT)),
        "svg_sha256": _sha(svg),
        "observation_coverage": {
            "semantic_occurrence_count": sum(len(block.occurrences) for block in plan.blocks),
            "observed_occurrence_count": observed,
            "missing_or_ambiguous_occurrences": missing,
            "wire_segment_count": len(segments),
        },
        "interface_flow": interface,
        "flow_order": flow_order,
        "functional_fragmentation": fragmentation,
        "page": page,
        "routing": {
            "bend_count": routing.bend_count,
            "u_shaped_detours": routing.u_shaped_detours,
            "sibling_branch_geometry_inconsistency_mm": round(
                routing.sibling_branch_geometry_inconsistency / MM_TO_NM, 6
            ),
            "local_label_disconnects": labels,
        },
        "semantic_features": features,
        "repeated_structure": repeated,
    }
    record["rank_key"] = [
        len(interface["interface_side_violations"]),
        len(labels),
        int(bool(page.get("low_utilization"))) + int(bool(page.get("edge_bias"))),
        routing.u_shaped_detours,
        record["routing"]["sibling_branch_geometry_inconsistency_mm"],
    ]
    return record


def _archetype_examples(records: list[dict]) -> dict:
    result = {}
    names = (
        "linear_chain",
        "branch_fanout",
        "feedback",
        "repeated_channels",
        "shared_rail",
        "internal_reference",
        "multi_output",
        "long_field_text",
    )
    for name in names:
        matches = [r for r in records if r["semantic_features"][name]]
        if matches:
            result[name] = min(matches, key=lambda r: r["case"])["case"]
    structural = [r for r in records if r["case"].startswith("structural__")]
    if structural:
        result["structural_multi_band"] = max(
            structural, key=lambda r: (r["semantic_features"]["active_core_band_count"], r["case"])
        )["case"]
        one = [r for r in structural if r["semantic_features"]["active_core_band_count"] == 1]
        if one:
            result["structural_one_band"] = max(
                one, key=lambda r: (r["semantic_features"]["active_core_block_count"], r["case"])
            )["case"]
    mixed = [
        r
        for r in records
        if r["case"].startswith("i")
        and sum(bool(r["semantic_features"][name]) for name in names) >= 3
    ]
    if mixed:
        result["mixed_interaction"] = max(
            mixed,
            key=lambda r: (sum(bool(r["semantic_features"][name]) for name in names), r["case"]),
        )["case"]
    return result


def _repeated_structure_corpus(records: list[dict]) -> dict:
    bands = {}
    applicable_total = 0
    for band, tolerance in FROZEN_TOLERANCES.items():
        candidates = [
            record
            for record in records
            if record["page"].get("tolerance", {}).get("band") == band
            and record["repeated_structure"]["applicable"]
        ]
        applicable_total += len(candidates)
        bands[band] = {
            "frozen_tolerance_mm": tolerance.maximum_repeated_alignment_variance_mm,
            "applicable_case_count": len(candidates),
            "passing_case_count": sum(
                record["repeated_structure"]["within_frozen_tolerance"] for record in candidates
            ),
            "failing_case_count": sum(
                not record["repeated_structure"]["within_frozen_tolerance"] for record in candidates
            ),
            "maximum_observed_off_axis_drift_mm": max(
                (
                    record["repeated_structure"]["maximum_off_axis_drift_mm"]
                    for record in candidates
                ),
                default=0.0,
            ),
        }
    return {
        "selection_rule": (
            "predeclared_generic_complexity_band_thresholds_recorded_against_"
            "the_full_frozen_corpus_without_case_specific_retuning"
        ),
        "applicable_case_count": applicable_total,
        "bands": bands,
    }


def build_report(root: Path = ROOT, manifest: Path = MANIFEST) -> dict:
    svgs, provenance = _svgs(root, manifest)
    designs = _designs()
    missing = sorted(set(svgs) - designs.keys())
    if missing:
        raise ValueError(f"no authored design fixture mapping for archived cases: {missing}")
    resolved = assets()
    records = [analyze_case(case, designs[case], svgs[case], resolved) for case in sorted(svgs)]
    ranked = sorted(records, key=lambda r: (tuple(-v for v in r["rank_key"]), r["case"]))
    return {
        "schema_version": "m2h2.historical-native-composition-baseline.1",
        "status": "historical_baseline_observation_only_not_current_qualification",
        "provenance": provenance,
        "observer_scope": {
            "geometry": "hash-verified native KiCad SVG text coordinates and wire paths",
            "production_scores_consumed": False,
            "acceptance_claimed": False,
        },
        "archetype_examples": _archetype_examples(records),
        "repeated_structure_corpus": _repeated_structure_corpus(records),
        "ranked_case_ids": [r["case"] for r in ranked],
        "cases": ranked,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    report = build_report(ROOT, args.manifest)
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    seed = next(r for r in report["cases"] if r["case"] == "i4__b2_mixed")
    print(
        json.dumps(
            {
                "cases": len(report["cases"]),
                "archive_inventory_sha256": report["provenance"]["inventory_sha256"],
                "i4_interface_side_violations": len(
                    seed["interface_flow"]["interface_side_violations"]
                ),
                "i4_local_label_disconnects": len(seed["routing"]["local_label_disconnects"]),
                "i4_u_shaped_detours": seed["routing"]["u_shaped_detours"],
                "i4_edge_bias": seed["page"].get("edge_bias"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
