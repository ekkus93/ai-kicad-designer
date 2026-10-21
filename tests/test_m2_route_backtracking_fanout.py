"""Generic route-backtracking metric must not overcharge multiway fanout."""

from types import SimpleNamespace

from ai_kicad.m2_composition_candidate_rank import (
    route_backtracking_penalty,
    route_branch_arm_spread,
)
from ai_kicad.m2a import PITCH


def _route(*segments):
    return SimpleNamespace(geometry_signature=segments)


def test_multiway_fanout_counts_distinct_neighbor_return_intervals() -> None:
    """A third adjacent branch adds one interval, not all earlier pairs."""
    trunk = ((0, 0), (4 * PITCH, 0))
    left = ((0, -PITCH), (0, 0))
    center = ((2 * PITCH, -PITCH), (2 * PITCH, 0))
    right = ((4 * PITCH, -PITCH), (4 * PITCH, 0))
    two = route_backtracking_penalty((_route(trunk, left, right),))
    three = route_backtracking_penalty((_route(trunk, left, center, right),))
    assert two == 4
    assert three == 4  # the same total trunk width, not 4 + 2 + 2
    assert route_backtracking_penalty((_route(trunk, left, center),)) == 2


def test_return_interval_metric_ignores_segment_splitting_and_direction() -> None:
    trunk = ((0, 0), (6 * PITCH, 0))
    legs = (
        ((0, 0), (0, -PITCH)),
        ((2 * PITCH, 0), (2 * PITCH, -PITCH)),
        ((6 * PITCH, 0), (6 * PITCH, -PITCH)),
    )
    whole = _route(trunk, *legs)
    split = _route(
        ((6 * PITCH, 0), (2 * PITCH, 0)),
        ((2 * PITCH, 0), (0, 0)),
        *tuple((end, start) for start, end in reversed(legs)),
    )
    # Neighbor gaps are 2 and 4 grid pitches, not three pairwise gaps
    # of 2, 4, and 6.
    assert route_backtracking_penalty((whole,)) == 6
    assert route_backtracking_penalty((split,)) == 6
    assert route_backtracking_penalty((whole, whole)) == 12


def test_two_leg_u_detour_keeps_original_penalty() -> None:
    source = _route(
        ((0, 0), (0, 2 * PITCH)),
        ((0, 2 * PITCH), (3 * PITCH, 2 * PITCH)),
        ((3 * PITCH, 2 * PITCH), (3 * PITCH, 0)),
    )
    assert route_backtracking_penalty((source,)) == 3


def test_branch_arm_spread_prefers_balanced_fanout_and_ignores_segmentation() -> None:
    balanced = _route(
        ((-2 * PITCH, 0), (0, 0)),
        ((0, -2 * PITCH), (0, 0)),
        ((0, 0), (0, 2 * PITCH)),
    )
    unbalanced = _route(
        ((-4 * PITCH, 0), (0, 0)),
        ((0, -2 * PITCH), (0, 0)),
        ((0, 0), (0, 2 * PITCH)),
    )
    split_balanced = _route(
        ((-2 * PITCH, 0), (-PITCH, 0)),
        ((-PITCH, 0), (0, 0)),
        ((0, -PITCH), (0, 0)),
        ((0, -2 * PITCH), (0, -PITCH)),
        ((0, 0), (0, PITCH)),
        ((0, PITCH), (0, 2 * PITCH)),
    )
    assert route_branch_arm_spread((balanced,)) == 0
    assert route_branch_arm_spread((unbalanced,)) == 2
    assert route_branch_arm_spread((split_balanced,)) == 0
