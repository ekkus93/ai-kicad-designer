from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import (
    compactness_whitespace_penalties,
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
    semantic_composition_penalties,
)


def _block(block_id: str, kind: str = "stage", roles: tuple[str, ...] = ()):
    ports = tuple(SimpleNamespace(role=role) for role in roles)
    return SimpleNamespace(id=block_id, kind=kind, ports=ports)


def _plan(blocks, edges=(), precedence=()):
    return SimpleNamespace(blocks=tuple(blocks), edges=tuple(edges), precedence=tuple(precedence))


def _edge(kind: str, source: str, target: str, net: str = "n"):
    return SimpleNamespace(kind=kind, source=source, target=target, net=net)


def _placed(
    block,
    x: int,
    y: int = 0,
    width: int = PITCH,
    height: int = PITCH,
    *,
    positions=None,
    text_positions=None,
    angles=None,
):
    rect = (x, y, x + width, y + height)
    fragment = SimpleNamespace(
        block=block,
        positions=positions or {},
        text_positions=text_positions or {},
        angles=angles or {},
    )
    return SimpleNamespace(
        fragment=fragment,
        content_envelope=rect,
        envelope=rect,
        delta=(x, y),
    )


def _packing(*items):
    return SimpleNamespace(fragments=tuple(items))


def test_semantic_flow_outranks_shorter_routing() -> None:
    input_block = _block("input", "interface", ("signal_in",))
    stage = _block("stage")
    output_block = _block("output", "interface", ("signal_out",))
    plan = _plan(
        (input_block, stage, output_block),
        (
            _edge("signal", "input", "stage", "in"),
            _edge("signal", "stage", "output", "out"),
        ),
    )
    readable = _packing(
        _placed(input_block, 0),
        _placed(stage, 2 * PITCH),
        _placed(output_block, 4 * PITCH),
    )
    reversed_flow = _packing(
        _placed(input_block, 4 * PITCH),
        _placed(stage, 2 * PITCH),
        _placed(output_block, 0),
    )
    readable_key = composition_candidate_key(plan, readable, (1000, 500, 4, 1.0, 1, 0))
    reversed_key = composition_candidate_key(plan, reversed_flow, (1, 1, 0, 1.0, 0, 0))
    assert readable_key < reversed_key


def test_feedback_and_support_are_locality_not_forward_precedence() -> None:
    stage = _block("stage")
    feedback = _block("feedback", "support")
    support = _block("support", "support")
    plan = _plan(
        (stage, feedback, support),
        (
            _edge("feedback", "feedback", "stage", "fb"),
            _edge("support", "support", "stage", "bias"),
        ),
    )
    near = _packing(
        _placed(stage, 2 * PITCH),
        _placed(feedback, 3 * PITCH),
        _placed(support, PITCH),
    )
    far = _packing(
        _placed(stage, 2 * PITCH),
        _placed(feedback, 30 * PITCH),
        _placed(support, 40 * PITCH),
    )
    near_penalties = semantic_composition_penalties(plan, near)
    far_penalties = semantic_composition_penalties(plan, far)
    assert near_penalties[1] == 0
    assert far_penalties[1] == 0
    assert near_penalties[6:8] < far_penalties[6:8]


def test_frontier_penalty_prefers_directed_interfaces_at_content_edges() -> None:
    input_block = _block("input", "interface", ("signal_in",))
    stage = _block("stage")
    output_block = _block("output", "interface", ("signal_out",))
    spare = _block("spare")
    far = _block("far")
    plan = _plan(
        (input_block, stage, output_block, spare, far),
        (
            _edge("signal", "input", "stage", "in"),
            _edge("signal", "stage", "output", "out"),
        ),
    )
    frontier = _packing(
        _placed(input_block, 0),
        _placed(stage, 2 * PITCH),
        _placed(output_block, 4 * PITCH),
        _placed(spare, 2 * PITCH, 2 * PITCH),
        _placed(far, 3 * PITCH, 2 * PITCH),
    )
    interior = _packing(
        _placed(spare, 0, 2 * PITCH),
        _placed(input_block, PITCH),
        _placed(stage, 2 * PITCH),
        _placed(output_block, 3 * PITCH),
        _placed(far, 4 * PITCH, 2 * PITCH),
    )
    assert (
        semantic_composition_penalties(plan, frontier)[5]
        < semantic_composition_penalties(plan, interior)[5]
    )


def test_compactness_penalty_is_deterministic_integer_geometry() -> None:
    first = _block("first")
    second = _block("second")
    compact = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 4 * PITCH, 2 * PITCH),
    )
    dispersed = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 40 * PITCH, 20 * PITCH),
    )
    compact_score = compactness_whitespace_penalties(compact)
    dispersed_score = compactness_whitespace_penalties(dispersed)
    assert compact_score[0] < dispersed_score[0]
    assert all(isinstance(value, int) for value in compact_score + dispersed_score)


def test_repeated_incomparable_peers_prefer_shared_row_or_column() -> None:
    first = _block("first", "filter", ("signal_in", "signal_out"))
    second = _block("second", "filter", ("signal_in", "signal_out"))
    plan = _plan((first, second))
    aligned = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 2 * PITCH, 8 * PITCH),
    )
    diagonal = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 8 * PITCH, 8 * PITCH),
    )
    assert semantic_composition_penalties(plan, aligned)[9] == 0
    assert semantic_composition_penalties(plan, diagonal)[9] > 0


def test_serial_equivalent_stages_are_not_repeated_peers() -> None:
    first = _block("first", "filter", ("signal_in", "signal_out"))
    second = _block("second", "filter", ("signal_in", "signal_out"))
    plan = _plan((first, second), (_edge("signal", "first", "second", "chain"),))
    diagonal = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 8 * PITCH, 8 * PITCH),
    )
    assert semantic_composition_penalties(plan, diagonal)[9] == 0


def test_intra_block_cohesion_penalizes_spread_internal_geometry() -> None:
    block = _block("gain", "amplifier")
    plan = _plan((block,))
    compact = _packing(
        _placed(
            block,
            0,
            positions={("U", 1): (0, 0), ("R", 1): (PITCH, 0)},
        )
    )
    dispersed = _packing(
        _placed(
            block,
            0,
            positions={("U", 1): (0, 0), ("R", 1): (8 * PITCH, 0)},
        )
    )
    assert (
        semantic_composition_penalty_breakdown(plan, compact).intra_block_dispersion
        < semantic_composition_penalty_breakdown(plan, dispersed).intra_block_dispersion
    )


