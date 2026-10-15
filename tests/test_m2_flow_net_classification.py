from types import SimpleNamespace

from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def test_distribution_is_not_forward_flow() -> None:
    a = SimpleNamespace(id="a", kind="interface", ports=(SimpleNamespace(net="n", role="passive"),))
    b = SimpleNamespace(id="b", kind="active", ports=(SimpleNamespace(net="n", role="signal_in"),))
    p = SimpleNamespace(blocks=(a, b), edges=(), presentation_nets=(SimpleNamespace(id="n", role="distributive"),))
    assert inferred_passive_interface_signal_relations(p) == ()
