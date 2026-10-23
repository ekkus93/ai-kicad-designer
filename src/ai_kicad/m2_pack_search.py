"""Implementation details for m2 pack search."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from .ir import InputError
from .m2_fragments_base import FragmentVariant
from .m2_pack_beam import (
    _band_count,
    _branch_fanout_repack_candidates,
    _partial_beam_candidates,
    _retain_composition_seed_diversity,
)
from .m2_pack_constants import (
    BOTTOM,
    CANDIDATE_BUDGET,
    CHANNEL_GAP,
    ENVELOPE_OUTER_PADDING,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    RIGHT,
    TOP,
)
from .m2_pack_core import Packing, _best_centroid_balanced_packing, _place, _signal_chains
from .m2_pack_distribution import _distribution_column_candidate
from .m2_pack_frontier import (
    _has_package_blocked_reference_output,
    _interface_frontier_candidates,
    _local_signal_proximity_candidates,
)
from .m2_pack_layout import (
    _arrangements,
    _pack_shelves,
)
from .m2_transform import transform_library_point
from .m2_pack_semantic import (
    _repeated_peer_alignment_candidates,
    _semantic_block_order_candidates,
    _structural_repack_candidates,
    _support_affinity_candidates,
)
from .m2_semantics_core import check_placement_constraints
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def _fanout_output_corridor_candidates(
    plan: SemanticPlan,
    variants: dict[str, tuple[FragmentVariant, ...]],
    baseline: Packing,
) -> tuple[Packing, ...]:
    """Repack fanout peers around a source row to expose a branch-output route."""
    from .m2_composition_qualification_observation import observe_composition_packing
    from .m2_route import route_between_fragments
    from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations

    by_id = {item.fragment.block.id: item for item in baseline.fragments}
    block_by_id = {block.id: block for block in plan.blocks}
    relations = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
    }
    relations.update(
        (item.source_fragment, item.target_fragment, item.net) for item in plan.precedence
    )
    relations.update(inferred_passive_interface_signal_relations(plan))
    output_relations = tuple(
        relation
        for relation in sorted(relations)
        if relation[0] in by_id
        and relation[1] in by_id
        and block_by_id[relation[1]].kind == "interface"
    )
    if not output_relations:
        return ()

    terminal = {item.terminal: item for item in plan.terminals}

    def point(placed: dict[str, object], key: tuple[str, str]) -> tuple[int, int]:
        obligation = terminal[key]
        item = placed[obligation.owner]
        origin = item.fragment.positions[obligation.occurrence]
        angle = item.fragment.angles.get(obligation.occurrence, 0)
        dx, dy = transform_library_point(
            obligation.pin_x,
            obligation.pin_y,
            angle,
            item.fragment.mirrors.get(obligation.occurrence),
        )
        return origin[0] + item.delta[0] + dx, origin[1] + item.delta[1] + dy

    def legal(items: tuple) -> bool:
        if any(
            item.envelope[0] < LEFT
            or item.envelope[1] < TOP
            or item.envelope[2] > RIGHT
            or item.envelope[3] > BOTTOM
            for item in items
        ):
            return False
        if (
            max(item.content_envelope[2] for item in items)
            - min(item.content_envelope[0] for item in items)
            > MAX_CONTENT_WIDTH
            or max(item.content_envelope[3] for item in items)
            - min(item.content_envelope[1] for item in items)
            > MAX_CONTENT_HEIGHT
        ):
            return False
        if any(
            max(first.envelope[0], second.envelope[0]) < min(first.envelope[2], second.envelope[2])
            and max(first.envelope[1], second.envelope[1])
            < min(first.envelope[3], second.envelope[3])
            for index, first in enumerate(items)
            for second in items[index + 1 :]
        ):
            return False
        current = {item.fragment.block.id: item for item in items}
        try:
            check_placement_constraints(
                plan, lambda component, pin: point(current, (component, pin))
            )
        except (InputError, KeyError, ValueError):
            return False
        return True

    def preferred_variant(
        block_id: str,
        net_sides: dict[str, str],
        required_nets: set[str],
    ) -> tuple[FragmentVariant, ...]:
        ranked = []
        for choice in variants.get(block_id, ()):
            gateways = {gateway.net: gateway for gateway in choice.gateways}
            if not required_nets <= gateways.keys():
                continue
            mismatches = sum(
                gateways[net].escape_direction != side
                for net, side in net_sides.items()
                if net in gateways
            )
            area = (choice.envelope[2] - choice.envelope[0]) * (
                choice.envelope[3] - choice.envelope[1]
            )
            ranked.append(((mismatches, area, choice.id), choice))
        return tuple(choice for _rank, choice in sorted(ranked, key=lambda item: item[0]))

    def place_output_interfaces(
        branch_ids: tuple[str, ...],
        branch_outputs: dict[str, tuple[str, str, str]],
        placed_blocks: dict[str, object],
        repair_interfaces: set[str] | None = None,
    ) -> Packing | None:
        branch_ids_to_place = tuple(
            branch_id
            for branch_id in branch_ids
            if repair_interfaces is None or branch_outputs[branch_id][1] in repair_interfaces
        )

        def place_next(
            index: int,
            placed: dict[str, object],
        ) -> Packing | None:
            if index == len(branch_ids_to_place):
                candidate_items = tuple(
                    sorted(placed.values(), key=lambda item: item.fragment.block.id)
                )
                if not legal(candidate_items):
                    return None
                candidate = Packing(
                    candidate_items,
                    (*baseline.attempts, "fanout-output-corridor"),
                )
                if not observe_composition_packing(plan, candidate).passed:
                    return None
                try:
                    route_between_fragments(plan, candidate_items)
                except InputError:
                    return None
                return candidate

            branch_id = branch_ids_to_place[index]
            _origin, interface_id, branch_net = branch_outputs[branch_id]
            branch = placed[branch_id]
            choices = preferred_variant(
                interface_id,
                {branch_net: "right"},
                {branch_net},
            )
            if not choices:
                return None
            interface = choices[0]
            branch_gateway = next(
                (gateway for gateway in branch.gateways if gateway.net == branch_net), None
            )
            interface_gateway = next(
                (gateway for gateway in interface.gateways if gateway.net == branch_net), None
            )
            if branch_gateway is None or interface_gateway is None:
                return None

            left = branch.envelope[2] + CHANNEL_GAP
            width = interface.envelope[2] - interface.envelope[0]
            height = interface.envelope[3] - interface.envelope[1]
            aligned_top = branch_gateway.point[1] - (
                interface_gateway.point[1] - interface.envelope[1]
            )
            x_overlapping = tuple(
                item.envelope
                for item in placed.values()
                if max(left, item.envelope[0]) < min(left + width, item.envelope[2])
            )
            tops = {aligned_top}
            if x_overlapping:
                tops.add(min(rect[1] for rect in x_overlapping) - height - PITCH)
                tops.add(max(rect[3] for rect in x_overlapping) + PITCH)

            for top in sorted(tops, key=lambda value: (abs(value - aligned_top), value)):
                if top < TOP or top + height > BOTTOM or left < LEFT or left + width > RIGHT:
                    continue
                positioned = _place(interface, left, top)
                if any(
                    max(positioned.envelope[0], item.envelope[0])
                    < min(positioned.envelope[2], item.envelope[2])
                    and max(positioned.envelope[1], item.envelope[1])
                    < min(positioned.envelope[3], item.envelope[3])
                    for item in placed.values()
                ):
                    continue
                next_placed = dict(placed)
                next_placed[interface_id] = positioned
                candidate = place_next(index + 1, next_placed)
                if candidate is not None:
                    return candidate
            return None

        return place_next(0, placed_blocks)

    results: list[Packing] = []
    seen: set[tuple[tuple[str, tuple[int, int]], ...]] = set()
    for owner_id, interface_id, output_net in output_relations:
        owner = by_id[owner_id]
        interface = by_id[interface_id]
        owner_ports = {port.port.net: port.port.role for port in owner.ports}
        input_nets = sorted(net for net, role in owner_ports.items() if role == "signal_in")
        for input_net in input_nets:
            producers = sorted(
                source
                for source, target, net in relations
                if target == owner_id and net == input_net and source in by_id
            )
            if len(producers) != 1:
                continue
            source_id = producers[0]
            source = by_id[source_id]
            siblings = sorted(
                {
                    target
                    for origin, target, net in relations
                    if origin == source_id
                    and net == input_net
                    and target != owner_id
                    and target in by_id
                    and block_by_id[target].kind != "interface"
                }
            )
            if not siblings:
                continue

            def side_of(first_id: str, second_id: str) -> str:
                first, second = by_id[first_id], by_id[second_id]
                first_x = (first.envelope[0] + first.envelope[2]) // 2
                second_x = (second.envelope[0] + second.envelope[2]) // 2
                return "right" if second_x >= first_x else "left"

            source_sides = {}
            source_required = {input_net}
            for previous, target, net in relations:
                if target == source_id and previous in by_id:
                    source_sides[net] = side_of(source_id, previous)
                    source_required.add(net)
            for origin, _target, net in relations:
                if origin == source_id:
                    source_sides[net] = side_of(source_id, owner_id)
                    source_required.add(net)
            owner_sides = {
                input_net: side_of(owner_id, source_id),
                output_net: side_of(owner_id, interface_id),
            }
            source_choices = preferred_variant(source_id, source_sides, source_required)
            owner_choices = preferred_variant(owner_id, owner_sides, {input_net, output_net})

            # A multi-output fanout needs one lane per branch and its output
            # interface.  Stacking every sibling below the source can exceed
            # both the page and the source-to-branch local-span bound.  Group
            # peers that currently occupy the same horizontal lane, shift each
            # lane with the source, and distribute a shared lane around the
            # source row.  Each output connector follows its own producer.
            branch_ids = (owner_id, *siblings)
            branch_outputs = {}
            for branch_id in branch_ids:
                matches = [relation for relation in output_relations if relation[0] == branch_id]
                if len(matches) != 1:
                    branch_outputs = {}
                    break
                branch_outputs[branch_id] = matches[0]
            if len(branch_outputs) == len(branch_ids) and len(branch_ids) >= 3:
                baseline_observer = observe_composition_packing(plan, baseline)
                repair_interfaces = {
                    violation.source
                    for violation in baseline_observer.violations
                    if violation.kind == "output_side_violation"
                    and violation.source
                    in {branch_outputs[branch_id][1] for branch_id in branch_ids}
                }
                if repair_interfaces:
                    initial_blocks = {
                        block_id: item
                        for block_id, item in by_id.items()
                        if block_id not in repair_interfaces
                    }
                    direct_repair = place_output_interfaces(
                        branch_ids,
                        branch_outputs,
                        initial_blocks,
                        repair_interfaces,
                    )
                    if direct_repair is not None:
                        return (direct_repair,)

                lanes: list[list[str]] = []
                for branch_id in sorted(
                    branch_ids,
                    key=lambda key: (by_id[key].envelope[0], key),
                ):
                    item = by_id[branch_id]
                    overlapping = [
                        lane
                        for lane in lanes
                        if max(by_id[key].envelope[0] for key in lane) < item.envelope[2]
                        and item.envelope[0] < max(by_id[key].envelope[2] for key in lane)
                    ]
                    if overlapping:
                        lane = overlapping[0]
                        lane.append(branch_id)
                        for merged in overlapping[1:]:
                            lane.extend(merged)
                            lanes.remove(merged)
                    else:
                        lanes.append([branch_id])
                lane_orders = tuple(
                    tuple(
                        sorted(
                            lane,
                            key=lambda key: (branch_outputs[key][2], key),
                        )
                    )
                    for lane in lanes
                )

                branch_choices = {}
                for branch_id in branch_ids:
                    _origin, branch_interface_id, branch_net = branch_outputs[branch_id]
                    branch_sides = {
                        input_net: side_of(branch_id, source_id),
                        branch_net: side_of(branch_id, branch_interface_id),
                    }
                    branch_choices[branch_id] = preferred_variant(
                        branch_id,
                        branch_sides,
                        {input_net, branch_net},
                    )[:4]

                option_lists = [branch_choices[key] for key in branch_ids]
                if all(option_lists):
                    # Favor source shifts that open the measured corridor;
                    # zero through the bounded candidate budget remain
                    # available when the page or placement constraints require
                    # a smaller move.
                    for source_choice in source_choices[:4]:
                        for branch_variants in product(*option_lists):
                            selected = dict(zip(branch_ids, branch_variants, strict=True))
                            above_height = max(
                                (
                                    sum(
                                        selected[branch_id].envelope[3]
                                        - selected[branch_id].envelope[1]
                                        for branch_id in lane_order[::2]
                                    )
                                    for lane_order in lane_orders
                                    if len(lane_order) > 1
                                ),
                                default=0,
                            )
                            below_height = max(
                                (
                                    sum(
                                        selected[branch_id].envelope[3]
                                        - selected[branch_id].envelope[1]
                                        for branch_id in lane_order[1::2]
                                    )
                                    for lane_order in lane_orders
                                    if len(lane_order) > 1
                                ),
                                default=0,
                            )
                            for source_steps in range(CANDIDATE_BUDGET, -1, -1):
                                interface_ids = {
                                    interface_id
                                    for _origin, interface_id, _net in branch_outputs.values()
                                }
                                items = {
                                    block_id: item
                                    for block_id, item in by_id.items()
                                    if block_id not in interface_ids
                                }
                                source_top = _place(
                                    source_choice,
                                    source.envelope[0] + source_steps * PITCH,
                                    source.envelope[1],
                                )
                                source_y = max(source_top.envelope[1], TOP + above_height)
                                if (
                                    source_y
                                    + source_top.envelope[3]
                                    - source_top.envelope[1]
                                    + below_height
                                    > BOTTOM
                                ):
                                    continue
                                source_top = _place(
                                    source_choice,
                                    source.envelope[0] + source_steps * PITCH,
                                    source_y,
                                )
                                items[source_id] = source_top
                                for lane_order in lane_orders:
                                    lane_left = max(by_id[key].envelope[0] for key in lane_order)
                                    lane_x = lane_left + source_steps * PITCH
                                    if len(lane_order) == 1:
                                        branch_id = lane_order[0]
                                        branch_choice = selected[branch_id]
                                        items[branch_id] = _place(
                                            branch_choice,
                                            lane_x,
                                            source_top.envelope[1],
                                        )
                                        continue

                                    above_cursor = source_top.envelope[1]
                                    below_cursor = source_top.envelope[3]
                                    for index, branch_id in enumerate(lane_order):
                                        branch_choice = selected[branch_id]
                                        branch_height = (
                                            branch_choice.envelope[3] - branch_choice.envelope[1]
                                        )
                                        if index % 2 == 0:
                                            branch_top = above_cursor - branch_height
                                            above_cursor = branch_top
                                        else:
                                            branch_top = below_cursor
                                            below_cursor += branch_height
                                        items[branch_id] = _place(
                                            branch_choice,
                                            lane_x,
                                            branch_top,
                                        )

                                candidate = place_output_interfaces(
                                    branch_ids, branch_outputs, items
                                )
                                if candidate is not None:
                                    return (candidate,)

            for source_choice in source_choices[:4]:
                for owner_choice in owner_choices[:4]:
                    for source_steps in range(CANDIDATE_BUDGET + 1):
                        direction = 1 if side_of(source_id, owner_id) == "right" else -1
                        items = dict(by_id)
                        source_top = _place(
                            source_choice,
                            source.envelope[0] + direction * source_steps * PITCH,
                            source.envelope[1],
                        )
                        owner_replacement = _place(
                            owner_choice, owner.envelope[0], owner.envelope[1]
                        )
                        items[source_id] = source_top
                        items[owner_id] = owner_replacement

                        # Keep the source's fanout branch peers in separate
                        # rows. This opens the source-to-owner route corridor
                        # while retaining each measured branch fragment.
                        source_center_y = (source.envelope[1] + source.envelope[3]) // 2
                        peer_items = [by_id[peer_id] for peer_id in siblings]
                        above = sorted(
                            (
                                peer
                                for peer in peer_items
                                if (peer.envelope[1] + peer.envelope[3]) // 2 <= source_center_y
                            ),
                            key=lambda peer: (peer.envelope[1], peer.fragment.block.id),
                        )
                        below = sorted(
                            (peer for peer in peer_items if peer not in above),
                            key=lambda peer: (peer.envelope[1], peer.fragment.block.id),
                        )
                        cursor = source_top.envelope[1]
                        for peer in above:
                            height = peer.envelope[3] - peer.envelope[1]
                            moved = _place(peer.fragment, peer.envelope[0], cursor - height)
                            items[peer.fragment.block.id] = moved
                            cursor = moved.envelope[1]
                        cursor = source_top.envelope[3]
                        for peer in below:
                            moved = _place(peer.fragment, peer.envelope[0], cursor)
                            items[peer.fragment.block.id] = moved
                            cursor = moved.envelope[3]

                        output_gateway = next(
                            (
                                gateway
                                for gateway in owner_replacement.gateways
                                if gateway.net == output_net
                            ),
                            None,
                        )
                        interface_gateway = next(
                            (
                                gateway
                                for gateway in interface.gateways
                                if gateway.net == output_net
                            ),
                            None,
                        )
                        if output_gateway is None or interface_gateway is None:
                            continue
                        output_left = owner_replacement.envelope[2] + CHANNEL_GAP
                        output_top = output_gateway.point[1] - (
                            interface_gateway.point[1] - interface.envelope[1]
                        )
                        items[interface_id] = _place(interface.fragment, output_left, output_top)
                        candidate_items = tuple(
                            sorted(items.values(), key=lambda item: item.fragment.block.id)
                        )
                        if not legal(candidate_items):
                            continue
                        candidate = Packing(
                            candidate_items,
                            (*baseline.attempts, "fanout-output-corridor"),
                        )
                        if not observe_composition_packing(plan, candidate).passed:
                            continue
                        identity = tuple(
                            sorted((item.fragment.id, item.delta) for item in candidate_items)
                        )
                        if identity in seen:
                            continue
                        seen.add(identity)
                        try:
                            route_between_fragments(plan, candidate_items)
                        except InputError:
                            continue
                        results.append(candidate)
                        if len(results) == 1:
                            return tuple(results)
    return tuple(results)


def _observed_output_corridor_candidate(
    plan: SemanticPlan,
    variants: dict[str, tuple[FragmentVariant, ...]],
    baseline: Packing,
) -> Packing | None:
    """Move observer-failing output interfaces into measured producer corridors."""
    from .m2_composition_qualification_observation import observe_composition_packing
    from .m2_composition_quality import observe_human_composition
    from .m2_route import route_between_fragments

    def terminal_point(placed: dict[str, object], key: tuple[str, str]) -> tuple[int, int]:
        obligation = next(item for item in plan.terminals if item.terminal == key)
        item = placed[obligation.owner]
        origin = item.fragment.positions[obligation.occurrence]
        angle = item.fragment.angles.get(obligation.occurrence, 0)
        dx, dy = transform_library_point(
            obligation.pin_x,
            obligation.pin_y,
            angle,
            item.fragment.mirrors.get(obligation.occurrence),
        )
        return origin[0] + item.delta[0] + dx, origin[1] + item.delta[1] + dy

    def terminal_observation(placed: dict[str, object]):
        points: dict[str, list[tuple[int, int]]] = {}
        for obligation in plan.terminals:
            points.setdefault(obligation.owner, []).append(
                terminal_point(placed, obligation.terminal)
            )
        envelopes = {
            block_id: (
                min(point[0] for point in block_points),
                min(point[1] for point in block_points),
                max(point[0] for point in block_points),
                max(point[1] for point in block_points),
            )
            for block_id, block_points in points.items()
            if block_points
        }
        return observe_human_composition(plan, envelopes)

    def output_failures(*observations):
        failures = {}
        for observation in observations:
            for violation in observation.violations:
                if violation.kind == "output_side_violation":
                    failures[(violation.source, violation.target, violation.net)] = violation
        return tuple(failures[key] for key in sorted(failures))

    def search(current: Packing, depth: int, seen: set[tuple]) -> Packing | None:
        observation = observe_composition_packing(plan, current)
        terminal_report = terminal_observation(
            {item.fragment.block.id: item for item in current.fragments}
        )
        failures = output_failures(observation, terminal_report)
        if not failures:
            try:
                route_between_fragments(plan, current.fragments)
            except InputError:
                return None
            return current
        if depth >= len(failures) + len(current.fragments):
            return None

        placed = {item.fragment.block.id: item for item in current.fragments}
        failure = failures[0]
        interface_id, owner_id, net = failure.source, failure.target, failure.net
        owner = placed.get(owner_id)
        if owner is None or interface_id not in variants:
            return None
        candidates = []
        for variant in variants[interface_id]:
            gateway = next((item for item in variant.gateways if item.net == net), None)
            if gateway is None:
                continue
            area = (variant.envelope[2] - variant.envelope[0]) * (
                variant.envelope[3] - variant.envelope[1]
            )
            candidates.append((area, variant.id, variant, gateway))
        for _area, _variant_id, variant, gateway in sorted(candidates):
            owner_gateway = next((item for item in owner.gateways if item.net == net), None)
            if owner_gateway is None:
                continue
            width = variant.envelope[2] - variant.envelope[0]
            height = variant.envelope[3] - variant.envelope[1]
            aligned_top = owner_gateway.point[1] - (gateway.point[1] - variant.envelope[1])
            local_content = variant.content_envelope or variant.envelope
            owner_content = owner.content_envelope
            # Output interfaces commonly need a vertical lane: the right lane
            # can exceed the page width even when a compact below-owner slot
            # preserves the output relationship and leaves a routeable path.
            vertical_left = (
                owner_content[0]
                + owner_content[2]
                + 2 * PITCH
                - local_content[0]
                - local_content[2]
            ) // 2
            # `_place` snaps the fragment origin to the symbol grid. The
            # content-center offset can therefore differ from the requested
            # offset when the local envelope has a fractional grid phase.
            # Compensate by whole pitches so the *placed* content center is
            # actually to the producer's right.
            center_probe = _place(variant, vertical_left, owner.envelope[3] + PITCH)
            target_center_twice = owner_content[0] + owner_content[2] + 2 * PITCH
            placed_center_twice = (
                center_probe.content_envelope[0] + center_probe.content_envelope[2]
            )
            center_deficit_twice = max(0, target_center_twice - placed_center_twice)
            vertical_left += ((center_deficit_twice + 2 * PITCH - 1) // (2 * PITCH)) * PITCH
            terminal_probe = _place(variant, vertical_left, owner.envelope[3] + PITCH)
            terminal_probe_placements = dict(placed)
            terminal_probe_placements[interface_id] = terminal_probe
            terminal_failure = next(
                (
                    item
                    for item in terminal_observation(terminal_probe_placements).violations
                    if item.kind == "output_side_violation"
                    and (item.source, item.target, item.net) == (interface_id, owner_id, net)
                ),
                None,
            )
            if terminal_failure is not None and terminal_failure.actual_nm > 0:
                vertical_left += ((terminal_failure.actual_nm + PITCH - 1) // PITCH) * PITCH
            placements = []
            if gateway.escape_direction == "right":
                placements.append((owner.envelope[2] + CHANNEL_GAP, aligned_top))
            placements.extend(
                (
                    (vertical_left, owner.envelope[3] + PITCH),
                    (vertical_left, owner.envelope[1] - height - PITCH),
                )
            )
            for desired_left, preferred_top in placements:
                obstacles = tuple(
                    item.envelope
                    for key, item in placed.items()
                    if key != interface_id
                    and max(desired_left, item.envelope[0])
                    < min(desired_left + width, item.envelope[2])
                )
                tops = {preferred_top, aligned_top, TOP, BOTTOM - height}
                for rectangle in obstacles:
                    tops.add(rectangle[1] - height - PITCH)
                    tops.add(rectangle[3] + PITCH)
                for top in sorted(tops, key=lambda value: (abs(value - preferred_top), value)):
                    left = desired_left
                    right = left + width
                    if left < LEFT or right > RIGHT or top < TOP or top + height > BOTTOM:
                        continue
                    replacement = _place(variant, left, top)
                    if any(
                        max(replacement.envelope[0], item.envelope[0])
                        < min(replacement.envelope[2], item.envelope[2])
                        and max(replacement.envelope[1], item.envelope[1])
                        < min(replacement.envelope[3], item.envelope[3])
                        for key, item in placed.items()
                        if key != interface_id
                    ):
                        continue
                    changed = dict(placed)
                    changed[interface_id] = replacement
                    identity = tuple(
                        sorted((key, item.fragment.id, item.delta) for key, item in changed.items())
                    )
                    if identity in seen:
                        continue
                    seen.add(identity)
                    candidate = Packing(
                        tuple(sorted(changed.values(), key=lambda item: item.fragment.block.id)),
                        (*current.attempts, "observed-output-corridor"),
                    )
                    content = [item.content_envelope for item in candidate.fragments]
                    if (
                        max(rect[2] for rect in content) - min(rect[0] for rect in content)
                        > MAX_CONTENT_WIDTH
                        or max(rect[3] for rect in content) - min(rect[1] for rect in content)
                        > MAX_CONTENT_HEIGHT
                    ):
                        continue
                    observed = observe_composition_packing(plan, candidate)
                    terminal_observed = terminal_observation(changed)
                    previous_score = (
                        observation.metrics.output_side_violations,
                        terminal_report.metrics.output_side_violations,
                    )
                    candidate_score = (
                        observed.metrics.output_side_violations,
                        terminal_observed.metrics.output_side_violations,
                    )
                    if candidate_score >= previous_score:
                        continue
                    try:
                        check_placement_constraints(
                            plan,
                            lambda component, pin, current=changed: terminal_point(
                                current, (component, pin)
                            ),
                        )
                    except (InputError, KeyError, ValueError):
                        continue
                    result = search(candidate, depth + 1, seen)
                    if result is not None:
                        return result
        return None

    initial = tuple(
        sorted(
            (item.fragment.id, item.fragment.block.id, item.delta) for item in baseline.fragments
        )
    )
    return search(baseline, 0, {initial})


def _frontier_candidate_rank(plan: SemanticPlan, packing: Packing) -> tuple[int, ...]:
    """Rank frontier moves by the production observer before semantic tie-breaks."""
    from .m2_composition_candidate_rank import semantic_composition_penalties
    from .m2_composition_qualification_observation import observe_composition_packing

    metrics = observe_composition_packing(plan, packing).metrics
    return (
        metrics.primary_stage_order_inversions,
        metrics.input_side_violations,
        metrics.output_side_violations,
        *semantic_composition_penalties(plan, packing),
    )


def pack_fragment_candidates(
    plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]
) -> tuple[Packing, ...]:
    """Build an at-most-eight deterministic beam of complete placement seeds."""
    attempts: list[str] = []
    keys = sorted(variants)
    if set(keys) != {block.id for block in plan.blocks}:
        raise InputError("PACK_VARIANT_BLOCK_MISMATCH")
    if any(not choices or len(choices) > 8 for choices in variants.values()):
        raise InputError("PACK_VARIANT_INVENTORY: each block requires one to eight variants")

    indivisible = sorted(
        (choice.id, choice.envelope)
        for choices in variants.values()
        for choice in choices
        if choice.envelope[2] - choice.envelope[0] > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
        or choice.envelope[3] - choice.envelope[1] > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
    )
    if indivisible and any(
        all(
            choice.envelope[2] - choice.envelope[0] > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            or choice.envelope[3] - choice.envelope[1] > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
            for choice in choices
        )
        for choices in variants.values()
    ):
        raise InputError(
            "PACK_SPREAD_INFEASIBLE: indivisible measured envelope exceeds "
            f"210x140 mm bounds={indivisible}"
        )

    by_block = {block.id: block for block in plan.blocks}

    def quality(item: FragmentVariant) -> tuple[int, int, int, str]:
        width = item.envelope[2] - item.envelope[0]
        height = item.envelope[3] - item.envelope[1]
        return width * height, max(width, height), width, item.id

    ordered_choices = {key: tuple(variants[key]) for key in keys}
    baseline = {key: ordered_choices[key][0] for key in keys}
    beam: list[dict[str, FragmentVariant]] = [baseline]
    kind_priority = {
        "package_power": 0,
        "interface": 1,
        "power_stage": 2,
        "timer": 3,
        "sallen_key": 4,
        "noninverting_amplifier": 4,
        "inverting_amplifier": 4,
        "buffer": 4,
    }
    branch_targets = {edge.target for edge in plan.edges if edge.kind == "branch"}
    substitutions = sorted(
        (
            rank,
            -1 if key in branch_targets else kind_priority.get(by_block[key].kind, 5),
            key,
            choice,
        )
        for key in keys
        for rank, choice in enumerate(ordered_choices[key][1:], start=1)
    )

    def access_delta(key: str, choice: FragmentVariant) -> tuple[tuple[str, str], ...]:
        original = {
            gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction
            for gateway in baseline[key].gateways
        }
        return tuple(
            sorted(
                (gateway.id.rsplit(".", 1)[-1], gateway.escape_direction)
                for gateway in choice.gateways
                if original.get(gateway.id.rsplit(".", 1)[-1]) != gateway.escape_direction
            )
        )

    proposals: list[tuple[tuple, dict[str, FragmentVariant]]] = []
    for rank, priority, key, choice in substitutions:
        base = baseline[key]
        base_width = base.envelope[2] - base.envelope[0]
        base_height = base.envelope[3] - base.envelope[1]
        if (
            base_width > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            or base_height > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
        ) and (
            choice.envelope[2] - choice.envelope[0] <= MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            and choice.envelope[3] - choice.envelope[1]
            <= MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
        ):
            proposals.append(((-2, rank, key), {**baseline, key: choice}))

    # A finite, measured text-slot variant for each affected block kind is
    # explored before ordinary access substitutions. This keeps at least one
    # field-only alternative visible to the bounded complete-placement beam.
    for kind in sorted({by_block[key].kind for key in keys}):
        field_candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            alternate = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if ".local-text-slot." in choice.rule_id
                ),
                None,
            )
            if alternate is not None:
                field_candidate[key] = alternate
        if any(field_candidate[key] is not baseline[key] for key in keys):
            proposals.append(((-3, "field-slot", kind), field_candidate))

    # A reusable inward-facing rail-access candidate for independent shelves:
    # upper bands expose references downward and lower bands upward.  This is
    # derived solely from the signal DAG bands and port access alternatives.
    band_facing = dict(baseline)
    chain_index_by_block = {
        fragment_id: index
        for index, chain in enumerate(_signal_chains(plan))
        for fragment_id in chain
    }
    for edge in plan.edges:
        if edge.kind == "package" and edge.source in chain_index_by_block:
            chain_index_by_block.setdefault(edge.target, chain_index_by_block[edge.source])
    for key, band_index in sorted(chain_index_by_block.items()):
        desired = "down" if band_index % 2 == 0 else "up"
        replacement = next(
            (
                choice
                for choice in ordered_choices[key]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "reference"
                    and gateway.escape_direction == desired
                    for gateway in choice.gateways
                )
            ),
            None,
        )
        if replacement is not None:
            band_facing[key] = replacement
    if any(band_facing[key] is not baseline[key] for key in keys):
        proposals.append(((-1, "band-facing-reference"), band_facing))
    output_access = dict(baseline)
    for key in keys:
        baseline_output = next(
            (
                gateway.escape_direction
                for gateway in baseline[key].gateways
                if gateway.id.rsplit(".", 1)[-1] == "output"
            ),
            None,
        )
        alternate = next(
            (
                choice
                for choice in ordered_choices[key][1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "output"
                    and gateway.escape_direction != baseline_output
                    for gateway in choice.gateways
                )
            ),
            None,
        )
        if alternate is not None:
            output_access[key] = alternate
    if any(output_access[key] is not baseline[key] for key in keys):
        proposals.append(((-1, "access-output"), output_access))
    output_band = dict(band_facing)
    for key in keys:
        if by_block[key].kind == "package_power":
            output_band[key] = baseline[key]
    for key in keys:
        selected_directions = {
            gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction
            for gateway in band_facing[key].gateways
        }
        alternate = next(
            (
                choice
                for choice in ordered_choices[key][1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "output"
                    and gateway.escape_direction
                    != next(
                        (
                            base_gateway.escape_direction
                            for base_gateway in baseline[key].gateways
                            if base_gateway.id.rsplit(".", 1)[-1] == "output"
                        ),
                        gateway.escape_direction,
                    )
                    for gateway in choice.gateways
                )
                and all(
                    selected_directions.get(gateway.id.rsplit(".", 1)[-1])
                    == gateway.escape_direction
                    for gateway in choice.gateways
                    if gateway.id.rsplit(".", 1)[-1] == "reference"
                )
            ),
            None,
        )
        if alternate is not None:
            output_band[key] = alternate
    if any(output_band[key] is not band_facing[key] for key in keys):
        proposals.append(((-1, "access-output-band"), output_band))
    for kind in sorted({block.kind for block in plan.blocks}):
        aspect_candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            alternate = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if ".above." in choice.rule_id or ".compact." in choice.rule_id
                ),
                None,
            )
            if alternate is not None:
                aspect_candidate[key] = alternate
        if any(aspect_candidate[key] is not baseline[key] for key in keys):
            proposals.append(((-1, f"aspect-{kind}"), aspect_candidate))
    compact_candidate = {
        key: next(
            (choice for choice in ordered_choices[key] if ".compact." in choice.rule_id),
            baseline[key],
        )
        for key in keys
    }
    if any(compact_candidate[key] is not baseline[key] for key in keys):
        proposals.append(((-2, "all-compact"), compact_candidate))

    rules = sorted(
        {
            (
                -1 if key in branch_targets else kind_priority.get(by_block[key].kind, 5),
                by_block[key].kind,
                access_delta(key, choice),
            )
            for _, _, key, choice in substitutions
            if access_delta(key, choice)
        }
    )
    rule_candidates = []
    port_priority = {
        "reference": 0,
        "output": 1,
        "positive": 1,
        "supply": 1,
        "input": 2,
        "negative": 2,
        "pin1": 2,
    }
    for priority, kind, delta in rules:
        candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            match = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if access_delta(key, choice) == delta
                ),
                None,
            )
            if match is not None:
                candidate[key] = match
        changed_port = delta[0][0] if delta else ""
        rule_candidates.append(
            (port_priority.get(changed_port, 3), priority, kind, delta, candidate)
        )
    # Preserve beam diversity instead of allowing the many access choices for
    # the first typed kind to consume every complete seed.
    by_kind_rules: dict[str, list[tuple]] = {}
    for item in sorted(rule_candidates, key=lambda value: value[:4]):
        by_kind_rules.setdefault(item[2], []).append(item)
    kind_order = sorted(
        by_kind_rules,
        key=lambda kind: min((item[1], item[0], kind) for item in by_kind_rules[kind]),
    )
    for round_index in range(max(map(len, by_kind_rules.values()), default=0)):
        for kind in kind_order:
            choices = by_kind_rules[kind]
            if round_index >= len(choices):
                continue
            port_rank, priority, _, delta, candidate = choices[round_index]
            proposals.append(((0, round_index, port_rank, priority, kind, delta), candidate))
    proposals.extend(
        ((1, rank, priority, key, choice.id), {**baseline, key: choice})
        for rank, priority, key, choice in substitutions
    )
    seen = {tuple((key, baseline[key].id) for key in keys)}
    for _, candidate in sorted(proposals, key=lambda item: (item[0][0], str(item[0][1:]))):
        identity = tuple((key, candidate[key].id) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        beam.append(candidate)
        if len(beam) == CANDIDATE_BUDGET:
            break

    successful: list[Packing] = []
    arranged = [(chosen, _arrangements(plan, chosen)) for chosen in beam]
    # Reserve beam slots for different variant assignments as well as shelf
    # arrangements. A repeated baseline shelf must not hide support orientation
    # or compactness choices behind the eight complete-candidate limit.
    preferred = [(0, 0), (0, 1)] + [(index, (index - 1) % 2) for index in range(1, len(arranged))]
    remaining = [
        (chosen_index, arrangement_index)
        for arrangement_index in range(4)
        for chosen_index in range(len(arranged))
        if (chosen_index, arrangement_index) not in preferred
    ]
    for chosen_index, arrangement_index in preferred + remaining:
        chosen, choices = arranged[chosen_index]
        arrangement_name, ordered = choices[arrangement_index]
        candidate_index = len(attempts) + 1
        try:
            placed, width, height = _pack_shelves(ordered, chosen)
        except ValueError as exc:
            attempts.append(f"candidate-{candidate_index}:{arrangement_name}:{exc}")
            continue
        attempts.append(
            f"candidate-{candidate_index}:{arrangement_name}:pass:measured={width}x{height}"
        )
        successful.append(
            Packing(
                tuple(sorted(placed, key=lambda item: item.fragment.id)),
                tuple(attempts),
            )
        )
        if len(successful) == CANDIDATE_BUDGET:
            break

    if successful:
        extras = []
        # Rigid, on-grid centering is considered without displacing a complete
        # original seed. Actual native-page acceptance remains independent.
        centered = _best_centroid_balanced_packing(successful)
        if centered is not None:
            extras.append(centered)
        structural = tuple(
            candidate
            for baseline in successful
            for candidate in _structural_repack_candidates(plan, baseline)
        )
        # Reserve candidate space for deterministic, legally measured interface
        # moves; the subsequent route proof remains authoritative.
        # A frontier move may be illegal in a shelf arrangement but legal after
        # structural compaction. Compare all measured placements and keep the
        # semantically strongest option for each directed role.
        frontier_options: dict[str, tuple[bool, tuple[int, ...], tuple, Packing]] = {}
        from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations

        interface_ids = {block.id for block in plan.blocks if block.kind == "interface"}
        output_count = len(
            {
                target_id
                for _source_id, target_id, _net in inferred_passive_interface_signal_relations(plan)
                if target_id in interface_ids
            }
        )
        frontier_bases = (*successful, *structural) if output_count >= 3 else successful
        frontier_candidates: dict[str, list[tuple[tuple[int, ...], tuple, Packing, Packing]]] = {}
        for baseline in frontier_bases:
            for option in _interface_frontier_candidates(plan, baseline):
                label = option.attempts[-1]
                rank = _frontier_candidate_rank(plan, option)
                identity = tuple(
                    sorted((item.fragment.id, item.delta) for item in option.fragments)
                )
                frontier_candidates.setdefault(label, []).append((rank, identity, baseline, option))
                if (
                    label
                    not in {
                        "interface-frontier-output",
                        "interface-frontier-output-staggered",
                        "interface-frontier-combined",
                    }
                    or rank[2] == 0
                ):
                    continue
                # A complete frontier move can improve most outputs while one
                # terminal-backed branch output remains blocked. Give that
                # measured candidate one bounded refinement pass so each
                # connector can use its own legal slot.
                for refined in _interface_frontier_candidates(plan, option):
                    refined_label = refined.attempts[-1]
                    if refined_label not in {
                        "interface-frontier-output",
                        "interface-frontier-output-staggered",
                        "interface-frontier-combined",
                    }:
                        continue
                    refined_rank = _frontier_candidate_rank(plan, refined)
                    refined_identity = tuple(
                        sorted((item.fragment.id, item.delta) for item in refined.fragments)
                    )
                    frontier_candidates.setdefault(refined_label, []).append(
                        (refined_rank, refined_identity, option, refined)
                    )
        for label, candidates in frontier_candidates.items():
            selected_rank, selected_identity, _baseline, selected = min(
                candidates, key=lambda item: (item[0], item[1])
            )
            route_proven = False
            if label == "interface-frontier-output" and output_count <= 3:
                # Search only the four strongest measured base placements for
                # a routeable output lane; route checks over every shelf and
                # structural seed made the bounded search needlessly expensive.
                for _rank, _identity, baseline, _option in sorted(
                    candidates, key=lambda item: (item[0], item[1])
                )[:4]:
                    routed = next(
                        (
                            option
                            for option in _interface_frontier_candidates(
                                plan, baseline, route_check=True
                            )
                            if option.attempts[-1] == label
                            and "route-proof:pass" in option.attempts
                        ),
                        None,
                    )
                    if routed is None:
                        continue
                    selected = routed
                    selected_rank = _frontier_candidate_rank(plan, routed)
                    selected_identity = tuple(
                        sorted((item.fragment.id, item.delta) for item in routed.fragments)
                    )
                    route_proven = True
                    break
            frontier_options[label] = (
                route_proven,
                selected_rank,
                selected_identity,
                selected,
            )
        frontier_order = (
            "interface-frontier-combined",
            "interface-frontier-output",
            "interface-frontier-output-staggered",
            "interface-frontier-input",
        )
        extras.extend(
            frontier_options[label][3] for label in frontier_order if label in frontier_options
        )
        for label in (
            "interface-frontier-combined",
            "interface-frontier-output",
            "interface-frontier-output-staggered",
        ):
            option = frontier_options.get(label)
            if option is None:
                continue
            corridor = _observed_output_corridor_candidate(plan, variants, option[3])
            if corridor is not None:
                extras.append(corridor)
                break
        extras.extend(_semantic_block_order_candidates(plan, successful[0]))
        extras.extend(_support_affinity_candidates(plan, successful[0]))
        extras.extend(_local_signal_proximity_candidates(plan, successful[0]))
        extras.extend(_branch_fanout_repack_candidates(plan, successful[0]))
        extras.extend(_repeated_peer_alignment_candidates(plan, successful[0]))
        distribution = _distribution_column_candidate(plan, variants, successful)
        if distribution is not None and all(
            tuple((item.fragment.id, item.delta) for item in distribution.fragments)
            != tuple((item.fragment.id, item.delta) for item in candidate.fragments)
            for candidate in successful
        ):
            extras.append(distribution)
            corridor = _observed_output_corridor_candidate(plan, variants, distribution)
            if corridor is not None:
                extras.append(corridor)
        for label in ("functional-row-compaction", "precedence-staggered-band"):
            candidate = next((item for item in structural if item.attempts[-1] == label), None)
            if candidate is not None:
                extras.append(candidate)
        # Shelf success alone does not prove structural coverage.  A shared
        # internally generated net with several physical islands can need an
        # interleaved partial placement to meet its whole-net length bound.
        distribution_demand = any(
            net.internally_generated and net.explicit_geometry_required and len(net.fragments) >= 2
            for net in plan.presentation_nets
        )
        fanout_targets: dict[tuple[str, str], set[str]] = {}
        for edge in plan.edges:
            if edge.kind in {"signal", "branch"} and edge.source != edge.target:
                fanout_targets.setdefault((edge.source, edge.net), set()).add(edge.target)
        branch_fanout_demand = any(len(targets) >= 3 for targets in fanout_targets.values())
        noninterface_count = sum(
            item.fragment.block.kind != "interface" for item in successful[0].fragments
        )
        needs_band_alternative = (
            noninterface_count >= 2
            and len({_band_count(item) for item in (*successful[:4], *extras)}) == 1
        )
        if distribution_demand or branch_fanout_demand or needs_band_alternative:
            partial = _partial_beam_candidates(plan, variants)
            if partial:
                for partial_candidate in partial:
                    corridor = _observed_output_corridor_candidate(
                        plan, variants, partial_candidate
                    )
                    if corridor is not None:
                        extras.append(corridor)
                        break
                baseline_bands = _band_count(successful[0])
                diverse = next(
                    (item for item in partial if _band_count(item) != baseline_bands), partial[0]
                )
                extras.append(diverse)
                # The band-diverse seed is only one of the bounded partial
                # candidates.  A routeable output fanout may live in another
                # measured geometry class, so probe every partial seed for a
                # corridor before the final eight-candidate retention step.
                from .m2_composition_qualification_observation import observe_composition_packing
                from .m2_route import route_between_fragments

                for partial_candidate in partial:
                    if partial_candidate is diverse:
                        continue
                    alternative_frontiers = _interface_frontier_candidates(
                        plan,
                        partial_candidate,
                        route_check=(
                            output_count <= 3
                            and _has_package_blocked_reference_output(plan, partial_candidate)
                        ),
                    )
                    for output_candidate in alternative_frontiers:
                        if output_candidate.attempts[-1] != "interface-frontier-output":
                            continue
                        try:
                            route_between_fragments(plan, output_candidate.fragments)
                        except InputError:
                            pass
                        else:
                            if observe_composition_packing(plan, output_candidate).passed:
                                continue
                        corridor = _fanout_output_corridor_candidates(
                            plan, variants, output_candidate
                        )
                        if corridor:
                            extras.extend(corridor)
                            break
                    else:
                        continue
                    break
                partial_frontiers = _interface_frontier_candidates(
                    plan,
                    diverse,
                    route_check=(
                        output_count <= 3 and _has_package_blocked_reference_output(plan, diverse)
                    ),
                )
                partial_frontiers = tuple(
                    candidate
                    for candidate in partial_frontiers
                    if candidate.attempts[-1] in frontier_order
                )
                if partial_frontiers:
                    output_alternatives = sorted(
                        (
                            candidate
                            for candidate in partial_frontiers
                            if candidate.attempts[-1] == "interface-frontier-output"
                        ),
                        key=lambda candidate: (
                            _frontier_candidate_rank(plan, candidate),
                            tuple(
                                sorted(
                                    (item.fragment.id, item.delta) for item in candidate.fragments
                                )
                            ),
                        ),
                    )
                    for output_candidate in output_alternatives[:2]:
                        from .m2_route import route_between_fragments

                        try:
                            route_between_fragments(plan, output_candidate.fragments)
                        except InputError:
                            pass
                        else:
                            if observe_composition_packing(plan, output_candidate).passed:
                                continue
                        corridor = _fanout_output_corridor_candidates(
                            plan, variants, output_candidate
                        )
                        if corridor:
                            extras.extend(corridor)
                            break
                    extras.extend(
                        sorted(
                            partial_frontiers,
                            key=lambda candidate: (
                                _frontier_candidate_rank(plan, candidate),
                                tuple(
                                    sorted(
                                        (item.fragment.id, item.delta)
                                        for item in candidate.fragments
                                    )
                                ),
                            ),
                        )
                    )
        retained = _retain_composition_seed_diversity(tuple(successful), tuple(extras))
        if output_count <= 3:
            # The measured frontier may be individually legal but routeable
            # only from a less prominent retained seed (for example when a
            # sibling output blocks the nearest candidate). Prove a bounded
            # route-aware alternative before the eight-seed cap discards it.
            from .m2_composition_qualification_observation import observe_composition_packing
            from .m2_route import route_between_fragments

            for baseline in retained:
                for option in _interface_frontier_candidates(plan, baseline, route_check=True):
                    if option.attempts[-1] != "interface-frontier-output":
                        continue
                    try:
                        route_between_fragments(plan, option.fragments)
                    except InputError:
                        continue
                    if not observe_composition_packing(plan, option).passed:
                        continue
                    route_proven = type(option)(
                        option.fragments,
                        (*option.attempts[:-1], "route-proof:pass", option.attempts[-1]),
                    )
                    remaining = tuple(
                        candidate
                        for candidate in retained
                        if candidate.attempts[-1] != "interface-frontier-output"
                    )
                    return (route_proven, *remaining)[:CANDIDATE_BUDGET]
        return retained

    partial = _partial_beam_candidates(plan, variants)
    if partial:
        return partial

    raise InputError(
        f"PACK_BUDGET_EXHAUSTED: candidates={len(attempts)}/{CANDIDATE_BUDGET} "
        f"spread_limit=210x140mm attempts={attempts}"
    )


def pack_fragments(plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]) -> Packing:
    """Return the first bounded seed with a feasible route demand when observable."""
    from . import m2_pack as facade

    candidates = facade.pack_fragment_candidates(plan, variants)
    # Lazy import avoids a module cycle while retaining the route-aware packing
    # contract for callers of this compatibility entry point.
    from .m2_route import route_between_fragments

    for candidate in candidates:
        try:
            route_between_fragments(plan, candidate.fragments)
        except InputError:
            continue
        return candidate
    return candidates[0]
