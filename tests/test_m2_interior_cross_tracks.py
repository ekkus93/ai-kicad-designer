"""Generic bounded interior cross-track alternatives for legal routed escapes."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_route import _direct_paths


def test_interior_cross_tracks_provide_both_orthogonal_escape_orders() -> None:
    first = (0, 0)
    second = (12 * PITCH, 12 * PITCH)
    x = 4 * PITCH
    y = 8 * PITCH
    paths = tuple(_direct_paths(first, second, (x,), (y,)))
    assert (first, (x, 0), (x, y), (second[0], y), second) in paths
    assert (first, (0, y), (x, y), (x, second[1]), second) in paths


def test_interior_cross_track_enumeration_is_bounded_and_order_invariant() -> None:
    first = (0, 0)
    second = (20 * PITCH, 20 * PITCH)
    tracks_x = tuple(index * PITCH for index in range(1, 13))
    tracks_y = tuple(index * PITCH for index in range(1, 13))
    forward = tuple(_direct_paths(first, second, tracks_x, tracks_y))
    reversed_order = tuple(_direct_paths(first, second, tracks_x[::-1], tracks_y[::-1]))
    # Cross-track enumeration adds at most 2 * 4 * 4 bounded paths.
    # The perimeter family is unaffected by the obstacle-derived track count.
    assert len(forward) == 3 + len(tracks_x) + len(tracks_y) + 32 + 256
    assert forward == reversed_order


def test_cross_tracks_do_not_create_zero_length_corner_legs() -> None:
    first = (0, 0)
    second = (12 * PITCH, 12 * PITCH)
    paths = tuple(_direct_paths(first, second, (0, 4 * PITCH), (12 * PITCH, 8 * PITCH)))
    assert (first, (4 * PITCH, 0), (4 * PITCH, 8 * PITCH), (12 * PITCH, 8 * PITCH), second) in paths
    assert (first, (0, 8 * PITCH), (4 * PITCH, 8 * PITCH), (4 * PITCH, 12 * PITCH), second) in paths
