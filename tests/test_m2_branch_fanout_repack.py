"""Bounded semantic fanout packing alternatives and retention controls."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    LEFT,
    TOP,
    Packing,
    _branch_fanout_repack_candidates,
    _place,
    _retain_composition_seed_diversity,
)
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan


def _fragment(block_id: str) -> FragmentVariant:
    return FragmentVariant(
        id=f"fragment-{block_id}",
        block=BlockPlan(block_id, "filter", (), frozenset(), ()),
        positions={},
        angles={},
        text_positions={},
        wires=(),
        wire_nets=(),
        labels=(),
        junctions=(),
        ports=(),
        envelope=(0, 0, 2 * PITCH, 2 * PITCH),
        protected_wires=frozenset(),
    )


def _fanout(*, reverse: bool = False, net: str = "fanout"):
    source = _fragment("source")
    upper = _fragment("upper")
    lower = _fragment("lower")
    fragments = (
        _place(source, LEFT + 2 * PITCH, TOP + 5 * PITCH),
        _place(upper, LEFT + 14 * PITCH, TOP + 2 * PITCH),
        _place(lower, LEFT + 20 * PITCH, TOP + 12 * PITCH),
    )
    edges = (
        SemanticEdge("signal", "source", "upper", net, ()),
        SemanticEdge("branch", "source", "lower", net, ()),
        SemanticEdge("signal", "source", "upper", net, ()),
    )
    plan = SemanticPlan(
        blocks=tuple(item.fragment.block for item in (reversed(fragments) if reverse else fragments)),
        edges=tuple(reversed(edges)) if reverse else edges,
        owners={},
        signal_order=(),
    )
    return plan, Packing(tuple(reversed(fragments)) if reverse else fragments, ("seed",))


def _coordinates(candidate: Packing):
    return {
        item.fragment.block.id: (item.envelope[0], item.envelope[1])
        for item in candidate.fragments
    }


def test_branch_search_centers_origin_between_two_sibling_rows() -> None:
    plan, baseline = _fanout()
    alternatives = _branch_fanout_repack_candidates(plan, baseline)
    centered = next(
        item for item in alternatives if item.attempts[-1] == "branch-fanout-origin-centered"
    )
    before = _coordinates(baseline)
    after = _coordinates(centered)
    assert after["source"][1] == TOP + 7 * PITCH
    assert after["source"][0] == before["source"][0]
    assert after["upper"] == before["upper"]
    assert after["lower"] == before["lower"]


def test_branch_search_aligns_sibling_depth_without_reversing_signal() -> None:
    plan, baseline = _fanout()
    alternatives = _branch_fanout_repack_candidates(plan, baseline)
    depth = next(
        item for item in alternatives if item.attempts[-1] == "branch-fanout-sibling-depth"
    )
    before = _coordinates(baseline)
    after = _coordinates(depth)
    assert after["upper"] == before["upper"]
    assert after["lower"][0] == before["upper"][0]
    assert after["lower"][1] == before["lower"][1]
    assert after["source"] == before["source"]


def test_branch_search_is_invariant_to_declaration_order_and_net_rename() -> None:
    plan, baseline = _fanout()
    shuffled_plan, shuffled_baseline = _fanout(reverse=True, net="different")
    first = _branch_fanout_repack_candidates(plan, baseline)
    second = _branch_fanout_repack_candidates(shuffled_plan, shuffled_baseline)
    assert {item.attempts[-1]: _coordinates(item) for item in first} == {
        item.attempts[-1]: _coordinates(item) for item in second
    }


def test_branch_search_retains_both_alternatives_under_seed_cap() -> None:
    plan, baseline = _fanout()
    extras = _branch_fanout_repack_candidates(plan, baseline)
    retained = _retain_composition_seed_diversity((baseline,) * 8, extras)
    assert len(retained) <= 8
    assert {item.attempts[-1] for item in extras} <= {
        item.attempts[-1] for item in retained
    }


def test_branch_search_ignores_nonfanout_and_unrelated_nets() -> None:
    plan, baseline = _fanout()
    one_each = SemanticPlan(
        blocks=plan.blocks,
        edges=(
            SemanticEdge("signal", "source", "upper", "one", ()),
            SemanticEdge("signal", "source", "lower", "two", ()),
        ),
        owners={},
        signal_order=(),
    )
    assert _branch_fanout_repack_candidates(one_each, baseline) == ()
