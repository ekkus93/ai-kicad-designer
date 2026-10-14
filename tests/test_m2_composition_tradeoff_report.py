from ai_kicad.m2_composition_tradeoff_report import summarize_comparable_candidates


def candidate(seed, row, frontier, length, side=0, backtracking=0):
    return {
        "seed": seed,
        "round": 0,
        "score": [length],
        "selection_key": [0] * 18 + [backtracking],
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
        "index": 18,
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


def test_tradeoff_reports_measured_bend_length_priority_without_reranking():
    # The candidate key's first route-shape tier follows semantic and
    # backtracking obligations; the report must expose the existing key
    # rather than recalculate its cost or change candidate selection.
    chosen = candidate(1, 0, 0, 200_000_000, backtracking=3)
    alternative = candidate(2, 0, 0, 190_000_000, backtracking=3)
    chosen["score"] = [200_000_000, 90_000_000, 6]
    alternative["score"] = [190_000_000, 90_000_000, 7]
    chosen["selection_key"] = [0] * 23 + [300_000_000, 6, 200_000_000]
    alternative["selection_key"] = [0] * 23 + [290_000_000, 7, 190_000_000]
    selection = {
        "selected_seed": 1,
        "selected_round": 0,
        "selected_score": chosen["score"],
        "selected_selection_key": chosen["selection_key"],
        "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
        "proved_candidates": [chosen, alternative],
    }
    report = summarize_comparable_candidates(selection)
    assert report["selected"]["route_geometry_cost_nm"] == 300_000_000
    assert report["selected"]["route_bend_count"] == 6
    row = report["best_row_locality_alternatives"][0]
    assert row["route_geometry_cost_nm"] == 290_000_000
    assert row["route_bend_count"] == 7
    assert row["first_rank_difference"] == {
        "index": 23,
        "candidate_value": 290_000_000,
        "selected_value": 300_000_000,
        "candidate_preferred": True,
    }
    assert report["acceptance_claimed"] is False


def test_route_shape_tradeoff_surfaces_better_route_behind_semantic_preference():
    """A route improvement hidden by frontier priority must be inspectable."""
    chosen = candidate(1, 0, 12, 200_000_000, backtracking=8)
    alternate = candidate(2, 0, 13, 180_000_000, backtracking=3)
    chosen["selection_key"] = [0] * 23 + [260_000_000]
    alternate["selection_key"] = [0] * 23 + [240_000_000]
    chosen["score"] = [200_000_000, 100_000_000, 6]
    alternate["score"] = [180_000_000, 100_000_000, 5]
    chosen["semantic_penalty_breakdown"]["repeated_alignment"] = 4
    alternate["semantic_penalty_breakdown"]["repeated_alignment"] = 2
    chosen["selection_key"][5] = 12
    alternate["selection_key"][5] = 13
    chosen["selection_key"][18] = 8
    alternate["selection_key"][18] = 3
    report = summarize_comparable_candidates(
        {
            "selected_seed": 1,
            "selected_round": 0,
            "selected_score": chosen["score"],
            "selected_selection_key": chosen["selection_key"],
            "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
            "proved_candidates": [chosen, alternate],
        }
    )
    assert report["better_route_aesthetics_count"] == 1
    better = report["best_route_aesthetics_alternatives"][0]
    assert better["seed"] == 2
    assert better["route_shape_delta_from_selected"] == {
        "route_backtracking": -5,
        "route_geometry_cost_nm": -20_000_000,
        "route_bend_count": -1,
        "routed_union_length_nm": -20_000_000,
        "branch_alignment": 0,
        "repeated_alignment": -2,
    }
    assert better["first_rank_difference"]["index"] == 5
    assert better["first_rank_difference"]["candidate_preferred"] is False
    assert report["acceptance_claimed"] is False


def test_route_shape_tradeoff_handles_missing_legacy_scores_and_permutations():
    chosen = candidate(1, 0, 0, 200_000_000, backtracking=0)
    unknown = candidate(2, 0, 0, 100_000_000, backtracking=0)
    better = candidate(3, 0, 0, 100_000_000, backtracking=0)
    better["selection_key"] = [0] * 23 + [100_000_000]
    chosen["selection_key"] = [0] * 23 + [200_000_000]
    selection = {
        "selected_seed": 1,
        "selected_round": 0,
        "selected_score": chosen["score"],
        "selected_selection_key": chosen["selection_key"],
        "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
        "proved_candidates": [unknown, better],
    }
    report = summarize_comparable_candidates(selection)
    assert report["better_route_aesthetics_count"] == 1
    assert [x["seed"] for x in report["best_route_aesthetics_alternatives"]] == [3, 2]
    selection["proved_candidates"] = list(reversed(selection["proved_candidates"]))
    assert summarize_comparable_candidates(selection) == report


def test_route_improvement_blockers_identify_earlier_semantic_priorities():
    chosen = candidate(1, 0, 12, 200_000_000, backtracking=8)
    blocked = candidate(2, 0, 13, 180_000_000, backtracking=3)
    other = candidate(3, 0, 14, 190_000_000, backtracking=5)
    excluded = candidate(4, 0, 15, 170_000_000, side=1, backtracking=2)
    for item in (chosen, blocked, other, excluded):
        item["selection_key"] = [0] * 23 + [item["score"][0]]
        item["selection_key"][5] = item["semantic_penalty_breakdown"]["frontier_distance"]
        item["selection_key"][18] = item["selection_key"][18] or {
            1: 8, 2: 3, 3: 5, 4: 2
        }[item["seed"]]
    selection = {
        "selected_seed": 1,
        "selected_round": 0,
        "selected_score": chosen["score"],
        "selected_selection_key": chosen["selection_key"],
        "selected_semantic_penalty_breakdown": chosen["semantic_penalty_breakdown"],
        "proved_candidates": [other, excluded, chosen, blocked],
    }
    result = summarize_comparable_candidates(selection, limit=1)
    assert result["better_route_aesthetics_count"] == 2
    assert result["better_routes_blocked_by_rank_index"] == {"5": 2}
    selection["proved_candidates"] = list(reversed(selection["proved_candidates"]))
    assert summarize_comparable_candidates(selection, limit=1) == result
    assert summarize_comparable_candidates({})["better_routes_blocked_by_rank_index"] == {}
