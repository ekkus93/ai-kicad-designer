"""Independent semantic-flow tests for terminal-backed signal sources."""

from ai_kicad.m2_composition_observer import (
    primary_precedence_pairs,
    reconstruct_semantic_flow,
    stage_order_witnesses,
)
from ai_kicad.m2_semantics import (
    BlockPlan,
    SemanticEdge,
    SemanticPlan,
    SemanticPort,
    SignalPrecedence,
)


def _block(block_id, ports=()):
    return BlockPlan(block_id, "interface", (), frozenset(), tuple(ports))


def _external_source_plan(*, direct_edge=False):
    connector = SemanticPort("connector.pin", "connector", "vin", "passive", (("J1", "1"),))
    input_port = SemanticPort("amp.input", "amp", "vin", "signal_in", (("U1", "3"),))
    precedence = SignalPrecedence(
        "external-source",
        "connector",
        "amp",
        ("J1", "1"),
        ("U1", "3"),
        "vin",
        ("authored",),
    )
    return SemanticPlan(
        blocks=(_block("connector", (connector,)), _block("amp", (input_port,))),
        edges=(
            (SemanticEdge("signal", "connector", "amp", "vin", ("authored",)),)
            if direct_edge
            else ()
        ),
        owners={},
        signal_order=(),
        precedence=(precedence,),
    )


def test_passive_terminal_source_has_independent_primary_flow() -> None:
    graph = reconstruct_semantic_flow(_external_source_plan())
    assert primary_precedence_pairs(graph) == (("connector", "amp"),)
    assert len(graph.edges) == 1
    witnesses = stage_order_witnesses(graph, {"connector": 50, "amp": 10})
    assert len(witnesses) == 1
    assert witnesses[0].reversal_distance == 41


def test_direct_signal_edge_is_not_double_counted_with_precedence() -> None:
    graph = reconstruct_semantic_flow(_external_source_plan(direct_edge=True))
    assert len(graph.edges) == 1
    assert len(stage_order_witnesses(graph, {"connector": 50, "amp": 10})) == 1


def test_terminal_backed_signal_precedence_is_declaration_order_invariant() -> None:
    plan = _external_source_plan()
    reversed_plan = SemanticPlan(
        blocks=tuple(reversed(plan.blocks)),
        edges=tuple(reversed(plan.edges)),
        owners={},
        signal_order=(),
        precedence=tuple(reversed(plan.precedence)),
    )
    for candidate in (plan, reversed_plan):
        graph = reconstruct_semantic_flow(candidate)
        assert primary_precedence_pairs(graph) == (("connector", "amp"),)
