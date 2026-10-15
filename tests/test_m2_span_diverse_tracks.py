"""Source-neutral bounded track sampling across dense routing obstacles."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_route import MAX_TRACKS_PER_SIDE, _bounded_tracks, _direct_paths


def test_dense_interior_tracks_keep_both_extremes_and_middle() -> None:
    values = {index * PITCH for index in range(1, 25)}
    tracks = _bounded_tracks(values, 0, 25 * PITCH)
    assert len(tracks) == MAX_TRACKS_PER_SIDE
    assert tracks[0] == PITCH
    assert tracks[-1] == 24 * PITCH
    assert tracks == tuple(sorted(tracks))
    assert any(9 * PITCH <= track <= 16 * PITCH for track in tracks)
    assert tracks == _bounded_tracks(set(reversed(sorted(values))), 25 * PITCH, 0)


def test_sparse_and_outside_tracks_keep_existing_near_first_priority() -> None:
    values = {-index * PITCH for index in range(1, 13)} | {
        index * PITCH for index in range(1, 5)
    } | {index * PITCH for index in range(11, 23)}
    tracks = _bounded_tracks(values, 0, 10 * PITCH)
    assert tracks[:MAX_TRACKS_PER_SIDE] == tuple(
        -index * PITCH for index in range(1, 9)
    )
    assert tracks[MAX_TRACKS_PER_SIDE : MAX_TRACKS_PER_SIDE + 4] == tuple(
        index * PITCH for index in range(1, 5)
    )
    assert tracks[-MAX_TRACKS_PER_SIDE:] == tuple(
        index * PITCH for index in range(11, 19)
    )


def test_span_diverse_tracks_expose_far_side_to_both_direct_escape_orders() -> None:
    first = (0, 0)
    second = (25 * PITCH, 25 * PITCH)
    values = {index * PITCH for index in range(1, 25)}
    xs = _bounded_tracks(values, first[0], second[0])
    ys = _bounded_tracks(values, first[1], second[1])
    paths = tuple(_direct_paths(first, second, xs, ys))
    far = 24 * PITCH
    assert (first, (far, first[1]), (far, second[1]), second) in paths
    assert (first, (first[0], far), (second[0], far), second) in paths
    assert len(xs) <= MAX_TRACKS_PER_SIDE
    assert len(ys) <= MAX_TRACKS_PER_SIDE


def test_dense_sampling_works_for_negative_grid_coordinates() -> None:
    values = {index * PITCH for index in range(-24, 0)}
    tracks = _bounded_tracks(values, -25 * PITCH, 0)
    assert tracks[0] == -24 * PITCH
    assert tracks[-1] == -PITCH
    assert len(tracks) == MAX_TRACKS_PER_SIDE
