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
):
    rect = (x, y, x + width, y + height)
    fragment = SimpleNamespace(block=block, positions=positions or {})
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