def test_intra_block_dispersion_uses_full_bounding_span() -> None:
    """Three corners expose fragmentation missed by pairwise max distance."""
    block = _block("generic-functional-cell", "amplifier")
    plan = _plan((block,))
    triangle_positions = {
        ("a", 1): (0, 0),
        ("b", 1): (4 * PITCH, PITCH),
        ("c", 1): (PITCH, 4 * PITCH),
    }
    triangle = _packing(_placed(block, 0, positions=triangle_positions))
    translated = _packing(_placed(block, 9 * PITCH, positions=triangle_positions))
    straight = _packing(
        _placed(
            block,
            0,
            positions={("a", 1): (0, 0), ("b", 1): (6 * PITCH, 0)},
        )
    )
    observed_triangle = semantic_composition_penalty_breakdown(
        plan, triangle
    ).intra_block_dispersion
    assert observed_triangle == 8
    assert (
        semantic_composition_penalty_breakdown(plan, translated).intra_block_dispersion
        == observed_triangle
    )
    assert semantic_composition_penalty_breakdown(plan, straight).intra_block_dispersion == 6


def test_unrelated_blocks_require_visual_separation() -> None:
    amplifier = _block("amp", "amplifier")
    controller = _block("ctrl", "controller")
    plan = _plan((amplifier, controller))
    touching = _packing(
        _placed(amplifier, 0),
        _placed(controller, PITCH),
    )
    separated = _packing(
        _placed(amplifier, 0),
        _placed(controller, 3 * PITCH),
    )
    assert (
        semantic_composition_penalty_breakdown(plan, touching).unrelated_block_proximity
        > semantic_composition_penalty_breakdown(plan, separated).unrelated_block_proximity
    )
    assert semantic_composition_penalty_breakdown(plan, separated).unrelated_block_proximity == 0


def test_related_blocks_are_exempt_from_inter_block_separation_penalty() -> None:
    source = _block("source", "amplifier")
    target = _block("target", "filter")
    plan = _plan((source, target), (_edge("signal", "source", "target"),))
    touching = _packing(_placed(source, 0), _placed(target, PITCH))
    assert semantic_composition_penalty_breakdown(plan, touching).unrelated_block_proximity == 0


def test_power_input_prefers_semantically_connected_supply_infrastructure() -> None:
    power = _block("power", "interface", ("power_in",))
    supply = _block("supply", "supply")
    signal = _block("signal", "filter", ("signal_in", "signal_out"))
    plan = _plan(
        (power, supply, signal),
        (_edge("power", "power", "supply", "rail"),),
    )
    grouped = _packing(
        _placed(power, 2 * PITCH, 8 * PITCH),
        _placed(supply, 4 * PITCH, 8 * PITCH),
        _placed(signal, 4 * PITCH, 2 * PITCH),
    )
    detached = _packing(
        _placed(power, 2 * PITCH, 2 * PITCH),
        _placed(supply, 4 * PITCH, 8 * PITCH),
        _placed(signal, 4 * PITCH, 2 * PITCH),
    )

    grouped_score = semantic_composition_penalty_breakdown(plan, grouped)
    detached_score = semantic_composition_penalty_breakdown(plan, detached)

    assert grouped_score.power_interface_distance < detached_score.power_interface_distance
    assert grouped_score.stage_order_violations == detached_score.stage_order_violations == 0


def test_supply_infrastructure_is_penalized_on_primary_signal_row() -> None:
    first = _block("first", "filter", ("signal_in", "signal_out"))
    second = _block("second", "filter", ("signal_in", "signal_out"))
    supply = _block("supply", "supply")
    plan = _plan(
        (first, second, supply),
        (
            _edge("signal", "first", "second", "signal"),
            _edge("power", "supply", "first", "rail"),
        ),
    )
    intruding = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 5 * PITCH, 2 * PITCH),
        _placed(supply, 4 * PITCH, 2 * PITCH),
    )
    subordinate = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 5 * PITCH, 2 * PITCH),
        _placed(supply, 4 * PITCH, 6 * PITCH),
    )

    intruding_score = semantic_composition_penalty_breakdown(plan, intruding)
    subordinate_score = semantic_composition_penalty_breakdown(plan, subordinate)

    assert intruding_score.infrastructure_primary_row_intrusion > 0
    assert subordinate_score.infrastructure_primary_row_intrusion == 0


def test_branch_fanout_prefers_centered_origin_and_equal_target_depth() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    plan = _plan(
        (source, upper, lower),
        (_edge("branch", "source", "upper"), _edge("branch", "source", "lower")),
    )
    centered = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    off_center = _packing(
        _placed(source, 0, 0),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    staggered = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 15 * PITCH, 10 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, centered).branch_alignment == 0
    assert (
        semantic_composition_penalty_breakdown(plan, off_center).branch_alignment
        > semantic_composition_penalty_breakdown(plan, centered).branch_alignment
    )
    assert (
        semantic_composition_penalty_breakdown(plan, staggered).branch_alignment
        > semantic_composition_penalty_breakdown(plan, centered).branch_alignment
    )


