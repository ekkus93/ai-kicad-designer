import pytest

from ai_kicad.m2_tiny_grid_composition_oracle import (
    TinyNode,
    exhaustive_tiny_grid_oracle,
)
from ai_kicad.m2_tiny_grid_oracle_miss_evidence import (
    require_bounded_search_miss_evidence,
)


def _oracle(*, reversed_order: bool):
    nodes = (
        TinyNode("input", "connector", side_preference="left"),
        TinyNode("output", "connector", side_preference="right"),
    )
    positions = (
        (("input", (10, 0)), ("output", (0, 0)))
        if reversed_order
        else (("input", (0, 0)), ("output", (10, 0)))
    )
    return exhaustive_tiny_grid_oracle(
        nodes,
        ((0, 0), (10, 0)),
        production_positions=positions,
    )


def test_optimal_candidate_needs_no_search_miss_excuse() -> None:
    oracle = _oracle(reversed_order=False)
    assert oracle.production_candidate is not None
    score = oracle.production_candidate.score_vector
    audit = require_bounded_search_miss_evidence(oracle, (score,), attempt_budget=1)
    assert not audit.missed_optimum
    assert audit.to_dict()["attempted_count"] == 1
    assert audit.to_dict()["oracle_best_score"] == list(score)


def test_bounded_miss_requires_full_budget_and_fixed_reason() -> None:
    oracle = _oracle(reversed_order=True)
    assert oracle.production_candidate is not None
    bad = oracle.production_candidate.score_vector
    audit = require_bounded_search_miss_evidence(
        oracle, (bad,), attempt_budget=1, miss_reason="bounded_candidate_budget"
    )
    assert audit.missed_optimum
    assert audit.selected_score > audit.oracle_best_score
    assert audit.to_dict()["miss_reason"] == "bounded_candidate_budget"


@pytest.mark.parametrize(
    ("attempts", "budget", "reason"),
    (
        (1, 1, None),
        (1, 1, "manual_override"),
        (1, 2, "bounded_candidate_budget"),
        (2, 2, "bounded_candidate_budget"),
    ),
)
def test_dominated_result_cannot_escape_without_valid_budget_witness(
    attempts: int, budget: int, reason: str | None
) -> None:
    oracle = _oracle(reversed_order=True)
    assert oracle.production_candidate is not None
    bad = oracle.production_candidate.score_vector
    with pytest.raises(ValueError, match="exhausted-budget"):
        require_bounded_search_miss_evidence(
            oracle, (bad,) * attempts, attempt_budget=budget, miss_reason=reason
        )


def test_rejects_skipping_better_attempted_candidate() -> None:
    oracle = _oracle(reversed_order=True)
    optimal = _oracle(reversed_order=False)
    assert oracle.production_candidate is not None
    assert optimal.production_candidate is not None
    with pytest.raises(ValueError, match="best attempted"):
        require_bounded_search_miss_evidence(
            oracle,
            (
                oracle.production_candidate.score_vector,
                optimal.production_candidate.score_vector,
            ),
            attempt_budget=2,
            miss_reason="bounded_candidate_budget",
        )


def test_rejects_invalid_scores_and_false_miss_excuses() -> None:
    oracle = _oracle(reversed_order=False)
    assert oracle.production_candidate is not None
    score = oracle.production_candidate.score_vector
    with pytest.raises(ValueError, match="invalid attempted"):
        require_bounded_search_miss_evidence(
            oracle, ((-1, *score[1:]),), attempt_budget=1
        )
    with pytest.raises(ValueError, match="must not claim"):
        require_bounded_search_miss_evidence(
            oracle, (score,), attempt_budget=1, miss_reason="bounded_candidate_budget"
        )
    with pytest.raises(ValueError, match="attempt accounting"):
        require_bounded_search_miss_evidence(oracle, (), attempt_budget=1)
