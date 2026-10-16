"""Production composition ranking for unambiguous passive external interfaces."""

from types import SimpleNamespace

from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown
from ai_kicad.m2a import PITCH


def _block(block_id: str, kind: str, net: str, role: str):
    return SimpleNamespace(
        id=block_id,
        kind=kind,
        ports=(SimpleNamespace(net=net, role=role),),
    )


def _packing(*placements):
    fragments = []
    for block, x in placements:
        rect = (x, 0, x + PITCH, PITCH)
        fragments.append(
            SimpleNamespace(
                fragment=SimpleNamespace(block=block, positions={}),
                content_envelope=rect,
                envelope=rect,
                delta=(0, 0),
            )
        )
    return SimpleNamespace(fragments=tuple(fragments))


def _plan(*blocks):
    return SimpleNamespace(blocks=blocks, edges=(), precedence=())


def test_passive_output_interface_prefers_final_producer_right_frontier() -> None:
    producer = _block("producer", "active", "signal", "signal_out")
    terminal = _block("terminal", "interface", "signal", "passive")
    plan = _plan(producer, terminal)
    correct = semantic_composition_penalty_breakdown(
        plan, _packing((producer, 2 * PITCH), (terminal, 4 * PITCH))
    )
    reversed_output = semantic_composition_penalty_breakdown(
        plan, _packing((producer, 2 * PITCH), (terminal, 0))
    )
    assert correct.stage_order_violations == correct.interface_side_violations == 0
    assert reversed_output.stage_order_violations == 1
    assert reversed_output.interface_side_violations == 1


def test_passive_input_interface_prefers_first_consumer_left_frontier() -> None:
    terminal = _block("terminal", "interface", "signal", "passive")
    consumer = _block("consumer", "active", "signal", "signal_in")
    plan = _plan(terminal, consumer)
    correct = semantic_composition_penalty_breakdown(
        plan, _packing((terminal, 0), (consumer, 2 * PITCH))
    )
    reversed_input = semantic_composition_penalty_breakdown(
        plan, _packing((terminal, 4 * PITCH), (consumer, 2 * PITCH))
    )
    assert correct.stage_order_violations == correct.interface_side_violations == 0
    assert reversed_input.stage_order_violations == 1
    assert reversed_input.interface_side_violations == 1


def test_ambiguous_or_power_related_passive_interface_is_not_direction_guessed() -> None:
    terminal = _block("terminal", "interface", "net", "passive")
    first = _block("first", "active", "net", "signal_out")
    second = _block("second", "active", "net", "signal_out")
    ambiguous = semantic_composition_penalty_breakdown(
        _plan(terminal, first, second),
        _packing((terminal, 0), (first, 2 * PITCH), (second, 4 * PITCH)),
    )
    assert ambiguous.stage_order_violations == ambiguous.interface_side_violations == 0

    power = _block("supply", "utility", "net", "power_in")
    excluded = semantic_composition_penalty_breakdown(
        _plan(terminal, first, power),
        _packing((terminal, 0), (first, 2 * PITCH), (power, 4 * PITCH)),
    )
    assert excluded.stage_order_violations == excluded.interface_side_violations == 0


def test_passive_interface_direction_survives_renaming_and_declaration_order() -> None:
    first = _block("producer", "active", "a", "signal_out")
    output = _block("output", "interface", "a", "passive")
    renamed_first = _block("omega", "active", "renamed", "signal_out")
    renamed_output = _block("zeta", "interface", "renamed", "passive")
    original = semantic_composition_penalty_breakdown(
        _plan(first, output), _packing((first, 2 * PITCH), (output, 0))
    )
    renamed = semantic_composition_penalty_breakdown(
        _plan(renamed_output, renamed_first),
        _packing((renamed_first, 2 * PITCH), (renamed_output, 0)),
    )
    assert original.vector() == renamed.vector()
