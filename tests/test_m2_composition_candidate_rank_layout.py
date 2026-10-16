from types import SimpleNamespace

from m2_composition_candidate_rank_helpers import (
    _block,
    _edge,
    _packing,
    _placed,
    _plan,
)

from ai_kicad.m2_composition_candidate_rank import (
    compactness_whitespace_penalties,
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
)
from ai_kicad.m2a import PITCH


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
