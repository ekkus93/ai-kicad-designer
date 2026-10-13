from ai_kicad.m2_composition_tradeoff_report import summarize_comparable_candidates


def candidate(seed, row, frontier, length, side=0, backtracking=0):
    return {
        "seed": seed,
        "round": 0,
        "score": [length],
        "selection_key": [0] * 17 + [backtracking],
        "semantic_penalty_breakdown": {
            "stage_order_violations": 0,
            "reversal_distance": 0,
            "interface_side_violations": side,
            "interface_owner_distance": 0,
            "frontier_distance": frontier,
            "branch_alignment": 0,
            "directed_interface_row_drift": row,
            "local_signal_neighbor_gap": 0,
        },
    }


def test_tradeoff_exposes_lower_row_drift_without_promoting_wrong_side():
    chosen = candidate(4, 68, 46, 335_280_000, backtracking=78)
    row_better = candidate(1, 28, 61, 287_020_000, backtracking=88)
    wrong_side = candidate(2, 0, 0, 200_000_000, side=1)
    selection = {
        "selected_seed": chosen["seed"],
        "selected_round": chosen["round"],
        "selected_score": chosen["score"],
        "selected_selection_key": chosen["selection_key"],
        "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
        "proved_candidates": [wrong_side, chosen, row_better],
    }
    report = summarize_comparable_candidates(selection)
    assert report["selected"]["route_backtracking"] == 78
    assert report["same_flow_side_alternative_count"] == 1
    assert report["better_row_locality_count"] == 1
    assert report["best_row_locality_alternatives"][0]["delta_from_selected"] == {
        "frontier_distance": 15,
        "directed_interface_row_drift": -40,
        "route_backtracking": 10,
        "routed_union_length_nm": -48_260_000,
    }
    assert report["best_row_locality_alternatives"][0]["seed"] == 1
    assert report["best_row_locality_alternatives"][0]["directed_interface_row_drift"] == 28
    assert report["acceptance_claimed"] is False
    assert summarize_comparable_candidates({})["best_row_locality_alternatives"] == []


def test_tradeoff_is_bounded_and_stable_under_candidate_permutation():
    chosen = candidate(4, 68, 46, 335_280_000)
    others = [
        candidate(seed, row, 60, 300_000_000 + seed) for seed, row in ((1, 3), (2, 2), (3, 1))
    ]
    selection = {
        "selected_seed": 4,
        "selected_round": 0,
        "selected_score": chosen["score"],
        "selected_selection_key": chosen["selection_key"],
        "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
        "proved_candidates": others,
    }
    report = summarize_comparable_candidates(selection, limit=2)
    assert [x["seed"] for x in report["best_row_locality_alternatives"]] == [3, 2]
    assert report["same_flow_side_alternative_count"] == 3
    assert report["better_row_locality_count"] == 3
    assert report["truncated"] is True
    selection["proved_candidates"] = list(reversed(others))
    assert summarize_comparable_candidates(selection, limit=2) == report


def test_first_rank_difference_identifies_earliest_production_priority():
    selected = candidate(4, 68, 46, 335_280_000, backtracking=78)
    alternative = candidate(1, 28, 61, 287_020_000, backtracking=88)
    selected["selection_key"][5] = 46
    alternative["selection_key"][5] = 61
    selection = {
        "selected_seed": selected["seed"],
        "selected_round": selected["round"],
        "selected_score": selected["score"],
        "selected_selection_key": selected["selection_key"],
        "selected_semantic_penalty_breakdown": selected["semantic_penalty_breakdown"],
        "proved_candidates": [alternative],
    }
    result = summarize_comparable_candidates(selection)
    assert result["best_row_locality_alternatives"][0]["first_rank_difference"] == {
        "index": 5,
        "candidate_value": 61,
        "selected_value": 46,
        "candidate_preferred": False,
    }

    alternative["selection_key"][5] = 46
    result = summarize_comparable_candidates(selection)
    assert result["best_row_locality_alternatives"][0]["first_rank_difference"] == {
        "index": 17,
        "candidate_value": 88,
        "selected_value": 78,
        "candidate_preferred": False,
    }


def test_first_rank_difference_handles_missing_or_equal_keys():
    selected = candidate(4, 68, 46, 335_280_000)
    alternative = candidate(1, 28, 46, 287_020_000)
    selection = {
        "selected_seed": selected["seed"],
        "selected_round": selected["round"],
        "selected_score": selected["score"],
        "selected_selection_key": selected["selection_key"],
        "selected_semantic_penalty_breakdown": selected["semantic_penalty_breakdown"],
        "proved_candidates": [alternative],
    }
    result = summarize_comparable_candidates(selection)
    assert result["best_row_locality_alternatives"][0]["first_rank_difference"] == {
        "index": None,
        "candidate_value": None,
        "selected_value": None,
        "candidate_preferred": False,
    }
    alternative["selection_key"] = []
    assert (
        summarize_comparable_candidates(selection)["best_row_locality_alternatives"][0][
            "first_rank_difference"
        ]
        is None
    )
