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


def test_output_frontier_search_fixes_worst_row_misalignment_first() -> None:
    """Do not consume the sole output slot on an almost aligned connector."""
    near_owner = _block("near-owner", "amplifier")
    far_owner = _block("far-owner", "amplifier")
    near_output = _block("near-output", "interface", "signal_out")
    far_output = _block("far-output", "interface", "signal_out")
    blocks = (near_owner, far_owner, near_output, far_output)
    edges = (
        SemanticEdge("signal", "near-owner", "near-output", "near", ()),
        SemanticEdge("signal", "far-owner", "far-output", "far", ()),
    )
    plan = SemanticPlan(blocks, edges, {}, ())
    baseline = Packing(
        (
            _place(_fragment(near_owner), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(far_owner), LEFT + 60 * PITCH, 80 * PITCH),
            _place(_fragment(near_output), LEFT + 90 * PITCH, 51 * PITCH),
            _place(_fragment(far_output), LEFT + 90 * PITCH, 98 * PITCH),
        ),
        (),
    )
    candidates = _interface_frontier_candidates(plan, baseline)
    assert len(candidates) == 1
    by_id = {item.fragment.block.id: item for item in candidates[0].fragments}
    original = {item.fragment.block.id: item for item in baseline.fragments}
    assert by_id["far-output"].delta != original["far-output"].delta
    assert by_id["near-output"].delta == original["near-output"].delta
    assert by_id["far-output"].envelope[1] == by_id["far-owner"].envelope[1]
    assert (
        _interface_frontier_candidates(
            SemanticPlan(tuple(reversed(blocks)), tuple(reversed(edges)), {}, ()),
            baseline,
        )
        == candidates
    )


def test_frontier_search_repairs_two_reversed_outputs_in_one_bounded_candidate() -> None:
    """All independent wrongly-sided outputs must be considered under one slot."""
    stage_a = _block("stage-a", "amplifier")
    stage_b = _block("stage-b", "amplifier")
    output_a = _block("output-a", "interface", "signal_out")
    output_b = _block("output-b", "interface", "signal_out")
    blocks = (stage_a, stage_b, output_a, output_b)
    edges = (
        SemanticEdge("signal", "stage-a", "output-a", "a", ()),
        SemanticEdge("signal", "stage-b", "output-b", "b", ()),
    )
    baseline = Packing(
        (
            _place(_fragment(stage_a), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(stage_b), LEFT + 60 * PITCH, 80 * PITCH),
            _place(_fragment(output_a), LEFT + 30 * PITCH, 50 * PITCH),
            _place(_fragment(output_b), LEFT + 30 * PITCH, 80 * PITCH),
        ),
        (),
    )
    plan = SemanticPlan(blocks, edges, {}, ())
    candidates = _interface_frontier_candidates(plan, baseline)
    assert len(candidates) == 1
    by_id = {item.fragment.block.id: item for item in candidates[0].fragments}
    assert candidates[0].attempts[-1] == "interface-frontier-output"
    for suffix in ("a", "b"):
        assert by_id[f"output-{suffix}"].envelope[0] > by_id[f"stage-{suffix}"].envelope[2]
    reversed_plan = SemanticPlan(tuple(reversed(blocks)), tuple(reversed(edges)), {}, ())
    assert _interface_frontier_candidates(reversed_plan, baseline) == candidates


def test_opposing_interfaces_exchange_blocked_frontier_slots() -> None:
    """An input and output may block one another's only direction-correct slot."""
    stage = _block("stage", "amplifier")
    input_block = _block("incoming", "interface", "signal_in")
    output_block = _block("outgoing", "interface", "signal_out")
    blocks = (stage, input_block, output_block)
    edges = (
        SemanticEdge("signal", "incoming", "stage", "in", ()),
        SemanticEdge("signal", "stage", "outgoing", "out", ()),
    )
    baseline = Packing(
        (
            _place(_fragment(stage), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(input_block), LEFT + 69 * PITCH, 50 * PITCH),
            _place(_fragment(output_block), LEFT + 51 * PITCH, 50 * PITCH),
        ),
        (),
    )
    plan = SemanticPlan(blocks, edges, {}, ())
    candidates = _interface_frontier_candidates(plan, baseline)
    assert len(candidates) == 2
    for candidate in candidates:
        by_id = {item.fragment.block.id: item for item in candidate.fragments}
        assert by_id["incoming"].envelope[2] < by_id["stage"].envelope[0]
        assert by_id["outgoing"].envelope[0] > by_id["stage"].envelope[2]
    assert _interface_frontier_candidates(
        SemanticPlan(tuple(reversed(blocks)), tuple(reversed(edges)), {}, ()), baseline
    ) == candidates


