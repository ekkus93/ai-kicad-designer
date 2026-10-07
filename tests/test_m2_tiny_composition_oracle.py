from ai_kicad.m2_tiny_composition_oracle import (
    TinyEdge,
    TinyNode,
    exhaustive_tiny_grid_oracle,
    production_dominated_by_oracle,
)


def test_tiny_oracle_prefers_input_left_output_right_and_forward_order() -> None:
    candidates = exhaustive_tiny_grid_oracle(
        (
            TinyNode("input", "input"),
            TinyNode("stage", "stage"),
            TinyNode("output", "output"),
        ),
        (TinyEdge("input", "stage"), TinyEdge("stage", "output")),
        width=3,
        height=1,
    )

    best = candidates[0]
    assert dict(best.positions) == {"input": (0, 0), "output": (2, 0), "stage": (1, 0)}
    assert best.score[:2] == (0, 0)


def test_tiny_oracle_preserves_sibling_incomparability() -> None:
    candidates = exhaustive_tiny_grid_oracle(
        (
            TinyNode("input", "input"),
            TinyNode("left_branch", "stage"),
            TinyNode("right_branch", "stage"),
        ),
        (TinyEdge("input", "left_branch"), TinyEdge("input", "right_branch")),
        width=2,
        height=2,
    )

    first_best = candidates[0].score
    tied_best = [candidate for candidate in candidates if candidate.score == first_best]
    sibling_orders = {
        dict(candidate.positions)["left_branch"][1] < dict(candidate.positions)["right_branch"][1]
        for candidate in tied_best
    }
    assert sibling_orders == {False, True}


def test_tiny_oracle_scores_support_grouping() -> None:
    candidates = exhaustive_tiny_grid_oracle(
        (TinyNode("stage", "stage"), TinyNode("support", "support", owner="stage")),
        (TinyEdge("support", "stage", "support"),),
        width=3,
        height=1,
    )

    assert candidates[0].score[2] == 1
    assert production_dominated_by_oracle((0, 0, 2, 0, 2), candidates)


def test_tiny_oracle_reports_reversal_witness_for_bad_production_score() -> None:
    candidates = exhaustive_tiny_grid_oracle(
        (TinyNode("a", "stage"), TinyNode("b", "stage")),
        (TinyEdge("a", "b"),),
        width=2,
        height=1,
    )

    assert candidates[0].score[1] == 0
    assert production_dominated_by_oracle((0, 1, 0, 0, 1), candidates)
