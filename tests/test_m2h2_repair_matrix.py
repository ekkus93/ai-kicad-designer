"""Current-source repair and lower-bound coverage for M2h2 finalization."""

from __future__ import annotations

import json

import pytest

import ai_kicad.m2_compose as compose_module
from ai_kicad.ir import InputError
from ai_kicad.m2_compose import _reservation_growth_repack, compose_with_evidence
from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown
from ai_kicad.m2_conflicts import ConflictKind, TypedConflict
from ai_kicad.m2_fragments import (
    FragmentVariant,
    PortAnchor,
    _clear_nonpassive_text,
    fragment_variants,
)
from ai_kicad.m2_geometry import (
    Gateway,
    GeometryItem,
    Reservation,
    prove_reservation_allocation,
)
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
from ai_kicad.m2a import PITCH, ROOT, Asset, Pin, emit
from ai_kicad.m2b import Draft, assets, check_observed_layout, validate


def _load_interaction(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


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
        "source.port",
        "source",
        net,
        source_role,
        (("source", "1"),),
    )
    target_port = SemanticPort(
        "sink.port",
        "sink",
        net,
        target_role,
        (("sink", "1"),),
    )
    source = BlockPlan("source", "rc", (), frozenset(), (source_port,))
    sink = BlockPlan("sink", "rc", (), frozenset(), (target_port,))

    def fragment(
        block: BlockPlan,
        port: SemanticPort,
        long_wire: bool,
    ) -> FragmentVariant:
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

    if edge_kind is None:
        edges = ()
    else:
        edges = (SemanticEdge(edge_kind, "source", "sink", net, ("case",)),)

    presentation = PresentationNet(
        net,
        (("source", "1"), ("sink", "1")),
        ("source", "sink"),
        presentation_role,
        edge_kind is None,
        True,
        ("source",),
    )
    plan = SemanticPlan(
        (source, sink),
        edges,
        {},
        (),
        presentation_nets=(presentation,),
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
        _load_interaction("fixtures/m2h2/interaction/i2/internal_2.json"),
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
        repair_classes=(
            "reservation_growth",
            "gateway_access",
            "distribution_placement",
        ),
    )
    conflict.gateways = (gateway.id,)

    repaired, decision = _reservation_growth_repack(plan, seed, conflict, 0)
    before_state = tuple((item.fragment.id, item.delta) for item in seed.fragments)
    after_state = tuple((item.fragment.id, item.delta) for item in repaired.fragments)

    assert decision["net"] == net
    assert decision["gateway"] == gateway.id
    assert decision["growth_nm"] == PITCH
    assert "parseable routing tokens" in decision["witness"]
    assert after_state != before_state


def test_route_corridor_capacity_is_checked_before_candidate_acceptance() -> None:
    first = GeometryItem("route.RAIL.0", "wire", "tree.RAIL", (0, 0, 10, 0), ("RAIL",))
    duplicate = GeometryItem(
        "route.RAIL.1",
        "wire",
        "tree.RAIL",
        (0, 0, 10, 0),
        ("RAIL",),
    )
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
        _load_interaction("fixtures/m2h2/interaction/i3/a0_interleaved.json"),
        resolved,
    )
    _scene, evidence = compose_with_evidence(design, resolved)

    search = evidence["structural_search"]
    assert search["seed_count"] >= search["attempted_structure_count"]
    assert search["proved_structure_count"] >= 2
    assert all(seed["structure"] for seed in search["seeds"])
    assert all(seed["placement_class"] for seed in search["seeds"])

    selection = evidence["candidate_selection"]
    assert selection["proved_candidate_count"] >= 2
    assert selection["proved_structure_count"] >= 2
    assert all(candidate["structure"] for candidate in selection["proved_candidates"])
    assert any(attempt["result"] == "pass" for attempt in evidence["layout_attempts"])


