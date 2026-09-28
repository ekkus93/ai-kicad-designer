"""Current-source repair and lower-bound coverage for M2h2 finalization."""

from __future__ import annotations

import json

import pytest

from ai_kicad.m2_conflicts import ConflictKind, TypedConflict
from ai_kicad.m2_fragments import FragmentVariant, PortAnchor, fragment_variants
from ai_kicad.m2a import PITCH, ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import _reservation_growth_repack, compose_with_evidence
from ai_kicad.m2_geometry import Gateway, GeometryItem, Reservation, prove_reservation_allocation
from ai_kicad.m2_pack import _place, pack_fragment_candidates
from ai_kicad.m2_route import RouteLengthBoundConflict, route_between_fragments
from ai_kicad.m2_semantics import (
    BlockPlan,
    PresentationNet,
    SemanticEdge,
    SemanticPlan,
    SemanticPort,
    semantic_plan,
)


def _role_bound_plan(
    *,
    edge_kind: str | None,
    source_role: str,
    target_role: str,
    presentation_role: str,
) -> tuple[SemanticPlan, tuple]:
    """Build a tiny two-fragment case with an impossible fixed conductor union."""
    net = "RAIL"
    source_port = SemanticPort(
        "source.port", "source", net, source_role, (("source", "1"),)
    )
    target_port = SemanticPort("sink.port", "sink", net, target_role, (("sink", "1"),))
    source = BlockPlan("source", "rc", (), frozenset(), (source_port,))
    sink = BlockPlan("sink", "rc", (), frozenset(), (target_port,))

    def fragment(block: BlockPlan, port: SemanticPort, long_wire: bool) -> FragmentVariant:
        gateway = Gateway(
            port.id,
            net,
            port.terminals,
            f"{block.id}:{net}",
            (0, 0),
            "up",
            ((0, 0), (0, -PITCH)),
            frozenset({"up"}),
            (),
        )
        wires = (((0, 0), (251_000_000, 0)),) if long_wire else ()
        return FragmentVariant(
            f"{block.id}.v0",
            block,
            {},
            {},
            {},
            wires,
            (net,) * len(wires),
            (),
            (),
            (PortAnchor(port, gateway.point, "up"),),
            (0, -2 * PITCH, 10 * PITCH, 2 * PITCH),
            frozenset(),
            gateways=(gateway,),
            wire_provenance=tuple(("local-long",) for _ in wires),
        )

    edge = (
        ()
        if edge_kind is None
        else (SemanticEdge(edge_kind, "source", "sink", net, ("case",)),)
    )
    plan = SemanticPlan(
        (source, sink),
        edge,
        {},
        (),
        presentation_nets=(
            PresentationNet(
                net,
                (("source", "1"), ("sink", "1")),
                ("source", "sink"),
                presentation_role,
                edge_kind is None,
                True,
                ("source",),
            ),
        ),
    )
    placed = (
        _place(fragment(source, source_port, True), 20 * PITCH, 30 * PITCH),
        _place(fragment(sink, target_port, False), 50 * PITCH, 30 * PITCH),
    )
    return plan, placed


@pytest.mark.parametrize(
    ("case_name", "edge_kind", "source_role", "target_role", "presentation_role"),
    (
        ("signal", "signal", "signal_out", "signal_in", "signal"),
        ("power", "power", "power_out", "power_in", "distributive"),
        ("branch", "branch", "signal_out", "passive", "distributive"),
        ("reference", None, "reference", "reference", "distributive"),
        ("support", None, "passive", "passive", "distributive"),
        ("shared_control", None, "passive", "passive", "distributive"),
    ),
)
def test_canonical_length_lower_bound_applies_to_every_m2h2_route_role(
    case_name: str,
    edge_kind: str | None,
    source_role: str,
    target_role: str,
    presentation_role: str,
) -> None:
    plan, placed = _role_bound_plan(
        edge_kind=edge_kind,
        source_role=source_role,
        target_role=target_role,
        presentation_role=presentation_role,
    )
    with pytest.raises(RouteLengthBoundConflict) as caught:
        route_between_fragments(plan, placed)
    assert caught.value.net == "RAIL"
    assert caught.value.lower_bound > caught.value.limit == 250_000_000
    assert case_name


@pytest.mark.parametrize(
    "category",
    (
        ConflictKind.RESERVATION,
        ConflictKind.COLLISION,
        ConflictKind.NET_CONNECTIVITY,
        ConflictKind.DANGLING_ENDPOINT,
    ),
)
def test_typed_growth_repairs_use_conflict_fields_for_remaining_categories(
    category: ConflictKind,
) -> None:
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2h2/interaction/i2/internal_2.json").read_text()),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    seed = pack_fragment_candidates(plan, variants)[0]
    net = next(item.id for item in plan.presentation_nets if item.internally_generated)
    gateway = next(item for placed in seed.fragments for item in placed.gateways if item.net == net)
    conflict = TypedConflict(
        category,
        f"opaque {category.value} diagnostic without parseable routing tokens",
        net=net,
        owners=(gateway.island.split(":", 1)[0],),
        offending_geometry=(
            (gateway.point[0], gateway.point[1], gateway.point[0], gateway.point[1]),
        ),
        repair_classes=("reservation_growth", "gateway_access", "distribution_placement"),
    )
    conflict.gateways = (gateway.id,)

    repaired, decision = _reservation_growth_repack(plan, seed, conflict, 0)

    assert decision["net"] == net
    assert decision["gateway"] == gateway.id
    assert decision["growth_nm"] == PITCH
    assert "parseable routing tokens" in decision["witness"]
    assert tuple((item.fragment.id, item.delta) for item in repaired.fragments) != tuple(
        (item.fragment.id, item.delta) for item in seed.fragments
    )


def test_route_corridor_capacity_is_checked_before_candidate_acceptance() -> None:
    first = GeometryItem("route.RAIL.0", "wire", "tree.RAIL", (0, 0, 10, 0), ("RAIL",))
    duplicate = GeometryItem("route.RAIL.1", "wire", "tree.RAIL", (0, 0, 10, 0), ("RAIL",))
    corridor = Reservation(
        "route.RAIL.0",
        "channel",
        "tree.RAIL",
        "global_route",
        (0, -1, 10, 1),
        "RAIL",
        1,
    )

    assert prove_reservation_allocation((first,), (corridor,)) == (
        ("tree.RAIL", "route.RAIL.0", "route.RAIL.0"),
    )
    with pytest.raises(TypedConflict) as caught:
        prove_reservation_allocation((first, duplicate), (corridor,))
    assert caught.value.category == ConflictKind.RESERVATION
    assert caught.value.actual == 2
    assert caught.value.limit == 1


def test_composition_evidence_reports_structural_diversity_not_raw_attempt_count() -> None:
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2h2/interaction/i3/a0_interleaved.json").read_text()),
        resolved,
    )
    _scene, evidence = compose_with_evidence(design, resolved)

    search = evidence["structural_search"]
    assert search["seed_count"] >= search["attempted_structure_count"]
    assert search["proved_structure_count"] >= 2
    assert all(seed["structure"] and seed["placement_class"] for seed in search["seeds"])

    selection = evidence["candidate_selection"]
    assert selection["proved_candidate_count"] >= 2
    assert selection["proved_structure_count"] >= 2
    assert all(candidate["structure"] for candidate in selection["proved_candidates"])
    assert any(attempt["result"] == "pass" for attempt in evidence["layout_attempts"])
