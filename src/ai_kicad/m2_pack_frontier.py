"""Implementation details for m2 pack frontier."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ir import InputError
from .m2_fragments_types import Rect
from .m2_pack_constants import (
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
from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def _has_package_blocked_reference_output(plan: SemanticPlan, packing: Packing) -> bool:
    """Return whether a directed output's owner-local lane is blocked by a reference package."""
    by_id = {item.fragment.block.id: item for item in packing.fragments}
    relations = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
    }
    relations.update(
        (item.source_fragment, item.target_fragment, item.net) for item in plan.precedence
    )
    relations.update(inferred_passive_interface_signal_relations(plan))
    generated_references = {
        net.id
        for net in plan.presentation_nets
        if net.internally_generated and len(net.fragments) >= 4
    }
    generated_references = {
        net.id
        for net in plan.presentation_nets
        if net.internally_generated and len(net.fragments) >= 4
    }
    for source_id, target_id, net_id in relations:
        owner = by_id.get(source_id)
        interface = by_id.get(target_id)
        if (
            owner is None
            or interface is None
            or interface.fragment.block.kind != "interface"
            or not any(gateway.net == net_id for gateway in owner.gateways)
        ):
            continue
        output_gateway = next(
            (gateway for gateway in interface.gateways if gateway.net == net_id), None
        )
        if output_gateway is None:
            continue
        row = min(gateway.point[1] for gateway in owner.gateways if gateway.net == net_id)
        top = row - (output_gateway.point[1] - interface.envelope[1])
        target = _place(
            interface.fragment,
            owner.envelope[2] + CHANNEL_GAP,
            top,
        )
        for blocker in packing.fragments:
            if blocker.fragment.block.kind != "package_power":
                continue
            overlaps = max(target.envelope[0], blocker.envelope[0]) < min(
                target.envelope[2], blocker.envelope[2]
            ) and max(target.envelope[1], blocker.envelope[1]) < min(
                target.envelope[3], blocker.envelope[3]
            )
            if overlaps and any(
                gateway.id.rsplit(".", 1)[-1] == "reference" and gateway.net in generated_references
                for gateway in blocker.gateways
            ):
                return True
    return False


def _observed_x(item: PlacedFragment) -> int:
    """Return the stable horizontal center of a fragment's measured text."""
    positions = item.fragment.text_positions
    xs = sorted(
        positions[occurrence][0] + item.delta[0]
        for occurrence in item.fragment.block.occurrences
        if occurrence in positions
    )
    if xs:
        return (xs[0] + xs[-1]) // 2
    return (item.envelope[0] + item.envelope[2]) // 2


