"""Screen verified historical native KiCad SVG wire geometry, never visual PASS."""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree

from ai_kicad.m2a import ROOT
from ai_kicad.m2_native_render_archive_materialize import load_native_baseline

SCALE = 10000
WIRE_STYLE = re.compile(r"(?:^|;)\s*stroke\s*:\s*#009600\b", re.IGNORECASE)
WIRE_PATH = re.compile(
    r"\s*M\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)"
    r"\s*L\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*"
)
Point = tuple[int, int]
Segment = tuple[Point, Point]


def extract_wire_segments(svg: bytes) -> tuple[Segment, ...]:
    """Only green wire paths; exclude page frame, symbol ink and text."""
    root = ElementTree.fromstring(svg)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("not an SVG document")
    result: list[Segment] = []
    for group in root:
        if not WIRE_STYLE.search(group.get("style", "")):
            continue
        for element in group.iter():
            if element.tag.rsplit("}", 1)[-1] != "path":
                continue
            match = WIRE_PATH.fullmatch(element.get("d", ""))
            if match is None:
                raise ValueError("unexpected green-wire SVG path grammar")
            x1, y1, x2, y2 = (int(Decimal(p) * SCALE) for p in match.groups())
            if (x1, y1) == (x2, y2):
                continue
            if x1 != x2 and y1 != y2:
                raise ValueError("unexpected diagonal wire in historical SVG")
            result.append(((x1, y1), (x2, y2)))
    return tuple(result)


def _merge_intervals(segments: tuple[Segment, ...]) -> tuple[Segment, ...]:
    """Physical strokes are invariant to reversal, splits and overlap."""
    by_line: dict[tuple[str, int], list[tuple[int, int]]] = defaultdict(list)
    for a, b in segments:
        if a == b:
            continue
        if a[1] == b[1]:
            key, span = ("h", a[1]), tuple(sorted((a[0], b[0])))
        elif a[0] == b[0]:
            key, span = ("v", a[0]), tuple(sorted((a[1], b[1])))
        else:
            raise ValueError("diagonal wire segment")
        by_line[key].append(span)
    result: list[Segment] = []
    for (axis, fixed), spans in sorted(by_line.items()):
        low, high = sorted(spans)[0]
        for left, right in sorted(spans)[1:]:
            if left <= high:
                high = max(high, right)
            else:
                result.append(_segment(axis, fixed, low, high))
                low, high = left, right
        result.append(_segment(axis, fixed, low, high))
    return tuple(sorted(result))


def _segment(axis: str, fixed: int, low: int, high: int) -> Segment:
    return ((low, fixed), (high, fixed)) if axis == "h" else ((fixed, low), (fixed, high))


def _arms(point: Point, segments: tuple[Segment, ...]) -> set[str]:
    x, y = point
    arms: set[str] = set()
    for a, b in segments:
        if a[1] == b[1] == y:
            low, high = sorted((a[0], b[0]))
            if low < x <= high:
                arms.add("left")
            if low <= x < high:
                arms.add("right")
        elif a[0] == b[0] == x:
            low, high = sorted((a[1], b[1]))
            if low < y <= high:
                arms.add("up")
            if low <= y < high:
                arms.add("down")
    return arms


def measure_svg_wires(svg: bytes) -> dict[str, int | float | None]:
    """Geometry-only observations; no net/ownership inference."""
    segments = _merge_intervals(extract_wire_segments(svg))
    if not segments:
        return {
            "wire_length_mm": 0.0,
            "wire_bbox_width_mm": 0.0,
            "wire_bbox_height_mm": 0.0,
            "wire_bbox_ratio_of_210x140": 0.0,
            "wire_centroid_x_mm": None,
            "wire_centroid_y_mm": None,
            "wire_bends": 0,
            "wire_branch_points": 0,
            "wire_stroke_count": 0,
        }
    points = {p for s in segments for p in s}
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    width, height = (max(xs) - min(xs)) / SCALE, (max(ys) - min(ys)) / SCALE
    bends = branches = 0
    for p in points:
        arms = _arms(p, segments)
        branches += len(arms) > 2
        bends += len(arms) == 2 and bool(arms & {"left", "right"}) and bool(
            arms & {"up", "down"}
        )
    return {
        "wire_length_mm": round(
            sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segments) / SCALE, 4
        ),
        "wire_bbox_width_mm": round(width, 4),
        "wire_bbox_height_mm": round(height, 4),
        "wire_bbox_ratio_of_210x140": round(width * height / (210 * 140), 6),
        "wire_centroid_x_mm": round((min(xs) + max(xs)) / (2 * SCALE), 4),
        "wire_centroid_y_mm": round((min(ys) + max(ys)) / (2 * SCALE), 4),
        "wire_bends": bends,
        "wire_branch_points": branches,
        "wire_stroke_count": len(segments),
    }


def analyze_archive(root: Path, manifest: Path) -> dict:
    inventory, parts = load_native_baseline(root, manifest)
    expected = dict(inventory.case_hashes)
    cases: list[dict] = []
    for part in parts:
        for record in part["renders"]:
            case = record["case"]
            svg = gzip.decompress(base64.b64decode(record["data"], validate=True))
            digest = hashlib.sha256(svg).hexdigest()
            if expected.get(case) != digest:
                raise ValueError(f"unverified historical SVG: {case}")
            cases.append({"case": case, "svg_sha256": digest, **measure_svg_wires(svg)})
    if len(cases) != len(expected) or len({e["case"] for e in cases}) != len(cases):
        raise ValueError("historical native SVG inventory incomplete or duplicated")
    # This ranks screening priority, NOT defects: tiny probes may be legitimate.
    cases.sort(key=lambda e: (e["wire_bbox_ratio_of_210x140"], e["case"]))
    for rank, case in enumerate(cases, 1):
        case["geometry_review_rank"] = rank
    return {
        "schema_version": "m2h2.historical-svg-wire-geometry-screening.1",
        "status": "historical_baseline_only_not_current_qualification",
        "metric_scope": "green SVG wire strokes only; excludes symbols, labels and fields",
        "ranking_scope": "smallest wire bounding box first; not a defect or acceptance decision",
        "historical_qualification_sha": inventory.qualification_head,
        "archive_inventory_sha256": inventory.inventory_sha256,
        "case_count": len(cases),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT
        / "fixtures/m2h2/human_composition_baseline_2026-10-08/"
        "native_render_archive_manifest_42ab8452.json",
    )
    args = parser.parse_args()
    report = analyze_archive(ROOT, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"Screened {report['case_count']} hash-verified historical native SVGs")
    print("Geometry-only review ranking; not a current-source composition PASS")


if __name__ == "__main__":
    main()
