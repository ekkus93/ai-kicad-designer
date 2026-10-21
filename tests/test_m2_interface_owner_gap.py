"""Verify nearest signal-owner spacing without case-specific layout rules."""

from types import SimpleNamespace

from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown
from ai_kicad.m2a import PITCH


def _block(identifier, kind, *roles):
    ports = tuple(SimpleNamespace(role=role) for role in roles)
    return SimpleNamespace(id=identifier, kind=kind, ports=ports)


def _plan(blocks, edges):
    return SimpleNamespace(blocks=blocks, edges=edges, precedence=())


def _edge(source, target, net):
    return SimpleNamespace(source=source, target=target, net=net, kind="signal")


def _packing(*items):
    parts = []
    for block, x, y in items:
        rect = (x, y, x + PITCH, y + PITCH)
        parts.append(
            SimpleNamespace(
                fragment=SimpleNamespace(block=block, positions={}),
                envelope=rect,
                content_envelope=rect,
                delta=(x, y),
            )
        )
    return SimpleNamespace(fragments=tuple(parts))


def test_correct_side_input_gap_prefers_nearby_consumer():
    port = _block("in", "interface", "signal_in")
    stage = _block("filter", "filter", "signal_in", "signal_out")
    plan = _plan((port, stage), (_edge("in", "filter", "in_net"),))
    close = semantic_composition_penalty_breakdown(
        plan, _packing((port, 0, 0), (stage, 4 * PITCH, 0))
    )
    distant = semantic_composition_penalty_breakdown(
        plan, _packing((port, 0, 0), (stage, 18 * PITCH, 0))
    )
    assert close.interface_side_violations == distant.interface_side_violations == 0
    assert close.interface_owner_distance == distant.interface_owner_distance == 0
    assert close.local_signal_neighbor_gap == 1
    assert distant.local_signal_neighbor_gap == 15


def test_correct_side_output_gap_prefers_nearby_producer():
    stage = _block("filter", "filter", "signal_in", "signal_out")
    port = _block("out", "interface", "signal_out")
    plan = _plan((stage, port), (_edge("filter", "out", "out_net"),))
    close = _packing((stage, 0, 0), (port, 4 * PITCH, 0))
    distant = _packing((stage, 0, 0), (port, 18 * PITCH, 0))
    assert semantic_composition_penalty_breakdown(plan, close).local_signal_neighbor_gap == 1
    assert semantic_composition_penalty_breakdown(plan, distant).local_signal_neighbor_gap == 15


def test_fanout_uses_nearest_owner_once():
    port = _block("in", "interface", "signal_in")
    near = _block("near", "filter")
    far = _block("far", "filter")
    plan = _plan(
        (far, port, near),
        (
            _edge("in", "far", "far_net"),
            _edge("in", "near", "near_net"),
            _edge("in", "near", "near_net"),
        ),
    )
    packed = _packing((port, 0, 0), (near, 4 * PITCH, 0), (far, 17 * PITCH, 8 * PITCH))
    assert semantic_composition_penalty_breakdown(plan, packed).local_signal_neighbor_gap == 1


def test_bidirectional_and_power_only_interfaces_are_exempt():
    port = _block("shared", "interface", "signal_in", "signal_out")
    power = _block("power", "interface", "power_in")
    stage = _block("stage", "filter")
    edges = (
        _edge("shared", "stage", "forward"),
        _edge("stage", "shared", "return"),
        SimpleNamespace(kind="power", source="power", target="stage", net="rail"),
    )
    plan = _plan((port, power, stage), edges)
    packed = _packing((port, 0, 0), (stage, 18 * PITCH, 0), (power, 25 * PITCH, 0))
    assert semantic_composition_penalty_breakdown(plan, packed).interface_owner_distance == 0


def test_soft_gap_does_not_outrank_functional_fragmentation():
    port = _block("input", "interface", "signal_in")
    stage = _block("owner", "filter", "signal_in", "signal_out")
    plan = _plan((port, stage), (_edge("input", "owner", "path"),))

    def score(stage_x, extra_span):
        packed = _packing((port, 0, 0), (stage, stage_x, 0))
        members = list(packed.fragments)
        base = members[1]
        # The functional cell's measured local symbol positions may be
        # fragmented even when its enclosing placement remains unchanged.
        members[1] = SimpleNamespace(
            fragment=SimpleNamespace(
                block=stage,
                positions={("u", 1): (0, 0), ("v", 1): (extra_span, 0)},
            ),
            envelope=base.envelope,
            content_envelope=base.content_envelope,
            delta=base.delta,
        )
        return semantic_composition_penalty_breakdown(
            plan, SimpleNamespace(fragments=tuple(members))
        )

    compact_but_distant = score(18 * PITCH, 0)
    fragmented_but_near = score(4 * PITCH, 5 * PITCH)
    assert compact_but_distant.interface_owner_distance == 0
    assert fragmented_but_near.interface_owner_distance == 0
    assert (
        compact_but_distant.local_signal_neighbor_gap
        > fragmented_but_near.local_signal_neighbor_gap
    )
    assert compact_but_distant.intra_block_dispersion < fragmented_but_near.intra_block_dispersion
    assert compact_but_distant.vector() < fragmented_but_near.vector()
