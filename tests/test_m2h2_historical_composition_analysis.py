from __future__ import annotations

from ai_kicad.m2a import ROOT

import sys

sys.path.insert(0, str(ROOT / "tools"))

from analyze_m2h2_historical_composition import (  # noqa: E402
    MANIFEST,
    _design_paths,
    _verified_svg_by_case,
    analyze_case,
    build_report,
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
    assert "stage_order_inversions" in record["flow_order"]
    assert "total_intra_block_span_mm" in record["functional_fragmentation"]


def test_full_historical_report_is_complete_ranked_and_archetype_covered() -> None:
    report = build_report()
    records = report["cases"]
    ranked = report["ranked_case_ids"]

    assert report["provenance"]["native_svg_count"] == 90
    assert len(records) == 90
    assert len(ranked) == 90
    assert len(set(ranked)) == 90
    assert set(ranked) == {record["case"] for record in records}
    assert [record["case"] for record in records] == ranked
    assert all(
        not record["observation_coverage"]["missing_or_ambiguous_occurrences"]
        for record in records
    )
    assert all("flow_order" in record and "functional_fragmentation" in record for record in records)

    required_archetypes = {
        "linear_chain",
        "branch_fanout",
        "feedback",
        "repeated_channels",
        "shared_rail",
        "internal_reference",
        "multi_output",
        "long_field_text",
        "structural_multi_band",
        "structural_one_band",
        "mixed_interaction",
    }
    assert required_archetypes <= report["archetype_examples"].keys()
    assert set(report["archetype_examples"].values()) <= set(ranked)

    seed = next(record for record in records if record["case"] == "i4__b2_mixed")
    assert seed["rank_key"][0] >= 2
    assert seed["rank_key"][1] >= 1
    assert seed["rank_key"][2] >= 1
    assert seed["rank_key"][3] >= 1
    assert seed["rank_key"][4] > 0


def test_analysis_is_evidence_only_and_never_claims_current_qualification() -> None:
    source = (ROOT / "tools/analyze_m2h2_historical_composition.py").read_text()
    assert "historical_baseline_observation_only_not_current_qualification" in source
    assert "production_scores_consumed\": False" in source
    assert "acceptance_claimed\": False" in source
    analysis_body = source.split("def analyze_case", 1)[1].split("def _archetype_examples", 1)[0]
    assert "i4__b2_mixed" not in analysis_body


def test_repeated_structure_tolerances_are_bound_to_full_corpus_without_retuning() -> None:
    report = build_report()
    evidence = report["repeated_structure_corpus"]
    assert evidence["selection_rule"] == (
        "predeclared_generic_complexity_band_thresholds_recorded_against_"
        "the_full_frozen_corpus_without_case_specific_retuning"
    )
    assert evidence["applicable_case_count"] > 0
    assert set(evidence["bands"]) == {"tiny", "small", "medium", "dense"}
    assert {
        band: item["frozen_tolerance_mm"]
        for band, item in evidence["bands"].items()
    } == {"tiny": 5.0, "small": 4.0, "medium": 3.0, "dense": 2.5}
    assert sum(
        item["applicable_case_count"] for item in evidence["bands"].values()
    ) == evidence["applicable_case_count"]
    assert all(
        item["passing_case_count"] + item["failing_case_count"]
        == item["applicable_case_count"]
        for item in evidence["bands"].values()
    )

    for record in report["cases"]:
        repeated = record["repeated_structure"]
        assert repeated["frozen_tolerance_mm"] == record["page"]["tolerance"][
            "maximum_repeated_alignment_variance_mm"
        ]
        assert repeated["peer_pair_count"] == len(repeated["witnesses"])
