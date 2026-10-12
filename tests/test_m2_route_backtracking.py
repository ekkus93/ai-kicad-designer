"""Metamorphic controls for production conductor backtracking ranking."""

from types import SimpleNamespace

import pytest

from ai_kicad.m2_composition_candidate_rank import route_backtracking_penalty


def _score(segments):
    return route_backtracking_penalty((SimpleNamespace(geometry_signature=segments),))


def test_backtracking_is_invariant_to_segment_splitting_and_serialization():
    original = (
        ((0, 0), (0, 10)),
        ((0, 10), (10, 10)),
        ((10, 10), (10, 0)),
    )
    split = (
        ((0, 0), (0, 4)),
        ((0, 4), (0, 10)),
        ((0, 10), (5, 10)),
        ((5, 10), (10, 10)),
        ((10, 10), (10, 4)),
        ((10, 4), (10, 0)),
    )
    assert _score(original) == 1
    assert _score(split) == 1
    assert _score(tuple((end, start) for start, end in reversed(split))) == 1
    assert _score(original + original) == 1
    assert _score(split + (((5, 10), (5, 15)),)) == 1


def test_backtracking_does_not_penalize_nonreversing_routes():
    assert _score((((0, 0), (0, 10)), ((0, 10), (10, 10)), ((10, 10), (10, 20)))) == 0
    assert _score(()) == 0


def test_backtracking_rejects_nonorthogonal_canonical_geometry():
    with pytest.raises(ValueError, match="orthogonal"):
        _score((((0, 0), (5, 5)),))