def test_frontier_exchange_never_reverses_a_correctly_sided_interface() -> None:
    """A connector already to the right of its producer must not be evicted left."""
    stage = _block("stage", "amplifier")
    output_a = _block("out-a", "interface", "signal_out")
    output_b = _block("out-b", "interface", "signal_out")
    plan = SemanticPlan(
        (stage, output_a, output_b),
        (
            SemanticEdge("signal", "stage", "out-a", "a", ()),
            SemanticEdge("signal", "stage", "out-b", "b", ()),
        ),
        {},
        (),
    )
    baseline = Packing(
        (
            _place(_fragment(stage), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(output_a), LEFT + 51 * PITCH, 50 * PITCH),
            _place(_fragment(output_b), LEFT + 69 * PITCH, 50 * PITCH),
        ),
        (),
    )
    for candidate in _interface_frontier_candidates(plan, baseline):
        by_id = {item.fragment.block.id: item for item in candidate.fragments}
        assert by_id["out-b"].envelope[0] > by_id["stage"].envelope[2]


def test_frontier_search_uses_unique_terminal_backed_passive_output() -> None:
    """A uniquely inferred passive output belongs after its producer."""
    stage = BlockPlan(
        "producer",
        "amplifier",
        (),
        frozenset(),
        (SemanticPort("producer.out", "producer", "SIGNAL", "signal_out", ()),),
    )
    output = BlockPlan(
        "external",
        "interface",
        (),
        frozenset(),
        (SemanticPort("external.pin", "external", "SIGNAL", "passive", ()),),
    )
    plan = SemanticPlan((stage, output), (), {}, ())
    baseline = Packing(
        (
            _place(_fragment(stage), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(output), LEFT + 30 * PITCH, 50 * PITCH),
        ),
        (),
    )
    candidates = _interface_frontier_candidates(plan, baseline)
    assert len(candidates) == 1
    by_id = {item.fragment.block.id: item for item in candidates[0].fragments}
    assert by_id["external"].envelope[0] > by_id["producer"].envelope[2]
    assert candidates[0].attempts[-1] == "interface-frontier-output"
    reversed_plan = SemanticPlan((output, stage), (), {}, ())
    assert _interface_frontier_candidates(reversed_plan, baseline) == candidates


def test_frontier_search_does_not_assign_ambiguous_passive_interface() -> None:
    """A passive interface shared by producer and consumer is undirected."""
    producer = BlockPlan(
        "producer",
        "amplifier",
        (),
        frozenset(),
        (SemanticPort("producer.out", "producer", "SHARED", "signal_out", ()),),
    )
    consumer = BlockPlan(
        "consumer",
        "amplifier",
        (),
        frozenset(),
        (SemanticPort("consumer.in", "consumer", "SHARED", "signal_in", ()),),
    )
    passive = BlockPlan(
        "external",
        "interface",
        (),
        frozenset(),
        (SemanticPort("external.pin", "external", "SHARED", "passive", ()),),
    )
    plan = SemanticPlan((producer, consumer, passive), (), {}, ())
    baseline = Packing(
        (
            _place(_fragment(producer), LEFT + 60 * PITCH, 50 * PITCH),
            _place(_fragment(consumer), LEFT + 80 * PITCH, 50 * PITCH),
            _place(_fragment(passive), LEFT + 30 * PITCH, 50 * PITCH),
        ),
        (),
    )
    assert _interface_frontier_candidates(plan, baseline) == ()


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


