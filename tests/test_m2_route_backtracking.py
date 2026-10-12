"""Metamorphic controls for production conductor backtracking ranking."""

from types import SimpleNamespace

import pytest

from ai_kicad.m2a import PITCH
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


def test_backtracking_counts_return_spanning_a_mid_run_branch():
    tree = (
        ((0, 0), (0, 10)),
        ((0, 10), (20, 10)),
        ((10, 0), (10, 10)),
    )
    assert _score(tree) == 1
    assert _score(tuple(reversed(tree))) == 1


def test_backtracking_does_not_count_opposite_side_branches():
    positive_branch = (
        ((0, 0), (0, 10)),
        ((0, 10), (20, 10)),
        ((10, 10), (10, 20)),
    )
    assert _score(positive_branch) == 0


def test_backtracking_rejects_nonorthogonal_canonical_geometry():
    with pytest.raises(ValueError, match="orthogonal"):
        _score((((0, 0), (5, 5)),))


def test_backtracking_prefers_shorter_same_side_return_spans():
    def detour(width):
        return (
            ((0, 0), (0, PITCH)),
            ((0, PITCH), (width, PITCH)),
            ((width, PITCH), (width, 0)),
        )

    assert _score(detour(2 * PITCH)) == 2
    assert _score(detour(8 * PITCH)) == 8
    assert _score(tuple(reversed(detour(8 * PITCH)))) == 8


def test_backtracking_span_respects_axis_rotation_translation_and_mirror():
    """A generic return-span score must not depend on sheet orientation."""
    width = 7 * PITCH
    route = (
        ((0, 0), (0, PITCH)),
        ((0, PITCH), (width, PITCH)),
        ((width, PITCH), (width, 0)),
    )

    def rotate(point):
        return point[1] + 13 * PITCH, -point[0] + 19 * PITCH

    def mirror(point):
        return -point[0] + 23 * PITCH, point[1] + 11 * PITCH

    assert _score(route) == 7
    assert _score(tuple((rotate(a), rotate(b)) for a, b in route)) == 7
    assert _score(tuple((mirror(a), mirror(b)) for a, b in route)) == 7


def test_backtracking_span_ignores_split_junction_and_duplicate_strokes():
    """A junction or serialization split cannot hide a wide return detour."""
    width = 7 * PITCH
    original = (
        ((0, 0), (0, PITCH)),
        ((0, PITCH), (width, PITCH)),
        ((width, PITCH), (width, 0)),
    )
    split_with_branch = (
        original[0],
        ((0, PITCH), (3 * PITCH, PITCH)),
        ((3 * PITCH, PITCH), (width, PITCH)),
        original[2],
        ((3 * PITCH, PITCH), (3 * PITCH, 2 * PITCH)),
        original[0],
    )
    assert _score(original) == 7
    assert _score(split_with_branch) == 7
    assert _score(tuple(reversed(split_with_branch))) == 7
