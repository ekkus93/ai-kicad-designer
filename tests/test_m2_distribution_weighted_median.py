"""Interior rail trunk follows the gateway-row median, not the bounding midpoint."""

from itertools import permutations

from ai_kicad.m2a import PITCH
from ai_kicad.m2_geometry import Gateway
from ai_kicad.m2_route import _distribution_initial_trees


def test_skewed_gateway_rows_choose_shorter_interior_trunk() -> None:
    gateways = tuple(
        Gateway(
            str(i),
            "RAIL",
            ((str(i), "1"),),
            str(i),
            (i * 10 * PITCH, (6 if i == 3 else 0) * PITCH),
            "up",
            (
                (i * 10 * PITCH, (6 if i == 3 else 0) * PITCH),
                (i * 10 * PITCH, (5 if i == 3 else -1) * PITCH),
            ),
            frozenset({"up"}),
            (),
        )
        for i in range(4)
    )
    bounds = (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH)

    def plans(ordered):
        return _distribution_initial_trees(
            "RAIL",
            "tree.RAIL",
            gateways[0],
            ordered,
            (),
            (),
            bounds,
        )

    for ordered in permutations(gateways[1:]):
        candidates = plans((gateways[0], *ordered))
        assert len(candidates) <= 8
        median = next(
            parts for name, parts, *_ in candidates if name == "horizontal_median"
        )
        trunk = next(
            part
            for part in median
            if part.provenance == ("horizontal_median", "trunk")
        )
        assert trunk.start[1] == trunk.end[1] == -PITCH
