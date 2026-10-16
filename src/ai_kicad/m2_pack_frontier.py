"""Implementation details for m2 pack frontier."""

from __future__ import annotations

from .m2_fragments import Rect
from .m2_pack import (
    CANDIDATE_BUDGET,
    CHANNEL_GAP,
    OUTPUT_FRONTIER_CLEARANCE,
)
from .m2_pack_core import (
    Packing,
    PlacedFragment,
    _place,
    _reference_escape_directions,
)
from .m2_pack_distribution import _measured_repack
from .m2_semantics import SemanticPlan
from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations
from .m2a import PITCH


def _interface_frontier_candidates(
    plan: SemanticPlan,
    baseline: Packing,
) -> tuple[Packing, ...]:
    """Explore bounded, measured input/output frontier placements.

    Inputs attach immediately before their downstream signal stage and outputs
    immediately after their producer. The same legality/geometry checks as
    structural repair apply; neither a fixture name nor a net literal informs
    the search. Bidirectional interfaces are deliberately not forced to a side.
    """
    # Keep bounded frontier search consistent with independent signal-flow
    # observation, including unique terminal-backed passive interfaces.
    relations = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
    }
    relations.update(
        (item.source_fragment, item.target_fragment, item.net) for item in plan.precedence
    )
    relations.update(inferred_passive_interface_signal_relations(plan))

    def frontier_roles(block) -> set[str]:
        roles = {port.role for port in block.ports}
        for source, target, _net in relations:
            if source == block.id:
                roles.add("signal_in")
            if target == block.id:
                roles.add("signal_out")
        return roles

    def frontier_owner_ids(interface_id: str, role: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    target if role == "signal_in" else source
                    for source, target, _net in relations
                    if role == "signal_in"
                    and source == interface_id
                    or role == "signal_out"
                    and target == interface_id
                }
            )
        )

    def frontier_rows(
        owner: PlacedFragment, interface: PlacedFragment, height: int
    ) -> tuple[int, ...]:
        """Try the signal row, measured aligned rows, then adjacent legal lanes.

        The connector's lead belongs on the row of the owner gateway it feeds
        or drains, so that lane comes first; an owner whose envelope hangs a
        shunt below its signal row is not centred on that row. Crowded
        circuits can have an unrelated block occupying the aligned options. A
        one-gap lane above or below the owner's envelope may be legal without
        displacing any functional stage or relaxing constraints.
        """
        owner_rows: dict[str, int] = {}
        for gateway in owner.gateways:
            owner_rows[gateway.net] = min(
                owner_rows.get(gateway.net, gateway.point[1]), gateway.point[1]
            )
        signal_rows = tuple(
            owner_rows[gateway.net] - (gateway.point[1] - interface.envelope[1])
            for gateway in interface.gateways
            if gateway.net in owner_rows
        )
        centered = (owner.envelope[1] + owner.envelope[3] - height) // 2
        # Alignment remains preferred; nearby lanes are fallbacks only.
        # Preserve order while dropping duplicate slots.
        return tuple(
            dict.fromkeys(
                (
                    *signal_rows,
                    centered,
                    owner.envelope[1],
                    owner.envelope[1] - height - CHANNEL_GAP,
                    owner.envelope[3] + CHANNEL_GAP,
                )
            )
        )

    def frontier_repack(
        packing: Packing,
        interface: PlacedFragment,
        owner: PlacedFragment,
        role: str,
        left: int,
        top: int,
        label: str,
    ) -> Packing | None:
        """Swap mutually reversed interface blockers when a frontier is occupied.

        A misplaced input may occupy the only legal output slot and vice versa.
        Displace only a directed interface whose side error strictly improves;
        never displace a functional stage or a correctly sided interface.
        The measured placement and precedence proofs remain mandatory.
        """
        direct = _measured_repack(plan, packing, interface, left, top, label)
        if direct is not None:
            return direct
        target = _place(interface.fragment, left, top)
        blockers = [
            item
            for item in packing.fragments
            if item.fragment.block.id != interface.fragment.block.id
            and max(target.envelope[0], item.envelope[0])
            < min(target.envelope[2], item.envelope[2])
            and max(target.envelope[1], item.envelope[1])
            < min(target.envelope[3], item.envelope[3])
        ]
        if len(blockers) != 1 or blockers[0].fragment.block.kind != "interface":
            return None
        blocker = blockers[0]
        blocker_roles = frontier_roles(blocker.fragment.block)
        if not blocker_roles & {"signal_in", "signal_out"}:
            # An undirected connector (a reference or rail pin) has no row of
            # its own to defend; it yields the directed interface's aligned
            # slot. The directed interface's side error must not worsen (lane
            # ranking already prefers its signal row), and the measured
            # placement proofs still apply.
            target_violation = (
                max(0, target.envelope[2] - owner.envelope[0])
                if role == "signal_in"
                else max(0, owner.envelope[2] - target.envelope[0])
            )
            current_violation = (
                max(0, interface.envelope[2] - owner.envelope[0])
                if role == "signal_in"
                else max(0, owner.envelope[2] - interface.envelope[0])
            )
            if target_violation > current_violation:
                return None
            # A displaced reference connector belongs beside its reference
            # rail: the lowest reference escape row of the stages it serves.
            # Try that measured slot first, then the vacated slot.
            blocker_nets = {port.net for port in blocker.fragment.block.ports}
            blocker_gateway = next(iter(blocker.gateways), None)
            rail_rows = sorted(
                {
                    # The rail runs on the escape row just past the gateway.
                    gateway.point[1]
                    + {"down": PITCH, "up": -PITCH}.get(gateway.escape_direction, 0)
                    for item in packing.fragments
                    if item.fragment.block.kind != "interface"
                    for gateway in item.gateways
                    if gateway.net in blocker_nets
                    and _reference_escape_directions(item.fragment)
                    and any(
                        port.port.id == gateway.id and port.port.role == "reference"
                        for port in item.fragment.ports
                    )
                },
                reverse=True,
            )
            if blocker_gateway is not None:
                pin_offset = blocker_gateway.point[1] - blocker.envelope[1]
                for rail_y in rail_rows:
                    beside_rail = _measured_repack(
                        plan,
                        packing,
                        interface,
                        left,
                        top,
                        label,
                        additional_moves=((blocker, left, rail_y - pin_offset),),
                    )
                    if beside_rail is not None:
                        return beside_rail
            return _measured_repack(plan, packing, interface, left, top, label, displaced=blocker)
        if blocker_roles not in ({"signal_in"}, {"signal_out"}):
            return None
        blocker_role = next(iter(blocker_roles))
        by_id = {item.fragment.block.id: item for item in packing.fragments}
        blocker_owners = tuple(
            by_id[owner_id]
            for owner_id in frontier_owner_ids(blocker.fragment.block.id, blocker_role)
            if owner_id in by_id and by_id[owner_id].fragment.block.kind != "interface"
        )
        if not blocker_owners:
            return None

        def side_violation(
            placed: PlacedFragment, peers: tuple[PlacedFragment, ...], side: str
        ) -> int:
            if side == "signal_in":
                return max(max(0, placed.envelope[2] - peer.envelope[0]) for peer in peers)
            return max(max(0, peer.envelope[2] - placed.envelope[0]) for peer in peers)

        if side_violation(interface, (owner,), role) <= side_violation(target, (owner,), role):
            return None
        relocated = _place(blocker.fragment, interface.envelope[0], interface.envelope[1])
        if side_violation(relocated, blocker_owners, blocker_role) >= side_violation(
            blocker, blocker_owners, blocker_role
        ):
            return None
        return _measured_repack(plan, packing, interface, left, top, label, displaced=blocker)

    output_frontier_ids = {
        block.id
        for block in plan.blocks
        if block.kind == "interface"
        and "signal_out" in frontier_roles(block)
        and not {"signal_in", "signal_out"} <= frontier_roles(block)
    }

    def frontier_search(base: Packing, role: str, label: str) -> Packing | None:
        """Move every directed interface of one role to its measured frontier."""
        by_id = {item.fragment.block.id: item for item in base.fragments}
        options: list[tuple[tuple[int, int, int, int, str, int], Packing]] = []
        for block in sorted(plan.blocks, key=lambda item: item.id):
            if block.kind != "interface" or block.id not in by_id:
                continue
            roles = frontier_roles(block)
            if role not in roles or {"signal_in", "signal_out"} <= roles:
                continue
            interface = by_id[block.id]
            width = interface.envelope[2] - interface.envelope[0]
            height = interface.envelope[3] - interface.envelope[1]
            owners = frontier_owner_ids(block.id, role)
            for owner_id in owners:
                owner = by_id.get(owner_id)
                if owner is None or owner.fragment.block.kind == "interface":
                    continue
                left = (
                    owner.envelope[0] - width - CHANNEL_GAP
                    if role == "signal_in"
                    else owner.envelope[2] + CHANNEL_GAP
                )
                if role == "signal_out":
                    # Outputs belong on the outside edge of the drawing, not
                    # merely just beyond their producer. This keeps unrelated
                    # connectors and their return wiring from visually boxing
                    # in an output that happens to share the producer's row.
                    outer_edge = max(
                        (
                            item.envelope[2]
                            for item in base.fragments
                            if item.fragment.block.id not in output_frontier_ids
                        ),
                        default=left - CHANNEL_GAP,
                    )
                    output_column = max(
                        (
                            item.envelope[0]
                            for item in base.fragments
                            if item.fragment.block.id in output_frontier_ids
                        ),
                        default=left,
                    )
                    left = max(
                        left,
                        outer_edge + OUTPUT_FRONTIER_CLEARANCE,
                        output_column,
                    )
                # Align both centers and upper edges as separate legal choices.
                for lane_rank, top in enumerate(frontier_rows(owner, interface, height)):
                    candidate = frontier_repack(base, interface, owner, role, left, top, label)
                    if candidate is None:
                        continue
                    # Repair semantic side violations before cosmetic row drift:
                    # one output slot must not ignore a left-of-producer output
                    # in favor of aligning an already right-side connector.
                    side_violation = (
                        max(0, interface.envelope[2] - owner.envelope[0])
                        if role == "signal_in"
                        else max(0, owner.envelope[2] - interface.envelope[0])
                    )
                    initial_row_gap = abs(
                        interface.envelope[1]
                        + interface.envelope[3]
                        - owner.envelope[1]
                        - owner.envelope[3]
                    )
                    frontier_deficit = (
                        max(0, left - interface.envelope[0]) if role == "signal_out" else 0
                    )
                    distance = abs(left - interface.envelope[0]) + abs(top - interface.envelope[1])
                    options.append(
                        (
                            (
                                -frontier_deficit,
                                -side_violation,
                                -initial_row_gap,
                                lane_rank,
                                distance,
                                block.id,
                                top,
                            ),
                            candidate,
                        )
                    )
        if not options:
            return None
        selected = min(options, key=lambda item: item[0])[1]
        # One frontier candidate may need to repair several distinct
        # directed interfaces. Apply further *measured* improvements to
        # the same candidate; a single-interface-only move leaves other
        # reversed output connectors untouched under the eight-seed cap.
        # Stop after at most one successful repair per interface. Never
        # move a correctly sided interface just to fill this budget.
        for _ in range(len(by_id) - 1):
            current = {item.fragment.block.id: item for item in selected.fragments}
            repairs: list[tuple[tuple[int, int, int, int, str, int], Packing]] = []
            for block in sorted(plan.blocks, key=lambda item: item.id):
                if block.kind != "interface" or block.id not in current:
                    continue
                roles = frontier_roles(block)
                if role not in roles or {"signal_in", "signal_out"} <= roles:
                    continue
                interface = current[block.id]
                owners = tuple(
                    current[owner_id]
                    for owner_id in frontier_owner_ids(block.id, role)
                    if owner_id in current and current[owner_id].fragment.block.kind != "interface"
                )
                if not owners:
                    continue

                def worst_violation(placed: PlacedFragment, owners=owners) -> int:
                    if role == "signal_in":
                        return max(
                            max(0, placed.envelope[2] - owner.envelope[0]) for owner in owners
                        )
                    return max(max(0, owner.envelope[2] - placed.envelope[0]) for owner in owners)

                before = worst_violation(interface)
                if before == 0:
                    continue
                width = interface.envelope[2] - interface.envelope[0]
                height = interface.envelope[3] - interface.envelope[1]
                for owner in owners:
                    left = (
                        owner.envelope[0] - width - CHANNEL_GAP
                        if role == "signal_in"
                        else owner.envelope[2] + CHANNEL_GAP
                    )
                    for lane_rank, top in enumerate(frontier_rows(owner, interface, height)):
                        proposal = frontier_repack(
                            selected, interface, owner, role, left, top, label
                        )
                        if proposal is None:
                            continue
                        moved = next(
                            item
                            for item in proposal.fragments
                            if item.fragment.block.id == block.id
                        )
                        after = worst_violation(moved)
                        if after >= before:
                            continue
                        travel = abs(left - interface.envelope[0]) + abs(
                            top - interface.envelope[1]
                        )
                        repairs.append(
                            (
                                (after - before, after, lane_rank, travel, block.id, top),
                                proposal,
                            )
                        )
            if not repairs:
                break
            selected = min(repairs, key=lambda item: item[0])[1]
        return selected

    def staggered_output(selected: Packing) -> Packing | None:
        role = "signal_out"
        current = {item.fragment.block.id: item for item in selected.fragments}
        output_column = max(
            (current[block_id].envelope[0] for block_id in output_frontier_ids),
            default=0,
        )
        for block_id in sorted(output_frontier_ids):
            interface = current.get(block_id)
            if interface is None or interface.envelope[0] >= output_column:
                continue
            owners = tuple(
                current[owner_id]
                for owner_id in frontier_owner_ids(block_id, role)
                if owner_id in current and current[owner_id].fragment.block.kind != "interface"
            )
            if not owners:
                continue
            owner = min(
                owners,
                key=lambda item: (
                    abs(item.envelope[1] - interface.envelope[1]),
                    item.fragment.block.id,
                ),
            )
            left = min(interface.envelope[0] + 9 * CHANNEL_GAP, output_column)
            proposal = frontier_repack(
                selected,
                interface,
                owner,
                role,
                left,
                interface.envelope[1],
                "interface-frontier-output-staggered",
            )
            if proposal is not None:
                return proposal
        return None

    alternatives: list[Packing] = []
    input_option = frontier_search(baseline, "signal_in", "interface-frontier-input")
    if input_option is not None:
        alternatives.append(input_option)
    output_option = frontier_search(baseline, "signal_out", "interface-frontier-output")
    if output_option is not None:
        alternatives.append(output_option)
        staggered = staggered_output(output_option)
        if staggered is not None:
            alternatives.append(staggered)
    if input_option is not None and output_option is not None:
        # Inputs and outputs reach their frontiers together. A one-role move
        # leaves the other role's connectors in their stacked seed column, so
        # neither single-role candidate shows the drawing with every directed
        # interface on its own edge. Outputs move first: they leave the seed
        # column for the outer edge and free the aligned slots an input needs.
        # The same measured proofs apply in turn.
        combined = frontier_search(output_option, "signal_in", "interface-frontier-combined")
        if combined is None:
            combined = frontier_search(input_option, "signal_out", "interface-frontier-combined")
        if combined is not None:
            alternatives.append(combined)
    return tuple(alternatives)


