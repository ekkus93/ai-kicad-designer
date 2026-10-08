"""Metamorphic checks for independent tiny-grid branch geometry evidence."""

import pytest

from ai_kicad.m2_tiny_grid_composition_oracle import (
    TinyBranch,
    TinyNode,
    exhaustive_tiny_grid_oracle,
)


def _evaluate(
    nodes: tuple[TinyNode, ...],
    branch: TinyBranch,
    positions: tuple[tuple[str, tuple[int, int]], ...],
):
    return exhaustive_tiny_grid_oracle(
        nodes,
        tuple(point for _, point in positions),
        branches=(branch,),
        production_positions=positions,
    )


def test_branch_target_permutation_preserves_penalty_and_dominance() -> None:
    nodes = (
        TinyNode("source", "stage"),
        TinyNode("first", "stage"),
        TinyNode("second", "stage"),
    )
    positions = (
        ("source", (0, 10)),
        ("first", (20, 0)),
        ("second", (20, 20)),
    )
    original = _evaluate(nodes, TinyBranch("source", ("first", "second")), positions)
    permuted = _evaluate(nodes, TinyBranch("source", ("second", "first")), positions)
    assert original.production_candidate is not None
    assert permuted.production_candidate is not None
    assert original.production_candidate.score_vector == permuted.production_candidate.score_vector
    assert (
        original.production_candidate.branch_geometry_penalty
        == permuted.production_candidate.branch_geometry_penalty
        == 0
    )
    assert original.production_is_dominated == permuted.production_is_dominated


def test_branch_node_renaming_preserves_geometry_and_dominance() -> None:
    original = _evaluate(
        (TinyNode("source", "stage"), TinyNode("first", "stage"), TinyNode("second", "stage")),
        TinyBranch("source", ("first", "second")),
        (("source", (20, 20)), ("first", (0, 0)), ("second", (40, 10))),
    )
    renamed = _evaluate(
        (TinyNode("z", "stage"), TinyNode("a", "stage"), TinyNode("b", "stage")),
        TinyBranch("z", ("a", "b")),
        (("z", (20, 20)), ("a", (0, 0)), ("b", (40, 10))),
    )
    assert original.production_candidate is not None
    assert renamed.production_candidate is not None
    assert original.production_candidate.score_vector == renamed.production_candidate.score_vector
    assert (
        original.production_candidate.branch_geometry_penalty
        == renamed.production_candidate.branch_geometry_penalty
    )
    assert original.production_is_dominated == renamed.production_is_dominated


def test_reordered_duplicate_branch_is_rejected() -> None:
    nodes = (TinyNode("src", "stage"), TinyNode("a", "stage"), TinyNode("b", "stage"))
    with pytest.raises(ValueError, match="duplicate tiny branch"):
        exhaustive_tiny_grid_oracle(
            nodes,
            ((0, 0), (10, 0), (20, 0)),
            branches=(
                TinyBranch("src", ("a", "b")),
                TinyBranch("src", ("b", "a")),
            ),
        )
