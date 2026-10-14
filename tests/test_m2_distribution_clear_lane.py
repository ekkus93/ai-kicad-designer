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
        (9 * PITCH, -PITCH // 2, 11 * PITCH, PITCH // 2),
    )
    for ordered in permutations(gateways):
        plans = _distribution_initial_trees(
            "RAIL", "tree.RAIL", gateways[0], ordered, (blocker,), (), bounds
        )
        assert len(plans) <= 8
        assert "horizontal_median" not in {name for name, *_ in plans}
        alternative = [plan for plan in plans if plan[0] == "horizontal_clear_lane"]
        assert len(alternative) == 1
        trunk = next(
            part
            for part in alternative[0][1]
            if part.provenance == ("horizontal_clear_lane", "trunk")
        )
        assert trunk.start[1] == trunk.end[1] == PITCH