def _envelope_manhattan_gap(first: Rect, second: Rect) -> int:
    """Measure the axis-separated free gap between two measured reservations."""
    return max(0, first[0] - second[2], second[0] - first[2]) + max(
        0, first[1] - second[3], second[1] - first[3]
    )


def _local_signal_proximity_candidates(
    plan: SemanticPlan, baseline: Packing
) -> tuple[Packing, ...]:
    """Try a legal direct-connection-friendly position for a local signal pair.

    A two-fragment signal presentation net is eligible only when it has no
    mandatory global distribution geometry and neither endpoint is an external
    interface. This is a *placement* alternative, not proof that a direct wire
    can be routed: the downstream route and electrical gates remain mandatory.
    Shared nets and power/reference distribution are never pulled together.
    """
    by_id = {item.fragment.block.id: item for item in baseline.fragments}
    directed = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
    }
    directed.update(
        (item.source_fragment, item.target_fragment, item.net) for item in plan.precedence
    )
    options: list[tuple[tuple[int, int, str, str, int, int], Packing]] = []
    trials = 0
    for net in sorted(plan.presentation_nets, key=lambda item: item.id):
        if net.role != "signal" or net.explicit_geometry_required or len(set(net.fragments)) != 2:
            continue
        first_id, second_id = sorted(set(net.fragments))
        first, second = by_id.get(first_id), by_id.get(second_id)
        if first is None or second is None:
            continue
        if any(
            item.fragment.block.kind == "interface" or item.fragment.block.unused
            for item in (first, second)
        ):
            continue
        forward = (first_id, second_id, net.id) in directed
        backward = (second_id, first_id, net.id) in directed
        if forward != backward:
            anchor, moving = (first, second) if forward else (second, first)
        elif len(set(net.producer_fragments)) == 1:
            producer = net.producer_fragments[0]
            anchor, moving = (first, second) if producer == first_id else (second, first)
            if producer not in {first_id, second_id}:
                continue
        else:
            anchor, moving = sorted(
                (first, second), key=lambda item: (item.envelope[0], item.fragment.block.id)
            )
        # Gap is measured between reserved envelopes, not an arbitrary refdes
        # or net-label anchor. Skip already-local pairs and identical states.
        old_gap = _envelope_manhattan_gap(anchor.envelope, moving.envelope)
        if old_gap <= 2 * PITCH:
            continue
        width = moving.envelope[2] - moving.envelope[0]
        height = moving.envelope[3] - moving.envelope[1]
        # Respect directed primary flow. Undirected pairs may use either side.
        # Try the direction-preserving local corridor first, then a nearby
        # upper/lower lane when unrelated geometry obstructs the aligned slot.
        # Every candidate still passes the measured hard placement gates.
        right = anchor.envelope[2] + CHANNEL_GAP
        slots = [
            (right, anchor.envelope[1]),
            (right, (anchor.envelope[1] + anchor.envelope[3] - height) // 2),
            (right, anchor.envelope[3] + CHANNEL_GAP),
            (right, anchor.envelope[1] - height - CHANNEL_GAP),
        ]
        if forward == backward:
            slots.extend(
                (
                    (anchor.envelope[0] - width - CHANNEL_GAP, anchor.envelope[1]),
                    (anchor.envelope[0], anchor.envelope[3] + CHANNEL_GAP),
                    (anchor.envelope[0], anchor.envelope[1] - height - CHANNEL_GAP),
                )
            )
        for x, y in dict.fromkeys(slots):
            if trials >= CANDIDATE_BUDGET * 4:
                break
            trials += 1
            proposal = _measured_repack(
                plan, baseline, moving, x, y, "local-signal-direct-proximity"
            )
            if proposal is None:
                continue
            moved = next(
                item
                for item in proposal.fragments
                if item.fragment.block.id == moving.fragment.block.id
            )
            new_gap = _envelope_manhattan_gap(anchor.envelope, moved.envelope)
            if new_gap >= old_gap:
                continue
            options.append(
                (
                    (
                        new_gap,
                        -(old_gap - new_gap),
                        anchor.fragment.block.id,
                        moving.fragment.block.id,
                        x,
                        y,
                    ),
                    proposal,
                )
            )
        if trials >= CANDIDATE_BUDGET * 4:
            break
    return (min(options, key=lambda item: item[0])[1],) if options else ()
