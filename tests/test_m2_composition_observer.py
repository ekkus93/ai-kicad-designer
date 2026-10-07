from ai_kicad.m2_composition_observer import (
    cumulative_primary_flow_reversal_distance,
    final_signal_output_blocks,
    primary_precedence_pairs,
    reconstruct_semantic_flow,
    stage_order_witnesses,
)
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _block(block_id: str, ports: tuple[SemanticPort, ...] = ()) -> BlockPlan:
    return BlockPlan(
        id=block_id,
        kind="test",
        relationships=(),
        occurrences=frozenset(),
        ports=ports,
    )


def _signal_port(block_id: str, name: str, role: str) -> SemanticPort:
    return SemanticPort(
        id=f"{block_id}.{name}",
        fragment=block_id,
        net=f"n_{block_id}_{name}",
        role=role,
        terminals=((block_id, name),),
    )


def _plan(blocks: tuple[BlockPlan, ...], edges: tuple[SemanticEdge, ...]) -> SemanticPlan:
    return SemanticPlan(blocks=blocks, edges=edges, owners={}, signal_order=())


def test_semantic_flow_observer_reports_stage_order_witnesses() -> None:
    graph = reconstruct_semantic_flow(
        _plan(
            (_block("input"), _block("amp"), _block("out")),
            (
                SemanticEdge("signal", "input", "amp", "vin", ("authored",)),
                SemanticEdge("signal", "amp", "out", "vout", ("authored",)),
            ),
        )
    )

    assert primary_precedence_pairs(graph) == (
        ("amp", "out"),
        ("input", "amp"),
        ("input", "out"),
    )

    witnesses = stage_order_witnesses(graph, {"input": 100, "amp": 90, "out": 200})
    assert witnesses[0].source == "input"
    assert witnesses[0].target == "amp"
    assert witnesses[0].reversal_distance == 11
    assert cumulative_primary_flow_reversal_distance(witnesses) == 11


def test_semantic_flow_observer_preserves_sibling_incomparability() -> None:
    graph = reconstruct_semantic_flow(
        _plan(
            (_block("source"), _block("left_branch"), _block("right_branch")),
            (
                SemanticEdge("branch", "source", "left_branch", "fan", ("authored",)),
                SemanticEdge("branch", "source", "right_branch", "fan", ("authored",)),
            ),
        )
    )

    pairs = set(primary_precedence_pairs(graph))
    assert ("source", "left_branch") in pairs
    assert ("source", "right_branch") in pairs
    assert ("left_branch", "right_branch") not in pairs
    assert ("right_branch", "left_branch") not in pairs


def test_feedback_and_power_edges_are_not_forward_precedence() -> None:
    graph = reconstruct_semantic_flow(
        _plan(
            (_block("amp"), _block("feedback"), _block("rail")),
            (
                SemanticEdge("feedback", "amp", "feedback", "fb", ("authored",)),
                SemanticEdge("feedback", "feedback", "amp", "fb", ("authored",)),
                SemanticEdge("power", "rail", "amp", "vcc", ("authored",)),
            ),
        )
    )

    assert primary_precedence_pairs(graph) == ()
    assert stage_order_witnesses(graph, {"amp": 200, "feedback": 50, "rail": 0}) == ()
    assert {edge.role for edge in graph.edges} == {"power", "return"}


def test_observer_distinguishes_interface_port_roles_and_final_outputs() -> None:
    output_port = _signal_port("output", "pin", "signal_out")
    graph = reconstruct_semantic_flow(
        _plan(
            (
                _block("input", (_signal_port("input", "pin", "signal_in"),)),
                _block("output", (output_port,)),
            ),
            (SemanticEdge("signal", "input", "output", "sig", ("authored",)),),
        )
    )

    assert final_signal_output_blocks(graph) == ("output",)
    assert [role.composition_role for role in graph.port_roles] == ["interface", "interface"]
