"""Instance-based composition of qualified M2 schematic fragments."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re

from .ir import InputError
from .m2a import PITCH, Scene
from .m2b import Draft, measure
from .m2_fragments import fragment_variants
from .m2_geometry import ConductorSegment, GeometryItem, Reservation, canonical_conductor_tree
from .m2_pack import (
    BOTTOM,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    RIGHT,
    TOP,
    Packing,
    pack_fragment_candidates,
)
from .m2_route import route_between_fragments
from .m2_semantics import semantic_plan


def _substitution_repack(plan, variants, packing: Packing, conflict: str, ordinal: int):
    match = re.search(r"net=([^ ]+)", conflict)
    if match is None:
        return packing, None
    net = match.group(1)
    current = {item.fragment.block.id: item.fragment for item in packing.fragments}
    incident = {
        block_id
        for edge in plan.edges
        if edge.net == net
        for block_id in (edge.source, edge.target)
    }

    def signature(variant):
        return tuple(
            (gateway.id.rsplit(".", 1)[-1], gateway.escape_direction)
            for gateway in variant.gateways
            if gateway.net == net
        )

    options = [
        (block_id, choice)
        for block_id in sorted(incident)
        if block_id in current
        for choice in variants[block_id]
        if choice.id != current[block_id].id and signature(choice) != signature(current[block_id])
    ]
    if not options:
        return packing, None
    block_id, choice = options[ordinal % len(options)]
    restricted = {
        key: ((choice,) if key == block_id else (current[key],)) for key in sorted(current)
    }
    replacements = pack_fragment_candidates(plan, restricted)
    return replacements[-1 - (ordinal % len(replacements))], {
        "block": block_id,
        "from": current[block_id].id,
        "to": choice.id,
        "net": net,
    }


def _reservation_growth_repack(plan, packing: Packing, conflict: str, ordinal: int):
    """Apply the one bounded, witnessed reservation-growth repair.

    Route failures name the affected net.  Grow the first incident gateway's
    packing side by exactly one pitch and retain that extra channel reservation
    in the immutable replacement variant before repacking every fragment.
    """
    match = re.search(r"net=([^ ]+)", conflict)
    if match is None:
        return packing, None
    net = match.group(1)
    current = {item.fragment.block.id: item.fragment for item in packing.fragments}
    candidates = sorted(
        (block_id, gateway)
        for block_id, fragment in current.items()
        for gateway in fragment.gateways
        if gateway.net == net
    )
    if not candidates:
        return packing, None
    block_id, gateway = candidates[ordinal % len(candidates)]
    fragment = current[block_id]
    left, top, right, bottom = fragment.envelope
    gl, gt, gr, gb = (
        gateway.tap_windows[0].rect
        if gateway.tap_windows
        else (
            gateway.point[0],
            gateway.point[1],
            gateway.point[0],
            gateway.point[1],
        )
    )
    if gateway.escape_direction == "left":
        new_envelope = (min(left, gl - PITCH), top, right, bottom)
        channel_rect = (gl - PITCH, gt - PITCH, gr, gb + PITCH)
    elif gateway.escape_direction == "right":
        new_envelope = (left, top, max(right, gr + PITCH), bottom)
        channel_rect = (gl, gt - PITCH, gr + PITCH, gb + PITCH)
    elif gateway.escape_direction == "up":
        new_envelope = (left, min(top, gt - PITCH), right, bottom)
        channel_rect = (gl - PITCH, gt - PITCH, gr + PITCH, gb)
    else:
        new_envelope = (left, top, right, max(bottom, gb + PITCH))
        channel_rect = (gl - PITCH, gt, gr + PITCH, gb + PITCH)
    grown = replace(
        fragment,
        id=f"{fragment.id}.growth-{gateway.id.rsplit('.', 1)[-1]}",
        envelope=new_envelope,
        packing_envelope=new_envelope,
        reservations=(
            *fragment.reservations,
            Reservation(
                f"growth.{gateway.id}",
                "channel",
                fragment.block.id,
                "blocked_escape",
                channel_rect,
                net,
                1,
            ),
        ),
    )
    restricted = {
        key: ((grown,) if key == block_id else (current[key],)) for key in sorted(current)
    }
    replacements = pack_fragment_candidates(plan, restricted)
    return replacements[0], {
        "block": block_id,
        "gateway": gateway.id,
        "net": net,
        "old_envelope": list(fragment.envelope),
        "new_envelope": list(new_envelope),
        "growth_nm": PITCH,
        "witness": conflict,
    }


@dataclass(frozen=True)
class StageGraph:
    """Compatibility view of signal-like relationship ordering."""

    ports: dict[str, tuple[str, str]]
    order: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]


class LayoutBudgetError(InputError):
    """Bounded composition failure retaining every completed attempt."""

    def __init__(self, message: str, attempts: tuple[dict, ...], evidence: dict | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.evidence = evidence or {}


def stage_graph(design: dict) -> StageGraph:
    """Return the legacy relation projection; composition uses the typed plan."""
    ports = {
        relation["id"]: (relation["input"], relation["output"])
        for relation in design["relationships"]
        if relation["kind"] in ("series", "amplifier", "power_stage") and not relation.get("unused")
    }
    ports.update(
        (relation["id"], (relation["supply"], relation["output"]))
        for relation in design["relationships"]
        if relation["kind"] == "timer"
    )
    edges = tuple(
        sorted(
            (first, second, output)
            for first, (_, output) in ports.items()
            for second, (input_net, _) in ports.items()
            if first != second and output == input_net
        )
    )
    remaining, order = set(ports), []
    while remaining:
        ready = sorted(
            stage
            for stage in remaining
            if not any(first in remaining and second == stage for first, second, _ in edges)
        )
        if not ready:
            raise InputError(f"unsupported stage graph cycle: {sorted(remaining)}")
        order.extend(ready)
        remaining.difference_update(ready)
    return StageGraph(ports, tuple(order), edges)


def _translate(point: tuple[int, int], delta: tuple[int, int]) -> tuple[int, int]:
    return point[0] + delta[0], point[1] + delta[1]


def _translated_rect(rect, delta):
    return tuple(value + shift for value, shift in zip(rect, (*delta, *delta), strict=True))


def _assemble_candidate(design: dict, resolved: dict, plan, packing: Packing, retry: int):
    draft = Draft(design, resolved, {}, {}, [], [], [], [], {})
    conductors: list[ConductorSegment] = []
    reservations = [reservation for item in packing.fragments for reservation in item.reservations]
    occupied = []
    for placed in packing.fragments:
        fragment, delta = placed.fragment, placed.delta
        for key, point in fragment.positions.items():
            if key in draft.positions:
                raise InputError(f"COMPOSE_GEOMETRY_OWNER_CONFLICT: {key}")
            draft.positions[key] = _translate(point, delta)
        draft.angles.update(fragment.angles)
        draft.text_positions.update(
            (key, _translate(point, delta)) for key, point in fragment.text_positions.items()
        )
        draft.labels.extend((net, _translate(point, delta)) for net, point in fragment.labels)
        occupied.extend(
            GeometryItem(
                item.id,
                item.kind,
                item.owner,
                _translated_rect(item.rect, delta),
                item.provenance,
            )
            for item in fragment.occupied_geometry
        )
        conductors.extend(
            ConductorSegment(
                _translate(first, delta),
                _translate(second, delta),
                net,
                fragment.block.id,
                provenance,
            )
            for (first, second), net, provenance in zip(
                fragment.wires,
                fragment.wire_nets,
                fragment.wire_provenance,
                strict=True,
            )
        )

    route_trees = route_between_fragments(plan, packing.fragments, retry_index=retry)
    for tree in route_trees:
        conductors.extend(
            ConductorSegment(first, second, tree.net, tree.owner, provenance)
            for (first, second), provenance in zip(
                tree.segments, tree.segment_provenance, strict=True
            )
        )
        for index, (first, second) in enumerate(tree.segments):
            rect = (
                min(first[0], second[0]) - 250_000,
                min(first[1], second[1]) - 250_000,
                max(first[0], second[0]) + 250_000,
                max(first[1], second[1]) + 250_000,
            )
            reservations.append(
                Reservation(
                    f"route.{tree.net}.{index}",
                    "channel",
                    tree.owner,
                    "global_route",
                    rect,
                    tree.net,
                    1,
                )
            )
            occupied.append(
                GeometryItem(
                    f"route.{tree.net}.{index}",
                    "wire",
                    tree.owner,
                    (
                        min(first[0], second[0]),
                        min(first[1], second[1]),
                        max(first[0], second[0]),
                        max(first[1], second[1]),
                    ),
                    tree.segment_provenance[index],
                )
            )

    canonical_trees = []
    for net in sorted({segment.net for segment in conductors}):
        canonical_trees.append(
            canonical_conductor_tree(
                (segment for segment in conductors if segment.net == net),
                pins=(
                    draft.point(component["id"], pin.number)
                    for component in design["components"]
                    for unit, pins in resolved[component["asset"]].units.items()
                    if (component["id"], unit) in draft.positions
                    for pin in pins
                    if any(
                        net_item["id"] == net
                        and [component["id"], pin.number] in net_item["members"]
                        for net_item in design["nets"]
                    )
                ),
            )
        )
    excessive = [(tree.net, tree.length) for tree in canonical_trees if tree.length > 250_000_000]
    if excessive:
        raise InputError(f"NET_DETOUR_OVERFLOW: {excessive} threshold=250000000")
    draft.wires = [
        (segment.start, segment.end) for tree in canonical_trees for segment in tree.segments
    ]
    draft.wire_nets = [tree.net for tree in canonical_trees for _ in tree.segments]
    draft.junctions = [point for tree in canonical_trees for point in tree.junctions]

    component_ids = {component["id"] for component in design["components"]}
    expected = set(plan.owners)
    actual = {key for key in draft.positions if key[0] in component_ids}
    if actual != expected:
        raise InputError(
            f"COMPOSE_OWNER_INCOMPLETE: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}"
        )
    for assertion in design["power_assertions"]:
        candidates = sorted(point for net, point in draft.labels if net == assertion["net"])
        candidates.extend(
            sorted(
                gateway.point
                for item in packing.fragments
                for gateway in item.gateways
                if gateway.net == assertion["net"]
            )
        )
        if not candidates:
            raise InputError(
                f"COMPOSE_ASSERTION_PORT_MISSING: {assertion['id']}:{assertion['net']}"
            )
        point = candidates[0]
        draft.positions[(assertion["id"], 1)] = point
        glyph = GeometryItem(
            assertion["id"],
            "source_glyph",
            assertion["id"],
            (point[0] - PITCH, point[1] - PITCH, point[0] + PITCH, point[1] + PITCH),
        )
        occupied.append(glyph)
        reservations.append(
            Reservation(
                f"source.{assertion['id']}",
                "exclusive",
                assertion["id"],
                "source_glyph",
                glyph.rect,
            )
        )

    if not all(
        any(reservation.contains(item.rect) for reservation in reservations) for item in occupied
    ):
        missing = sorted(
            item.id
            for item in occupied
            if not any(reservation.contains(item.rect) for reservation in reservations)
        )
        raise InputError(f"RESERVATION_GROWTH: uncovered={missing}")
    final_rect = (
        min(item.rect[0] for item in occupied),
        min(item.rect[1] for item in occupied),
        max(item.rect[2] for item in occupied),
        max(item.rect[3] for item in occupied),
    )
    if (
        final_rect[0] < LEFT
        or final_rect[1] < TOP
        or final_rect[2] > RIGHT
        or final_rect[3] > BOTTOM
    ):
        raise InputError(f"PAGE_CONTENT_OVERFLOW: final={final_rect}")
    final_width = final_rect[2] - final_rect[0]
    final_height = final_rect[3] - final_rect[1]
    if final_width > MAX_CONTENT_WIDTH or final_height > MAX_CONTENT_HEIGHT:
        raise InputError(
            f"SPREAD_OVERFLOW: actual={final_width}x{final_height} "
            f"threshold={MAX_CONTENT_WIDTH}x{MAX_CONTENT_HEIGHT}"
        )
    metrics = measure(design, resolved, draft)
    metrics.update(
        {
            "semantic_block_count": len(plan.blocks),
            "semantic_edge_count": len(plan.edges),
            "packing_attempts": list(packing.attempts),
            "final_content_envelope": list(final_rect),
            "final_content_width_mm": final_width / 1_000_000,
            "final_content_height_mm": final_height / 1_000_000,
            "reservation_containment_pass": True,
        }
    )
    return draft, route_trees, canonical_trees, tuple(reservations), metrics


def compose_with_evidence(design: dict, resolved: dict) -> tuple[Scene, dict]:
    """Compose using at most eight seeds and four attempts per seed."""
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    seeds = pack_fragment_candidates(plan, variants)
    attempts = []
    selected = None
    last_error = None
    for seed_index, packing in enumerate(seeds[:8]):
        state_digests = set()
        working_packing = packing
        for round_index in range(4):
            substitution = None
            growth = None
            if round_index == 2 and last_error:
                try:
                    working_packing, substitution = _substitution_repack(
                        plan, variants, working_packing, last_error, seed_index
                    )
                except InputError as exc:
                    last_error = str(exc)
                    attempts.append(
                        {
                            "seed": seed_index,
                            "round": round_index,
                            "operation": "variant_substitution",
                            "result": "rejected",
                            "failure_class": "page/spread",
                            "conflict": last_error,
                        }
                    )
                    continue
            if round_index == 3 and last_error:
                try:
                    working_packing, growth = _reservation_growth_repack(
                        plan, working_packing, last_error, seed_index
                    )
                except InputError as exc:
                    last_error = str(exc)
                    attempts.append(
                        {
                            "seed": seed_index,
                            "round": round_index,
                            "operation": "reservation_growth",
                            "result": "rejected",
                            "failure_class": "page/spread",
                            "conflict": last_error,
                            "reservation_growth": growth,
                        }
                    )
                    continue
            digest = (
                tuple((item.fragment.id, item.delta) for item in working_packing.fragments),
                round_index if round_index in {1, 3} else 0,
            )
            if digest in state_digests:
                attempts.append(
                    {
                        "seed": seed_index,
                        "round": round_index,
                        "operation": (
                            "route_retry",
                            "route_retry",
                            "variant_substitution",
                            "reservation_growth",
                        )[round_index],
                        "result": "repeat_state_skipped",
                    }
                )
                continue
            state_digests.add(digest)
            try:
                candidate = _assemble_candidate(
                    design,
                    resolved,
                    plan,
                    working_packing,
                    retry=1 if round_index == 1 else 2 if round_index == 3 else 0,
                )
            except InputError as exc:
                last_error = str(exc)
                attempts.append(
                    {
                        "seed": seed_index,
                        "round": round_index,
                        "operation": (
                            "initial",
                            "route_retry",
                            "variant_substitution",
                            "reservation_growth",
                        )[round_index],
                        "result": "rejected",
                        "failure_class": (
                            "connectivity/protection"
                            if "ROUTE" in last_error or "CONDUCTOR" in last_error
                            else "body/pin"
                            if "body" in last_error or "pin" in last_error
                            else "text"
                            if "text" in last_error
                            else "page/spread"
                            if "OVERFLOW" in last_error
                            else "other_quality"
                        ),
                        "conflict": last_error,
                        "reservation_growth_pitch": 1 if round_index == 3 else 0,
                        "reservation_growth": growth,
                        "substitution": substitution,
                    }
                )
                continue
            attempts.append(
                {
                    "seed": seed_index,
                    "round": round_index,
                    "operation": (
                        "initial",
                        "route_retry",
                        "variant_substitution",
                        "reservation_growth",
                    )[round_index],
                    "result": "pass",
                    "reservation_growth_pitch": 1 if round_index == 3 else 0,
                    "reservation_growth": growth,
                    "substitution": substitution,
                }
            )
            selected = (working_packing, *candidate)
            break
        if selected is not None:
            break
    if selected is None:
        failure_evidence = {
            "schema_version": "m2g2.composition-failure.1",
            "stage": "layout_schematic",
            "semantic_obligations": sorted(
                {
                    obligation.id
                    for choices in variants.values()
                    for variant in choices
                    for obligation in variant.obligations
                }
            ),
            "owners": [
                {"occurrence": list(occurrence), "fragment": owner}
                for occurrence, owner in sorted(plan.owners.items())
            ],
            "variants": [
                {
                    "fragment": block_id,
                    "variant": variant.id,
                    "content_envelope": list(variant.content_envelope),
                    "packing_envelope": list(variant.packing_envelope),
                    "reservations": [
                        {
                            "id": reservation.id,
                            "owner": reservation.owner,
                            "class": reservation.clearance_class,
                            "rect": list(reservation.rect),
                            "net": reservation.permitted_net,
                            "capacity": reservation.capacity,
                        }
                        for reservation in variant.reservations
                    ],
                    "gateways": [
                        {
                            "id": gateway.id,
                            "net": gateway.net,
                            "terminals": [list(terminal) for terminal in gateway.terminals],
                            "escape_direction": gateway.escape_direction,
                            "escape_polyline": [list(point) for point in gateway.escape_polyline],
                        }
                        for gateway in variant.gateways
                    ],
                    "wire_provenance": [list(value) for value in variant.wire_provenance],
                    "protected_paths": [
                        {
                            "id": path.id,
                            "owner": path.owner,
                            "net": path.net,
                            "terminal_pairs": [list(pair) for pair in path.terminal_pairs],
                            "edges": [
                                [list(edge.start), list(edge.end)] for edge in path.local_tree_edges
                            ],
                        }
                        for path in variant.protected_paths
                    ],
                }
                for block_id, choices in sorted(variants.items())
                for variant in choices
            ],
            "candidate_decisions": [
                {
                    "seed": index,
                    "packing_attempts": list(seed.attempts),
                    "placements": [
                        {
                            "fragment": item.fragment.block.id,
                            "variant": item.fragment.id,
                            "envelope": list(item.envelope),
                        }
                        for item in seed.fragments
                    ],
                }
                for index, seed in enumerate(seeds[:8])
            ],
            "layout_attempts": attempts,
            "route_junction_provenance": "not_evaluated_no_accepted_route",
            "failed_metric": last_error,
            "threshold": "unchanged M2 layout/electrical gates",
            "budgets": {
                "seed_limit": 8,
                "repair_rounds_per_seed": 3,
                "complete_attempt_limit": 32,
                "complete_attempts_used": len(attempts),
            },
        }
        raise LayoutBudgetError(
            f"LAYOUT_BUDGET_EXHAUSTED: attempts={len(attempts)}/32 last={last_error}",
            tuple(attempts),
            failure_evidence,
        )
    packing, draft, route_trees, canonical_trees, reservations, metrics = selected
    metrics["layout_attempt_count"] = len(attempts)
    metrics["layout_repair_count"] = max(0, len(attempts) - 1)
    scene = Scene(
        draft.positions,
        draft.wires,
        draft.wire_nets,
        draft.labels,
        draft.junctions,
        metrics,
        draft.angles,
        draft.text_positions,
    )
    evidence = {
        "schema_version": "m2g2.composition.1",
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
            "complete_attempts_used": len(attempts),
        },
    }
    return scene, evidence


def compose_layout(design: dict, resolved: dict) -> Scene:
    """Compatibility entry point returning the composed scene."""
    return compose_with_evidence(design, resolved)[0]