def test_failure_exit_preserves_candidate_decisions_and_exact_failure_witness(
    monkeypatch,
) -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i2/internal_2.json"),
        resolved,
    )
    conflict = compose_module.ConductorLengthConflict("VREF", 250_000_001, 0, 250_000_001)

    def fail_candidate(*_args, **_kwargs):
        raise conflict

    monkeypatch.setattr(compose_module, "_assemble_candidate", fail_candidate)
    with pytest.raises(compose_module.LayoutBudgetError) as caught:
        compose_module.compose_with_evidence(design, resolved)

    evidence = caught.value.evidence
    rejected = [item for item in evidence["layout_attempts"] if item["result"] == "rejected"]
    assert rejected
    assert evidence["candidate_decisions"]
    assert all(decision["placements"] for decision in evidence["candidate_decisions"])
    assert evidence["failed_metric"] == str(conflict)
    assert evidence["budgets"]["complete_attempts_used"] == len(rejected)
    assert tuple(evidence["layout_attempts"]) == caught.value.attempts
    assert all(item["failure_class"] == conflict.kind for item in rejected)
    assert all(item["conflict"] == str(conflict) for item in rejected)
    assert all(item["net"] == "VREF" for item in rejected)
    assert all(item["actual"] == 250_000_001 for item in rejected)
    assert all(item["limit"] == 250_000_000 for item in rejected)


def test_obligation_certificate_exports_pre_emission_invariant_witnesses() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i2/internal_2.json"),
        resolved,
    )
    scene, evidence = compose_with_evidence(design, resolved)
    certificate = evidence["obligation_certificate"]

    owner_keys = [tuple(item["occurrence"]) for item in certificate["geometry_owners"]]
    assert len(owner_keys) == len(set(owner_keys)) == len(evidence["owners"])

    terminal_components = {
        tuple(entry[0])
        for proof in certificate["net_graph_witnesses"]
        for entry in proof["terminal_components"]
    }
    gateway_witnesses = certificate["gateway_witnesses"]
    assert certificate["terminal_inventory_count"] == len(terminal_components)
    for proof in certificate["net_graph_witnesses"]:
        assert proof["component_count"] >= 1
    for witness in gateway_witnesses:
        assert witness["proved"]
        assert witness["terminals"]

    left, top, right, bottom = certificate["final_content_envelope_nm"]
    canonical_lengths = certificate["canonical_lengths_nm"].values()
    assert right - left <= 210_000_000
    assert bottom - top <= 140_000_000
    assert all(length <= 250_000_000 for length in canonical_lengths)
    assert certificate["reservation_containment_pass"] is True
    assert certificate["reservation_allocation_count"] > 0
    assert certificate["no_unintended_dangling_endpoints"] is True
    assert certificate["no_cross_net_contacts"] is True
    assert certificate["no_unallocated_growth"] is True
    assert certificate["scene_geometry_sha256"] == scene.certificate_digest
    assert certificate["candidate_input_policy_sha256"] == scene.certificate_input_digest


def test_certificate_covers_required_net_graphs_and_placement_obligations() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i1/d2_b1.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    _scene, evidence = compose_with_evidence(design, resolved)
    certificate = evidence["obligation_certificate"]

    presentation_by_net = {item.id: item for item in plan.presentation_nets}
    graph_by_net = {item["net"]: item for item in certificate["net_graph_witnesses"]}
    assert set(graph_by_net) == set(presentation_by_net)
    for net, presentation in presentation_by_net.items():
        proof = graph_by_net[net]
        if presentation.explicit_geometry_required:
            assert proof["component_count"] == 1
        assert proof["canonical_length_nm"] <= 250_000_000

    placement_witness_count = len(certificate["placement_witnesses"])
    assert certificate["local_span_obligation_count"] == len(plan.local_spans)
    assert placement_witness_count == len(plan.precedence) + len(plan.local_spans)
    assert certificate["placement_witnesses"]
    for witness in certificate["placement_witnesses"]:
        assert len(witness) == 3


