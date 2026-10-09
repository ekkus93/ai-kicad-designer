from __future__ import annotations

import json
from pathlib import Path

from ai_kicad.m2a import ROOT

import sys

sys.path.insert(0, str(ROOT / "tools"))

from analyze_m2h2_historical_composition import (  # noqa: E402
    MANIFEST,
    _design_paths,
    _verified_svg_by_case,
    analyze_case,
)
from ai_kicad.m2b import assets  # noqa: E402


def test_frozen_native_inventory_maps_every_archived_render_to_authored_design() -> None:
    svgs, provenance = _verified_svg_by_case(ROOT, MANIFEST)
    designs = _design_paths()
    assert provenance["native_svg_count"] == 90
    assert set(svgs) <= designs.keys()
    assert provenance["inventory_sha256"] == (
        "759f49bf715da357d70f4fb4ae5513594328acb3ba8612031866ac6788a21fe0"
    )


def test_i4_falsification_seed_is_detected_from_semantics_and_native_geometry() -> None:
    svgs, _ = _verified_svg_by_case(ROOT, MANIFEST)
    designs = _design_paths()
    record = analyze_case("i4__b2_mixed", designs["i4__b2_mixed"], svgs["i4__b2_mixed"], assets())

    violations = record["interface_flow"]["interface_side_violations"]
    assert [(item["interface_id"], item["expected_side"]) for item in violations] == [
        ("interface.output_1", "right"),
        ("interface.output_2", "right"),
    ]
    assert all(item["distance"] > 60 for item in violations)
    detachments = record["interface_flow"]["interface_owner_detachments"]
    assert {item["interface_id"] for item in detachments} == {
        "interface.output_1",
        "interface.output_2",
    }
    assert record["page"]["edge_bias"] is True
    assert record["routing"]["u_shaped_detours"] >= 1
    assert record["routing"]["sibling_branch_geometry_inconsistency_mm"] > 0
    assert any(
        witness["net"] == "INPUT" for witness in record["routing"]["local_label_disconnects"]
    )
    assert record["observation_coverage"]["missing_or_ambiguous_occurrences"] == []


def test_analysis_is_evidence_only_and_never_claims_current_qualification() -> None:
    source = (ROOT / "tools/analyze_m2h2_historical_composition.py").read_text()
    assert "historical_baseline_observation_only_not_current_qualification" in source
    assert "production_scores_consumed\": False" in source
    assert "acceptance_claimed\": False" in source
    analysis_body = source.split("def analyze_case", 1)[1].split("def _archetype_examples", 1)[0]
    assert "i4__b2_mixed" not in analysis_body
