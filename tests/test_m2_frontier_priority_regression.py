"""Directed interface-frontier priority must be invariant to declaration order."""

import pytest

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import LEFT, Packing, _interface_frontier_candidates, _place
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _block(name: str, role: str | None = None) -> BlockPlan:
    ports = ((SemanticPort(f"{name}.port", name, "net", role, ()),) if role else ())
    return BlockPlan(name, "interface" if role else "amplifier", (), frozenset(), ports)


def _at(block: BlockPlan, x: int, y: int):
    fragment = FragmentVariant(
        block.id, block, {}, {}, {}, (), (), (), (), (),
        (0, 0, 8 * PITCH, 4 * PITCH), frozenset(),
    )
    return _place(fragment, LEFT + x * PITCH, y * PITCH)


@pytest.mark.parametrize(
    ("role", "bad_x", "good_x"),
    (("signal_in", 100, 25), ("signal_out", 30, 90)),
)
def test_wrong_side_is_repaired_before_distant_row(
    role: str, bad_x: int, good_x: int
) -> None:
    producer = _block("producer")
    peer = _block("peer")
    bad = _block("bad", role)
    good = _block("good", role)
    edges = (
        (SemanticEdge("signal", "bad", "producer", "a", ()),
         SemanticEdge("signal", "good", "peer", "b", ()))
        if role == "signal_in"
        else (SemanticEdge("signal", "producer", "bad", "a", ()),
              SemanticEdge("signal", "peer", "good", "b", ()))
    )
    blocks = (producer, peer, bad, good)
    plan = SemanticPlan(blocks, edges, {}, ())
    baseline = Packing(
        (_at(producer, 60, 50), _at(peer, 60, 80),
         _at(bad, bad_x, 50), _at(good, good_x, 98)),
        (),
    )
    candidates = _interface_frontier_candidates(plan, baseline)
    assert len(candidates) == 1
    changed = {item.fragment.block.id: item for item in candidates[0].fragments}
    initial = {item.fragment.block.id: item for item in baseline.fragments}
    assert changed["bad"].delta != initial["bad"].delta
    assert changed["good"].delta == initial["good"].delta
    assert _interface_frontier_candidates(
        SemanticPlan(tuple(reversed(blocks)), tuple(reversed(edges)), {}, ()),
        baseline,
    ) == candidates
