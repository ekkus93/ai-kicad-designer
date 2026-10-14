"""Soft interface-owner locality must not hide same-hard-flow route alternatives."""

from ai_kicad.m2_composition_tradeoff_report import summarize_comparable_candidates


def test_soft_owner_distance_does_not_hide_better_route() -> None:
    selected = {
        "stage_order_violations": 0,
        "reversal_distance": 0,
        "interface_side_violations": 0,
        "interface_owner_distance": 8,
    }
    alternative = {**selected, "interface_owner_distance": 12}
    selection = {
        "selected_seed": 1,
        "selected_round": 0,
        "selected_score": [200_000_000, 0, 8],
        "selected_selection_key": [0] * 18 + [10] + [0] * 4 + [250_000_000],
        "selected_semantic_penalty_breakdown": selected,
        "proved_candidates": [
            {
                "seed": 2,
                "round": 0,
                "score": [180_000_000, 0, 6],
                "selection_key": [0] * 18 + [5] + [0] * 4 + [220_000_000],
                "semantic_penalty_breakdown": alternative,
            }
        ],
    }
    report = summarize_comparable_candidates(selection)
    assert report["same_flow_side_alternative_count"] == 1
    row = report["best_row_locality_alternatives"][0]
    assert row["soft_semantic_delta_from_selected"]["interface_owner_distance"] == 4
    assert row["delta_from_selected"]["route_backtracking"] == -5
    assert report["acceptance_claimed"] is False
