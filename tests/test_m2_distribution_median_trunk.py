"""Controls for deterministic bounded interior distribution trunks."""

from ai_kicad.m2_geometry import Gateway
from ai_kicad.m2_route import _distribution_initial_trees
from ai_kicad.m2a import PITCH


def test_flat_distribution_has_no_redundant_median() -> None:
    gateways = tuple(
        Gateway(
            f"port.{index}",
            "RAIL",
            ((f"unit.{index}", "1"),),
            f"island.{index}",
            (index * 10 * PITCH, 0),
            "up",
            ((index * 10 * PITCH, 0), (index * 10 * PITCH, -PITCH)),
            frozenset({"up"}),
            (),
        )
        for index in range(3)
    )
    plans = _distribution_initial_trees(
        "RAIL",
        "tree.RAIL",
        gateways[0],
        gateways,
        (),
        (),
        (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH),
    )
    assert "horizontal_median" not in {name for name, *_ in plans}
    assert len(plans) <= 8
