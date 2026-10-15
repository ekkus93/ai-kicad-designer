"""The distribution tie-break must measure distance to the finite conductor."""

import pytest

from ai_kicad.m2_route import _point_to_trunk_distance


@pytest.mark.parametrize(
    ("point", "first", "second", "distance"),
    [
        ((5, 8), (0, 0), (10, 0), 8),
        ((5, 8), (10, 0), (0, 0), 8),
        ((-3, 4), (0, 0), (10, 0), 7),
        ((13, 4), (0, 0), (10, 0), 7),
        ((0, 0), (0, 0), (10, 0), 0),
        ((8, 5), (0, 0), (0, 10), 8),
        ((4, -3), (0, 0), (0, 10), 7),
        ((4, 13), (0, 0), (0, 10), 7),
        ((4, 5), (0, 10), (0, 0), 4),
        ((0, 0), (0, 0), (0, 10), 0),
    ],
)
def test_exact_manhattan_point_to_trunk_distance(point, first, second, distance) -> None:
    assert _point_to_trunk_distance(point, first, second) == distance


def test_diagonal_is_not_a_trunk() -> None:
    with pytest.raises(ValueError, match="axis-aligned"):
        _point_to_trunk_distance((5, 5), (0, 0), (10, 10))
