"""Compatibility packing must select a routeable seed or retain a deterministic fallback."""

from types import SimpleNamespace

from ai_kicad.ir import InputError
from ai_kicad import m2_pack, m2_route


def _candidates(monkeypatch):
    seeds = tuple(SimpleNamespace(fragments=(i,)) for i in range(3))
    monkeypatch.setattr(m2_pack, "pack_fragment_candidates", lambda plan, variants: seeds)
    return seeds


def test_pack_fragments_skips_unrouteable_seeds(monkeypatch):
    seeds = _candidates(monkeypatch)
    attempted = []

    def route(plan, fragments):
        attempted.append(fragments)
        if fragments[0] == 0:
            raise InputError("unrouteable")
        return ()

    monkeypatch.setattr(m2_route, "route_between_fragments", route)
    assert m2_pack.pack_fragments(None, {}) is seeds[1]
    assert attempted == [(0,), (1,)]


def test_pack_fragments_retains_first_seed_when_all_routes_fail(monkeypatch):
    seeds = _candidates(monkeypatch)
    attempted = []

    def route(plan, fragments):
        attempted.append(fragments)
        raise InputError("unrouteable")

    monkeypatch.setattr(m2_route, "route_between_fragments", route)
    assert m2_pack.pack_fragments(None, {}) is seeds[0]
    assert attempted == [(0,), (1,), (2,)]
