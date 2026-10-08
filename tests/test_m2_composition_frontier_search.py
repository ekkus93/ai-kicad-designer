"""Small generic frontier-search contracts for the bounded M2 composition placer."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    LEFT,
    Packing,
    _interface_frontier_candidates,
    _place,
    _repeated_peer_alignment_candidates,
    _support_affinity_candidates,
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
    reversed_plan = SemanticPlan(tuple(reversed(plan.blocks)), tuple(reversed(plan.edges)), {}, ())
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


def test_independent_functional_stages_have_measured_block_order_alternative() -> None:
    from ai_kicad.m2_pack import _semantic_block_order_candidates

    left = BlockPlan("left", "filter", (), frozenset(), (), function=("filter", "a"))
    right = BlockPlan("right", "amplifier", (), frozenset(), (), function=("gain", "b"))
    plan = SemanticPlan((left, right), (), {}, ())
    baseline = Packing(
        (
            _place(_fragment(left), LEFT + 60 * PITCH, 60 * PITCH),
            _place(_fragment(right), LEFT + 80 * PITCH, 60 * PITCH),
        ),
        (),
    )
    alternatives = _semantic_block_order_candidates(plan, baseline)
    assert len(alternatives) == 1
    swapped = {item.fragment.block.id: item.envelope[0] for item in alternatives[0].fragments}
    before = {item.fragment.block.id: item.envelope[0] for item in baseline.fragments}
    assert swapped["left"] == before["right"]
    assert swapped["right"] == before["left"]
    assert alternatives[0].attempts[-1] == "semantic-block-order-swap"


def test_forward_dependent_stages_cannot_be_swapped_by_block_search() -> None:
    from ai_kicad.m2_pack import _semantic_block_order_candidates

    first = BlockPlan("first", "filter", (), frozenset(), (), function=("stage", "a"))
    next_stage = BlockPlan("next", "filter", (), frozenset(), (), function=("stage", "b"))
    plan = SemanticPlan(
        (first, next_stage),
        (SemanticEdge("signal", "first", "next", "signal", ()),),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(first), LEFT + 60 * PITCH, 60 * PITCH),
            _place(_fragment(next_stage), LEFT + 80 * PITCH, 60 * PITCH),
        ),
        (),
    )
    assert _semantic_block_order_candidates(plan, baseline) == ()


def test_support_affinity_relocates_local_bias_near_owning_stage() -> None:
    stage = BlockPlan("gain", "amplifier", (), frozenset(), (), function=("amplifier", "gain"))
    bias = BlockPlan("bias", "rc", (), frozenset(), ())
    plan = SemanticPlan(
        (stage, bias),
        (SemanticEdge("support", "bias", "gain", "bias", ()),),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(stage), LEFT + 60 * PITCH, 55 * PITCH),
            _place(_fragment(bias), LEFT + 100 * PITCH, 85 * PITCH),
        ),
        (),
    )
    options = _support_affinity_candidates(plan, baseline)
    assert len(options) == 1
    moved = next(item for item in options[0].fragments if item.fragment.block.id == "bias")
    original = next(item for item in baseline.fragments if item.fragment.block.id == "bias")
    assert moved.envelope[0] < original.envelope[0]
    assert options[0].attempts[-1] == "semantic-support-affinity"
    assert (
        _support_affinity_candidates(
            SemanticPlan(tuple(reversed(plan.blocks)), plan.edges, {}, ()), baseline
        )
        == options
    )


def test_support_affinity_requires_explicit_functional_ownership() -> None:
    first = BlockPlan("first", "rc", (), frozenset(), ())
    second = BlockPlan("second", "rc", (), frozenset(), ())
    plan = SemanticPlan(
        (first, second),
        (SemanticEdge("support", "first", "second", "rail", ()),),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(first), LEFT + 60 * PITCH, 55 * PITCH),
            _place(_fragment(second), LEFT + 100 * PITCH, 85 * PITCH),
        ),
        (),
    )
    assert _support_affinity_candidates(plan, baseline) == ()


def test_repeated_signal_peers_search_legal_row_or_column_arrangement() -> None:
    first = BlockPlan("first", "filter", (), frozenset(), (), function=("stage", "first"))
    second = BlockPlan("second", "filter", (), frozenset(), (), function=("stage", "second"))
    plan = SemanticPlan((first, second), (), {}, ())
    baseline = Packing(
        (
            _place(_fragment(first), LEFT + 60 * PITCH, 55 * PITCH),
            _place(_fragment(second), LEFT + 85 * PITCH, 80 * PITCH),
        ),
        (),
    )
    aligned = _repeated_peer_alignment_candidates(plan, baseline)
    assert len(aligned) == 2
    assert [candidate.attempts[-1] for candidate in aligned] == [
        "repeated-peer-row",
        "repeated-peer-column",
    ]
    for candidate in aligned:
        layout = {item.fragment.block.id: item.envelope for item in candidate.fragments}
        assert (
            layout["first"][0] == layout["second"][0] or layout["first"][1] == layout["second"][1]
        )
    reversed_plan = SemanticPlan(tuple(reversed(plan.blocks)), plan.edges, {}, ())
    assert _repeated_peer_alignment_candidates(reversed_plan, baseline) == aligned


def test_repeated_alignment_search_does_not_reorder_serial_stages() -> None:
    first = BlockPlan("first", "filter", (), frozenset(), (), function=("stage", "first"))
    second = BlockPlan("second", "filter", (), frozenset(), (), function=("stage", "second"))
    plan = SemanticPlan(
        (first, second),
        (SemanticEdge("signal", "first", "second", "signal", ()),),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(first), LEFT + 60 * PITCH, 55 * PITCH),
            _place(_fragment(second), LEFT + 85 * PITCH, 80 * PITCH),
        ),
        (),
    )
    assert _repeated_peer_alignment_candidates(plan, baseline) == ()
