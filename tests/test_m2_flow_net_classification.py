"""Passive-interface inference respects distributive and feedback semantics."""

from types import SimpleNamespace

from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def _block(name: str, kind: str, role: str):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=(SimpleNamespace(net="n", role=role),),
    )


def test_distribution_is_not_forward_flow() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_in")
    plan = SimpleNamespace(
        blocks=(a, b),
        edges=(),
        presentation_nets=(SimpleNamespace(id="n", role="distributive"),),
    )
    assert inferred_passive_interface_signal_relations(plan) == ()
    plan.presentation_nets = (SimpleNamespace(id="n", role="signal"),)
    assert inferred_passive_interface_signal_relations(plan) == (("a", "b", "n"),)


def test_feedback_relation_is_not_forward_flow() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_out")
    edge = SimpleNamespace(net="n", kind="feedback")
    plan = SimpleNamespace(blocks=(a, b), edges=(edge,), presentation_nets=())
    assert inferred_passive_interface_signal_relations(plan) == ()
