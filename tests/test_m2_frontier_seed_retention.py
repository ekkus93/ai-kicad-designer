"""Ensure directed interface seeds survive a saturated generic placement beam."""

from types import SimpleNamespace

from ai_kicad.m2_pack import Packing, _retain_composition_seed_diversity
from ai_kicad.m2a import PITCH


def _seed(label: str, index: int) -> Packing:
    fragment = SimpleNamespace(id="generic", rule_id="generic")
    placed = SimpleNamespace(fragment=fragment, delta=(index * PITCH, 0))
    return Packing((placed,), (label,))


def test_output_frontier_survives_saturated_seed_beam() -> None:
    baseline = _seed("baseline", 0)
    labels = (
        "distribution-column:shared",
        "partial-beam",
        "repeated-peer-row",
        "repeated-peer-column",
        "branch-fanout-origin-centered",
        "branch-fanout-sibling-depth",
        "interface-frontier-input",
        "interface-frontier-output",
        "centroid-balanced-page",
        "local-signal-direct-proximity",
    )
    extras = tuple(_seed(label, index) for index, label in enumerate(labels, 1))
    retained = _retain_composition_seed_diversity((baseline,), extras)
    assert len(retained) == 8
    assert retained[0] is baseline
    assert "interface-frontier-output" in {item.attempts[-1] for item in retained}
    assert "repeated-peer-row" in {item.attempts[-1] for item in retained}
    assert "repeated-peer-column" in {item.attempts[-1] for item in retained}


def test_both_frontier_roles_survive_when_capacity_allows() -> None:
    baseline = _seed("baseline", 0)
    extras = (
        _seed("interface-frontier-input", 1),
        _seed("interface-frontier-output", 2),
        _seed("centroid-balanced-page", 3),
    )
    retained = _retain_composition_seed_diversity((baseline,), extras)
    assert len(retained) == 4
    assert {item.attempts[-1] for item in retained} == {
        "baseline",
        "interface-frontier-input",
        "interface-frontier-output",
        "centroid-balanced-page",
    }
