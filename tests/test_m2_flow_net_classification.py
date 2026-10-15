"""Bounded semantic inference checks for passive connector ports."""

from types import SimpleNamespace

from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def _block(name: str, kind: str, role: str):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=(SimpleNamespace(net="n", role=role),),
    )


def test_unique_passive_connector_input_flow() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_in")
    plan = SimpleNamespace(blocks=(a, b), edges=(), presentation_nets=())
    assert inferred_passive_interface_signal_relations(plan) == (("a", "b", "n"),)


def test_unique_passive_connector_output_flow() -> None:
    a = _block("a", "interface", "passive")
    b = _block("b", "active", "signal_out")
    plan = SimpleNamespace(blocks=(b, a), edges=(), presentation_nets=())
    assert inferred_passive_interface_signal_relations(plan) == (("b", "a", "n"),)