def test_certificate_exports_complete_semantic_obligation_inventory() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i1/d2_b1.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    _scene, evidence = compose_with_evidence(design, resolved)
    obligations = evidence["obligation_certificate"]["semantic_obligations"]

    exported_ports = {item["id"] for item in obligations["ports"]}
    expected_ports = {port.id for block in plan.blocks for port in block.ports}
    assert exported_ports == expected_ports

    exported_edges = [
        (item["kind"], item["source"], item["target"], item["net"], tuple(item["origins"]))
        for item in obligations["edges"]
    ]
    expected_edges = [
        (edge.kind, edge.source, edge.target, edge.net, edge.origins) for edge in plan.edges
    ]
    assert exported_edges == expected_edges

    exported_constraints = {item["id"] for item in obligations["constraints"]}
    exported_precedence = {item["id"] for item in obligations["precedence"]}
    exported_terminals = {tuple(item["terminal"]) for item in obligations["terminals"]}
    exported_nets = {item["id"] for item in obligations["presentation_nets"]}
    exported_spans = {item["id"] for item in obligations["local_spans"]}

    assert exported_constraints == {item.id for item in plan.constraints}
    assert exported_precedence == {item.id for item in plan.precedence}
    assert exported_terminals == {item.terminal for item in plan.terminals}
    assert exported_nets == {item.id for item in plan.presentation_nets}
    assert exported_spans == {item.id for item in plan.local_spans}
    assert len(obligations["terminals"]) == len(plan.terminals)
    assert len(obligations["precedence"]) == len(plan.precedence)
    assert len(obligations["local_spans"]) == len(plan.local_spans)


def test_failed_certificate_prevents_successful_schematic_emission(tmp_path) -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i2/internal_2.json"),
        resolved,
    )
    scene, _evidence = compose_with_evidence(design, resolved)
    scene.metrics["body_overlap_count"] = 1

    output = tmp_path / "stale_certificate"
    with pytest.raises(InputError, match="SCENE_CERTIFICATE_STALE"):
        emit(design, resolved, scene, output)
    assert not output.exists()


