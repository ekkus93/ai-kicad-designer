"""Generic signal-row composition ranking controls; no fixture-specific dispatch."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import (
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
)


def _block(block_id: str, kind: str = "stage", roles: tuple[str, ...] = ()):
    return SimpleNamespace(
        id=block_id,
        kind=kind,
        ports=tuple(SimpleNamespace(role=role) for role in roles),
    )


def _edge(kind: str, source: str, target: str, net: str = "n"):
    return SimpleNamespace(kind=kind, source=source, target=target, net=net)


def _plan(blocks, edges=()):
    return SimpleNamespace(blocks=tuple(blocks), edges=tuple(edges), precedence=())


def _packing(*entries):
    return SimpleNamespace(
        fragments=tuple(
            SimpleNamespace(
                fragment=SimpleNamespace(block=block, positions={}),
                content_envelope=(x, y, x + PITCH, y + PITCH),
                envelope=(x, y, x + PITCH, y + PITCH),
                delta=(0, 0),
            )
            for block, x, y in entries
        )
    )


def _stage(name: str):
    return _block(name, "amplifier", ("signal_in", "signal_out"))


def test_serial_active_stages_prefer_one_signal_baseline() -> None:
    first, second, third = (_stage(name) for name in ("first", "second", "third"))
    plan = _plan(
        (first, second, third),
        (_edge("signal", "first", "second"), _edge("signal", "second", "third")),
    )
    aligned = _packing(
        (first, 0, 5 * PITCH),
        (second, 10 * PITCH, 5 * PITCH),
        (third, 20 * PITCH, 5 * PITCH),
    )
    drifting = _packing(
        (first, 0, 5 * PITCH),
        (second, 10 * PITCH, 8 * PITCH),
        (third, 20 * PITCH, 5 * PITCH),
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, drifting)
    assert good.sequential_stage_row_drift == 0
    assert bad.sequential_stage_row_drift == 6
    assert good.stage_order_violations == bad.stage_order_violations == 0
    assert good.vector()[-2:] == (0, 0)
    assert bad.as_dict()["sequential_stage_row_drift"] == 6


def test_branch_siblings_are_not_forced_to_one_signal_row() -> None:
    source, upper, lower = (_stage(name) for name in ("source", "upper", "lower"))
    plan = _plan(
        (source, upper, lower),
        (
            _edge("branch", "source", "upper", "fan"),
            _edge("branch", "source", "lower", "fan"),
        ),
    )
    packing = _packing(
        (source, 0, 5 * PITCH),
        (upper, 10 * PITCH, 0),
        (lower, 10 * PITCH, 10 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).sequential_stage_row_drift == 0


def test_converging_stages_are_not_forced_to_one_signal_row() -> None:
    upper, lower, sink = (_stage(name) for name in ("upper", "lower", "sink"))
    plan = _plan(
        (upper, lower, sink),
        (_edge("signal", "upper", "sink"), _edge("signal", "lower", "sink")),
    )
    packing = _packing(
        (upper, 0, 0),
        (lower, 0, 10 * PITCH),
        (sink, 10 * PITCH, 5 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).sequential_stage_row_drift == 0


def test_feedback_and_power_edges_do_not_create_serial_signal_rows() -> None:
    source, target = (_stage(name) for name in ("source", "target"))
    plan = _plan(
        (source, target),
        (_edge("feedback", "source", "target"), _edge("power", "source", "target")),
    )
    packing = _packing((source, 0, 0), (target, 10 * PITCH, 10 * PITCH))
    assert semantic_composition_penalty_breakdown(plan, packing).sequential_stage_row_drift == 0


def test_input_and_output_interfaces_prefer_their_stage_rows() -> None:
    input_block = _block("input", "interface", ("signal_in",))
    stage = _stage("stage")
    output_block = _block("output", "interface", ("signal_out",))
    plan = _plan(
        (input_block, stage, output_block),
        (_edge("signal", "input", "stage"), _edge("signal", "stage", "output")),
    )
    aligned = _packing(
        (input_block, 0, 5 * PITCH),
        (stage, 10 * PITCH, 5 * PITCH),
        (output_block, 20 * PITCH, 5 * PITCH),
    )
    misaligned = _packing(
        (input_block, 0, 2 * PITCH),
        (stage, 10 * PITCH, 5 * PITCH),
        (output_block, 20 * PITCH, 8 * PITCH),
    )
    good = semantic_composition_penalty_breakdown(plan, aligned)
    bad = semantic_composition_penalty_breakdown(plan, misaligned)
    assert good.directed_interface_row_drift == 0
    assert bad.directed_interface_row_drift == 6
    assert good.stage_order_violations == bad.stage_order_violations == 0


def test_fanout_interface_only_needs_one_connected_signal_row() -> None:
    input_block = _block("input", "interface", ("signal_in",))
    upper, lower = (_stage(name) for name in ("upper", "lower"))
    plan = _plan(
        (input_block, upper, lower),
        (_edge("signal", "input", "upper"), _edge("signal", "input", "lower")),
    )
    packing = _packing(
        (input_block, 0, 0),
        (upper, 10 * PITCH, 0),
        (lower, 10 * PITCH, 10 * PITCH),
    )
    assert semantic_composition_penalty_breakdown(plan, packing).directed_interface_row_drift == 0


def test_ambiguous_bidirectional_interface_has_no_row_preference() -> None:
    interface = _block("io", "interface", ("signal_in", "signal_out"))
    stage = _stage("stage")
    plan = _plan((interface, stage), (_edge("signal", "io", "stage"),))
    packing = _packing((interface, 0, 20 * PITCH), (stage, 10 * PITCH, 0))
    assert semantic_composition_penalty_breakdown(plan, packing).directed_interface_row_drift == 0


def test_power_interface_does_not_get_signal_row_penalty() -> None:
    power = _block("power", "interface", ("power_in",))
    stage = _stage("stage")
    plan = _plan((power, stage), (_edge("power", "power", "stage"),))
    packing = _packing((power, 0, 20 * PITCH), (stage, 10 * PITCH, 0))
    assert semantic_composition_penalty_breakdown(plan, packing).directed_interface_row_drift == 0


def test_signal_row_scores_are_permutation_and_net_rename_invariant() -> None:
    first, second = (_stage(name) for name in ("first", "second"))
    plan = _plan((first, second), (_edge("signal", "first", "second", "original"),))
    equivalent = _plan(
        (second, first),
        (
            _edge("signal", "first", "second", "renamed"),
            _edge("signal", "first", "second", "renamed"),
        ),
    )
    packing = _packing((first, 0, 0), (second, 10 * PITCH, 3 * PITCH))
    left = semantic_composition_penalty_breakdown(plan, packing)
    right = semantic_composition_penalty_breakdown(equivalent, packing)
    assert left.sequential_stage_row_drift == right.sequential_stage_row_drift == 3
    assert left.directed_interface_row_drift == right.directed_interface_row_drift == 0


def test_signal_flow_order_outranks_row_alignment() -> None:
    first, second = (_stage(name) for name in ("first", "second"))
    plan = _plan((first, second), (_edge("signal", "first", "second"),))
    ordered = _packing((first, 0, 0), (second, 10 * PITCH, 3 * PITCH))
    reversed_placement = _packing((first, 10 * PITCH, 0), (second, 0, 0))
    assert composition_candidate_key(plan, ordered, (100, 100, 10, 0, 0, 0)) < (
        composition_candidate_key(plan, reversed_placement, (1, 1, 0, 0, 0, 0))
    )
