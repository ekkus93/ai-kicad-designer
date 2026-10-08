"""Small generic frontier-search contracts for the bounded M2 composition placer."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    LEFT,
    Packing,
    _interface_frontier_candidates,
    _place,
)
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _block(block_id: str, kind: str, role: str | None = None) -> BlockPlan:
    ports = (
        (SemanticPort(f"{block_id}.port", block_id, f"{block_id}.net", role, ()),)
        if role is not None
        else ()
    )
    return BlockPlan(block_id, kind, (), frozenset(), ports)


def _fragment(block: BlockPlan) -> FragmentVariant:
    return FragmentVariant(
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


def _layout():
    input_block = _block("input", "interface", "signal_in")
    stage = _block("stage", "amplifier")
    output_block = _block("output", "interface", "signal_out")
    plan = SemanticPlan(
        (input_block, stage, output_block),
        (
            SemanticEdge("signal", "input", "stage", "net_a", ()),
            SemanticEdge("signal", "stage", "output", "net_b", ()),
        ),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(input_block), LEFT + 100 * PITCH, 60 * PITCH),
            _place(_fragment(stage), LEFT + 60 * PITCH, 48 * PITCH),
            _place(_fragment(output_block), LEFT + 30 * PITCH, 65 * PITCH),
        ),
        (),
    )
    return plan, baseline


def test_frontier_alternatives_place_interfaces_next_to_signal_owner() -> None:
    plan, baseline = _layout()
    alternatives = _interface_frontier_candidates(plan, baseline)
    assert len(alternatives) == 2
    for candidate, role in zip(alternatives, ("input", "output"), strict=True):
        by_id = {item.fragment.block.id: item for item in candidate.fragments}
        interface = by_id[role].envelope
        owner = by_id["stage"].envelope
        assert candidate.attempts[-1] == f"interface-frontier-{role}"
        assert abs((interface[1] + interface[3]) - (owner[1] + owner[3])) <= PITCH
        if role == "input":
            assert interface[2] < owner[0]
        else:
            assert interface[0] > owner[2]


def test_frontier_search_is_independent_of_semantic_declaration_order() -> None:
    plan, baseline = _layout()
    reversed_plan = SemanticPlan(
        tuple(reversed(plan.blocks)), tuple(reversed(plan.edges)), {}, ()
    )
    candidates = _interface_frontier_candidates(plan, baseline)
    reordered = _interface_frontier_candidates(reversed_plan, baseline)
    assert candidates == reordered


def test_bidirectional_interface_is_not_forced_to_a_signal_frontier() -> None:
    plan, baseline = _layout()
    bidirectional = BlockPlan(
        "input",
        "interface",
        (),
        frozenset(),
        (
            SemanticPort("in", "input", "signal", "signal_in", ()),
            SemanticPort("out", "input", "signal", "signal_out", ()),
        ),
    )
    new_blocks = (bidirectional, *plan.blocks[1:])
    new_plan = SemanticPlan(new_blocks, plan.edges, {}, ())
    options = _interface_frontier_candidates(new_plan, baseline)
    assert len(options) == 1
    assert options[0].attempts[-1] == "interface-frontier-output"
