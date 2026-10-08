from ai_kicad.m2_composition_production_integration_audit import (
    ProductionIntegrationFinding,
    audit_production_ranking_integration,
    production_ranking_integration_passes,
)


def test_audit_rejects_old_routing_first_candidate_selection() -> None:
    source = """
score = (sum(tree.length for tree in canonical_trees), seed_index)
selected = min(proved_candidates, key=lambda item: item[0])
evidence = {"candidate_selection": {"rule": "proved_union_length_then_worst_length_bends_area"}}
"""

    findings = audit_production_ranking_integration(source)

    assert (
        ProductionIntegrationFinding(
            "routing_compactness_still_primary",
            "selected = min(proved_candidates, key=lambda item: item[0])",
        )
        in findings
    )
    assert (
        ProductionIntegrationFinding(
            "stale_candidate_selection_rule",
            "proved_union_length_then_worst_length_bends_area",
        )
        in findings
    )
    assert not production_ranking_integration_passes(source)


def test_audit_requires_semantic_key_on_proved_candidate_packing() -> None:
    source = "from .m2_composition_candidate_rank import composition_candidate_key\n"

    findings = audit_production_ranking_integration(source)

    assert (
        ProductionIntegrationFinding(
            "semantic_key_not_applied_to_proved_candidates",
            "composition_candidate_key(plan, <packing>, <routing_compactness>)",
        )
        in findings
    )


def test_audit_accepts_semantic_first_candidate_selection() -> None:
    source = """
from .m2_composition_candidate_rank import (
    composition_candidate_key,
    semantic_composition_penalties,
)
routing_compactness = (wire_length, worst_length, bends, area, seed_index, round_index)
semantic_score = composition_candidate_key(plan, working_packing, routing_compactness)
proved_candidates.append((semantic_score, routing_compactness, structure, working_packing))
selected = min(proved_candidates, key=lambda item: item[0])
evidence = {"candidate_selection": {"rule": "semantic_readability_then_routing_clarity_then_compactness"}}
"""

    assert production_ranking_integration_passes(source)
