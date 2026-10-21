"""Passive connector flow must respect typed net and edge semantics."""

from types import SimpleNamespace

from ai_kicad.m2_semantics import PresentationNet, SemanticEdge, SemanticPlan
from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def _block(name: str, kind: str, role: str):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=(SimpleNamespace(net="n", role=role),),
    )


def _plan(blocks, edges=(), presentation_nets=()):
    return SemanticPlan(
        blocks=blocks,
        edges=edges,
        owners={},
        signal_order=(),
        presentation_nets=presentation_nets,
    )


def test_unique_passive_connector_input_and_output() -> None:
    a = _block("a", "interface", "passive")
    for role, expected in (
        ("signal_in", ("a", "b", "n")),
        ("signal_out", ("b", "a", "n")),
    ):
        b = _block("b", "active", role)
        assert inferred_passive_interface_signal_relations(_plan((b, a))) == (expected,)


def test_distributive_net_does_not_create_primary_flow() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_in")
    for role in ("signal", "distributive"):
        net = PresentationNet("n", (), ("a", "b"), role, False)
        expected = (("a", "b", "n"),) if role == "signal" else ()
        assert (
            inferred_passive_interface_signal_relations(_plan((a, b), presentation_nets=(net,)))
            == expected
        )


def test_feedback_edge_does_not_erase_explicit_signal_output_direction() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_out")
    edge = SemanticEdge("feedback", "b", "a", "n", ("authored",))
    assert inferred_passive_interface_signal_relations(_plan((a, b), (edge,))) == (("b", "a", "n"),)


def test_feedback_relation_alone_does_not_infer_interface_direction() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "passive")
    edge = SemanticEdge("feedback", "b", "a", "n", ("authored",))
    assert inferred_passive_interface_signal_relations(_plan((a, b), (edge,))) == ()
