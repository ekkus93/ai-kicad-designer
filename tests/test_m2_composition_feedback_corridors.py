"""Authored generic controls for conservative feedback obstacle ranking."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import (
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
)


def _block(name: str, kind: str = "stage"):
    return SimpleNamespace(id=name, kind=kind, ports=())


def _edge(kind: str, source: str, target: str, net: str = "feedback"):
    return SimpleNamespace(kind=kind, source=source, target=target, net=net)


def _plan(*blocks, edges=()):
    return SimpleNamespace(blocks=blocks, edges=edges, precedence=())


def _packing(*entries):
    fragments = tuple(
        SimpleNamespace(
            fragment=SimpleNamespace(block=block, positions={}),
            content_envelope=(x, y, x + PITCH, y + PITCH),
            envelope=(x, y, x + PITCH, y + PITCH),
            delta=(0, 0),
        )
        for block, x, y in entries
    )
    return SimpleNamespace(fragments=fragments)


def test_straight_feedback_corridor_prefers_no_unrelated_intrusion() -> None:
    source, owner, intruder = (_block(name) for name in ("source", "owner", "intruder"))
    plan = _plan(source, owner, intruder, edges=(_edge("feedback", "source", "owner"),))
    crossing = _packing(
        (source, 0, 5 * PITCH),
        (owner, 10 * PITCH, 5 * PITCH),
        (intruder, 5 * PITCH, 5 * PITCH),
    )
    clear = _packing(
        (source, 0, 5 * PITCH),
        (owner, 10 * PITCH, 5 * PITCH),
        (intruder, 5 * PITCH, 9 * PITCH),
    )
    blocked = semantic_composition_penalty_breakdown(plan, crossing)
    unblocked = semantic_composition_penalty_breakdown(plan, clear)
    assert blocked.feedback_intrusion == 1
    assert unblocked.feedback_intrusion == 0
    assert blocked.feedback_distance == unblocked.feedback_distance
    assert blocked.as_dict()["feedback_intrusion"] == 1
    # The vector must remain aligned with the named metric mapping as new
    # semantic tie-breakers are appended after feedback intrusion.
    assert blocked.vector() == tuple(blocked.as_dict().values())


def test_one_clear_shortest_elbow_does_not_claim_an_intrusion() -> None:
    source, owner, intruder = (_block(name) for name in ("source", "owner", "intruder"))
    plan = _plan(source, owner, intruder, edges=(_edge("feedback", "source", "owner"),))
    packing = _packing(
        (source, 0, 0),
        (owner, 10 * PITCH, 10 * PITCH),
        (intruder, 5 * PITCH, 0),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).feedback_intrusion == 0


def test_both_shortest_feedback_elbows_blocked_are_penalized() -> None:
    source, owner, upper, lower = (_block(name) for name in ("source", "owner", "upper", "lower"))
    plan = _plan(source, owner, upper, lower, edges=(_edge("feedback", "source", "owner"),))
    packing = _packing(
        (source, 0, 0),
        (owner, 10 * PITCH, 10 * PITCH),
        (upper, 5 * PITCH, 0),
        (lower, 0, 5 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).feedback_intrusion == 1


def test_semantically_owned_feedback_support_is_not_an_unrelated_obstacle() -> None:
    source, owner, support = (_block(name) for name in ("source", "owner", "support"))
    plan = _plan(
        source,
        owner,
        support,
        edges=(
            _edge("feedback", "source", "owner"),
            _edge("support", "support", "owner", "bias"),
        ),
    )
    packing = _packing(
        (source, 0, 5 * PITCH),
        (owner, 10 * PITCH, 5 * PITCH),
        (support, 5 * PITCH, 5 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).feedback_intrusion == 0


def test_permuted_and_renamed_equivalents_deduplicate_feedback_edges() -> None:
    source, owner, intruder = (_block(name) for name in ("source", "owner", "intruder"))
    placement = _packing(
        (source, 0, 0),
        (owner, 10 * PITCH, 0),
        (intruder, 5 * PITCH, 0),
    )
    canonical = _plan(source, owner, intruder, edges=(_edge("feedback", "source", "owner"),))
    permuted = _plan(
        intruder,
        owner,
        source,
        edges=(
            _edge("feedback", "source", "owner"),
            _edge("feedback", "source", "owner"),
        ),
    )
    renamed_net = _plan(
        source,
        owner,
        intruder,
        edges=(_edge("feedback", "source", "owner", "renamed"),),
    )
    observed = (
        semantic_composition_penalty_breakdown(plan, placement).feedback_intrusion
        for plan in (canonical, permuted, renamed_net)
    )
    assert tuple(observed) == (1, 1, 1)


def test_feedback_intrusion_cannot_reverse_semantic_precedence() -> None:
    source, sink, intruder = (_block(name) for name in ("source", "sink", "intruder"))
    plan = _plan(
        source,
        sink,
        intruder,
        edges=(
            _edge("signal", "source", "sink", "forward"),
            _edge("feedback", "sink", "source"),
        ),
    )
    ordered = _packing(
        (source, 0, 0),
        (sink, 10 * PITCH, 0),
        (intruder, 5 * PITCH, 0),
    )
    reversed_placement = _packing(
        (source, 10 * PITCH, 0),
        (sink, 0, 0),
        (intruder, 5 * PITCH, 5 * PITCH),
    )
    assert composition_candidate_key(plan, ordered, (100, 50, 0, 0, 0, 0)) < (
        composition_candidate_key(plan, reversed_placement, (10, 5, 0, 0, 0, 0))
    )


def test_feedback_intrusion_is_direction_invariant() -> None:
    source, owner, intruder = (_block(name) for name in ("source", "owner", "intruder"))
    placed = _packing(
        (source, 0, 5 * PITCH),
        (owner, 10 * PITCH, 5 * PITCH),
        (intruder, 5 * PITCH, 5 * PITCH),
    )
    forward = _plan(source, owner, intruder, edges=(_edge("feedback", "source", "owner"),))
    reversed_plan = _plan(owner, source, intruder, edges=(_edge("feedback", "owner", "source"),))
    assert semantic_composition_penalty_breakdown(forward, placed).feedback_intrusion == 1
    assert semantic_composition_penalty_breakdown(reversed_plan, placed).feedback_intrusion == 1
