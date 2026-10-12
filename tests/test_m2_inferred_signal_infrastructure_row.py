"""Inferred signal flow must determine the primary row for power separation."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown


def _block(name, kind, *ports):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=tuple(SimpleNamespace(role=role, net=net) for role, net in ports),
    )


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


def _plan(interface_port_role="passive", stage_port_role="signal_in"):
    connector = _block("connector", "interface", (interface_port_role, "signal"))
    stage = _block("stage", "filter", (stage_port_role, "signal"))
    rail = _block("rail", "infrastructure")
    power_edge = SimpleNamespace(kind="power", source="stage", target="rail", net="vcc")
    return SimpleNamespace(blocks=(connector, stage, rail), edges=(power_edge,), precedence=())


def _score(plan, rail_row):
    connector, stage, rail = plan.blocks
    return semantic_composition_penalty_breakdown(
        plan,
        _packing(
            (connector, 0, 5 * PITCH),
            (stage, 6 * PITCH, 5 * PITCH),
            (rail, 12 * PITCH, rail_row * PITCH),
        ),
    )


def test_terminal_inferred_primary_signal_row_keeps_power_away():
    plan = _plan()
    intruding = _score(plan, 5)
    separate = _score(plan, 12)
    assert intruding.stage_order_violations == separate.stage_order_violations == 0
    assert intruding.infrastructure_primary_row_intrusion == 2
    assert separate.infrastructure_primary_row_intrusion == 0
    assert intruding.vector() > separate.vector()


def test_reference_only_terminal_does_not_define_primary_signal_row():
    plan = _plan(stage_port_role="reference")
    assert _score(plan, 5).infrastructure_primary_row_intrusion == 0
    assert _score(plan, 12).infrastructure_primary_row_intrusion == 0
