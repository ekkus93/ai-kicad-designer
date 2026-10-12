"""Regression for semantic-side priority in directed frontier alternatives."""

import pytest

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import LEFT, Packing, _interface_frontier_candidates, _place
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _block(name: str, role: str | None = None) -> BlockPlan:
    ports = (
        (SemanticPort(f"{name}.port", name, f"{name}.net", role, ()),) if role is not None else ()
    )
    return BlockPlan(name, "interface" if role else "amplifier", (), frozenset(), ports)


def _placed(block: BlockPlan, x: int, y: int):
    fragment = FragmentVariant(
        f"{block.id}.variant",
        block,
        {},
        {},
        {},
        (),
        (),
        (),
        (),
        (),
        (0, 0, 8 * PITCH, 4 * PITCH),
        frozenset(),
    )
    return _place(fragment, LEFT + x * PITCH, y * PITCH)


@pytest.mark.parametrize(
    ("role", "wrong_x", "other_x"),
    [("signal_out", 30, 90), ("signal_in", 100, 25)],
)
def test_wrong_side_outweighs_already_correct_side_row_drift(
    role: str, wrong_x: int, other_x: int
) -> None:
    owner = _block("owner")
    other_owner = _block("other-owner")
    wrong = _block("wrong", role)
    other = _block("other", role)
    if role == "signal_out":
        edges = (
            SemanticEdge("signal", "owner", "wrong", "a", ()),
            SemanticEdge("signal", "other-owner", "other", "b", ()),
        )
    else:
        edges = (
            SemanticEdge("signal", "wrong", "owner", "a", ()),
            SemanticEdge("signal", "other", "other-owner", "b", ()),
        )
    blocks = (owner, other_owner, wrong, other)
    plan = SemanticPlan(blocks, edges, {}, ())
    baseline = Packing(
        (
            _placed(owner, 60, 50),
            _placed(other_owner, 60, 80),
            _placed(wrong, wrong_x, 50),
            _placed(other, other_x, 98),
        ),
        (),
    )
    result = _interface_frontier_candidates(plan, baseline)
    assert len(result) == 1
    moved = {item.fragment.block.id: item for item in result[0].fragments}
    original = {item.fragment.block.id: item for item in baseline.fragments}
    assert moved["wrong"].delta != original["wrong"].delta
    assert moved["other"].delta == original["other"].delta
    if role == "signal_out":
        assert moved["wrong"].envelope[0] > moved["owner"].envelope[2]
    else:
        assert moved["wrong"].envelope[2] < moved["owner"].envelope[0]
    reversed_plan = SemanticPlan(tuple(reversed(blocks)), tuple(reversed(edges)), {}, ())
    assert _interface_frontier_candidates(reversed_plan, baseline) == result