@pytest.mark.parametrize("degree", (1, 2, 3))
def test_external_signal_source_precedes_each_consumer_without_sibling_order(degree) -> None:
    resolved = assets()
    design = validate(
        _load_interaction(f"fixtures/m2h2/interaction/i1/d1_b{degree}.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    sources = [item for item in plan.precedence if item.source_fragment == "interface.input"]
    assert {item.source_terminal for item in sources} == {("input", "1")}
    assert {item.target_terminal for item in sources} == {
        (f"branch_{index}_r", "1") for index in range(1, degree + 1)
    }
    assert len(plan.precedence) == degree
    assert all(item.minimum_x_separation == 1 for item in sources)
    assert all(item.source_fragment.startswith("interface.") for item in plan.precedence)


def test_external_interface_on_internally_produced_net_is_not_a_signal_source() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i1/d2_b2.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    branch_edges = [
        item for item in plan.precedence if item.target_terminal[0].startswith("branch_")
    ]
    assert len(branch_edges) == 2
    assert {item.source_terminal for item in branch_edges} == {("prefix_1_r", "2")}
    assert not any(
        item.source_terminal[0].startswith("output_") or item.source_terminal[0] == "return"
        for item in plan.precedence
    )


def test_external_output_is_routed_for_internal_signal_fanout() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/development/dp1.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    assert {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.target.startswith("interface.")
    } == {("passive.a.series", "interface.out_a", "A")}
    assert {
        (item.source_fragment, item.target_fragment, item.net)
        for item in plan.precedence
        if item.target_fragment.startswith("interface.")
    } == {("passive.a.series", "interface.out_a", "A")}


def test_feedback_output_connectors_remain_directed_output_boundaries() -> None:
    from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations

    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i3/three_amplifier_one_band.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)

    output_relations = {
        ("function.pair.a", "interface.output_1", "OUTPUT_1"),
        ("function.pair.b", "interface.output_2", "OUTPUT_2"),
        ("function.single.a", "interface.output_3", "OUTPUT_3"),
    }
    assert {
        relation
        for relation in inferred_passive_interface_signal_relations(plan)
        if relation[1].startswith("interface.output_")
    } == output_relations
    assert not any(edge.target.startswith("interface.output_") for edge in plan.edges)
    assert not any(item.target_fragment.startswith("interface.output_") for item in plan.precedence)


def test_multi_output_frontier_retains_side_correct_structural_candidate() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i3/three_amplifier_one_band.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    candidates = pack_fragment_candidates(plan, variants)

    output_frontiers = [
        candidate
        for candidate in candidates
        if candidate.attempts[-1] in {"interface-frontier-output", "interface-frontier-combined"}
    ]
    assert output_frontiers
    assert (
        min(
            semantic_composition_penalty_breakdown(plan, candidate).interface_side_violations
            for candidate in output_frontiers
        )
        == 0
    )


def test_partial_beam_frontier_survives_when_distribution_repair_is_needed() -> None:
    """Keep a side-correct output move available to the route repair pass."""
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2blind_v6/ir/V6-3.json").read_text()),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    candidates = pack_fragment_candidates(plan, variants)

    output_frontiers = [
        candidate
        for candidate in candidates
        if candidate.attempts[0] == "partial-beam"
        and candidate.attempts[-1] == "interface-frontier-output"
    ]
    assert len(candidates) <= 8
    assert output_frontiers
    assert (
        semantic_composition_penalty_breakdown(plan, output_frontiers[0]).interface_side_violations
        == 0
    )


def test_multi_pin_interface_is_not_reclassified_as_a_single_output() -> None:
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2blind_v3/ir/V3-1.json").read_text()),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    assert not any(edge.target == "interface.interface" for edge in plan.edges)
    assert not any(item.target_fragment == "interface.interface" for item in plan.precedence)


def test_reference_and_supply_interfaces_do_not_create_signal_precedence() -> None:
    resolved = assets()
    design = validate(
        _load_interaction("fixtures/m2h2/interaction/i2/external_2.json"),
        resolved,
    )
    plan = semantic_plan(design, resolved)
    distributive = {net.id for net in plan.presentation_nets if net.role == "distributive"}
    assert not any(
        item.source_fragment.startswith("interface.") and item.net in distributive
        for item in plan.precedence
    )


@pytest.mark.parametrize("obstacle_kind", ["body", "label", "field"])
def test_required_field_slot_avoids_non_wire_obstacles(obstacle_kind):
    design = {
        "components": [
            {"id": "active", "refdes": "U1", "value": "Active", "asset": "Example:Active"},
            {"id": "support", "refdes": "C1", "value": "100n", "asset": "Device:C"},
        ]
    }
    resolved = {
        "Example:Active": Asset("Example:Active", "", {1: ()}, {1: (-PITCH, PITCH, PITCH, -PITCH)}),
        "Device:C": Asset("Device:C", "", {1: ()}, {1: (-PITCH, PITCH, PITCH, -PITCH)}),
    }
    initial = (50 * PITCH, 42 * PITCH)
    draft = Draft(
        design,
        resolved,
        {
            ("active", 1): (50 * PITCH, 50 * PITCH),
            ("support", 1): initial if obstacle_kind == "body" else (100 * PITCH, 100 * PITCH),
        },
        {},
        [],
        [],
        [("CONTROL", initial)] if obstacle_kind == "label" else [],
        [],
        {
            ("active", 1): initial,
            ("support", 1): initial if obstacle_kind == "field" else (120 * PITCH, 100 * PITCH),
        },
    )
    _clear_nonpassive_text(design, resolved, draft)
    assert draft.text_positions[("active", 1)] != initial
    assert draft.wires == []
    assert draft.positions[("active", 1)] == (50 * PITCH, 50 * PITCH)


def test_long_connector_text_keeps_clear_existing_slot_before_preferred_slot():
    existing = (50 * PITCH, 42 * PITCH)
    design = {
        "components": [
            {
                "id": "connector",
                "refdes": "J1",
                "value": "Long Input Label",
                "asset": "Connector_Generic:Conn_01x02",
            }
        ]
    }
    resolved = {
        "Connector_Generic:Conn_01x02": Asset(
            "Connector_Generic:Conn_01x02",
            "",
            {1: (Pin("1", "1", "passive", 5 * PITCH, 0),)},
            {1: (-PITCH // 2, -PITCH // 2, PITCH // 2, PITCH // 2)},
        )
    }
    draft = Draft(
        design,
        resolved,
        {("connector", 1): (50 * PITCH, 50 * PITCH)},
        {},
        [],
        [],
        [],
        [],
        {("connector", 1): existing},
    )

    _clear_nonpassive_text(design, resolved, draft)
    assert draft.text_positions[("connector", 1)] == existing


def test_short_connector_text_keeps_preferred_slot_ahead_of_existing_slot():
    existing = (50 * PITCH, 42 * PITCH)
    component = {
        "id": "connector",
        "refdes": "J1",
        "value": "Input",
        "asset": "Connector_Generic:Conn_01x02",
    }
    design = {"components": [component]}
    resolved = {
        component["asset"]: Asset(
            component["asset"],
            "",
            {1: (Pin("1", "1", "passive", 5 * PITCH, 0),)},
            {1: (-PITCH // 2, -PITCH // 2, PITCH // 2, PITCH // 2)},
        )
    }
    draft = Draft(
        design,
        resolved,
        {("connector", 1): (50 * PITCH, 50 * PITCH)},
        {},
        [],
        [],
        [],
        [],
        {("connector", 1): existing},
    )

    _clear_nonpassive_text(design, resolved, draft)
    assert draft.text_positions[("connector", 1)] == (42 * PITCH, 48 * PITCH)


@pytest.mark.parametrize("obstacle_kind", ["body", "label"])
def test_independent_observer_rejects_required_field_body_or_label_overlap(tmp_path, obstacle_kind):
    x, y = (50, 50) if obstacle_kind == "body" else (80, 30)
    schematic = tmp_path / "mutated.kicad_sch"
    schematic.write_text(
        "(kicad_sch "
        '(lib_symbols (symbol "Example:Block" '
        '(symbol "Block_1_1" (rectangle (start -1 1) (end 1 -1))))) '
        '(symbol (lib_id "Example:Block") (at 50 50 0) (unit 1) '
        f'(property "Reference" "U1" (at {x} {y} 0)) '
        '(property "Value" "Active" (at 80 32.54 0))))'
    )
    observed = {
        "labels": [("CONTROL", (80_000_000, 30_000_000))] if obstacle_kind == "label" else []
    }
    with pytest.raises(InputError, match="observed required field overlaps body/label"):
        check_observed_layout(schematic, observed, {})


def test_quality_selection_finishes_all_retained_seed_slots():
    design = validate(_load_interaction("fixtures/m2h2/interaction/i1/d1_b1.json"), assets())
    _, evidence = compose_with_evidence(design, assets())
    search = evidence["structural_search"]
    attempts = evidence["layout_attempts"]
    retained = min(8, search["seed_count"])
    assert {(item["seed"], item["round"]) for item in attempts} == {
        (seed, slot) for seed in range(retained) for slot in range(4)
    }
    candidates = evidence["candidate_selection"]["proved_candidates"]
    assert evidence["candidate_selection"]["selected_selection_key"] == min(
        item["selection_key"] for item in candidates
    )
    rejected = evidence["candidate_selection"]["best_rejected_candidate"]
    if len(candidates) > 1:
        assert rejected is not None
        assert rejected["selection_key"] == sorted(item["selection_key"] for item in candidates)[1]
    assert evidence["budgets"]["complete_attempts_used"] <= 32
