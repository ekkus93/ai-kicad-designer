"""Source-neutral controls for bounded interior vertical distribution trunks."""

from ai_kicad.m2_geometry import Gateway, Reservation
from ai_kicad.m2_route import _distribution_initial_trees
from ai_kicad.m2a import PITCH


def _gateway(name: str, x: int, y: int) -> Gateway:
    return Gateway(
        name,
        "REF",
        ((name, "1"),),
        name,
        (x, y - PITCH),
        "down",
        ((x, y - PITCH), (x, y)),
        frozenset({"down"}),
        (),
    )


def _plans(obstacles: tuple[Reservation, ...] = ()):
    points = (
        _gateway("a", 5 * PITCH, 10 * PITCH),
        _gateway("b", 20 * PITCH, 25 * PITCH),
        _gateway("c", 35 * PITCH, 40 * PITCH),
    )
    return _distribution_initial_trees(
        "REF",
        "tree.REF",
        points[0],
        points,
        obstacles,
        (),
        (-10 * PITCH, -10 * PITCH, 60 * PITCH, 60 * PITCH),
    )


def test_legal_median_vertical_distribution_trunk_is_bounded_and_seed_connected() -> None:
    choices = _plans()
    assert 1 <= len(choices) <= 8
    strategies = {strategy for strategy, *_ in choices}
    assert "producer_centered" in strategies
    median = next(item for item in choices if item[0] == "vertical_median")
    _strategy, conductors, trunk, _expansions = median
    assert trunk == ((20 * PITCH, 11 * PITCH), (20 * PITCH, 41 * PITCH))
    assert conductors[0].start == (5 * PITCH, 10 * PITCH)
    assert any(segment.end == trunk[0] for segment in conductors)


def test_obstructed_median_searches_adjacent_legal_vertical_lane() -> None:
    blocking = Reservation(
        "median-obstruction",
        "exclusive",
        "unrelated",
        "body",
        (19 * PITCH, 21 * PITCH, 21 * PITCH, 23 * PITCH),
    )
    choices = _plans((blocking,))
    assert len(choices) <= 8
    clear = next(item for item in choices if item[0] == "vertical_clear_lane")
    assert clear[2] is not None
    assert clear[2][0][0] != 20 * PITCH
    assert clear[2][0][0] == clear[2][1][0]