def test_branch_readability_ignores_non_branch_edges_and_order() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    blocks = (source, upper, lower)
    branches = (_edge("branch", "source", "upper"), _edge("branch", "source", "lower"))
    placed = _packing(
        _placed(source, 0, 0),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    forward = semantic_composition_penalty_breakdown(_plan(blocks, branches), placed)
    backward = semantic_composition_penalty_breakdown(
        _plan(tuple(reversed(blocks)), tuple(reversed(branches))), placed
    )
    ordinary = semantic_composition_penalty_breakdown(
        _plan(blocks, (_edge("signal", "source", "upper"), _edge("feedback", "lower", "source"))),
        placed,
    )
    assert forward.branch_alignment > 0
    assert forward.branch_alignment == backward.branch_alignment
    assert ordinary.branch_alignment == 0


def test_two_band_repeated_channel_stage_columns_are_semantically_aligned() -> None:
    blocks = tuple(_block(f"{band}{stage}") for band in ("a", "b") for stage in range(3))
    edges = tuple(
        _edge("signal", f"{band}{stage}", f"{band}{stage + 1}", f"{band}-{stage}")
        for band in ("a", "b")
        for stage in range(2)
    )
    plan = _plan(blocks, edges)
    aligned = _packing(
        *(
            _placed(
                block,
                (2 + 6 * int(block.id[1])) * PITCH,
                (2 if block.id[0] == "a" else 12) * PITCH,
            )
            for block in blocks
        )
    )
    drifted = _packing(
        *(
            _placed(
                block,
                (2 + 6 * int(block.id[1]) + (2 if block.id == "b1" else 0)) * PITCH,
                (2 if block.id[0] == "a" else 12) * PITCH,
            )
            for block in blocks
        )
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, drifted)
    permuted = semantic_composition_penalty_breakdown(
        _plan(tuple(reversed(blocks)), tuple(reversed(edges))), drifted
    )
    assert good.repeated_alignment == 0
    assert bad.repeated_alignment > good.repeated_alignment
    assert good.stage_order_violations == bad.stage_order_violations == 0
    assert bad.repeated_alignment == permuted.repeated_alignment


def test_ordinary_signal_fanout_prefers_a_centered_visible_origin() -> None:
    source = _block("origin", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    plan = _plan(
        (source, upper, lower),
        (
            _edge("signal", "origin", "upper", "shared"),
            _edge("signal", "origin", "lower", "shared"),
        ),
    )
    centered = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    detached = _packing(
        _placed(source, 0, 0),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    good = semantic_composition_penalty_breakdown(plan, centered)
    bad = semantic_composition_penalty_breakdown(plan, detached)
    assert good.branch_alignment == 0
    assert bad.branch_alignment > good.branch_alignment
    assert good.stage_order_violations == bad.stage_order_violations == 0
    assert composition_candidate_key(plan, centered, (1000, 100, 8, 1, 1, 0)) < (
        composition_candidate_key(plan, detached, (1, 1, 0, 1, 0, 0))
    )


def test_signal_fanout_deduplicates_mixed_branch_annotations_and_renames() -> None:
    source = _block("origin")
    upper = _block("upper")
    lower = _block("lower")
    blocks = (source, upper, lower)
    placed = _packing(
        _placed(source, 0, 0),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    canonical = _plan(
        blocks,
        (_edge("branch", "origin", "upper", "net"), _edge("branch", "origin", "lower", "net")),
    )
    mixed = _plan(
        tuple(reversed(blocks)),
        (
            _edge("signal", "origin", "lower", "net"),
            _edge("branch", "origin", "upper", "net"),
            _edge("signal", "origin", "upper", "net"),
        ),
    )
    assert semantic_composition_penalty_breakdown(canonical, placed).branch_alignment == (
        semantic_composition_penalty_breakdown(mixed, placed).branch_alignment
    )
    renamed = _plan(
        blocks,
        (
            _edge("signal", "origin", "upper", "different"),
            _edge("signal", "origin", "lower", "different"),
        ),
    )
    assert semantic_composition_penalty_breakdown(renamed, placed).branch_alignment == (
        semantic_composition_penalty_breakdown(canonical, placed).branch_alignment
    )


def test_signal_fanout_does_not_conflate_unrelated_or_non_signal_edges() -> None:
    source = _block("origin")
    upper = _block("upper")
    lower = _block("lower")
    placed = _packing(
        _placed(source, 0, 0),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
    )
    separate_nets = _plan(
        (source, upper, lower),
        (_edge("signal", "origin", "upper", "a"), _edge("signal", "origin", "lower", "b")),
    )
    mixed_roles = _plan(
        (source, upper, lower),
        (
            _edge("signal", "origin", "upper", "same"),
            _edge("feedback", "origin", "lower", "same"),
            _edge("power", "origin", "lower", "same"),
        ),
    )
    assert semantic_composition_penalty_breakdown(separate_nets, placed).branch_alignment == 0
    assert semantic_composition_penalty_breakdown(mixed_roles, placed).branch_alignment == 0


def test_owned_support_prefers_axis_alignment_at_equal_manhattan_distance() -> None:
    owner = _block("owner", "stage")
    local = _block("local", "support")
    plan = _plan((owner, local), (_edge("support", "owner", "local"),))
    aligned = _packing(_placed(owner, 0), _placed(local, 6 * PITCH))
    diagonal = _packing(_placed(owner, 0), _placed(local, 4 * PITCH, 2 * PITCH))
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, diagonal)

    assert good.support_distance == bad.support_distance
    assert good.support_axis_drift == 0
    assert bad.support_axis_drift == 2
    assert composition_candidate_key(plan, aligned, (1000, 500, 8, 1, 0, 0)) < (
        composition_candidate_key(plan, diagonal, (1, 1, 0, 1, 0, 0))
    )


def test_package_support_alignment_is_deduplicated_and_order_independent() -> None:
    owner = _block("owner", "stage")
    local = _block("local", "support")
    placed = _packing(_placed(owner, 0), _placed(local, 4 * PITCH, 2 * PITCH))
    support = _edge("support", "owner", "local")
    package = _edge("package", "local", "owner")
    single = semantic_composition_penalty_breakdown(_plan((owner, local), (support,)), placed)
    duplicated = semantic_composition_penalty_breakdown(
        _plan((local, owner), (package, support, support)), placed
    )
    assert single.support_axis_drift == duplicated.support_axis_drift == 2
    assert single.as_dict()["support_axis_drift"] == 2


def test_unowned_feedback_and_shared_infrastructure_do_not_claim_support_axis() -> None:
    owner = _block("owner", "stage")
    other = _block("other", "stage")
    placed = _packing(_placed(owner, 0), _placed(other, 4 * PITCH, 2 * PITCH))
    for kind in ("signal", "branch", "feedback", "power", "reference"):
        plan = _plan((owner, other), (_edge(kind, "owner", "other"),))
        assert semantic_composition_penalty_breakdown(plan, placed).support_axis_drift == 0


def test_serial_signal_stages_prefer_a_shared_row_with_equal_forward_progress() -> None:
    first = _block("a", "filter", ("signal_in", "signal_out"))
    second = _block("b", "amplifier", ("signal_in", "signal_out"))
    plan = _plan((first, second), (_edge("signal", "a", "b", "data"),))
    aligned = _packing(_placed(first, 0), _placed(second, 8 * PITCH))
    drifting = _packing(_placed(first, 0), _placed(second, 8 * PITCH, 3 * PITCH))
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, drifting)
    assert good.sequential_stage_row_drift == 0
    assert bad.sequential_stage_row_drift == 3
    assert good.stage_order_violations == bad.stage_order_violations == 0


def test_inferred_precedence_serial_stages_align_without_explicit_roles() -> None:
    """Passive stages with unique inferred signal neighbors have a row axis."""
    source = _block("source", "interface", ("signal_in",))
    first = _block("first", "rc")
    second = _block("second", "rc")
    output = _block("output", "interface", ("signal_out",))
    relations = (
        SimpleNamespace(source_fragment="source", target_fragment="first", net="input"),
        SimpleNamespace(source_fragment="first", target_fragment="second", net="signal"),
        SimpleNamespace(source_fragment="second", target_fragment="output", net="output"),
    )
    plan = _plan((source, first, second, output), precedence=relations)
    aligned = _packing(
        _placed(source, 0),
        _placed(first, 4 * PITCH),
        _placed(second, 8 * PITCH),
        _placed(output, 12 * PITCH),
    )
    drifting = _packing(
        _placed(source, 0),
        _placed(first, 4 * PITCH),
        _placed(second, 8 * PITCH, 3 * PITCH),
        _placed(output, 12 * PITCH, 3 * PITCH),
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, drifting)
    assert good.sequential_stage_row_drift == 0
    assert bad.sequential_stage_row_drift == 3
    assert good.stage_order_violations == bad.stage_order_violations == 0
    renamed = _plan((output, second, first, source), precedence=tuple(reversed(relations)))
    assert (
        semantic_composition_penalty_breakdown(renamed, drifting).sequential_stage_row_drift
        == bad.sequential_stage_row_drift
    )


def test_inferred_serial_row_exempts_fanout_and_single_ended_stages() -> None:
    source = _block("source", "interface", ("signal_in",))
    root = _block("root", "rc")
    upper = _block("upper", "rc")
    lower = _block("lower", "rc")
    output = _block("output", "interface", ("signal_out",))
    fanout = _plan(
        (source, root, upper, lower, output),
        (
            _edge("signal", "source", "root", "input"),
            _edge("signal", "root", "upper", "branch"),
            _edge("signal", "root", "lower", "branch"),
            _edge("signal", "upper", "output", "output"),
        ),
    )
    placed = _packing(
        _placed(source, 0),
        _placed(root, 4 * PITCH),
        _placed(upper, 8 * PITCH, 3 * PITCH),
        _placed(lower, 8 * PITCH, 7 * PITCH),
        _placed(output, 12 * PITCH, 3 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(fanout, placed).sequential_stage_row_drift == 0

    single_ended = _plan((root, upper), (_edge("signal", "root", "upper", "one_way"),))
    alone = _packing(_placed(root, 0), _placed(upper, 4 * PITCH, 5 * PITCH))
    assert (
        semantic_composition_penalty_breakdown(single_ended, alone).sequential_stage_row_drift == 0
    )


def test_fanout_and_feedback_do_not_impose_one_serial_baseline() -> None:
    source = _block("source", "filter", ("signal_in", "signal_out"))
    upper = _block("upper", "filter", ("signal_in", "signal_out"))
    lower = _block("lower", "filter", ("signal_in", "signal_out"))
    plan = _plan(
        (source, upper, lower),
        (
            _edge("signal", "source", "upper", "split"),
            _edge("signal", "source", "lower", "split"),
            _edge("feedback", "lower", "source", "loop"),
        ),
    )
    spread = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 8 * PITCH),
        _placed(lower, 8 * PITCH, 10 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, spread).sequential_stage_row_drift == 0


def test_directed_connector_prefers_its_owned_signal_row() -> None:
    input_port = _block("input", "interface", ("signal_in",))
    stage = _block("stage", "filter", ("signal_in", "signal_out"))
    output_port = _block("output", "interface", ("signal_out",))
    plan = _plan(
        (input_port, stage, output_port),
        (
            _edge("signal", "input", "stage", "in"),
            _edge("signal", "stage", "output", "out"),
        ),
    )
    aligned = _packing(
        _placed(input_port, 0),
        _placed(stage, 4 * PITCH),
        _placed(output_port, 8 * PITCH),
    )
    drifting = _packing(
        _placed(input_port, 0, 2 * PITCH),
        _placed(stage, 4 * PITCH),
        _placed(output_port, 8 * PITCH, 3 * PITCH),
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, drifting)
    assert good.directed_interface_row_drift == 0
    assert bad.directed_interface_row_drift == 5
    assert good.stage_order_violations == bad.stage_order_violations == 0


def test_connector_fanout_aligns_with_any_owned_row_not_all_rows() -> None:
    interface = _block("input", "interface", ("signal_in",))
    upper = _block("upper", "filter", ("signal_in", "signal_out"))
    lower = _block("lower", "filter", ("signal_in", "signal_out"))
    plan = _plan(
        (interface, upper, lower),
        (
            _edge("signal", "input", "upper", "a"),
            _edge("signal", "input", "lower", "b"),
        ),
    )
    aligned = _packing(
        _placed(interface, 0),
        _placed(upper, 8 * PITCH),
        _placed(lower, 8 * PITCH, 6 * PITCH),
    )
    detached = _packing(
        _placed(interface, 0, 3 * PITCH),
        _placed(upper, 8 * PITCH),
        _placed(lower, 8 * PITCH, 6 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, aligned).directed_interface_row_drift == 0
    assert semantic_composition_penalty_breakdown(plan, detached).directed_interface_row_drift == 3


def test_branch_corridor_penalizes_only_unavoidable_short_elbow_obstacles() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    blocker_a = _block("obstacle-a", "controller")
    blocker_b = _block("obstacle-b", "controller")
    plan = _plan(
        (source, upper, lower, blocker_a, blocker_b),
        (
            _edge("signal", "source", "upper", "fan"),
            _edge("signal", "source", "lower", "fan"),
        ),
    )
    # Both minimum Manhattan elbows from source to upper are obstructed.
    obstructed = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
        _placed(blocker_a, 4 * PITCH, 5 * PITCH),
        _placed(blocker_b, 4 * PITCH, 0),
    )
    # Same branch geometry and components; neither short elbow is blocked.
    unobstructed = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
        _placed(blocker_a, 4 * PITCH, 16 * PITCH),
        _placed(blocker_b, 4 * PITCH, 19 * PITCH),
    )
    blocked_score = semantic_composition_penalty_breakdown(plan, obstructed)
    clear_score = semantic_composition_penalty_breakdown(plan, unobstructed)
    assert clear_score.branch_alignment == 0
    assert blocked_score.branch_alignment == 1


def test_branch_corridor_accepts_one_clear_short_elbow() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    blocker = _block("blocker", "controller")
    plan = _plan(
        (source, upper, lower, blocker),
        (
            _edge("branch", "source", "upper", "n"),
            _edge("branch", "source", "lower", "n"),
        ),
    )
    placed = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
        _placed(blocker, 4 * PITCH, 5 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, placed).branch_alignment == 0


def test_branch_corridor_is_deduplicated_and_rename_order_invariant() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    first_obstacle = _block("obstacle-a", "controller")
    second_obstacle = _block("obstacle-b", "controller")
    blocks = (source, upper, lower, first_obstacle, second_obstacle)
    placements = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
        _placed(first_obstacle, 4 * PITCH, 5 * PITCH),
        _placed(second_obstacle, 4 * PITCH, 0),
    )
    edges = (
        _edge("signal", "source", "upper", "original"),
        _edge("branch", "source", "upper", "original"),
        _edge("signal", "source", "lower", "original"),
    )
    canonical = _plan(blocks, edges)
    renamed = _plan(
        tuple(reversed(blocks)),
        (
            _edge("signal", "source", "lower", "renamed"),
            _edge("signal", "source", "upper", "renamed"),
        ),
    )
    assert semantic_composition_penalty_breakdown(canonical, placements).branch_alignment == (
        semantic_composition_penalty_breakdown(renamed, placements).branch_alignment
    )


def test_branch_corridor_exempts_local_owned_support_as_unrelated_obstacles() -> None:
    source = _block("source", "stage")
    upper = _block("upper", "stage")
    lower = _block("lower", "stage")
    support_a = _block("support-a", "support")
    support_b = _block("support-b", "support")
    blocks = (source, upper, lower, support_a, support_b)
    edges = (
        _edge("branch", "source", "upper", "fan"),
        _edge("branch", "source", "lower", "fan"),
        _edge("support", "upper", "support-a", "bias"),
        _edge("package", "upper", "support-b", "package"),
    )
    placed = _packing(
        _placed(source, 0, 5 * PITCH),
        _placed(upper, 10 * PITCH, 0),
        _placed(lower, 10 * PITCH, 10 * PITCH),
        _placed(support_a, 4 * PITCH, 5 * PITCH),
        _placed(support_b, 4 * PITCH, 0),
    )
    assert (
        semantic_composition_penalty_breakdown(_plan(blocks, edges), placed).branch_alignment == 0
    )


def _passive_with_reference(main_id: str = "main", ref_id: str = "shunt"):
    return SimpleNamespace(
        id="passive-stage",
        kind="rc",
        ports=(
            SimpleNamespace(role="signal_in", terminals=((main_id, "1"),)),
            SimpleNamespace(role="signal_out", terminals=((main_id, "2"),)),
            SimpleNamespace(role="reference", terminals=((ref_id, "2"),)),
        ),
    )


def test_local_passive_reference_leg_prefers_vertical_axis() -> None:
    block = _passive_with_reference()
    plan = _plan((block,))
    aligned = _packing(
        _placed(
            block,
            0,
            positions={("main", 1): (0, 0), ("shunt", 1): (0, 4 * PITCH)},
        )
    )
    diagonal = _packing(
        _placed(
            block,
            0,
            positions={("main", 1): (0, 0), ("shunt", 1): (3 * PITCH, 4 * PITCH)},
        )
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, diagonal)
    assert good.passive_reference_axis_drift == 0
    assert bad.passive_reference_axis_drift == 3
    assert bad.as_dict()["passive_reference_axis_drift"] == 3
    assert bad.vector()[-1] == 3


def test_passive_reference_axis_is_rename_and_order_invariant() -> None:
    first = _passive_with_reference("input-resistor", "capacitor")
    renamed = _passive_with_reference("other-main", "other-ref")
    renamed.ports = tuple(reversed(renamed.ports))
    first_placed = _packing(
        _placed(
            first,
            0,
            positions={
                ("input-resistor", 1): (0, 0),
                ("capacitor", 1): (2 * PITCH, 4 * PITCH),
            },
        )
    )
    renamed_placed = _packing(
        _placed(
            renamed,
            0,
            positions={
                ("other-ref", 1): (2 * PITCH, 4 * PITCH),
                ("other-main", 1): (0, 0),
            },
        )
    )
    original_score = semantic_composition_penalty_breakdown(
        _plan((first,)), first_placed
    ).passive_reference_axis_drift
    renamed_score = semantic_composition_penalty_breakdown(
        _plan((renamed,)), renamed_placed
    ).passive_reference_axis_drift
    assert original_score == renamed_score == 2


def test_passive_reference_axis_exempts_shared_or_missing_ownership() -> None:
    shared = SimpleNamespace(
        id="shared",
        kind="rc",
        ports=(
            SimpleNamespace(role="signal_in", terminals=(("main", "1"),)),
            SimpleNamespace(role="signal_out", terminals=(("main", "2"),)),
            SimpleNamespace(role="reference", terminals=(("ref-a", "2"), ("ref-b", "2"))),
        ),
    )
    placed = _packing(
        _placed(
            shared,
            0,
            positions={
                ("main", 1): (0, 0),
                ("ref-a", 1): (3 * PITCH, 4 * PITCH),
                ("ref-b", 1): (4 * PITCH, 4 * PITCH),
            },
        )
    )
    score = semantic_composition_penalty_breakdown(_plan((shared,)), placed)
    assert score.passive_reference_axis_drift == 0


def _field_role_stage(block_id: str, component_id: str, *, role: str = "signal_in"):
    return SimpleNamespace(
        id=block_id,
        kind="filter",
        ports=(SimpleNamespace(role=role, terminals=((component_id, "1"),)),),
    )


def _field_role_placed(
    block,
    component_id: str,
    x: int,
    *,
    slot: tuple[int, int],
    angle: int = 0,
):
    occurrence = (component_id, 1)
    return _placed(
        block,
        x,
        positions={occurrence: (0, 0)},
        text_positions={occurrence: slot},
        angles={occurrence: angle},
    )


def test_comparable_field_slots_are_aesthetic_tiebreakers_not_routing_overrides() -> None:
    first = _field_role_stage("a", "Rfirst")
    second = _field_role_stage("b", "Rsecond")
    plan = _plan((first, second))
    first_item = _field_role_placed(first, "Rfirst", 0, slot=(2 * PITCH, -3 * PITCH))
    matching = _packing(
        first_item,
        _field_role_placed(second, "Rsecond", 10 * PITCH, slot=(2 * PITCH, -3 * PITCH)),
    )
    inconsistent = _packing(
        first_item,
        _field_role_placed(second, "Rsecond", 10 * PITCH, slot=(5 * PITCH, -3 * PITCH)),
    )
    routing = (100, 100, 1, 1.0, 0, 0)
    aligned_key = composition_candidate_key(plan, matching, routing)
    drifted_key = composition_candidate_key(plan, inconsistent, routing)
    assert aligned_key[:-3] == drifted_key[:-3]
    assert aligned_key[-3] == 0
    assert drifted_key[-3] == 3
    assert aligned_key < drifted_key
    # Better real routing must outrank a prettier field slot.
    shorter_route = composition_candidate_key(plan, inconsistent, (99, 100, 1, 1.0, 0, 0))
    assert shorter_route < aligned_key


def test_field_slot_tiebreaker_ignores_refdes_and_insertion_order() -> None:
    first = _field_role_stage("a", "Rfirst")
    second = _field_role_stage("b", "Rsecond")
    base = _packing(
        _field_role_placed(first, "Rfirst", 0, slot=(0, -3 * PITCH)),
        _field_role_placed(second, "Rsecond", 10 * PITCH, slot=(2 * PITCH, -3 * PITCH)),
    )
    renamed_first = _field_role_stage("renamed-a", "new-A")
    renamed_second = _field_role_stage("renamed-b", "new-B")
    renamed = _packing(
        _field_role_placed(renamed_second, "new-B", 10 * PITCH, slot=(2 * PITCH, -3 * PITCH)),
        _field_role_placed(renamed_first, "new-A", 0, slot=(0, -3 * PITCH)),
    )
    routing = (100, 100, 1, 1.0, 0, 0)
    assert composition_candidate_key(_plan((first, second)), base, routing)[-3] == 2
    assert (
        composition_candidate_key(_plan((renamed_second, renamed_first)), renamed, routing)[-3] == 2
    )


def test_field_slot_tiebreaker_exempts_different_roles_or_rotations() -> None:
    first = _field_role_stage("a", "Rfirst")
    second = _field_role_stage("b", "Rsecond", role="reference")
    third = _field_role_stage("c", "Rthird")
    plan = _plan((first, second, third))
    packed = _packing(
        _field_role_placed(first, "Rfirst", 0, slot=(0, -3 * PITCH)),
        _field_role_placed(second, "Rsecond", 10 * PITCH, slot=(4 * PITCH, 3 * PITCH)),
        _field_role_placed(third, "Rthird", 20 * PITCH, slot=(4 * PITCH, 3 * PITCH), angle=180),
    )
    assert composition_candidate_key(plan, packed, (100, 100, 1, 1.0, 0, 0))[-3] == 0


def test_field_slot_tiebreaker_uses_median_and_exempts_missing_text() -> None:
    blocks = tuple(_field_role_stage(f"stage-{i}", f"R{i}") for i in range(4))
    packed = _packing(
        _field_role_placed(blocks[0], "R0", 0, slot=(0, -3 * PITCH)),
        _field_role_placed(blocks[1], "R1", 10 * PITCH, slot=(0, -3 * PITCH)),
        _field_role_placed(blocks[2], "R2", 20 * PITCH, slot=(6 * PITCH, -3 * PITCH)),
        _placed(blocks[3], 30 * PITCH, positions={("R3", 1): (0, 0)}),
    )
    assert composition_candidate_key(_plan(blocks), packed, (100, 100, 1, 1.0, 0, 0))[-3] == 6


def _presentation_net(
    role: str, fragments: tuple[str, ...], *, explicit_geometry_required: bool = False
):
    return SimpleNamespace(
        role=role,
        fragments=fragments,
        explicit_geometry_required=explicit_geometry_required,
    )


def test_local_label_eligible_signal_neighbors_prefer_proximity() -> None:
    source = _block("source", "filter")
    target = _block("target", "amplifier")
    plan = _plan((source, target))
    plan.presentation_nets = (_presentation_net("signal", ("source", "target")),)
    nearby = _packing(_placed(source, 0), _placed(target, 3 * PITCH))
    detached = _packing(_placed(source, 0), _placed(target, 11 * PITCH))
    nearby_score = semantic_composition_penalty_breakdown(plan, nearby)
    detached_score = semantic_composition_penalty_breakdown(plan, detached)
    assert nearby_score.local_signal_neighbor_gap == 0
    assert detached_score.local_signal_neighbor_gap == 8
    assert detached_score.as_dict()["local_signal_neighbor_gap"] == 8


def test_local_label_gap_exempts_interfaces_shared_and_explicit_geometry() -> None:
    first = _block("first", "filter")
    second = _block("second", "amplifier")
    third = _block("third", "filter")
    output = _block("output", "interface", ("signal_out",))
    plan = _plan((first, second, third, output))
    detached = _packing(
        _placed(first, 0),
        _placed(second, 12 * PITCH),
        _placed(third, 24 * PITCH),
        _placed(output, 36 * PITCH),
    )
    exempt_nets = (
        _presentation_net("signal", ("first", "second"), explicit_geometry_required=True),
        _presentation_net("signal", ("first", "second", "third")),
        _presentation_net("signal", ("third", "output")),
        _presentation_net("power", ("first", "second")),
        _presentation_net("reference", ("second", "third")),
    )
    for net in exempt_nets:
        plan.presentation_nets = (net,)
        assert semantic_composition_penalty_breakdown(plan, detached).local_signal_neighbor_gap == 0
    plan.presentation_nets = (_presentation_net("signal", ("first", "second")),)
    assert semantic_composition_penalty_breakdown(plan, detached).local_signal_neighbor_gap > 0


def test_local_label_gap_is_net_name_order_and_duplicate_invariant() -> None:
    first = _block("alpha", "filter")
    second = _block("beta", "amplifier")
    placed = _packing(_placed(first, 0), _placed(second, 11 * PITCH))
    plan = _plan((first, second))
    pair = _presentation_net("signal", ("alpha", "beta"))
    plan.presentation_nets = (pair,)
    original = semantic_composition_penalty_breakdown(plan, placed).local_signal_neighbor_gap

    renamed_first = _block("renamed-a", "filter")
    renamed_second = _block("renamed-b", "amplifier")
    renamed_placed = _packing(
        _placed(renamed_second, 11 * PITCH),
        _placed(renamed_first, 0),
    )
    renamed_plan = _plan((renamed_second, renamed_first))
    reversed_net = _presentation_net("signal", ("renamed-b", "renamed-a"))
    renamed_plan.presentation_nets = (reversed_net, reversed_net)
    assert original == 8
    assert (
        semantic_composition_penalty_breakdown(
            renamed_plan, renamed_placed
        ).local_signal_neighbor_gap
        == original
    )


def test_page_balance_precedes_area_within_compactness_tier() -> None:
    first = _block("first")
    second = _block("second")
    layout = _packing(_placed(first, 2 * PITCH), _placed(second, 12 * PITCH))
    area, edge_bias, imbalance = compactness_whitespace_penalties(layout)
    key = composition_candidate_key(_plan((first, second)), layout, (100, 100, 1, 0, 0, 0))
    assert key[-6:-3] == (edge_bias, area, imbalance)


def test_rigid_page_balance_uses_the_same_center_as_candidate_ranking() -> None:
    """The optional translation seed must optimize the ranking target."""
    from ai_kicad.m2_pack import (
        BOTTOM,
        LEFT,
        RIGHT,
        TOP,
        Packing,
        PlacedFragment,
        _centroid_balanced_packing,
    )

    block = _block("ordinary-stage")
    envelope = (
        LEFT + 10 * PITCH,
        TOP + 10 * PITCH,
        LEFT + 16 * PITCH,
        TOP + 14 * PITCH,
    )
    fragment = SimpleNamespace(
        block=block,
        envelope=envelope,
        content_envelope=envelope,
        ports=(),
        reservations=(),
        gateways=(),
        occupied_geometry=(),
    )
    initial = Packing(
        (PlacedFragment(fragment, (0, 0), envelope, (), envelope),),
        (),
    )
    balanced = _centroid_balanced_packing(initial)
    assert balanced is not None
    assert balanced.attempts[-1] == "centroid-balanced-page"

    initial_score = compactness_whitespace_penalties(initial)
    balanced_score = compactness_whitespace_penalties(balanced)
    assert balanced_score[0] == initial_score[0]
    assert balanced_score[1] < initial_score[1]
    assert balanced_score[2] < initial_score[2]

    content = balanced.fragments[0].content_envelope
    assert content is not None
    assert abs((content[0] + content[2]) // 2 - (LEFT + RIGHT) // 2) <= PITCH
    assert abs((content[1] + content[3]) // 2 - (TOP + BOTTOM) // 2) <= PITCH


def test_page_rank_prefers_the_physical_envelope_center() -> None:
    from ai_kicad.m2_pack import BOTTOM, LEFT, RIGHT, TOP

    block = _block("stage")
    width = 5 * PITCH
    height = 5 * PITCH
    centered_x = (LEFT + RIGHT - width) // 2
    centered_y = (TOP + BOTTOM - height) // 2
    centered = _packing(_placed(block, centered_x, centered_y, width, height))
    displaced = _packing(_placed(block, centered_x + 4 * PITCH, centered_y, width, height))
    centered_metrics = compactness_whitespace_penalties(centered)
    displaced_metrics = compactness_whitespace_penalties(displaced)
    assert centered_metrics[1] == 0
    assert centered_metrics[1] < displaced_metrics[1]
    assert centered_metrics[0] == displaced_metrics[0]


def test_equal_semantics_prefers_readable_low_bend_routing_over_shorter_maze() -> None:
    """Prioritize route clarity only after proving the same semantic layout."""
    first = _block("functional-stage", "filter", ("signal_in", "signal_out"))
    layout = _packing(_placed(first, 2 * PITCH, 2 * PITCH))
    plan = _plan((first,))

    readable = composition_candidate_key(plan, layout, (180, 180, 2, 1, 0, 0))
    short_but_turny = composition_candidate_key(plan, layout, (95, 95, 7, 1, 0, 0))
    assert readable < short_but_turny

    # With equal bend count the shorter proof remains preferable.
    equally_straight_shorter = composition_candidate_key(plan, layout, (95, 95, 2, 1, 0, 0))
    assert equally_straight_shorter < readable


def test_route_backtracking_penalty_detects_axis_reversal_without_external_oracle():
    from types import SimpleNamespace
    from ai_kicad.m2_composition_candidate_rank import route_backtracking_penalty

    def route(segments):
        return SimpleNamespace(geometry_signature=segments)

    direct = route((((0, 0), (10, 0)), ((10, 0), (10, 10))))
    detour = route((((0, 0), (0, 10)), ((0, 10), (10, 10)), ((10, 0), (10, 10))))
    assert route_backtracking_penalty((direct,)) == 0
    assert route_backtracking_penalty((detour,)) == 1
    assert route_backtracking_penalty((detour, direct)) == 1


def test_route_backtracking_penalty_separates_equally_semantic_candidates():
    from types import SimpleNamespace

    plan = _plan(())
    packing = SimpleNamespace(fragments=())
    routing = (1000, 500, 1, 1.0, 0, 0)
    assert composition_candidate_key(plan, packing, routing, routing_backtracking=0) < (
        composition_candidate_key(plan, packing, routing, routing_backtracking=1)
    )


def test_serial_row_exempts_explicit_signal_stage_before_fanout() -> None:
    """The fanout junction is not forced onto its upstream stage row."""
    first = _block("first", "filter", ("signal_in", "signal_out"))
    branch = _block("branch", "filter", ("signal_in", "signal_out"))
    upper = _block("upper", "filter", ("signal_in", "signal_out"))
    lower = _block("lower", "filter", ("signal_in", "signal_out"))
    edges = (
        _edge("signal", "first", "branch", "entry"),
        _edge("branch", "branch", "upper", "split"),
        _edge("branch", "branch", "lower", "split"),
    )
    placed = _packing(
        _placed(first, 0),
        _placed(branch, 4 * PITCH, 3 * PITCH),
        _placed(upper, 8 * PITCH),
        _placed(lower, 8 * PITCH, 6 * PITCH),
    )
    for blocks, relations in (
        ((first, branch, upper, lower), edges),
        ((lower, upper, branch, first), tuple(reversed(edges))),
    ):
        score = semantic_composition_penalty_breakdown(_plan(blocks, relations), placed)
        assert score.sequential_stage_row_drift == 0
        assert score.stage_order_violations == 0


def test_serial_row_exempts_explicit_signal_stage_after_convergence() -> None:
    """A multi-input merge need not share its downstream stage row."""
    upper = _block("upper", "filter", ("signal_in", "signal_out"))
    lower = _block("lower", "filter", ("signal_in", "signal_out"))
    merge = _block("merge", "filter", ("signal_in", "signal_out"))
    tail = _block("tail", "filter", ("signal_in", "signal_out"))
    edges = (
        _edge("signal", "upper", "merge", "upper"),
        _edge("signal", "lower", "merge", "lower"),
        _edge("signal", "merge", "tail", "out"),
    )
    placed = _packing(
        _placed(upper, 0),
        _placed(lower, 0, 6 * PITCH),
        _placed(merge, 4 * PITCH, 3 * PITCH),
        _placed(tail, 8 * PITCH),
    )
    for blocks, relations in (
        ((upper, lower, merge, tail), edges),
        ((tail, merge, lower, upper), tuple(reversed(edges))),
    ):
        score = semantic_composition_penalty_breakdown(_plan(blocks, relations), placed)
        assert score.sequential_stage_row_drift == 0
        assert score.stage_order_violations == 0


def test_precedence_only_repeated_chains_align_corresponding_stages() -> None:
    """Do not align unrelated chain depths just because their kinds match."""
    a0, a1, b0, b1 = (_block(name, "filter") for name in ("a0", "a1", "b0", "b1"))
    precedences = (
        SimpleNamespace(source_fragment="a0", target_fragment="a1", net="first"),
        SimpleNamespace(source_fragment="b0", target_fragment="b1", net="second"),
    )
    blocks = (a0, a1, b0, b1)
    aligned = _packing(
        _placed(a0, 0),
        _placed(a1, 8 * PITCH),
        _placed(b0, 0, 6 * PITCH),
        _placed(b1, 8 * PITCH, 6 * PITCH),
    )
    drifted = _packing(
        _placed(a0, 0),
        _placed(a1, 8 * PITCH),
        _placed(b0, 0, 6 * PITCH),
        _placed(b1, 10 * PITCH, 6 * PITCH),
    )
    plan = _plan(blocks, precedence=precedences)
    score = semantic_composition_penalty_breakdown(plan, aligned)
    assert score.repeated_alignment == 0
    assert semantic_composition_penalty_breakdown(plan, drifted).repeated_alignment == 2
    # Mixed representations and repeated declarations describe the same
    # structural roles. Neither may change repeated-stage alignment scores.
    mixed = _plan(
        tuple(reversed(blocks)),
        (
            _edge("signal", "a0", "a1", "first"),
            _edge("branch", "a0", "a1", "first"),
        ),
        tuple(reversed(precedences)),
    )
    assert semantic_composition_penalty_breakdown(mixed, aligned).repeated_alignment == 0
    assert semantic_composition_penalty_breakdown(mixed, drifted).repeated_alignment == 2


def test_inferred_passive_terminal_links_define_repeated_stage_context() -> None:
    """Only matched terminal-backed signal stages are repeated peers."""
    first = _block("stage-a", "filter", ("signal_out",))
    second = _block("stage-b", "filter", ("signal_out",))
    port_a = _block("port-a", "interface", ("passive",))
    port_b = _block("port-b", "interface", ("passive",))
    first.ports = (SimpleNamespace(role="signal_out", net="alpha"),)
    second.ports = (SimpleNamespace(role="signal_out", net="beta"),)
    port_a.ports = (SimpleNamespace(role="passive", net="alpha"),)
    port_b.ports = (SimpleNamespace(role="passive", net="beta"),)
    placed = _packing(
        _placed(first, 2 * PITCH, 2 * PITCH),
        _placed(second, 7 * PITCH, 7 * PITCH),
        _placed(port_a, 12 * PITCH, 2 * PITCH),
        _placed(port_b, 12 * PITCH, 7 * PITCH),
    )

    lone = _plan((first, second, port_a))
    paired = _plan((first, second, port_a, port_b))
    assert semantic_composition_penalty_breakdown(lone, placed).repeated_alignment == 0
    assert semantic_composition_penalty_breakdown(paired, placed).repeated_alignment == 5

    # An authored representation of one inferred link must not duplicate
    # incident context. Ordering and renaming the distinct nets are irrelevant.
    mixed = _plan(
        (port_b, second, port_a, first),
        (
            _edge("signal", "stage-a", "port-a", "alpha"),
            _edge("branch", "stage-a", "port-a", "alpha"),
        ),
    )
    assert semantic_composition_penalty_breakdown(mixed, placed).repeated_alignment == 5
    for port, stage in ((port_a, first), (port_b, second)):
        port.ports = (SimpleNamespace(role="passive", net=f"renamed-{stage.id}"),)
        stage.ports = (SimpleNamespace(role="signal_out", net=f"renamed-{stage.id}"),)
    renamed = _plan((port_b, port_a, second, first))
    assert semantic_composition_penalty_breakdown(renamed, placed).repeated_alignment == 5


def test_shared_passive_net_does_not_falsely_split_repeated_peers() -> None:
    """Ambiguous passive ownership is not evidence of a directed output."""
    first = _block("first", "filter", ("signal_out",))
    second = _block("second", "filter", ("signal_out",))
    terminal = _block("terminal", "interface", ("passive",))
    shared = _block("shared", "resistor", ("passive",))
    first.ports = (SimpleNamespace(role="signal_out", net="a"),)
    second.ports = (SimpleNamespace(role="signal_out", net="b"),)
    terminal.ports = (SimpleNamespace(role="passive", net="a"),)
    shared.ports = (SimpleNamespace(role="passive", net="a"),)
    placed = _packing(
        _placed(first, 0),
        _placed(second, 5 * PITCH, 5 * PITCH),
        _placed(terminal, 10 * PITCH),
        _placed(shared, 2 * PITCH),
    )
    plan = _plan((shared, second, terminal, first))
    assert semantic_composition_penalty_breakdown(plan, placed).repeated_alignment == 5


def test_parallel_output_frontiers_follow_their_own_signal_producers() -> None:
    """Unrelated rightmost producers must not displace another chain's output."""
    first = _block("first", "filter")
    second = _block("second", "filter")
    out_a = _block("out_a", "interface", ("signal_out",))
    out_b = _block("out_b", "interface", ("signal_out",))
    plan = _plan(
        (first, second, out_a, out_b),
        (
            _edge("signal", "first", "out_a", "a"),
            _edge("signal", "second", "out_b", "b"),
        ),
    )
    attached = _packing(
        _placed(first, 2 * PITCH),
        _placed(out_a, 4 * PITCH),
        _placed(second, 8 * PITCH, 5 * PITCH),
        _placed(out_b, 10 * PITCH, 5 * PITCH),
    )
    reversed_first = _packing(
        _placed(first, 2 * PITCH),
        _placed(out_a, 0),
        _placed(second, 8 * PITCH, 5 * PITCH),
        _placed(out_b, 10 * PITCH, 5 * PITCH),
    )
    proper = semantic_composition_penalty_breakdown(plan, attached)
    backward = semantic_composition_penalty_breakdown(plan, reversed_first)
    assert proper.frontier_distance == 0
    assert backward.frontier_distance == 2
    assert proper.interface_side_violations == 0
    assert backward.interface_side_violations == 1

    renamed = _plan(
        (out_b, second, out_a, first),
        (_edge("signal", "second", "out_b", "renamed_b"),
         _edge("signal", "first", "out_a", "renamed_a")),
    )
    assert semantic_composition_penalty_breakdown(renamed, attached) == proper


def test_single_output_still_prefers_global_page_frontier() -> None:
    """A lone output retains the established global edge preference."""
    producer = _block("producer", "filter")
    output = _block("output", "interface", ("signal_out",))
    unrelated = _block("unrelated", "filter")
    plan = _plan(
        (producer, unrelated, output),
        (_edge("signal", "producer", "output"),),
    )
    local = _packing(
        _placed(producer, 0),
        _placed(output, 2 * PITCH),
        _placed(unrelated, 8 * PITCH, 4 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, local).frontier_distance == 6
