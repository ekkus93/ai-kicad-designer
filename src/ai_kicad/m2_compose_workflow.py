"""Implementation details for m2 compose workflow."""

from __future__ import annotations

from collections import Counter

from .ir import InputError
from .m2_compose_candidate import (
    LayoutBudgetError,
    _missing_interface_output_routes,
    _missing_optional_reference_routes,
    _route_interface_enclosure_count,
    _structural_signature,
)
from .m2_compose_failure import _layout_failure_evidence
from .m2_compose_repairs import (
    ConductorLengthConflict,
    _distribution_repack,
    _reservation_growth_repack,
    _structural_repack,
    _substitution_repack,
)
from .m2_composition_candidate_rank import (
    compactness_whitespace_penalties,
    composition_candidate_key,
    route_backtracking_penalty,
    route_branch_arm_spread,
    semantic_composition_penalties,
    semantic_composition_penalty_breakdown,
)
from .m2_composition_qualification_observation import observe_composition_packing_envelopes
from .m2_conflicts import ConflictKind, TypedConflict
from .m2_fragments import fragment_variants
from .m2_pack import (
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    _worksheet_clearance_packing,
    pack_fragment_candidates,
)
from .m2_route import (
    RouteBlockedConflict,
)
from .m2_routing_composition_observer import measure_routing_readability
from .m2_semantics import PlacementConflict, semantic_plan
from .m2a import PITCH, Scene, certify_scene_geometry, certify_scene_inputs


def _candidate_observer_priority(observed_composition) -> tuple[int, int, int]:
    """Keep observer failures ahead of routing-quality tie-breaks."""
    return (
        observed_composition.primary_stage_order_inversions,
        observed_composition.input_side_violations,
        observed_composition.output_side_violations,
    )


