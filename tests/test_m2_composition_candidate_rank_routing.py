from types import SimpleNamespace

from m2_composition_candidate_rank_helpers import (
    _block,
    _edge,
    _packing,
    _placed,
    _plan,
)

from ai_kicad.m2_composition_candidate_rank import (
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
)
from ai_kicad.m2a import PITCH


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


def test_branch_arm_spread_breaks_routing_ties():
    plan = _plan(())
    packing = SimpleNamespace(fragments=())
    routing = (1000, 500, 1, 1.0, 0, 0)
    balanced = composition_candidate_key(
        plan, packing, routing, routing_backtracking=0, branch_arm_spread=0
    )
    uneven = composition_candidate_key(
        plan, packing, routing, routing_backtracking=0, branch_arm_spread=1
    )
    assert balanced < uneven


def test_observed_route_shape_precedes_length_and_bend_compactness() -> None:
    plan = _plan(())
    packing = SimpleNamespace(fragments=())
    compact = (80, 50, 2, 1.0, 0, 0)
    longer = (120, 70, 4, 1.0, 1, 0)

    clear_route = composition_candidate_key(
        plan,
        packing,
        compact,
        routing_u_shaped_detours=0,
        routing_branch_inconsistency=0,
    )
    detoured_route = composition_candidate_key(
        plan,
        packing,
        longer,
        routing_u_shaped_detours=1,
        routing_branch_inconsistency=0,
    )
    inconsistent_fanout = composition_candidate_key(
        plan,
        packing,
        longer,
        routing_u_shaped_detours=0,
        routing_branch_inconsistency=1,
    )

    assert clear_route < detoured_route
    assert clear_route < inconsistent_fanout


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
        (
            _edge("signal", "second", "out_b", "renamed_b"),
            _edge("signal", "first", "out_a", "renamed_a"),
        ),
    )
    assert semantic_composition_penalty_breakdown(renamed, attached) == proper


def test_interface_side_ranking_uses_rendered_occurrence_centers() -> None:
    """Envelope centers can misstate the side of a multi-occurrence stage."""
    producer = _block("producer", "filter")
    producer.occurrences = frozenset({("stage", 1)})
    output = _block("output", "interface", ("signal_out",))
    output.occurrences = frozenset({("connector", 1)})
    plan = _plan(
        (producer, output),
        (_edge("signal", "producer", "output"),),
    )
    placed = _packing(
        _placed(
            producer,
            100,
            width=10,
            text_positions={("stage", 1): (0, 0)},
        ),
        _placed(
            output,
            0,
            width=10,
            text_positions={("connector", 1): (200, 0)},
        ),
    )

    assert semantic_composition_penalty_breakdown(plan, placed).interface_side_violations == 0


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


def test_material_output_row_dislocation_precedes_route_backtracking() -> None:
    """A >80 mm disconnected output row outweighs a small return-leg gain."""
    from ai_kicad.m2_route import MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE

    producer = _block("producer", "filter")
    output = _block("output", "interface", ("signal_out",))
    plan = _plan((producer, output), (_edge("signal", "producer", "output"),))
    aligned = _packing(_placed(producer, 0), _placed(output, 4 * PITCH))
    remote = _packing(
        _placed(producer, 0),
        _placed(output, 4 * PITCH, MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE + PITCH),
    )
    aligned_score = semantic_composition_penalty_breakdown(plan, aligned)
    remote_score = semantic_composition_penalty_breakdown(plan, remote)
    assert aligned_score.material_interface_row_dislocation == 0
    assert remote_score.material_interface_row_dislocation == 1
    assert aligned_score.interface_side_violations == remote_score.interface_side_violations == 0
    route_metrics = (100, 100, 1, 1.0, 0, 0)
    assert composition_candidate_key(
        plan, aligned, route_metrics, routing_backtracking=999
    ) < composition_candidate_key(plan, remote, route_metrics, routing_backtracking=0)

    # Under the existing 80 mm locality limit, route shape wins even over
    # a small row-alignment improvement, preserving prior priority semantics.
    near = _packing(_placed(producer, 0), _placed(output, 4 * PITCH, PITCH))
    assert (
        semantic_composition_penalty_breakdown(plan, near).material_interface_row_dislocation == 0
    )
    assert composition_candidate_key(
        plan, near, route_metrics, routing_backtracking=0
    ) < composition_candidate_key(plan, aligned, route_metrics, routing_backtracking=1)


def test_material_dislocation_keeps_wrong_side_and_renaming_invariants() -> None:
    from ai_kicad.m2_route import MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE

    first = _block("source")
    second = _block("other")
    first_output = _block("output_a", "interface", ("signal_out",))
    second_output = _block("output_b", "interface", ("signal_out",))
    relations = (
        _edge("signal", "source", "output_a", "a"),
        _edge("signal", "other", "output_b", "b"),
    )
    plan = _plan((first, second, first_output, second_output), relations)
    distant = _packing(
        _placed(first, 0),
        _placed(first_output, 4 * PITCH, MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE + PITCH),
        _placed(second, 6 * PITCH, 3 * PITCH),
        _placed(second_output, 10 * PITCH, 3 * PITCH),
    )
    breakdown = semantic_composition_penalty_breakdown(plan, distant)
    assert breakdown.material_interface_row_dislocation == 1
    renamed = _plan(
        (second_output, first_output, second, first),
        (
            _edge("signal", "other", "output_b", "renamed_b"),
            _edge("signal", "source", "output_a", "renamed_a"),
        ),
    )
    assert semantic_composition_penalty_breakdown(renamed, distant) == breakdown
    wrong_side = _packing(
        _placed(first, 0),
        _placed(first_output, -2 * PITCH),
        _placed(second, 6 * PITCH, 3 * PITCH),
        _placed(second_output, 10 * PITCH, 3 * PITCH),
    )
    metrics = (100, 100, 1, 1.0, 0, 0)
    assert composition_candidate_key(
        plan, distant, metrics, routing_backtracking=999
    ) < composition_candidate_key(plan, wrong_side, metrics, routing_backtracking=0)


