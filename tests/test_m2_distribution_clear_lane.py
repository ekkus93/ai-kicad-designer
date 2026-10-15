"""Blocked median trunks should retain bounded deterministic clear-lane alternatives."""

from itertools import permutations

from ai_kicad.m2a import PITCH
from ai_kicad.m2_geometry import Gateway, Reservation
from ai_kicad.m2_route import _distribution_initial_trees


def test_blocked_median_selects_adjacent_legal_interior_lane() -> None:
    gateways = tuple(
        Gateway(
            str(index),
            "RAIL",
            ((str(index), "1"),),
            str(index),
            (10 * index * PITCH, (6 if index == 1 else 0) * PITCH),
            "up",
            (
                (10 * index * PITCH, (6 if index == 1 else 0) * PITCH),
                (10 * index * PITCH, ((6 if index == 1 else 0) - 1) * PITCH),
            ),
            frozenset({"up"}),
            (),
        )
        for index in range(3)
    )
    bounds = (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH)
    blocker = Reservation(
        "unrelated.body",
        "exclusive",
        "unrelated",
        "body",
        (9 * PITCH, -3 * PITCH // 2, 11 * PITCH, -PITCH // 2),
    )
    for ordered in permutations(gateways):
        plans = _distribution_initial_trees(
            "RAIL", "tree.RAIL", gateways[0], ordered, (blocker,), (), bounds
        )
        assert len(plans) <= 8
        assert "horizontal_median" not in {name for name, *_ in plans}
        alternative = [plan for plan in plans if plan[0] == "horizontal_clear_lane"]
        assert len(alternative) == 2
        trunks = [
            next(part for part in plan[1] if part.provenance == ("horizontal_clear_lane", "trunk"))
            for plan in alternative
        ]
        assert [(trunk.start[1], trunk.end[1]) for trunk in trunks] == [
            (0, 0),
            (PITCH, PITCH),
        ]


def test_vertical_interiors_include_two_distinct_legal_corridors() -> None:
    gateways = tuple(
        Gateway(
            str(index),
            "RAIL",
            ((str(index), "1"),),
            str(index),
            (6 * index * PITCH, 10 * index * PITCH),
            "up",
            (
                (6 * index * PITCH, 10 * index * PITCH),
                (6 * index * PITCH, (10 * index - 1) * PITCH),
            ),
            frozenset({"up"}),
            (),
        )
        for index in range(3)
    )
    bounds = (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH)
    for ordered in permutations(gateways):
        plans = _distribution_initial_trees(
            "RAIL", "tree.RAIL", gateways[0], ordered, (), (), bounds
        )
        assert len(plans) <= 8
        vertical = [plan for plan in plans if plan[0] in {"vertical_median", "vertical_clear_lane"}]
        assert len(vertical) == 2
        assert [plan[0] for plan in vertical] == ["vertical_median", "vertical_clear_lane"]
        trunks = [
            next(part for part in plan[1] if part.provenance == (plan[0], "trunk"))
            for plan in vertical
        ]
        assert [(part.start[0], part.end[0]) for part in trunks] == [
            (6 * PITCH, 6 * PITCH),
            (5 * PITCH, 5 * PITCH),
        ]