def test_final_beam_retains_both_repeated_grammars_and_variant_seeds() -> None:
    from ai_kicad.m2_pack import CANDIDATE_BUDGET, _retain_composition_seed_diversity

    block = _block("stage", "filter")
    variant = _fragment(block)

    def seed(index: int, label: str) -> Packing:
        return Packing(
            (_place(variant, LEFT + (20 + index * 9) * PITCH, 55 * PITCH),),
            (label,),
        )

    baseline = tuple(seed(index, f"baseline-{index}") for index in range(8))
    extras = (
        seed(9, "interface-frontier-input"),
        seed(10, "interface-frontier-output"),
        seed(11, "semantic-block-order-swap"),
        seed(12, "semantic-support-affinity"),
        seed(13, "repeated-peer-row"),
        seed(14, "repeated-peer-column"),
        seed(15, "functional-row-compaction"),
    )
    retained = _retain_composition_seed_diversity(baseline, extras)
    labels = [candidate.attempts[-1] for candidate in retained]
    assert len(retained) == CANDIDATE_BUDGET
    # Both semantic interface frontiers now have explicit retention priority
    # under the saturated beam; the older baseline-only expectation would
    # reject that intentional improvement before routing can evaluate it.
    assert labels[:5] == [
        "baseline-0",
        "repeated-peer-row",
        "repeated-peer-column",
        "interface-frontier-output",
        "interface-frontier-input",
    ]
    assert len({candidate.fragments[0].delta for candidate in retained}) == CANDIDATE_BUDGET


def test_repeated_beam_retention_deduplicates_same_placement() -> None:
    from ai_kicad.m2_pack import _retain_composition_seed_diversity

    block = _block("stage", "filter")
    variant = _fragment(block)
    base = Packing((_place(variant, LEFT + 20 * PITCH, 55 * PITCH),), ("base",))
    duplicate = Packing(base.fragments, ("repeated-peer-row",))
    different = Packing(
        (_place(variant, LEFT + 45 * PITCH, 55 * PITCH),),
        ("repeated-peer-column",),
    )
    assert _retain_composition_seed_diversity((base,), (duplicate, different)) == (
        base,
        different,
    )


def test_final_beam_preserves_measured_field_slot_variant() -> None:
    from dataclasses import replace

    from ai_kicad.m2_pack import CANDIDATE_BUDGET, _retain_composition_seed_diversity

    block = _block("stage", "filter")
    plain = _fragment(block)
    alternate = replace(
        plain,
        id="stage.local-text-slot",
        rule_id="m2g2.local-text-slot.filter.alternate.v1",
    )

    def make_seed(index: int, fragment: FragmentVariant = plain) -> Packing:
        return Packing(
            (_place(fragment, LEFT + (20 + index * 9) * PITCH, 55 * PITCH),),
            (f"baseline-{index}",),
        )

    baseline = tuple(make_seed(index) for index in range(8))
    # A legally measured field-slot choice in a late successful seed must
    # remain in the final eight-candidate route-aware search.
    field_slot_seed = make_seed(9, alternate)
    seeds = baseline + (field_slot_seed,)
    extras = tuple(
        Packing(
            (_place(plain, LEFT + (140 + index * 9) * PITCH, 55 * PITCH),),
            (f"other-{index}",),
        )
        for index in range(4)
    )
    kept = _retain_composition_seed_diversity(seeds, extras)
    assert len(kept) == CANDIDATE_BUDGET
    assert field_slot_seed in kept
    assert all(
        len(
            [
                placed
                for placed in packing.fragments
                if ".local-text-slot." in placed.fragment.rule_id
            ]
        )
        <= 1
        for packing in kept
    )


def test_directed_frontiers_survive_full_competing_seed_budget() -> None:
    from ai_kicad.m2_pack import CANDIDATE_BUDGET, _retain_composition_seed_diversity

    block = _block("stage", "filter")
    fragment = _fragment(block)

    def seed(index: int, label: str) -> Packing:
        return Packing(
            (_place(fragment, LEFT + (20 + index * 9) * PITCH, 55 * PITCH),),
            (label,),
        )

    baseline = tuple(seed(index, f"baseline-{index}") for index in range(CANDIDATE_BUDGET))
    extras = (
        seed(8, "distribution-column:legal"),
        Packing(seed(9, "partial-beam:pass").fragments, ("partial-beam", "partial-beam:pass")),
        seed(10, "repeated-peer-row"),
        seed(11, "repeated-peer-column"),
        seed(12, "branch-fanout-origin-centered"),
        seed(13, "branch-fanout-sibling-depth"),
        seed(14, "interface-frontier-input"),
        seed(15, "interface-frontier-output"),
        seed(16, "centroid-balanced-page"),
    )
    retained = _retain_composition_seed_diversity(baseline, extras)
    labels = [item.attempts[-1] for item in retained]
    assert len(retained) == CANDIDATE_BUDGET
    assert labels == [
        "baseline-0",
        "distribution-column:legal",
        "partial-beam:pass",
        "repeated-peer-row",
        "repeated-peer-column",
        "interface-frontier-output",
        "interface-frontier-input",
        "branch-fanout-origin-centered",
    ]