def test_two_independent_output_chains_prefer_producer_owned_rows() -> None:
    from ai_kicad.m2_composition_candidate_rank import _independent_output_owner_row_drift

    first = _block("stage-a", "filter")
    second = _block("stage-b", "filter")
    a = _block("interface-a", "interface", ("signal_out",))
    b = _block("interface-b", "interface", ("signal_out",))
    edges = (
        _edge("signal", "stage-a", "interface-a", "net-a"),
        _edge("signal", "stage-b", "interface-b", "net-b"),
    )
    plan = _plan((first, second, a, b), edges)
    aligned = _packing(
        _placed(first, 0),
        _placed(a, 4 * PITCH),
        _placed(second, 8 * PITCH, 10 * PITCH),
        _placed(b, 12 * PITCH, 10 * PITCH),
    )
    detached = _packing(
        _placed(first, 0),
        _placed(a, 4 * PITCH, 5 * PITCH),
        _placed(second, 8 * PITCH, 10 * PITCH),
        _placed(b, 12 * PITCH, 5 * PITCH),
    )
    assert _independent_output_owner_row_drift(plan, aligned) == 0
    assert _independent_output_owner_row_drift(plan, detached) == 10
    routing = (1_000, 500, 2, 1.0, 0, 0)
    assert composition_candidate_key(
        plan, aligned, routing, routing_backtracking=100
    ) < composition_candidate_key(plan, detached, routing, routing_backtracking=0)

    renamed = _plan(
        (b, second, a, first),
        (
            _edge("signal", "stage-b", "interface-b", "new-z"),
            _edge("signal", "stage-a", "interface-a", "new-y"),
        ),
    )
    assert _independent_output_owner_row_drift(renamed, detached) == 10
    assert composition_candidate_key(renamed, detached, routing, routing_backtracking=0) == (
        composition_candidate_key(plan, detached, routing, routing_backtracking=0)
    )


def test_shared_producer_and_single_output_exempt_from_independent_row_priority() -> None:
    from ai_kicad.m2_composition_candidate_rank import _independent_output_owner_row_drift

    stage = _block("stage", "filter")
    a = _block("first", "interface", ("signal_out",))
    b = _block("second", "interface", ("signal_out",))
    shared = _plan(
        (stage, a, b),
        (
            _edge("branch", "stage", "first", "n"),
            _edge("branch", "stage", "second", "n"),
        ),
    )
    placed = _packing(
        _placed(stage, 0),
        _placed(a, 4 * PITCH),
        _placed(b, 4 * PITCH, 10 * PITCH),
    )
    assert _independent_output_owner_row_drift(shared, placed) == 0
    sole = _plan((stage, b), (_edge("signal", "stage", "second", "n"),))
    assert (
        _independent_output_owner_row_drift(
            sole, _packing(_placed(stage, 0), _placed(b, 4 * PITCH, 10 * PITCH))
        )
        == 0
    )

    ambiguous = _plan(
        (stage, a, b, _block("other", "filter")),
        (
            _edge("signal", "stage", "first", "n"),
            _edge("signal", "stage", "second", "n"),
            _edge("signal", "other", "second", "other-n"),
        ),
    )
    assert (
        _independent_output_owner_row_drift(
            ambiguous,
            _packing(
                _placed(stage, 0),
                _placed(a, 4 * PITCH),
                _placed(b, 4 * PITCH, 10 * PITCH),
                _placed(_block("other", "filter"), 8 * PITCH, 10 * PITCH),
            ),
        )
        == 0
    )


def test_route_geometry_cost_rejects_gross_detour_for_one_saved_bend() -> None:
    """One extra turn is preferable to an otherwise avoidable long wire."""
    stage = _block("stage", "filter", ("signal_in", "signal_out"))
    plan = _plan((stage,))
    packing = _packing(_placed(stage, 2 * PITCH, 2 * PITCH))
    # Both candidates have the same proved semantics and return-leg shape.
    short = composition_candidate_key(
        plan,
        packing,
        (100 * PITCH, 60 * PITCH, 5, 1.0, 0, 0),
        routing_backtracking=3,
    )
    long = composition_candidate_key(
        plan,
        packing,
        (121 * PITCH, 60 * PITCH, 4, 1.0, 1, 0),
        routing_backtracking=3,
    )
    assert short < long
    # A five-bend maze with only a small length saving still loses.
    turny = composition_candidate_key(
        plan,
        packing,
        (95 * PITCH, 60 * PITCH, 9, 1.0, 2, 0),
        routing_backtracking=3,
    )
    assert long < turny
    # Backtracking is still the higher-priority routing aesthetic.
    assert long < composition_candidate_key(
        plan,
        packing,
        (80 * PITCH, 60 * PITCH, 3, 1.0, 3, 0),
        routing_backtracking=4,
    )
