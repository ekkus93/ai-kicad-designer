"""Conservative passive-interface inference for shared passive nets."""

from types import SimpleNamespace

from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def _block(name, kind, role, net="shared"):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=(SimpleNamespace(role=role, net=net),),
    )


def _infer(blocks):
    return inferred_passive_interface_signal_relations(SimpleNamespace(blocks=blocks))


def test_unique_signal_input_is_inferred_without_other_passive_owners():
    interface = _block("connector", "interface", "passive")
    sink = _block("stage", "filter", "signal_in")
    assert _infer((interface, sink)) == (("connector", "stage", "shared"),)


def test_shared_passive_net_does_not_claim_unique_interface_owner():
    interface = _block("connector", "interface", "passive")
    source = _block("source", "filter", "signal_out")
    load = _block("load", "resistor", "passive")
    assert _infer((interface, source, load)) == ()
    assert _infer((load, source, interface)) == ()


def test_unrelated_passive_net_does_not_block_unique_direction():
    interface = _block("connector", "interface", "passive")
    source = _block("source", "filter", "signal_out")
    load = _block("load", "resistor", "passive", net="unrelated")
    assert _infer((interface, source, load)) == (("source", "connector", "shared"),)
