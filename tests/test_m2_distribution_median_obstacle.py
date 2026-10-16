"""Interior shared-rail trunk must not cross unrelated fragment bodies."""

from ai_kicad.m2_geometry import Gateway, Reservation
from ai_kicad.m2_route import _distribution_initial_trees
from ai_kicad.m2a import PITCH


def test_median_trunk_respects_unrelated_obstacles() -> None:
    gateways = tuple(
        Gateway(
            str(i),
            "RAIL",
            ((str(i), "1"),),
            str(i),
            (10 * i * PITCH, (6 if i == 1 else 0) * PITCH),
            "up",
            (
                (10 * i * PITCH, (6 if i == 1 else 0) * PITCH),
                (10 * i * PITCH, ((6 if i == 1 else 0) - 1) * PITCH),
            ),
            frozenset({"up"}),
            (),
        )
        for i in range(3)
    )
    bounds = (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH)
    blocker = Reservation(
        "body",
        "exclusive",
        "unrelated",
        "body",
        (9 * PITCH, -2 * PITCH, 11 * PITCH, 2 * PITCH),
    )
    clear = _distribution_initial_trees(
        "RAIL",
        "tree.RAIL",
        gateways[0],
        gateways,
        (),
        (),
        bounds,
    )
    blocked = _distribution_initial_trees(
        "RAIL",
        "tree.RAIL",
        gateways[0],
        gateways,
        (blocker,),
        (),
        bounds,
    )
    assert "horizontal_median" in {name for name, *_ in clear}
    assert "horizontal_median" not in {name for name, *_ in blocked}
    assert "producer_centered" in {name for name, *_ in blocked}
    assert len(blocked) <= 8