def _interface_frontier_candidates(
    plan: SemanticPlan,
    baseline: Packing,
    *,
    route_check: bool = False,
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
    generated_references = {
        net.id
        for net in plan.presentation_nets
        if net.internally_generated and len(net.fragments) >= 4
    }

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
        signal_lanes = tuple(
            row + offset * PITCH for row in signal_rows for offset in (-4, -3, -2, -1, 1, 2, 3, 4)
        )
        centered = (owner.envelope[1] + owner.envelope[3] - height) // 2
        # Alignment remains preferred; nearby lanes are fallbacks only.
        # Preserve order while dropping duplicate slots.
        return tuple(
            dict.fromkeys(
                (
                    *signal_rows,
                    *signal_lanes,
                    centered,
                    owner.envelope[1],
                    owner.envelope[1] - height - CHANNEL_GAP,
                    owner.envelope[3] + CHANNEL_GAP,
                )
            )
        )

    def side_violation(placed: PlacedFragment, peers: tuple[PlacedFragment, ...], side: str) -> int:
        if side == "signal_in":
            return max(max(0, _observed_x(placed) - _observed_x(peer)) for peer in peers)
        return max(max(0, _observed_x(peer) - _observed_x(placed)) for peer in peers)

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
        if (
            route_check
            and role == "signal_out"
            and len(blockers) == 1
            and blockers[0].fragment.block.kind == "package_power"
        ):
            blocker = blockers[0]
            clearance = max(0, target.envelope[2] - blocker.envelope[0])
            package_dx = ((clearance + PITCH - 1) // PITCH) * PITCH
            reference_gateway = next(
                (
                    gateway
                    for gateway in blocker.gateways
                    if gateway.id.rsplit(".", 1)[-1] == "reference"
                ),
                None,
            )
            reference_net = next(
                (
                    net
                    for net in plan.presentation_nets
                    if reference_gateway is not None
                    and net.id == reference_gateway.net
                    and net.internally_generated
                    and net.id in generated_references
                    and len(net.fragments) >= 4
                ),
                None,
            )
            if package_dx and reference_gateway is not None and reference_net is not None:
                by_id = {item.fragment.block.id: item for item in packing.fragments}
                cluster = tuple(
                    by_id[fragment_id]
                    for fragment_id in reference_net.fragments
                    if fragment_id in by_id
                    and fragment_id != blocker.fragment.block.id
                    and fragment_id != interface.fragment.block.id
                )
                peer_x = [
                    gateway.point[0]
                    for item in cluster
                    for gateway in item.gateways
                    if gateway.net == reference_net.id
                ]
                anchor_x = reference_gateway.point[0] + package_dx
                direction = 1 if not peer_x or anchor_x >= sum(peer_x) // len(peer_x) else -1
                for cluster_steps in range(17):
                    additional_moves = (
                        (blocker, blocker.envelope[0] + package_dx, blocker.envelope[1]),
                        *(
                            (
                                item,
                                item.envelope[0] + direction * cluster_steps * PITCH,
                                item.envelope[1],
                            )
                            for item in cluster
                        ),
                    )
                    proposal = _measured_repack(
                        plan,
                        packing,
                        interface,
                        left,
                        top,
                        label,
                        additional_moves=additional_moves,
                    )
                    if proposal is None:
                        continue
                    from .m2_route import route_between_fragments

                    try:
                        route_between_fragments(plan, proposal.fragments)
                    except InputError:
                        continue
                    return Packing(
                        proposal.fragments,
                        (
                            *proposal.attempts[:-1],
                            "coupled-reference-frontier",
                            proposal.attempts[-1],
                        ),
                    )
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

    def frontier_search(
        base: Packing,
        role: str,
        label: str,
        *,
        only_interface_ids: frozenset[str] | None = None,
    ) -> Packing | None:
        """Move every directed interface of one role to its measured frontier."""
        by_id = {item.fragment.block.id: item for item in base.fragments}
        options: list[tuple[tuple[int, int, int, int, str, int], Packing]] = []
        coupled_reference_options: list[Packing] = []
        for block in sorted(plan.blocks, key=lambda item: item.id):
            if block.kind != "interface" or block.id not in by_id:
                continue
            if only_interface_ids is not None and block.id not in only_interface_ids:
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
                local_left = (
                    owner.envelope[0] - width - CHANNEL_GAP - 2 * PITCH
                    if role == "signal_in"
                    else owner.envelope[2] + CHANNEL_GAP
                )
                left_choices = (local_left,)
                if role == "signal_out":
                    # Prefer the nearest legal point beyond the producer. Keep
                    # the outside edge as a fallback when nearby geometry
                    # blocks the direct route or leaves the output visually
                    # boxed in by unrelated content.
                    outer_edge = max(
                        (
                            item.envelope[2]
                            for item in base.fragments
                            if item.fragment.block.id not in output_frontier_ids
                        ),
                        default=local_left - CHANNEL_GAP,
                    )
                    output_column = max(
                        (
                            item.envelope[0]
                            for item in base.fragments
                            if item.fragment.block.id in output_frontier_ids
                        ),
                        default=local_left,
                    )
                    outer_left = max(
                        local_left,
                        outer_edge + OUTPUT_FRONTIER_CLEARANCE,
                        output_column,
                    )
                    left_choices = (
                        tuple(dict.fromkeys((local_left, outer_left)))
                        if len(output_frontier_ids) == 1 or len(output_frontier_ids) >= 3
                        else (outer_left,)
                    )
                    package_blocks_local = (
                        role == "signal_out"
                        and len(output_frontier_ids) == 2
                        and _has_package_blocked_reference_output(plan, base)
                    )
                # Align both centers and upper edges as separate legal choices.
                for lane_rank, top in enumerate(frontier_rows(owner, interface, height)):
                    for left in left_choices:
                        if (
                            route_check
                            and role == "signal_out"
                            and package_blocks_local
                            and left == local_left
                            and lane_rank > 0
                        ):
                            continue
                        candidate = frontier_repack(base, interface, owner, role, left, top, label)
                        if candidate is None:
                            continue
                        if "coupled-reference-frontier" in candidate.attempts:
                            coupled_reference_options.append(candidate)
                        # Correct side and owner-row alignment outrank travel to
                        # the outer edge; that edge remains a fallback for
                        # crowded multi-output layouts.
                        observed_side_violation = (
                            max(0, _observed_x(interface) - _observed_x(owner))
                            if role == "signal_in"
                            else max(0, _observed_x(owner) - _observed_x(interface))
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
                        distance = abs(left - interface.envelope[0]) + abs(
                            top - interface.envelope[1]
                        )
                        options.append(
                            (
                                (
                                    -observed_side_violation,
                                    -initial_row_gap,
                                    lane_rank,
                                    distance,
                                    -frontier_deficit,
                                    block.id,
                                    top,
                                ),
                                candidate,
                            )
                        )
        if not options:
            return None
        selected = min(options, key=lambda item: item[0])[1]
        needs_output_side_repair = role == "signal_out" and any(
            owner_id in by_id
            and by_id[owner_id].fragment.block.kind != "interface"
            and by_id[owner_id].envelope[2] >= by_id[block_id].envelope[0]
            for block_id in output_frontier_ids
            for owner_id in frontier_owner_ids(block_id, role)
        )
        if route_check and needs_output_side_repair and len(output_frontier_ids) <= 3:
            # An aligned interface lane can still block its conductor. Check
            # only a small, output-side repair frontier for up to three
            # outputs; keep route generation bounded and leave the final
            # candidate proof authoritative.
            from .m2_route import route_between_fragments

            route_candidates = (
                *coupled_reference_options,
                *(candidate for _rank, candidate in sorted(options, key=lambda item: item[0])[:8]),
            )
            for candidate in route_candidates:
                try:
                    route_between_fragments(plan, candidate.fragments)
                except InputError:
                    continue
                selected = Packing(
                    candidate.fragments,
                    (*candidate.attempts[:-1], "route-proof:pass", candidate.attempts[-1]),
                )
                break
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
                if only_interface_ids is not None and block.id not in only_interface_ids:
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
                    return side_violation(placed, owners, role)

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
        # A staggered output variant is useful only when every output needs
        # the same column repair. Otherwise it can spend a bounded seed on
        # moving a correctly placed sibling after the wrong-side output has
        # already been fixed.
        output_positions = {item.fragment.block.id: item for item in baseline.fragments}
        all_outputs_misplaced = all(
            any(
                owner_id in output_positions
                and output_positions[owner_id].envelope[2] >= output_positions[block_id].envelope[0]
                for owner_id in frontier_owner_ids(block_id, "signal_out")
            )
            for block_id in output_frontier_ids
            if block_id in output_positions
        )
        if all_outputs_misplaced:
            staggered = staggered_output(output_option)
            if staggered is not None:
                alternatives.append(staggered)
    # A blocked sibling must not suppress an independently legal directed
    # output move, and a partially successful combined move must not suppress
    # a repair for a still-reversed connector. Avoid spending candidate slots
    # on outputs whose observed centers already satisfy their direction.
    output_basis = output_option or baseline
    output_positions = {item.fragment.block.id: item for item in output_basis.fragments}
    residual_output_ids = {
        block_id
        for block_id in output_frontier_ids
        if block_id in output_positions
        and (
            owners := tuple(
                output_positions[owner_id]
                for owner_id in frontier_owner_ids(block_id, "signal_out")
                if owner_id in output_positions
                and output_positions[owner_id].fragment.block.kind != "interface"
            )
        )
        and side_violation(output_positions[block_id], owners, "signal_out") > 0
    }
    for block_id in sorted(residual_output_ids):
        single_output = frontier_search(
            output_basis,
            "signal_out",
            "interface-frontier-output",
            only_interface_ids=frozenset({block_id}),
        )
        if single_output is not None:
            alternatives.append(single_output)
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