def compose_with_evidence(design: dict, resolved: dict) -> tuple[Scene, dict]:
    """Compose using at most eight seeds and four attempts per seed."""
    from . import m2_compose as facade

    plan = semantic_plan(design, resolved)
    block_kind = {block.id: block.kind for block in plan.blocks}
    external_output_nets = {
        obligation.net
        for obligation in plan.precedence
        if block_kind.get(obligation.source_fragment) != "interface"
        and block_kind.get(obligation.target_fragment) == "interface"
    }
    variants = fragment_variants(design, resolved, plan)
    seeds = pack_fragment_candidates(plan, variants)
    attempts = []
    proved_candidates = []
    proved_structures = set()
    last_error = None
    complete_attempts = 0
    state_digests: set[tuple] = set()
    operations = ("initial", "route_retry", "structural_repair", "bounded_repair")
    for seed_index, packing in enumerate(seeds[:8]):
        working_packing = packing
        last_conflict: InputError | None = None
        for round_index, operation in enumerate(operations):
            substitution = None
            growth = None
            repair_changed = False
            reroutable = isinstance(
                last_conflict, (ConductorLengthConflict, RouteBlockedConflict)
            ) or (
                isinstance(last_conflict, TypedConflict)
                and last_conflict.category
                in {
                    ConflictKind.NET_CONNECTIVITY,
                    ConflictKind.DANGLING_ENDPOINT,
                    ConflictKind.CANONICAL_LENGTH,
                }
                and last_conflict.net is not None
            )
            if round_index == 1 and last_conflict is not None and not reroutable:
                attempts.append(
                    {
                        "seed": seed_index,
                        "round": round_index,
                        "operation": operation,
                        "result": "not_applicable",
                        "failure_class": getattr(last_conflict, "kind", "proof_failure"),
                    }
                )
                continue
            if round_index in {2, 3}:
                before = tuple((item.fragment.id, item.delta) for item in working_packing.fragments)
                try:
                    if round_index == 2 and isinstance(last_conflict, PlacementConflict):
                        working_packing, substitution = _structural_repack(
                            design, resolved, plan, working_packing, last_conflict
                        )
                    elif round_index == 2 and isinstance(last_conflict, RouteBlockedConflict):
                        # A blocked uniquely inferred passive interface may need
                        # the mirrored local gateway family rather than a global
                        # placement move. Prefer the bounded certified access
                        # substitution, then fall back to distribution repacking.
                        try:
                            working_packing, substitution = _substitution_repack(
                                plan,
                                variants,
                                working_packing,
                                last_conflict,
                                seed_index,
                            )
                        except InputError:
                            working_packing, substitution = _distribution_repack(
                                design, resolved, plan, working_packing, last_conflict
                            )
                    elif (
                        round_index == 2
                        and isinstance(last_conflict, ConductorLengthConflict)
                        or (
                            round_index == 2
                            and isinstance(last_conflict, TypedConflict)
                            and last_conflict.net is not None
                            and "distribution_placement" in last_conflict.repair_classes
                        )
                    ):
                        working_packing, substitution = _distribution_repack(
                            design, resolved, plan, working_packing, last_conflict
                        )
                    elif round_index == 3 and isinstance(last_conflict, RouteBlockedConflict):
                        working_packing, growth = _reservation_growth_repack(
                            plan, working_packing, last_conflict, seed_index
                        )
                    elif round_index == 3 and isinstance(last_conflict, ConductorLengthConflict):
                        # A preceding placement repair can expose a distribution
                        # length conflict. Keep the final bounded round available
                        # for that measured repair before changing access variants.
                        try:
                            working_packing, substitution = _distribution_repack(
                                design, resolved, plan, working_packing, last_conflict
                            )
                        except InputError:
                            working_packing, substitution = _substitution_repack(
                                plan,
                                variants,
                                working_packing,
                                last_conflict,
                                seed_index,
                            )
                    elif (
                        round_index == 3
                        and isinstance(last_conflict, TypedConflict)
                        and last_conflict.net is not None
                        and "distribution_placement" in last_conflict.repair_classes
                    ):
                        try:
                            working_packing, substitution = _distribution_repack(
                                design, resolved, plan, working_packing, last_conflict
                            )
                        except InputError:
                            working_packing, substitution = _substitution_repack(
                                plan,
                                variants,
                                working_packing,
                                last_conflict,
                                seed_index,
                            )
                    elif (
                        round_index == 3
                        and isinstance(last_conflict, TypedConflict)
                        and last_conflict.net is not None
                        and "gateway_access" in last_conflict.repair_classes
                    ):
                        working_packing, substitution = _substitution_repack(
                            plan, variants, working_packing, last_conflict, seed_index
                        )
                    else:
                        attempts.append(
                            {
                                "seed": seed_index,
                                "round": round_index,
                                "operation": operation,
                                "result": "not_applicable",
                                "failure_class": getattr(last_conflict, "kind", "proof_failure"),
                            }
                        )
                        continue
                except InputError as exc:
                    attempts.append(
                        {
                            "seed": seed_index,
                            "round": round_index,
                            "operation": operation,
                            "result": "repair_rejected",
                            "failure_class": getattr(last_conflict, "kind", "proof_failure"),
                            "conflict": str(exc),
                        }
                    )
                    continue
                after = tuple((item.fragment.id, item.delta) for item in working_packing.fragments)
                if after == before:
                    attempts.append(
                        {
                            "seed": seed_index,
                            "round": round_index,
                            "operation": operation,
                            "result": "noop_rejected",
                        }
                    )
                    continue
                repair_changed = True
            working_packing = _worksheet_clearance_packing(working_packing)
            from .m2_composition_qualification_observation import observe_composition_packing

            if observe_composition_packing(plan, working_packing).metrics.output_side_violations:
                from .m2_pack_search import _observed_output_corridor_candidate

                corridor = _observed_output_corridor_candidate(plan, variants, working_packing)
                if corridor is not None:
                    working_packing = corridor
            route_retry = (
                1
                if round_index == 1
                else (
                    1
                    if round_index == 3
                    and getattr(last_conflict, "net", None) in external_output_nets
                    else 2
                    if round_index == 3
                    else 0
                )
            )
            digest = (
                tuple((item.fragment.id, item.delta) for item in working_packing.fragments),
                route_retry,
            )
            if digest in state_digests:
                attempts.append(
                    {
                        "seed": seed_index,
                        "round": round_index,
                        "operation": operation,
                        "result": "repeat_state_skipped",
                    }
                )
                continue
            state_digests.add(digest)
            complete_attempts += 1
            try:
                candidate = facade._assemble_candidate(
                    design, resolved, plan, working_packing, retry=route_retry
                )
            except InputError as exc:
                last_error = str(exc)
                last_conflict = exc
                attempts.append(
                    {
                        "seed": seed_index,
                        "round": round_index,
                        "operation": operation,
                        "result": "rejected",
                        "failure_class": getattr(exc, "kind", "proof_failure"),
                        "conflict": last_error,
                        "net": getattr(exc, "net", None),
                        "actual": getattr(exc, "actual", None),
                        "limit": getattr(exc, "limit", None),
                        "repair_state_changed": repair_changed,
                        "reservation_growth": growth,
                        "substitution": substitution,
                    }
                )
                continue
            attempts.append(
                {
                    "seed": seed_index,
                    "round": round_index,
                    "operation": operation,
                    "result": "pass",
                    "repair_state_changed": repair_changed,
                    "reservation_growth": growth,
                    "substitution": substitution,
                }
            )
            canonical_trees = candidate[2]
            candidate_metrics = candidate[-1]
            routing_compactness = (
                sum(tree.length for tree in canonical_trees),
                max((tree.length for tree in canonical_trees), default=0),
                sum(tree.bends for tree in canonical_trees),
                candidate_metrics["final_content_width_mm"]
                * candidate_metrics["final_content_height_mm"],
                seed_index,
                round_index,
            )
            route_segments = tuple(
                (segment.start, segment.end)
                for tree in canonical_trees
                for segment in tree.segments
            )
            routing_readability = measure_routing_readability(
                route_segments,
                semantic_local_length=sum(tree.length for tree in canonical_trees),
            )
            semantic_penalties = semantic_composition_penalties(plan, working_packing)
            observed_composition = observe_composition_packing_envelopes(
                plan, working_packing
            ).metrics
            compactness_penalties = compactness_whitespace_penalties(working_packing)
            interface_enclosures = _route_interface_enclosure_count(
                plan, candidate[0], canonical_trees
            )
            missing_output_routes = _missing_interface_output_routes(plan, candidate[1])
            missing_reference_routes = _missing_optional_reference_routes(plan, candidate[1])
            candidate_metrics["interface_enclosure_count"] = interface_enclosures
            candidate_metrics["missing_interface_output_route_count"] = missing_output_routes
            candidate_metrics["missing_reference_route_count"] = missing_reference_routes
            selection_key = (
                *_candidate_observer_priority(observed_composition),
                missing_output_routes,
                missing_reference_routes,
                interface_enclosures,
                *composition_candidate_key(
                    plan,
                    working_packing,
                    routing_compactness,
                    routing_backtracking=route_backtracking_penalty(canonical_trees),
                    branch_arm_spread=route_branch_arm_spread(canonical_trees),
                    routing_u_shaped_detours=routing_readability.u_shaped_detours,
                    routing_branch_inconsistency=(
                        routing_readability.sibling_branch_geometry_inconsistency
                    ),
                ),
            )
            structure = _structural_signature(working_packing)
            proved_candidates.append(
                (
                    selection_key,
                    semantic_penalties,
                    compactness_penalties,
                    routing_compactness,
                    structure,
                    seed_index,
                    round_index,
                    working_packing,
                    *candidate,
                )
            )
            proved_structures.add(structure)
            # A proved candidate does not truncate the remaining ranked seeds.
            # Keep the same global ledger and let non-needed repair slots be recorded.
            last_conflict = None
    if not proved_candidates:
        failure_evidence = _layout_failure_evidence(
            plan, variants, seeds, attempts, last_error, complete_attempts
        )
        raise LayoutBudgetError(
            f"LAYOUT_BUDGET_EXHAUSTED: attempts={complete_attempts}/32 last={last_error}",
            tuple(attempts),
            failure_evidence,
        )
    ranked_candidates = sorted(proved_candidates, key=lambda candidate: candidate[0])
    selected = ranked_candidates[0]
    best_proved_rejected = ranked_candidates[1] if len(ranked_candidates) > 1 else None
    (
        selection_key,
        semantic_penalties,
        compactness_penalties,
        routing_compactness,
        structure,
        selected_seed,
        selected_round,
        packing,
        draft,
        route_trees,
        canonical_trees,
        reservations,
        metrics,
    ) = selected
    metrics["layout_attempt_count"] = complete_attempts
    metrics["layout_repair_count"] = sum(
        bool(item.get("repair_state_changed")) for item in attempts
    )
    physically_connected_nets = {
        proof["net"]
        for proof in metrics["pre_emission_net_witnesses"]
        if proof["component_count"] == 1
        and all(component >= 0 for _, component in proof["terminal_components"])
    }
    # A redundant label on a continuous conductor is dropped. A local escape
    # stub that only existed to carry such a label would then end in free
    # space as an unconnected wire end, so dead-end spurs are pruned back to
    # the first pin, junction or retained label. Terminal connectivity was
    # proved on the full draft and no spur carries a terminal.
    scene_labels = [
        (net, point) for net, point in draft.labels if net not in physically_connected_nets
    ]
    pin_points = {
        draft.point(component["id"], pin.number)
        for component in design["components"]
        for unit, pins in resolved[component["asset"]].units.items()
        if (component["id"], unit) in draft.positions
        for pin in pins
    }
    anchored_points = pin_points | {point for _net, point in scene_labels}
    scene_conductors = list(zip(draft.wires, draft.wire_nets, strict=True))
    while True:
        endpoint_degree: Counter[tuple[int, int]] = Counter()
        for (first, second), _net in scene_conductors:
            endpoint_degree[first] += 1
            endpoint_degree[second] += 1
        dangling = {
            point
            for point, degree in endpoint_degree.items()
            if degree == 1 and point not in anchored_points
        }
        if not dangling:
            break
        scene_conductors = [
            ((first, second), net)
            for (first, second), net in scene_conductors
            if first not in dangling and second not in dangling
        ]
    scene_wires = [wire for wire, _net in scene_conductors]
    scene_wire_nets = [net for _wire, net in scene_conductors]
    # A junction marker that only existed for a pruned spur is dropped too.
    scene_junctions = [
        point for point in draft.junctions if endpoint_degree[point] >= 3 or point in pin_points
    ]
    metrics["label_count"] = len(scene_labels)
    metrics["pruned_spur_count"] = len(draft.wires) - len(scene_wires)
    if metrics["pruned_spur_count"]:
        # Preflight counts describe the emitted conductors, not pruned spurs.
        metrics["wire_count"] = len(scene_wires)
        metrics["bend_count"] = sum(
            1
            for index, (_start, end) in enumerate(scene_wires)
            for start, far in scene_wires[index + 1 :]
            if end == start and ((scene_wires[index][0][0] == end[0]) != (start[0] == far[0]))
        )
        metrics["wire_length_mm"] = (
            sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in scene_wires) / 1_000_000
        )
    scene = certify_scene_geometry(
        Scene(
            draft.positions,
            scene_wires,
            scene_wire_nets,
            scene_labels,
            scene_junctions,
            metrics,
            draft.angles,
            draft.text_positions,
            {
                (component["id"], unit): angle
                for component in design["components"]
                if component["asset"] in {"Device:R", "Device:C"}
                and max(len(component["refdes"]), len(component["value"])) > 4
                for (cid, unit), angle in draft.angles.items()
                if cid == component["id"] and angle % 180
            },
        )
    )
    scene = certify_scene_inputs(
        scene,
        design,
        resolved,
        {
            "schema_version": "m2h2.policy.1",
            "content_width_nm": MAX_CONTENT_WIDTH,
            "content_height_nm": MAX_CONTENT_HEIGHT,
            "canonical_conductor_length_nm": 250_000_000,
            "candidate_budget": 8,
            "repair_rounds_per_seed": 3,
            "grid_pitch_nm": PITCH,
        },
    )
    emitted_by_net: dict[str, list[list[list[int]]]] = {}
    for (first, second), net in zip(scene.wires, scene.wire_nets, strict=True):
        emitted_by_net.setdefault(net, []).append([list(first), list(second)])
    evidence = {
        "schema_version": "m2g2.composition.1",
        "best_rejected_candidate": min(
            (item for item in attempts if item["result"] == "rejected"),
            key=lambda item: (
                max(0, item["actual"] - item["limit"])
                if isinstance(item.get("actual"), int) and isinstance(item.get("limit"), int)
                else 10**18,
                item["seed"],
                item["round"],
            ),
            default=None,
        ),
        "structural_search": {
            "seed_count": len(seeds),
            "attempted_structure_count": len({_structural_signature(item) for item in seeds}),
            "proved_structure_count": len(proved_structures),
            "seeds": [
                {
                    "seed": index,
                    "structure": [list(part) for part in _structural_signature(item)],
                    "placement_class": item.attempts[-1] if item.attempts else "unspecified",
                }
                for index, item in enumerate(seeds)
            ],
        },
        "candidate_selection": {
            "rule": "semantic_readability_then_routing_clarity_then_compactness",
            "selected_seed": selected_seed,
            "selected_round": selected_round,
            "selected_score": list(routing_compactness),
            "selected_selection_key": list(selection_key),
            "selected_semantic_penalties": list(semantic_penalties),
            "selected_semantic_penalty_breakdown": semantic_composition_penalty_breakdown(
                plan, packing
            ).as_dict(),
            "selected_compactness_penalties": list(compactness_penalties),
            "best_rejected_candidate": (
                {
                    "seed": best_proved_rejected[5],
                    "round": best_proved_rejected[6],
                    "score": list(best_proved_rejected[3]),
                    "selection_key": list(best_proved_rejected[0]),
                    "semantic_penalties": list(best_proved_rejected[1]),
                    "semantic_penalty_breakdown": semantic_composition_penalty_breakdown(
                        plan, best_proved_rejected[7]
                    ).as_dict(),
                    "compactness_penalties": list(best_proved_rejected[2]),
                    "structure": [list(value) for value in best_proved_rejected[4]],
                }
                if best_proved_rejected is not None
                else None
            ),
            "proved_candidate_count": len(proved_candidates),
            "proved_structure_count": len(proved_structures),
            "proved_candidates": [
                {
                    "seed": item[5],
                    "round": item[6],
                    "score": list(item[3]),
                    "selection_key": list(item[0]),
                    "semantic_penalties": list(item[1]),
                    "semantic_penalty_breakdown": semantic_composition_penalty_breakdown(
                        plan, item[7]
                    ).as_dict(),
                    "compactness_penalties": list(item[2]),
                    "structure": [list(value) for value in item[4]],
                }
                for item in proved_candidates
            ],
        },
        "blocks": [
            {
                "id": block.id,
                "kind": block.kind,
                "relationships": list(block.relationships),
                "occurrences": [list(item) for item in sorted(block.occurrences)],
                "function": list(block.function) if block.function else None,
                "unused": block.unused,
                "ports": [
                    {
                        "id": port.id,
                        "net": port.net,
                        "role": port.role,
                        "terminals": [list(item) for item in port.terminals],
                    }
                    for port in block.ports
                ],
            }
            for block in plan.blocks
        ],
        "owners": [
            {"occurrence": list(occurrence), "fragment": owner}
            for occurrence, owner in sorted(plan.owners.items())
        ],
        "edges": [
            {
                "kind": edge.kind,
                "source": edge.source,
                "target": edge.target,
                "net": edge.net,
                "origins": list(edge.origins),
            }
            for edge in plan.edges
        ],
        "signal_order": list(plan.signal_order),
        "variants": [
            {
                "fragment": item.fragment.block.id,
                "variant": item.fragment.id,
                "rule": item.fragment.rule_id,
                "origins": list(item.fragment.origins),
                "local_envelope": list(item.fragment.envelope),
                "content_envelope": list(item.fragment.content_envelope),
                "packing_envelope": list(item.fragment.packing_envelope),
                "placed_envelope": list(item.envelope),
                "translation": list(item.delta),
                "protected_wire_count": len(item.fragment.protected_wires),
                "obstacle_count": len(item.fragment.obstacles),
                "reservation_count": len(item.fragment.reservations),
                "gateways": [
                    {
                        "id": gateway.id,
                        "net": gateway.net,
                        "terminals": [list(terminal) for terminal in gateway.terminals],
                        "anchor": list(gateway.anchor),
                        "escape_direction": gateway.escape_direction,
                        "escape_polyline": [list(point) for point in gateway.escape_polyline],
                    }
                    for gateway in item.gateways
                ],
                "protected_paths": [path.id for path in item.fragment.protected_paths],
            }
            for item in packing.fragments
        ],
        "packing_attempts": list(packing.attempts),
        "routes": [
            {
                "net": tree.net,
                "edge_count": len(tree.edges),
                "segments": [[list(first), list(second)] for first, second in tree.segments],
                "junctions": [list(point) for point in tree.junctions],
                "owner": tree.owner,
                "segment_provenance": [list(value) for value in tree.segment_provenance],
                "tap_tests": tree.tap_tests,
                "state_expansions": tree.state_expansions,
                "strategy": tree.strategy,
                "plan_tests": tree.plan_tests,
            }
            for tree in route_trees
        ],
        "canonical_trees": [
            {
                "net": tree.net,
                "segments": [[list(segment.start), list(segment.end)] for segment in tree.segments],
                "junctions": [list(point) for point in tree.junctions],
                "length_nm": tree.length,
                "bends": tree.bends,
                "provenance": [list(segment.provenance) for segment in tree.segments],
            }
            for tree in canonical_trees
        ],
        # Keep emitted conductors distinct from canonical route proposals.
        "emitted_conductors": [
            {"net": net, "segments": segments} for net, segments in sorted(emitted_by_net.items())
        ],
        "reservations": [
            {
                "id": reservation.id,
                "owner": reservation.owner,
                "class": reservation.clearance_class,
                "occupancy": reservation.occupancy,
                "rect": list(reservation.rect),
                "net": reservation.permitted_net,
                "capacity": reservation.capacity,
            }
            for reservation in reservations
        ],
        "layout_attempts": attempts,
        "budgets": {
            "seed_limit": 8,
            "repair_rounds_per_seed": 3,
            "complete_attempt_limit": 32,
            "complete_attempts_used": complete_attempts,
        },
    }
    evidence["obligation_certificate"] = {
        "schema_version": "m2h2.obligation-certificate.1",
        "scene_geometry_sha256": scene.certificate_digest,
        "candidate_input_policy_sha256": scene.certificate_input_digest,
        "geometry_owners": [
            {"occurrence": list(occurrence), "fragment": owner}
            for occurrence, owner in sorted(plan.owners.items())
        ],
        "semantic_obligations": {
            "ports": [
                {
                    "id": port.id,
                    "fragment": port.fragment,
                    "net": port.net,
                    "role": port.role,
                    "terminals": [list(terminal) for terminal in port.terminals],
                }
                for block in plan.blocks
                for port in block.ports
            ],
            "edges": [
                {
                    "kind": edge.kind,
                    "source": edge.source,
                    "target": edge.target,
                    "net": edge.net,
                    "origins": list(edge.origins),
                }
                for edge in plan.edges
            ],
            "constraints": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "strength": item.strength,
                    "anchors": list(item.anchors),
                    "origins": list(item.origins),
                    "parameters": [list(value) for value in item.parameters],
                }
                for item in plan.constraints
            ],
            "precedence": [
                {
                    "id": item.id,
                    "source_fragment": item.source_fragment,
                    "target_fragment": item.target_fragment,
                    "source_terminal": list(item.source_terminal),
                    "target_terminal": list(item.target_terminal),
                    "net": item.net,
                    "origins": list(item.origins),
                    "minimum_x_separation_nm": item.minimum_x_separation,
                }
                for item in plan.precedence
            ],
            "terminals": [
                {
                    "terminal": list(item.terminal),
                    "occurrence": list(item.occurrence),
                    "owner": item.owner,
                    "asset": item.asset,
                    "unit": item.unit,
                    "pin_name": item.pin_name,
                    "pin_xy_nm": [item.pin_x, item.pin_y],
                    "net": item.net,
                }
                for item in plan.terminals
            ],
            "presentation_nets": [
                {
                    "id": item.id,
                    "terminals": [list(terminal) for terminal in item.terminals],
                    "fragments": list(item.fragments),
                    "role": item.role,
                    "internally_generated": item.internally_generated,
                    "explicit_geometry_required": item.explicit_geometry_required,
                    "producer_fragments": list(item.producer_fragments),
                }
                for item in plan.presentation_nets
            ],
            "local_spans": [
                {
                    "id": item.id,
                    "first": list(item.first),
                    "second": list(item.second),
                    "maximum_nm": item.maximum,
                    "metric": item.metric,
                    "subtype": item.subtype,
                    "origins": list(item.origins),
                }
                for item in plan.local_spans
            ],
        },
        "terminal_inventory_count": scene.metrics["pre_emission_terminal_inventory_count"],
        "net_graph_witnesses": scene.metrics["pre_emission_net_witnesses"],
        "gateway_witnesses": scene.metrics["pre_emission_gateway_witnesses"],
        "placement_witnesses": scene.metrics["pre_emission_placement_proofs"],
        "local_span_obligation_count": scene.metrics["pre_emission_local_span_count"],
        "canonical_lengths_nm": {tree.net: tree.length for tree in canonical_trees},
        "final_content_envelope_nm": list(scene.metrics["final_content_envelope"]),
        "reservation_containment_pass": scene.metrics["reservation_containment_pass"],
        "reservation_allocation_count": scene.metrics["reservation_allocation_count"],
        "no_unintended_dangling_endpoints": True,
        "no_cross_net_contacts": True,
        "no_unallocated_growth": True,
        "serialized_scene_verified": "pending_emission",
    }
    return scene, evidence


def compose_layout(design: dict, resolved: dict) -> Scene:
    """Compatibility entry point returning the composed scene."""
    return compose_with_evidence(design, resolved)[0]
