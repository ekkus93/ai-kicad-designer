"""Blocked aligned frontiers should search bounded neighboring legal lanes."""

import pytest

from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import LEFT, Packing, _interface_frontier_candidates, _place
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort
from ai_kicad.m2a import PITCH


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
    ("role", "wrong_x", "blocked_x"),
    (("signal_out", 30, 69), ("signal_in", 90, 51)),
)
def test_directed_frontier_uses_adjacent_lane_when_aligned_slots_blocked(
    role: str, wrong_x: int, blocked_x: int
) -> None:
    owner = _block("owner")
    unrelated = _block("unrelated")
    interface = _block("interface", role)
    edges = (
        (SemanticEdge("signal", "owner", "interface", "net", ()),)
        if role == "signal_out"
        else (SemanticEdge("signal", "interface", "owner", "net", ()),)
    )
    plan = SemanticPlan((owner, unrelated, interface), edges, {}, ())
    baseline = Packing(
        (
            _placed(owner, 60, 50),
            _placed(unrelated, blocked_x, 50),
            _placed(interface, wrong_x, 50),
        ),
        (),
    )
    options = _interface_frontier_candidates(plan, baseline)
    assert len(options) == 1
    relocated = {item.fragment.block.id: item for item in options[0].fragments}
    assert options[0].attempts[-1] == (
        "interface-frontier-output" if role == "signal_out" else "interface-frontier-input"
    )
    assert relocated["owner"].delta == _placed(owner, 60, 50).delta
    assert relocated["unrelated"].delta == _placed(unrelated, blocked_x, 50).delta
    interface_rect = relocated["interface"].envelope
    owner_rect = relocated["owner"].envelope
    unrelated_rect = relocated["unrelated"].envelope
    if role == "signal_out":
        # An output belongs on the outer frontier beyond every unrelated
        # block, where its aligned row is free; no adjacent lane is needed.
        assert interface_rect[1] == 50 * PITCH
        assert interface_rect[0] > max(owner_rect[2], unrelated_rect[2])
    else:
        # An adjacent lane must be clear of both the unrelated blocker and owner.
        assert interface_rect[1] in {45 * PITCH, 55 * PITCH}
        assert interface_rect[2] < owner_rect[0]
    shuffled = SemanticPlan(tuple(reversed(plan.blocks)), tuple(reversed(plan.edges)), {}, ())
    assert _interface_frontier_candidates(shuffled, baseline) == options
