"""Metamorphic controls for historical SVG wire geometry."""

import pytest

from ai_kicad.m2a import ROOT
from tools.inspect_m2h2_historical_svg_routes import analyze_archive, measure_svg_wires


def svg(*paths: str) -> bytes:
    strokes = "".join(f'<path d="{path}"/>' for path in paths)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g style="stroke:#840000"><path d="M0 0 L297 0"/></g>'
        f'<g style="stroke:#009600">{strokes}</g></svg>'
    ).encode()


def test_split_duplicate_and_reversal_invariant() -> None:
    original = measure_svg_wires(svg("M10 20 L30 20", "M30 20 L30 40"))
    split = measure_svg_wires(
        svg("M30 20 L20 20", "M10 20 L20 20", "M30 40 L30 20", "M20 20 L30 20")
    )
    assert original == split
    assert original["wire_length_mm"] == 40
    assert original["wire_bends"] == 1


def test_endpoint_tee_vs_pure_crossing() -> None:
    tee = measure_svg_wires(svg("M0 10 L30 10", "M15 10 L15 20"))
    crossing = measure_svg_wires(svg("M0 10 L30 10", "M15 0 L15 20"))
    assert tee["wire_branch_points"] == 1
    assert crossing["wire_branch_points"] == 0


def test_invalid_wire_path_rejected() -> None:
    with pytest.raises(ValueError, match="grammar"):
        measure_svg_wires(svg("M0 0 C1 1 2 2 3 3"))
    with pytest.raises(ValueError, match="diagonal"):
        measure_svg_wires(svg("M0 0 L1 1"))


def test_all_hash_verified_native_renders_screened() -> None:
    manifest = (
        ROOT / "fixtures/m2h2/human_composition_baseline_2026-10-08/"
        "native_render_archive_manifest_42ab8452.json"
    )
    report = analyze_archive(ROOT, manifest)
    assert report["case_count"] == 90
    assert report["status"] == "historical_baseline_only_not_current_qualification"
    seed = next(case for case in report["cases"] if case["case"] == "i4__b2_mixed")
    assert seed["wire_bbox_width_mm"] == 93.98
    assert seed["wire_bbox_height_mm"] == 52.07
    assert seed["wire_length_mm"] == 177.8
