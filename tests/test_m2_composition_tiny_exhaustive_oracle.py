"""Authored exhaustive controls independent of the production rank key."""

import pytest

from ai_kicad.m2_composition_tiny_exhaustive_oracle import (
    TinyEdge,
    TinyNode,
    exhaustive_tiny_composition,
    tiny_composition_metrics,
)


def test_linear_signal_chain_prefers_left_to_right() -> None:
    nodes = (TinyNode("source", "input"), TinyNode("gain"), TinyNode("sink", "output"))
    edges = (TinyEdge("source", "gain"), TinyEdge("gain", "sink"))
    result = exhaustive_tiny_composition(nodes, edges, ((0, 0), (1, 0), (2, 0)))
    assert result.evaluated == 6
    assert result.best_score[:3] == (0, 0, 0)
    assert all(
        dict(placement)["source"][0]
        < dict(placement)["gain"][0]
        < dict(placement)["sink"][0]
        for placement in result.best_placements
    )


def test_incomparable_siblings_can_swap_without_penalty() -> None:
    nodes = (TinyNode("root"), TinyNode("left"), TinyNode("right"))
    edges = (TinyEdge("root", "left", "branch"), TinyEdge("root", "right", "branch"))
    result = exhaustive_tiny_composition(nodes, edges, ((0, 0), (1, 0), (2, 0)))
    assert len(result.best_placements) == 2
    assert {dict(p)["root"] for p in result.best_placements} == {(0, 0)}


def test_feedback_and_shared_rail_do_not_create_forward_precedence() -> None:
    nodes = (TinyNode("a"), TinyNode("b"))
    slots = ((0, 0), (1, 0))
    for kind in ("feedback", "power", "reference"):
        result = exhaustive_tiny_composition(nodes, (TinyEdge("a", "b", kind),), slots)
        assert result.best_score[:3] == (0, 0, 0)
        assert len(result.best_placements) == 2


def test_support_owner_distance_is_measured_independently() -> None:
    nodes = (TinyNode("stage"), TinyNode("cap", "support"), TinyNode("out", "output"))
    edges = (TinyEdge("cap", "stage", "support"), TinyEdge("stage", "out"))
    near = {"stage": (0, 0), "cap": (1, 0), "out": (4, 0)}
    far = {"stage": (0, 0), "cap": (4, 0), "out": (1, 0)}
    assert tiny_composition_metrics(nodes, edges, near)[4] == 1
    assert tiny_composition_metrics(nodes, edges, far)[4] == 4


def test_hard_gate_cannot_be_traded_for_aesthetic_score() -> None:
    nodes = (TinyNode("a"), TinyNode("b"))
    result = exhaustive_tiny_composition(
        nodes,
        (TinyEdge("a", "b"),),
        ((0, 0), (1, 0)),
        hard_gate=lambda placement: placement["a"][0] > placement["b"][0],
    )
    assert result.legal == 1
    assert dict(result.best_placements[0])["a"] == (1, 0)
    assert result.best_score[1] == 1


def test_rename_and_declaration_order_do_not_change_oracle_metric() -> None:
    slots = ((0, 0), (1, 0), (2, 0))
    first = exhaustive_tiny_composition(
        (TinyNode("i", "input"), TinyNode("s"), TinyNode("o", "output")),
        (TinyEdge("i", "s"), TinyEdge("s", "o")),
        slots,
    )
    renamed = exhaustive_tiny_composition(
        (TinyNode("z", "output"), TinyNode("b", "input"), TinyNode("a")),
        (TinyEdge("b", "a"), TinyEdge("a", "z")),
        tuple(reversed(slots)),
    )
    assert first.best_score == renamed.best_score
    assert first.pareto_scores == renamed.pareto_scores


def test_exhaustive_budget_and_invalid_inventory_are_rejected() -> None:
    with pytest.raises(ValueError, match="budget"):
        exhaustive_tiny_composition(
            tuple(TinyNode(str(i)) for i in range(6)),
            (),
            tuple((i, 0) for i in range(10)),
        )
    with pytest.raises(ValueError, match="duplicate"):
        exhaustive_tiny_composition((TinyNode("x"), TinyNode("x")), (), ((0, 0), (1, 0)))
    with pytest.raises(ValueError, match="unknown"):
        tiny_composition_metrics(
            (TinyNode("x"),),
            (TinyEdge("x", "missing"),),
            {"x": (0, 0)},
        )
