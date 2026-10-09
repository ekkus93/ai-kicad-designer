"""Instance-based composition of qualified M2 schematic fragments."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .ir import InputError
from .m2_conflicts import ConflictKind, TypedConflict
from .m2_composition_candidate_rank import (
    compactness_whitespace_penalties,
    composition_candidate_key,
    semantic_composition_penalty_breakdown,
    semantic_composition_penalties,
)
from .m2a import PITCH, Scene, certify_scene_geometry, certify_scene_inputs
from .m2b import Draft, measure
from .m2_geometry import label_text_rect
from .m2_fragments import fragment_variants
from .m2_geometry import (
    ConductorSegment,
    GeometryItem,
    Reservation,
    canonical_conductor_tree,
    prove_conductor_graph,
    prove_gateway_witnesses,
    prove_no_cross_net_contacts,
    prove_reservation_allocation,
)
from .m2_pack import (
    BOTTOM,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    RIGHT,
    TOP,
    Packing,
    _measured_repack,
    _place,
    _worksheet_clearance_packing,
    pack_fragment_candidates,
)
from .m2_route import (
    RouteBlockedConflict,
    _crosses,
    _routable_edges,
    route_between_fragments,
)
from .m2_semantics import PlacementConflict, check_placement_constraints, semantic_plan


class ConductorLengthConflict(InputError):
    """Canonical union over a hard net budget, with geometric owners."""

    kind = "canonical_net_length"

    def __init__(self, net: str, actual: int, local: int, global_length: int):
        self.category = ConflictKind.CANONICAL_LENGTH
        self.net = net
        self.actual = actual
        self.local = local
        self.global_length = global_length
        self.limit = 250_000_000
        super().__init__(
            f"NET_DETOUR_OVERFLOW: net={net} actual={actual} local={local} "
            f"global={global_length} threshold={self.limit}"
        )


def _distribution_repack(
    design,
    resolved,
    plan,
    packing: Packing,
    conflict: ConductorLengthConflict | RouteBlockedConflict | TypedConflict,
    steps_left: int = 3,
):
    """Move the blocked island or the outermost distribution island inward."""
    connected = [
        (item, gateway)
        for item in packing.fragments
        for gateway in item.gateways
        if gateway.net == conflict.net
    ]
    if len(connected) < 2:
        raise InputError(f"DISTRIBUTION_REPAIR_UNAVAILABLE: {conflict.net}")
    blocked = (
        next(
            (item for item, gateway in connected if gateway.id in conflict.gateways),
            None,
        )
        if isinstance(conflict, RouteBlockedConflict)
        else None
    )
    if blocked is not None:
        target = blocked
    else:
        center_x = sum(gateway.point[0] for _, gateway in connected) // len(connected)
        center_y = sum(gateway.point[1] for _, gateway in connected) // len(connected)
        target = max(
            connected,
            key=lambda pair: (
                abs(pair[1].point[0] - center_x) + abs(pair[1].point[1] - center_y),
                pair[0].fragment.block.id,
            ),
        )[0]
    other = [item for item in packing.fragments if item is not target]
    gateway = next(gateway for item, gateway in connected if item is target)
    baseline_box = (
        max(g.point[0] for _, g in connected)
        - min(g.point[0] for _, g in connected)
        + max(g.point[1] for _, g in connected)
        - min(g.point[1] for _, g in connected)
    )
    consumer_points = [g.point for item, g in connected if item is not target]
    center_x = sum(point[0] for point in consumer_points) // len(consumer_points)
    center_y = sum(point[1] for point in consumer_points) // len(consumer_points)
    width = target.envelope[2] - target.envelope[0]
    height = target.envelope[3] - target.envelope[1]
    lefts = {target.envelope[0] + center_x - gateway.point[0]}
    tops = {target.envelope[1] + center_y - gateway.point[1]}
    for obstacle in other:
        lefts.update((obstacle.envelope[0] - width - PITCH, obstacle.envelope[2] + PITCH))
        tops.update(
            (
                obstacle.envelope[1] - height - PITCH,
                obstacle.envelope[3] + PITCH,
                obstacle.envelope[1],
            )
        )
    candidates = []
    for left in lefts:
        for top in tops:
            moved = _place(target.fragment, left, top)
            if moved.delta == target.delta or moved.envelope[0] < LEFT or moved.envelope[1] < TOP:
                continue
            if moved.envelope[2] > RIGHT or moved.envelope[3] > BOTTOM:
                continue
            if any(
                max(moved.envelope[0], item.envelope[0]) < min(moved.envelope[2], item.envelope[2])
                and max(moved.envelope[1], item.envelope[1])
                < min(moved.envelope[3], item.envelope[3])
                for item in other
            ):
                continue
            changed = tuple(moved if item is target else item for item in packing.fragments)
            if (
                max(item.content_envelope[2] for item in changed)
                - min(item.content_envelope[0] for item in changed)
                > MAX_CONTENT_WIDTH
                or max(item.content_envelope[3] for item in changed)
                - min(item.content_envelope[1] for item in changed)
                > MAX_CONTENT_HEIGHT
            ):
                continue
            new_points = [
                (
                    g.point[0] + moved.delta[0] - target.delta[0],
                    g.point[1] + moved.delta[1] - target.delta[1],
                )
                if item is target
                else g.point
                for item, g in connected
            ]
            box = (
                max(point[0] for point in new_points)
                - min(point[0] for point in new_points)
                + max(point[1] for point in new_points)
                - min(point[1] for point in new_points)
            )
            if box >= baseline_box:
                continue
            local_wires = [
                (
                    net,
                    (first[0] + item.delta[0], first[1] + item.delta[1]),
                    (second[0] + item.delta[0], second[1] + item.delta[1]),
                )
                for item in changed
                for (first, second), net in zip(
                    item.fragment.wires, item.fragment.wire_nets, strict=True
                )
            ]
            if any(
                first_net != second_net and _crosses(a, b, c, d)
                for index, (first_net, a, b) in enumerate(local_wires)
                for second_net, c, d in local_wires[index + 1 :]
            ):
                continue
            positions = {
                key: (point[0] + item.delta[0], point[1] + item.delta[1])
                for item in changed
                for key, point in item.fragment.positions.items()
            }
            angles = {key: angle for item in changed for key, angle in item.fragment.angles.items()}
            draft = Draft(design, resolved, positions, angles, [], [], [], [], {})
            try:
                check_placement_constraints(plan, draft.point)
            except PlacementConflict:
                continue
            candidates.append((box, moved.envelope[0], moved.envelope[1], changed, moved))
    if not candidates:
        raise InputError(f"DISTRIBUTION_REPAIR_EXHAUSTED: {conflict.net}")
    box, _, _, changed, moved = min(candidates, key=lambda item: item[:3])
    repaired = Packing(changed, packing.attempts + (f"distribution:{conflict.net}",))
    decision = {
        "kind": conflict.kind,
        "net": conflict.net,
        "fragment": target.fragment.block.id,
        "from": list(target.delta),
        "to": list(moved.delta),
        "gateway_bbox_before_nm": baseline_box,
        "gateway_bbox_after_nm": box,
    }
    if steps_left > 1 and (
        isinstance(conflict, ConductorLengthConflict)
        or isinstance(conflict, TypedConflict)
        and conflict.category == ConflictKind.CANONICAL_LENGTH
    ):
        try:
            further, next_decision = _distribution_repack(
                design, resolved, plan, repaired, conflict, steps_left - 1
            )
        except InputError:
            pass
        else:
            return further, {
                "kind": conflict.kind,
                "net": conflict.net,
                "moves": [decision, next_decision],
            }
    return repaired, decision


def _structural_repack(design, resolved, plan, packing: Packing, conflict: PlacementConflict):
    """Move the responsible fragment to a measured adjacent legal slot."""
    by_id = {item.fragment.block.id: item for item in packing.fragments}
    source = by_id.get(conflict.source_fragment)
    target = by_id.get(conflict.target_fragment)
    if source is None or target is None or source is target:
        raise InputError(f"STRUCTURAL_REPAIR_UNAVAILABLE: {conflict.obligation}")
    positions = {
        key: (point[0] + item.delta[0], point[1] + item.delta[1])
        for item in packing.fragments
        for key, point in item.fragment.positions.items()
    }
    angles = {
        key: angle for item in packing.fragments for key, angle in item.fragment.angles.items()
    }
    draft = Draft(design, resolved, positions, angles, [], [], [], [], {})
    relation = next((item for item in plan.precedence if item.id == conflict.obligation), None)
    if relation is None:
        relation = next((item for item in plan.local_spans if item.id == conflict.obligation), None)
    first_terminal = (
        relation.source_terminal if hasattr(relation, "source_terminal") else relation.first
    )
    second_terminal = (
        relation.target_terminal if hasattr(relation, "target_terminal") else relation.second
    )
    first_point = draft.point(*first_terminal)
    second_point = draft.point(*second_terminal)
    if (
        hasattr(relation, "source_terminal")
        and source.fragment.block.kind == "interface"
        and target.fragment.block.kind != "interface"
        and second_point[0] <= first_point[0]
    ):
        # A connector boundary can constrain a complete serial group. Moving
        # only its first cell would collide with the already placed successor.
        shift = ((first_point[0] + PITCH - second_point[0] + PITCH - 1) // PITCH) * PITCH
        related_ids = {target.fragment.block.id}
        while True:
            components = {
                component
                for item in packing.fragments
                if item.fragment.block.id in related_ids
                for component, _unit in item.fragment.block.occurrences
            }
            expanded = related_ids | {
                item.fragment.block.id
                for item in packing.fragments
                if item.fragment.block.kind != "interface"
                and any(
                    component in components for component, _unit in item.fragment.block.occurrences
                )
            }
            for edge in plan.edges:
                if edge.kind in {
                    "signal",
                    "branch",
                    "package",
                    "feedback",
                    "support",
                } and (edge.source in related_ids or edge.target in related_ids):
                    expanded.update(
                        owner
                        for owner in (edge.source, edge.target)
                        if by_id[owner].fragment.block.kind != "interface"
                    )
            if expanded == related_ids:
                break
            related_ids = expanded
        related = [item for item in packing.fragments if item.fragment.block.id in related_ids]
        grouped = _measured_repack(
            plan,
            packing,
            target,
            target.envelope[0] + shift,
            target.envelope[1],
            "external-precedence-transaction",
            additional_moves=tuple(
                (item, item.envelope[0] + shift, item.envelope[1])
                for item in related
                if item is not target
            ),
        )
        if grouped is not None:
            return grouped, {
                "kind": conflict.kind,
                "obligation": conflict.obligation,
                "fragments": [item.fragment.block.id for item in related],
                "shift_nm": shift,
            }
        blockers = [
            item
            for item in packing.fragments
            if item.fragment.block.kind == "interface"
            and any(
                max(item.envelope[0], member.envelope[0] + shift)
                < min(item.envelope[2], member.envelope[2] + shift)
                and max(item.envelope[1], member.envelope[1])
                < min(item.envelope[3], member.envelope[3])
                for member in related
            )
        ]
        if len(blockers) == 1:
            blocker = blockers[0]
            blocker_height = blocker.envelope[3] - blocker.envelope[1]
            tops = {TOP, blocker.envelope[1]}
            for item in packing.fragments:
                if item is not blocker:
                    tops.add(item.envelope[3] + PITCH)
                    tops.add(item.envelope[1] - blocker_height - PITCH)
            for left in sorted({LEFT + PITCH, target.envelope[0], blocker.envelope[0]}):
                for top in sorted(tops):
                    adjusted = _measured_repack(
                        plan,
                        packing,
                        target,
                        target.envelope[0] + shift,
                        target.envelope[1],
                        "external-precedence-interface-transaction",
                        additional_moves=(
                            *(
                                (item, item.envelope[0] + shift, item.envelope[1])
                                for item in related
                                if item is not target
                            ),
                            (blocker, left, top),
                        ),
                    )
                    if adjusted is not None:
                        return adjusted, {
                            "kind": conflict.kind,
                            "obligation": conflict.obligation,
                            "fragments": [item.fragment.block.id for item in related],
                            "shift_nm": shift,
                            "interface": blocker.fragment.block.id,
                            "interface_to": [left, top],
                        }
        source_width = source.envelope[2] - source.envelope[0]
        source_height = source.envelope[3] - source.envelope[1]
        interface_left = (
            (second_point[0] - PITCH - (first_point[0] - source.envelope[0])) // PITCH
        ) * PITCH
        if interface_left >= LEFT and interface_left + source_width <= RIGHT:
            tops = {source.envelope[1], TOP}
            for item in packing.fragments:
                if item is not source:
                    tops.add(item.envelope[3] + PITCH)
                    tops.add(item.envelope[1] - source_height - PITCH)
            for top in sorted(tops, key=lambda value: (abs(value - source.envelope[1]), value)):
                adjusted = _measured_repack(
                    plan,
                    packing,
                    source,
                    interface_left,
                    top,
                    "external-interface-boundary",
                )
                if adjusted is not None:
                    return adjusted, {
                        "kind": conflict.kind,
                        "obligation": conflict.obligation,
                        "fragment": source.fragment.block.id,
                        "from": list(source.envelope[:2]),
                        "to": [interface_left, top],
                    }
    target_width = target.envelope[2] - target.envelope[0]
    target_height = target.envelope[3] - target.envelope[1]
    lefts = {
        target.envelope[0] + first_point[0] + 5 * PITCH - second_point[0],
        source.envelope[2] + PITCH,
        source.envelope[2] + 2 * PITCH,
        source.envelope[0],
    }
    tops = {
        target.envelope[1] + first_point[1] - second_point[1],
        source.envelope[1],
        source.envelope[3] - target_height,
        source.envelope[3] + PITCH,
        source.envelope[1] - target_height - PITCH,
    }
    for obstacle in packing.fragments:
        if obstacle is target:
            continue
        lefts.update(
            (
                obstacle.envelope[0],
                obstacle.envelope[2] + PITCH,
                obstacle.envelope[0] - target_width - PITCH,
            )
        )
        tops.update(
            (
                obstacle.envelope[1],
                obstacle.envelope[3] + PITCH,
                obstacle.envelope[1] - target_height - PITCH,
            )
        )

    def overlaps(a, b):
        return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])

    ranked_origins = sorted(
        ((left, top) for left in lefts for top in tops),
        key=lambda pair: (
            abs(second_point[0] + pair[0] - target.envelope[0] - first_point[0])
            + abs(second_point[1] + pair[1] - target.envelope[1] - first_point[1]),
            pair,
        ),
    )[:4096]
    for left, top in ranked_origins:
        moved = _place(target.fragment, left, top)
        if moved.delta == target.delta:
            continue
        if any(
            overlaps(moved.envelope, other.envelope)
            for other in packing.fragments
            if other is not target
        ):
            continue
        if (
            moved.envelope[0] < LEFT
            or moved.envelope[1] < TOP
            or moved.envelope[2] > RIGHT
            or moved.envelope[3] > BOTTOM
        ):
            continue
        changed = tuple(moved if item is target else item for item in packing.fragments)
        min_x = min(item.content_envelope[0] for item in changed)
        max_x = max(item.content_envelope[2] for item in changed)
        min_y = min(item.content_envelope[1] for item in changed)
        max_y = max(item.content_envelope[3] for item in changed)
        if max_x - min_x > MAX_CONTENT_WIDTH or max_y - min_y > MAX_CONTENT_HEIGHT:
            continue
        moved_positions = {
            key: (point[0] + item.delta[0], point[1] + item.delta[1])
            for item in changed
            for key, point in item.fragment.positions.items()
        }
        trial = Draft(design, resolved, moved_positions, angles, [], [], [], [], {})
        try:
            check_placement_constraints(plan, trial.point)
        except PlacementConflict:
            continue
        return Packing(changed, packing.attempts + (f"structural:{conflict.kind}",)), {
            "kind": conflict.kind,
            "obligation": conflict.obligation,
            "fragment": target.fragment.block.id,
            "from": list(target.delta),
            "to": list(moved.delta),
            "changed_terminal_count": len(moved_positions),
        }
    raise InputError(f"STRUCTURAL_REPAIR_EXHAUSTED: {conflict.obligation}")


def _substitution_repack(
    plan,
    variants,
    packing: Packing,
    conflict: ConductorLengthConflict | RouteBlockedConflict | TypedConflict,
    ordinal: int,
):
    net = conflict.net
    current = {item.fragment.block.id: item.fragment for item in packing.fragments}
    incident = {
        block_id
        for edge in _routable_edges(plan)
        if edge.net == net
        for block_id in (edge.source, edge.target)
    }
    incident.update(
        fragment_id
        for presentation in plan.presentation_nets
        if presentation.id == net
        for fragment_id in presentation.fragments
    )

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
        raise InputError(f"VARIANT_REPAIR_EXHAUSTED: {net}")
    if isinstance(conflict, RouteBlockedConflict):
        blocked_gateway_ids = set(conflict.gateways)
        blocked_options = [
            option
            for option in options
            if any(
                gateway.id in blocked_gateway_ids
                for gateway in current[option[0]].gateways
                if gateway.net == net
            )
        ]
        if blocked_options:
            options = blocked_options
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


def _reservation_growth_repack(
    plan, packing: Packing, conflict: RouteBlockedConflict, ordinal: int
):
    """Apply the one bounded, witnessed reservation-growth repair.

    Route failures name the affected net.  Grow the first incident gateway's
    packing side by exactly one pitch and retain that extra channel reservation
    in the immutable replacement variant before repacking every fragment.
    """
    net = conflict.net
    current = {item.fragment.block.id: item.fragment for item in packing.fragments}
    candidates = sorted(
        (block_id, gateway)
        for block_id, fragment in current.items()
        for gateway in fragment.gateways
        if gateway.net == net
    )
    if not candidates:
        raise InputError(f"RESERVATION_GROWTH_NO_GATEWAY: {net}")
    blocked = [item for item in candidates if item[1].id in conflict.gateways]
    block_id, gateway = (blocked or candidates)[ordinal % len(blocked or candidates)]
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
    if new_envelope == fragment.envelope:
        raise InputError(f"RESERVATION_GROWTH_NO_CHANGE: {gateway.id}")
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
        "witness": str(conflict),
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


def _source_marker_placement(candidates, body, obstacles, wires=()):
    """Choose one existing electrical contact and a measured glyph orientation."""
    left, top, right, bottom = body
    for point in dict.fromkeys(candidates):
        for angle in (0, 180):
            local = (left, -top, right, -bottom)
            if angle == 180:
                local = (-right, bottom, -left, top)
            rect = tuple(v + d for v, d in zip(local, (*point, *point), strict=True))
            if rect[0] < LEFT or rect[1] < TOP or rect[2] > RIGHT or rect[3] > BOTTOM:
                continue
            if any(
                max(rect[0], other[0]) < min(rect[2], other[2])
                and max(rect[1], other[1]) < min(rect[3], other[3])
                for other in obstacles
            ):
                continue
            if any(
                (
                    first[0] == second[0]
                    and rect[0] < first[0] < rect[2]
                    and max(min(first[1], second[1]), rect[1])
                    < min(max(first[1], second[1]), rect[3])
                )
                or (
                    first[1] == second[1]
                    and rect[1] < first[1] < rect[3]
                    and max(min(first[0], second[0]), rect[0])
                    < min(max(first[0], second[0]), rect[2])
                )
                for first, second in wires
            ):
                continue
            return point, angle, rect
    raise InputError("COMPOSE_SOURCE_GLYPH_CLEARANCE: no measured source-marker slot")


def _assemble_candidate(design: dict, resolved: dict, plan, packing: Packing, retry: int):
    draft = Draft(design, resolved, {}, {}, [], [], [], [], {})
    conductors: list[ConductorSegment] = []
    reservations = [reservation for item in packing.fragments for reservation in item.reservations]
    occupied = []
    for placed in packing.fragments:
        fragment, delta = placed.fragment, placed.delta
        for key, point in fragment.positions.items():
            if key in draft.positions:
                raise TypedConflict(
                    ConflictKind.OWNERSHIP,
                    f"COMPOSE_GEOMETRY_OWNER_CONFLICT: {key}",
                    owners=(key[0],),
                )
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

    # Pin inequalities are hard gates on this exact translated candidate.
    placement_proofs = check_placement_constraints(plan, draft.point)

    route_trees = route_between_fragments(plan, packing.fragments, retry_index=retry)
    for tree in route_trees:
        reservations.extend(tree.planned_corridors)
        conductors.extend(
            ConductorSegment(first, second, tree.net, tree.owner, provenance)
            for (first, second), provenance in zip(
                tree.segments, tree.segment_provenance, strict=True
            )
        )
        for index, (first, second) in enumerate(tree.segments):
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
                    (tree.net, *tree.segment_provenance[index]),
                )
            )

    canonical_trees = []
    pruned_route_leaves: dict[str, int] = {}
    for net in sorted({segment.net for segment in conductors}):
        pins = tuple(
            draft.point(component["id"], pin.number)
            for component in design["components"]
            for unit, unit_pins in resolved[component["asset"]].units.items()
            if (component["id"], unit) in draft.positions
            for pin in unit_pins
            if any(
                net_item["id"] == net and [component["id"], pin.number] in net_item["members"]
                for net_item in design["nets"]
            )
        )
        required_contacts = (
            set(pins)
            | {point for label_net, point in draft.labels if label_net == net}
            | {
                gateway.point
                for item in packing.fragments
                for gateway in item.gateways
                if gateway.net == net
            }
        )
        net_segments = tuple(segment for segment in conductors if segment.net == net)
        removed = 0
        while True:
            tree = canonical_conductor_tree(
                net_segments,
                junctions=(
                    *draft.junctions,
                    *(point for route in route_trees for point in route.junctions),
                ),
                pins=pins,
            )
            redundant = {
                segment
                for segment in tree.segments
                if any(
                    tree.degree.get(point) == 1 and point not in required_contacts
                    for point in (segment.start, segment.end)
                )
            }
            if not redundant:
                break
            net_segments = tuple(segment for segment in tree.segments if segment not in redundant)
            removed += len(redundant)
            if not net_segments:
                raise InputError(f"CONDUCTOR_NET_MISSING: {net}")
        if removed:
            pruned_route_leaves[net] = removed
        canonical_trees.append(tree)
    conductors = [segment for tree in canonical_trees for segment in tree.segments]
    assertion_points = {}
    assertion_glyphs = {}
    marker_obstacles = [
        item.rect for item in occupied if item.kind in {"body", "text", "label", "pin"}
    ]
    marker_obstacles.extend(label_text_rect(net, point) for net, point in draft.labels)
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
        candidates.extend(
            sorted(
                {
                    point
                    for tree in canonical_trees
                    if tree.net == assertion["net"]
                    for segment in tree.segments
                    for point in (segment.start, segment.end)
                }
            )
        )
        if not candidates:
            raise InputError(
                f"COMPOSE_ASSERTION_PORT_MISSING: {assertion['id']}:{assertion['net']}"
            )
        source_body = resolved["power:PWR_FLAG"].bodies[0]
        point, angle, rect = _source_marker_placement(
            candidates,
            source_body,
            marker_obstacles,
            [(segment.start, segment.end) for segment in conductors],
        )
        assertion_points[assertion["id"]] = point
        assertion_glyphs[assertion["id"]] = rect
        draft.angles[(assertion["id"], 1)] = angle
        marker_obstacles.append(rect)
    net_proofs = []
    presentation_by_net = {item.id: item for item in plan.presentation_nets}
    for tree in canonical_trees:
        presentation = presentation_by_net.get(tree.net)
        if presentation is None:
            raise InputError(f"CONDUCTOR_NET_UNDECLARED: {tree.net}")
        net_proofs.append(
            prove_conductor_graph(
                tree,
                {terminal: draft.point(*terminal) for terminal in presentation.terminals},
                labels=(point for net, point in draft.labels if net == tree.net),
                allow_labeled_islands=not presentation.explicit_geometry_required,
                # The canonical junction inventory is the one serialization
                # will write; earlier local lists are construction inputs.
                declared_junctions=tree.junctions,
                intentional_ends=(
                    *(
                        gateway.point
                        for item in packing.fragments
                        for gateway in item.gateways
                        if gateway.net == tree.net and not presentation.explicit_geometry_required
                    ),
                    *(
                        assertion_points[assertion["id"]]
                        for assertion in design["power_assertions"]
                        if assertion["net"] == tree.net
                    ),
                ),
            )
        )
    missing_nets = set(presentation_by_net) - {tree.net for tree in canonical_trees}
    if missing_nets:
        raise InputError(f"CONDUCTOR_NET_MISSING: {sorted(missing_nets)}")
    tree_by_net = {tree.net: tree for tree in canonical_trees}
    gateway_proofs = []
    for item in packing.fragments:
        for gateway in item.gateways:
            tree = tree_by_net.get(gateway.net)
            if tree is None:
                raise TypedConflict(
                    ConflictKind.GATEWAY_WITNESS,
                    f"GATEWAY_NET_MISSING: {gateway.id}:{gateway.net}",
                    net=gateway.net,
                    owners=(item.fragment.block.id,),
                    repair_classes=("gateway_access", "distribution_placement"),
                )
            proved = prove_gateway_witnesses(
                tree,
                gateway,
                {terminal: draft.point(*terminal) for terminal in gateway.terminals},
                require_escape=False,
            )
            gateway_proofs.append((gateway, proved))
    prove_no_cross_net_contacts(conductors)
    terminal_inventory = {item.terminal for item in plan.terminals if item.net}
    proved_terminals = {
        terminal for proof in net_proofs for terminal, _ in proof.terminal_components
    }
    if terminal_inventory != proved_terminals:
        raise InputError(
            f"COMPOSE_TERMINAL_INVENTORY: missing={sorted(terminal_inventory - proved_terminals)} "
            f"extra={sorted(proved_terminals - terminal_inventory)}"
        )
    excessive = [tree for tree in canonical_trees if tree.length > 250_000_000]
    if excessive:
        worst = max(excessive, key=lambda tree: (tree.length, tree.net))
        local_segments = [
            segment
            for segment in conductors
            if segment.net == worst.net and not segment.owner.startswith("tree.")
        ]
        global_segments = [
            segment
            for segment in conductors
            if segment.net == worst.net and segment.owner.startswith("tree.")
        ]
        local_length = canonical_conductor_tree(local_segments).length if local_segments else 0
        global_length = canonical_conductor_tree(global_segments).length if global_segments else 0
        raise ConductorLengthConflict(worst.net, worst.length, local_length, global_length)
    draft.wires = [
        (segment.start, segment.end) for tree in canonical_trees for segment in tree.segments
    ]
    draft.wire_nets = [tree.net for tree in canonical_trees for _ in tree.segments]
    draft.junctions = [point for tree in canonical_trees for point in tree.junctions]

    component_ids = {component["id"] for component in design["components"]}
    expected = set(plan.owners)
    actual = {key for key in draft.positions if key[0] in component_ids}
    if actual != expected:
        raise TypedConflict(
            ConflictKind.OWNERSHIP,
            f"COMPOSE_OWNER_INCOMPLETE: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}",
            owners=tuple(sorted({item[0] for item in expected ^ actual})),
        )
    for assertion in design["power_assertions"]:
        point = assertion_points[assertion["id"]]
        draft.positions[(assertion["id"], 1)] = point
        # KiCad serializes hidden source properties too. Give them a measured
        # on-page position instead of the emitter's unmeasured fallback offset.
        draft.text_positions[(assertion["id"], 1)] = (
            min(max(point[0], LEFT), RIGHT),
            min(max(point[1], TOP + 2 * PITCH), BOTTOM - 2 * PITCH),
        )
        text_x, text_y = draft.text_positions[(assertion["id"], 1)]
        for offset in (0, 2 * PITCH):
            property_item = GeometryItem(
                f"{assertion['id']}.hidden_property.{offset}",
                "source_property",
                assertion["id"],
                (text_x, text_y + offset, text_x, text_y + offset),
            )
            occupied.append(property_item)
            reservations.append(
                Reservation(
                    f"source_property.{assertion['id']}.{offset}",
                    "exclusive",
                    assertion["id"],
                    "source_property",
                    property_item.rect,
                )
            )
        glyph = GeometryItem(
            assertion["id"],
            "source_glyph",
            assertion["id"],
            assertion_glyphs[assertion["id"]],
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

    # Locked KiCad A4 worksheet: native border starts at (177.0022, 166.0072) mm.
    # Reserve its stroke as an obstacle independently of the 210 x 140 spread gate.
    worksheet = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
    page_geometry = [item.rect for item in occupied] + [
        (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])) for a, b in draft.wires
    ]
    for rectangle in page_geometry:
        if (
            rectangle[0] < worksheet[2]
            and rectangle[2] > worksheet[0]
            and rectangle[1] < worksheet[3]
            and rectangle[3] > worksheet[1]
        ):
            raise TypedConflict(
                ConflictKind.PAGE_SPREAD,
                f"PAGE_WORKSHEET_OVERLAP: geometry={rectangle}",
                offending_geometry=(rectangle,),
            )

    allocation_witnesses = prove_reservation_allocation(occupied, reservations)
    final_rect = (
        min(item.rect[0] for item in occupied),
        min(item.rect[1] for item in occupied),
        max(item.rect[2] for item in occupied),
        max(item.rect[3] for item in occupied),
    )
    # The packing corridor uses an inset search box. Final occupied geometry
    # is certified against the historical A4 content margins themselves.
    if (
        final_rect[0] < 20_320_000
        or final_rect[1] < 25_400_000
        or final_rect[2] > 276_680_000
        or final_rect[3] > 184_600_000
    ):
        raise TypedConflict(
            ConflictKind.PAGE_SPREAD,
            f"PAGE_CONTENT_OVERFLOW: final={final_rect}",
            offending_geometry=(final_rect,),
        )
    final_width = final_rect[2] - final_rect[0]
    final_height = final_rect[3] - final_rect[1]
    if final_width > MAX_CONTENT_WIDTH or final_height > MAX_CONTENT_HEIGHT:
        raise TypedConflict(
            ConflictKind.PAGE_SPREAD,
            f"SPREAD_OVERFLOW: actual={final_width}x{final_height} "
            f"threshold={MAX_CONTENT_WIDTH}x{MAX_CONTENT_HEIGHT}",
            offending_geometry=(final_rect,),
            actual=max(final_width, final_height),
            limit=max(MAX_CONTENT_WIDTH, MAX_CONTENT_HEIGHT),
        )
    metrics = measure(design, resolved, draft)
    invalid_metrics = {
        key: metrics.get(key)
        for key in (
            "body_overlap_count",
            "wire_through_body_count",
            "wire_through_text_count",
            "unrelated_wire_crossing_count",
            "unrouted_pin_count",
        )
        if metrics.get(key) != 0
    }
    if invalid_metrics or not metrics.get("page_margin_pass"):
        raise TypedConflict(
            ConflictKind.COLLISION,
            f"COMPOSE_GEOMETRY_CERTIFICATE_FAILED: collisions={invalid_metrics} "
            f"page_margin={metrics.get('page_margin_pass')}",
            owners=tuple(sorted(invalid_metrics)),
        )
    metrics.update(
        {
            "semantic_block_count": len(plan.blocks),
            "semantic_edge_count": len(plan.edges),
            "packing_attempts": list(packing.attempts),
            "final_content_envelope": list(final_rect),
            "final_content_width_mm": final_width / 1_000_000,
            "final_content_height_mm": final_height / 1_000_000,
            "reservation_containment_pass": True,
            "reservation_allocation_count": len(allocation_witnesses),
            "reservation_allocation_witnesses": [
                {"owner": owner, "geometry": item, "reservation": reservation}
                for owner, item, reservation in allocation_witnesses
            ],
            "pre_emission_conductor_components": {
                proof.net: len(proof.components) for proof in net_proofs
            },
            "pre_emission_terminal_coverage": {
                proof.net: len(proof.terminal_components) for proof in net_proofs
            },
            "pre_emission_precedence_count": len(plan.precedence),
            "pruned_route_leaves": pruned_route_leaves,
            "pre_emission_placement_proofs": [list(item) for item in placement_proofs],
            "pre_emission_net_witnesses": [
                {
                    "net": proof.net,
                    "component_count": len(proof.components),
                    "terminal_components": [
                        [list(terminal), component]
                        for terminal, component in proof.terminal_components
                    ],
                    "label_components": [
                        [list(point), component] for point, component in proof.label_components
                    ],
                    "canonical_length_nm": proof.length,
                }
                for proof in net_proofs
            ],
            "pre_emission_terminal_inventory_count": len(terminal_inventory),
            "pre_emission_gateway_witness_count": len(gateway_proofs),
            "pre_emission_gateway_witnesses": [
                {
                    "id": gateway.id,
                    "net": gateway.net,
                    "point": list(gateway.point),
                    "anchor": list(gateway.anchor),
                    "terminals": [
                        {"id": list(terminal), "point": list(draft.point(*terminal))}
                        for terminal in proved
                    ],
                    "proved": True,
                }
                for gateway, proved in gateway_proofs
            ],
            "pre_emission_local_span_count": len(plan.local_spans),
        }
    )
    return draft, route_trees, canonical_trees, tuple(reservations), metrics


def _structural_signature(packing: Packing) -> tuple[tuple, ...]:
    """Normalize row and left-to-right decisions without absolute coordinates."""
    items = tuple(item for item in packing.fragments if item.fragment.block.kind != "interface")
    x_order = {
        item.fragment.block.id: index
        for index, item in enumerate(
            sorted(
                items,
                key=lambda item: (
                    item.envelope[0] + item.envelope[2],
                    item.fragment.block.id,
                ),
            )
        )
    }
    band_tops = []
    band_by_top = {}
    for top in sorted({item.envelope[1] for item in items}):
        if not band_tops or top - band_tops[-1] > PITCH:
            band_tops.append(top)
        band_by_top[top] = len(band_tops) - 1
    return tuple(
        (
            item.fragment.block.kind,
            x_order[item.fragment.block.id],
            band_by_top[item.envelope[1]],
            item.envelope[2] - item.envelope[0] > item.envelope[3] - item.envelope[1],
        )
        for item in sorted(items, key=lambda item: item.fragment.block.id)
    )


def compose_with_evidence(design: dict, resolved: dict) -> tuple[Scene, dict]:
    """Compose using at most eight seeds and four attempts per seed."""
    plan = semantic_plan(design, resolved)
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
                    elif round_index == 2 and isinstance(last_conflict, ConductorLengthConflict):
                        working_packing, substitution = _distribution_repack(
                            design, resolved, plan, working_packing, last_conflict
                        )
                    elif (
                        round_index == 2
                        and isinstance(last_conflict, TypedConflict)
                        and last_conflict.net is not None
                        and "distribution_placement" in last_conflict.repair_classes
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
            route_retry = 1 if round_index == 1 else 2 if round_index == 3 else 0
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
                candidate = _assemble_candidate(
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
            semantic_penalties = semantic_composition_penalties(plan, working_packing)
            compactness_penalties = compactness_whitespace_penalties(working_packing)
            selection_key = composition_candidate_key(plan, working_packing, routing_compactness)
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
                    "local_construction": variant.construction_evidence(),
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
                            "local_construction": item.fragment.construction_evidence(),
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
                "complete_attempts_used": complete_attempts,
            },
        }
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
    scene = certify_scene_geometry(
        Scene(
            draft.positions,
            draft.wires,
            draft.wire_nets,
            draft.labels,
            draft.junctions,
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
