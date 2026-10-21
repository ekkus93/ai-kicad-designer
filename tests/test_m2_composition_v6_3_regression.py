"""Source-level composition regression for the V6-3 reference/filter/feedback archetype."""

import json

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2_semantics import semantic_plan
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate


def test_v6_3_internal_reference_and_filter_feedback_remain_composable() -> None:
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2blind_v6/ir/V6-3.json").read_text()),
        resolved,
    )
    plan = semantic_plan(design, resolved)

    assert any(
        edge.kind == "reference"
        and edge.source == "function.amp.a"
        and edge.target == "package.amp.power"
        for edge in plan.edges
    )
    assert any(
        edge.kind == "feedback" and edge.source == edge.target == "function.amp.a"
        for edge in plan.edges
    )
    assert any(
        edge.kind == "branch"
        and edge.source == "function.amp.a"
        and edge.target == "passive.output_filter.series"
        for edge in plan.edges
    )

    _scene, evidence = compose_with_evidence(design, resolved)
    selection = evidence["candidate_selection"]

    assert selection["proved_candidate_count"] >= 1
    assert selection["selected_semantic_penalty_breakdown"]["feedback_distance"] == 0
    assert selection["selected_semantic_penalty_breakdown"]["missing_geometry"] == 0
