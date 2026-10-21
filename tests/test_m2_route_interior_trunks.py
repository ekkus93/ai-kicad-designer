"""Verify legal orientation candidates for shared-net distribution routing."""

from types import SimpleNamespace

from ai_kicad.m2_route import _distribution_initial_trees
from ai_kicad.m2a import PITCH


def test_distribution_plan_count_is_bounded() -> None:
    gateways = tuple(
        SimpleNamespace(id=f"g{index}", point=(0, index * 4 * PITCH), escape_direction="right")
        for index in range(3)
    )
    plans = _distribution_initial_trees(
        "rail",
        "tree.rail",
        gateways[0],
        gateways,
        (),
        (),
        (-20 * PITCH, -20 * PITCH, 40 * PITCH, 40 * PITCH),
    )
    assert plans[0][0] == "producer_centered"
    assert 1 <= len(plans) <= 8
