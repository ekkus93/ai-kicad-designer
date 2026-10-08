from types import SimpleNamespace

from ai_kicad.m2_pack import _signal_chains


def test_passive_series_chain_follows_directed_electrical_order() -> None:
    blocks = tuple(
        SimpleNamespace(id=block_id, kind="series") for block_id in ("third", "first", "second")
    )
    edges = (
        SimpleNamespace(kind="signal", source="first", target="second"),
        SimpleNamespace(kind="signal", source="second", target="third"),
    )
    plan = SimpleNamespace(blocks=blocks, edges=edges, precedence=())

    assert _signal_chains(plan) == (("first", "second", "third"),)
