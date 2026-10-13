"""Generic priorities between routed detours and soft connector row drift."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import composition_candidate_key


def _block(identifier, kind, *roles):
    return SimpleNamespace(
        id=identifier,
        kind=kind,
        ports=tuple(SimpleNamespace(role=role) for role in roles),
    )


def _packing(*entries):
    return SimpleNamespace(
        fragments=tuple(
            SimpleNamespace(
                fragment=SimpleNamespace(block=block, positions={}),
                content_envelope=(x, y, x + PITCH, y + PITCH),
                envelope=(x, y, x + PITCH, y + PITCH),
                delta=(0, 0),
            )
            for block, x, y in entries
        )
    )


def _key(plan, packing, backtracking):
    return composition_candidate_key(
        plan, packing, (100, 100, 4, 0, 0, 0), routing_backtracking=backtracking
    )


def test_less_backtracking_outranks_soft_interface_row_alignment():
    source = _block("source", "interface", "signal_in")
    owner = _block("owner", "filter", "signal_in", "signal_out")
    edge = SimpleNamespace(kind="signal", source="source", target="owner", net="path")
    plan = SimpleNamespace(blocks=(source, owner), edges=(edge,), precedence=())
    aligned = _packing((source, 0, 0), (owner, 10 * PITCH, 0))
    off_row = _packing((source, 0, 5 * PITCH), (owner, 10 * PITCH, 0))
    assert _key(plan, off_row, 2) < _key(plan, aligned, 9)
    assert _key(plan, aligned, 2) < _key(plan, off_row, 2)


def test_wrong_side_signal_flow_cannot_be_bought_with_shorter_route():
    source = _block("source", "interface", "signal_in")
    owner = _block("owner", "filter", "signal_in", "signal_out")
    edge = SimpleNamespace(kind="signal", source="source", target="owner", net="path")
    plan = SimpleNamespace(blocks=(source, owner), edges=(edge,), precedence=())
    forward = _packing((source, 0, 0), (owner, 10 * PITCH, 0))
    backwards = _packing((source, 10 * PITCH, 0), (owner, 0, 0))
    assert _key(plan, forward, 1000) < _key(plan, backwards, 0)
