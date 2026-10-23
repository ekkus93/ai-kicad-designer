"""Implementation details for m2 compose repairs."""

from __future__ import annotations

from dataclasses import replace

from .ir import InputError
from .m2_conflicts import ConflictKind, TypedConflict
from .m2_geometry import (
    Reservation,
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
    pack_fragment_candidates,
)
from .m2_route import (
    RouteBlockedConflict,
    _crosses,
    _routable_edges,
)
from .m2_semantics import PlacementConflict, check_placement_constraints
from .m2a import PITCH
from .m2b import Draft


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
            mirrors = {key: axis for item in changed for key, axis in item.fragment.mirrors.items()}
            draft = Draft(design, resolved, positions, angles, [], [], [], [], {}, mirrors)
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
    mirrors = {
        key: axis for item in packing.fragments for key, axis in item.fragment.mirrors.items()
    }
    draft = Draft(design, resolved, positions, angles, [], [], [], [], {}, mirrors)
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
        mirrors = {key: axis for item in changed for key, axis in item.fragment.mirrors.items()}
        trial = Draft(design, resolved, moved_positions, angles, [], [], [], [], {}, mirrors)
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
