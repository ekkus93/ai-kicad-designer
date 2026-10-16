"""Implementation details for m2 composition rank scoring."""

from __future__ import annotations

from dataclasses import dataclass


import itertools
from collections import defaultdict

from .m2_composition_candidate_rank import (
    CandidateKey,
    CompactnessPenaltyVector,
    Point,
    SemanticPenaltyVector,
)
from .m2_composition_rank_metrics import (
    _branch_readability_penalty,
    _center,
    _feedback_corridor_intrusions,
    _grid_units,
    _independent_output_owner_row_drift,
    _infrastructure_primary_row_intrusion,
    _interface_roles,
    _intra_block_dispersion,
    _local_signal_neighbor_gap,
    _passive_reference_axis_alignment_penalty,
    _placed_rects,
    _power_interface_distance,
    _repeated_alignment_penalty,
    _signal_relations,
    _signal_row_alignment_components,
    _support_axis_alignment_penalty,
    _unrelated_block_proximity,
)
from .m2_pack import BOTTOM, LEFT, RIGHT, TOP
from .m2a import PITCH


@dataclass(frozen=True)
class SemanticPenaltyBreakdown:
    missing_geometry: int
    stage_order_violations: int
    reversal_distance: int
    interface_side_violations: int
    interface_owner_distance: int
    frontier_distance: int
    feedback_distance: int
    support_distance: int
    branch_alignment: int
    repeated_alignment: int
    intra_block_dispersion: int
    unrelated_block_proximity: int
    power_interface_distance: int
    infrastructure_primary_row_intrusion: int
    feedback_intrusion: int
    sequential_stage_row_drift: int
    directed_interface_row_drift: int
    material_interface_row_dislocation: int
    support_axis_drift: int
    passive_reference_axis_drift: int
    local_signal_neighbor_gap: int

    def vector(self) -> SemanticPenaltyVector:
        return (
            self.missing_geometry,
            self.stage_order_violations,
            self.reversal_distance,
            self.interface_side_violations,
            self.interface_owner_distance,
            self.frontier_distance,
            self.feedback_distance,
            self.support_distance,
            self.branch_alignment,
            self.repeated_alignment,
            self.intra_block_dispersion,
            self.unrelated_block_proximity,
            self.power_interface_distance,
            self.infrastructure_primary_row_intrusion,
            self.feedback_intrusion,
            self.sequential_stage_row_drift,
            self.directed_interface_row_drift,
            self.support_axis_drift,
            self.local_signal_neighbor_gap,
            self.passive_reference_axis_drift,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "missing_geometry": self.missing_geometry,
            "stage_order_violations": self.stage_order_violations,
            "reversal_distance": self.reversal_distance,
            "interface_side_violations": self.interface_side_violations,
            "interface_owner_distance": self.interface_owner_distance,
            "frontier_distance": self.frontier_distance,
            "feedback_distance": self.feedback_distance,
            "support_distance": self.support_distance,
            "branch_alignment": self.branch_alignment,
            "repeated_alignment": self.repeated_alignment,
            "intra_block_dispersion": self.intra_block_dispersion,
            "unrelated_block_proximity": self.unrelated_block_proximity,
            "power_interface_distance": self.power_interface_distance,
            "infrastructure_primary_row_intrusion": self.infrastructure_primary_row_intrusion,
            "feedback_intrusion": self.feedback_intrusion,
            "sequential_stage_row_drift": self.sequential_stage_row_drift,
            "directed_interface_row_drift": self.directed_interface_row_drift,
            "support_axis_drift": self.support_axis_drift,
            "passive_reference_axis_drift": self.passive_reference_axis_drift,
            "local_signal_neighbor_gap": self.local_signal_neighbor_gap,
        }


def semantic_composition_penalty_breakdown(plan, packing) -> SemanticPenaltyBreakdown:
    """Return semantic readability penalties for one fully proved placement.

    The vector deliberately keeps hard-to-read semantic defects ahead of softer
    locality preferences.  Incomparable siblings are not assigned precedence.
    Feedback, support, and package relations contribute locality only; they are
    never reinterpreted as forward signal order.
    """

    rects = _placed_rects(packing)
    centers = {block_id: _center(rect) for block_id, rect in rects.items()}
    missing_geometry = sum(1 for block in plan.blocks if block.id not in centers)
    signal_relations = _signal_relations(plan)

    stage_order_violations = 0
    reversal_distance = 0
    for source, target, _net in signal_relations:
        if source not in centers or target not in centers:
            continue
        delta = centers[target][0] - centers[source][0]
        if delta < 0:
            stage_order_violations += 1
            reversal_distance += -delta

    roles = _interface_roles(plan, signal_relations)
    interface_side_violations = 0
    interface_owner_distance = 0
    interface_soft_gap = 0
    for source, target, _net in signal_relations:
        if source not in centers or target not in centers:
            continue
        source_x = centers[source][0]
        target_x = centers[target][0]
        source_roles = roles.get(source, set())
        target_roles = roles.get(target, set())
        if "signal_in" in source_roles and "signal_out" not in source_roles and source_x > target_x:
            interface_side_violations += 1
            interface_owner_distance += source_x - target_x
        if "signal_out" in target_roles and "signal_in" not in target_roles and target_x < source_x:
            interface_side_violations += 1
            interface_owner_distance += source_x - target_x

    # Preserve producer/consumer locality after an interface reaches the
    # correct side. Use the nearest owner for fanout; do not turn shared
    # distribution into an artificial all-owner constraint.
    for interface_id, interface_roles in sorted(roles.items()):
        interface_rect = rects.get(interface_id)
        if interface_rect is None:
            continue
        if interface_roles == {"signal_in"}:
            owners = {
                target
                for source, target, _net in signal_relations
                if source == interface_id and target in rects and target not in roles
            }
            gaps = [max(0, rects[owner][0] - interface_rect[2]) for owner in sorted(owners)]
        elif interface_roles == {"signal_out"}:
            owners = {
                source
                for source, target, _net in signal_relations
                if target == interface_id and source in rects and source not in roles
            }
            gaps = [max(0, interface_rect[0] - rects[owner][2]) for owner in sorted(owners)]
        else:
            continue
        if gaps:
            interface_soft_gap += max(0, min(gaps) - 2 * PITCH)

    # A multi-output schematic can contain separate parallel signal chains.
    # The rightmost cell of an unrelated chain is not the output frontier for
    # this chain. Only use producer-local frontiers when there are multiple
    # directed outputs (or consumer-local frontiers for multiple inputs).
    # Single-interface layouts preserve the original page-edge preference.
    signal_parents: dict[str, set[str]] = defaultdict(set)
    signal_children: dict[str, set[str]] = defaultdict(set)
    for source, target, _net in signal_relations:
        if source != target:
            signal_parents[target].add(source)
            signal_children[source].add(target)

    def signal_lineage_extreme(interface_id: str, *, upstream: bool) -> int | None:
        links = signal_parents if upstream else signal_children
        pending = sorted(links[interface_id])
        visited: set[str] = set()
        positions: list[int] = []
        while pending:
            member = pending.pop()
            if member in visited:
                continue
            visited.add(member)
            # Interfaces delimit a corridor: do not borrow the frontier of a
            # different output (or walk through an external shared endpoint).
            if member in roles:
                continue
            if member in centers:
                positions.append(centers[member][0])
            pending.extend(sorted(links[member]))
        if not positions:
            return None
        return max(positions) if upstream else min(positions)

    directed_inputs = {
        block_id
        for block_id, block_roles in roles.items()
        if block_roles == {"signal_in"} and block_id in centers
    }
    directed_outputs = {
        block_id
        for block_id, block_roles in roles.items()
        if block_roles == {"signal_out"} and block_id in centers
    }
    frontier_distance = 0
    if centers:
        min_x = min(point[0] for point in centers.values())
        max_x = max(point[0] for point in centers.values())
        for block_id, block_roles in sorted(roles.items()):
            point = centers.get(block_id)
            if point is None or block_roles == {"signal_in", "signal_out"}:
                continue
            if "signal_in" in block_roles:
                bound = (
                    signal_lineage_extreme(block_id, upstream=False)
                    if block_id in directed_inputs and len(directed_inputs) > 1
                    else None
                )
                frontier_distance += max(0, point[0] - (min_x if bound is None else bound))
            if "signal_out" in block_roles:
                bound = (
                    signal_lineage_extreme(block_id, upstream=True)
                    if block_id in directed_outputs and len(directed_outputs) > 1
                    else None
                )
                frontier_distance += max(0, (max_x if bound is None else bound) - point[0])

    feedback_distance = 0
    support_distance = 0
    for edge in plan.edges:
        source = centers.get(edge.source)
        target = centers.get(edge.target)
        if source is None or target is None:
            continue
        distance = abs(source[0] - target[0]) + abs(source[1] - target[1])
        if edge.kind == "feedback":
            feedback_distance += distance
        elif edge.kind in {"support", "package"}:
            support_distance += distance

    branch_alignment = _branch_readability_penalty(plan, centers, rects, signal_relations)
    repeated_alignment = _repeated_alignment_penalty(plan, centers, signal_relations)
    intra_block_dispersion = _intra_block_dispersion(packing)
    unrelated_block_proximity = _unrelated_block_proximity(plan, rects)
    power_interface_distance = _power_interface_distance(plan, centers)
    infrastructure_primary_row_intrusion = _infrastructure_primary_row_intrusion(plan, centers)
    feedback_intrusion = _feedback_corridor_intrusions(plan, rects, centers)
    (
        sequential_stage_row_drift,
        directed_interface_row_drift,
        material_interface_row_dislocation,
    ) = _signal_row_alignment_components(plan, centers, signal_relations)
    support_axis_drift = _support_axis_alignment_penalty(plan, centers)
    passive_reference_axis_drift = _passive_reference_axis_alignment_penalty(packing)
    # Nearest directed connector-to-owner gap is a soft signal-neighbor
    # preference, not a wrong-side violation. Keep it below fragmentation,
    # grouping, and all stronger semantic obligations in the lexicographic key.
    local_signal_neighbor_gap = _local_signal_neighbor_gap(plan, rects) + _grid_units(
        interface_soft_gap
    )

    return SemanticPenaltyBreakdown(
        missing_geometry=missing_geometry,
        stage_order_violations=stage_order_violations,
        reversal_distance=_grid_units(reversal_distance),
        interface_side_violations=interface_side_violations,
        interface_owner_distance=_grid_units(interface_owner_distance),
        frontier_distance=_grid_units(frontier_distance),
        feedback_distance=_grid_units(feedback_distance),
        support_distance=_grid_units(support_distance),
        branch_alignment=_grid_units(branch_alignment),
        repeated_alignment=repeated_alignment,
        intra_block_dispersion=intra_block_dispersion,
        unrelated_block_proximity=unrelated_block_proximity,
        power_interface_distance=power_interface_distance,
        infrastructure_primary_row_intrusion=infrastructure_primary_row_intrusion,
        feedback_intrusion=feedback_intrusion,
        sequential_stage_row_drift=sequential_stage_row_drift,
        directed_interface_row_drift=directed_interface_row_drift,
        material_interface_row_dislocation=material_interface_row_dislocation,
        support_axis_drift=support_axis_drift,
        passive_reference_axis_drift=passive_reference_axis_drift,
        local_signal_neighbor_gap=local_signal_neighbor_gap,
    )


def semantic_composition_penalties(plan, packing) -> SemanticPenaltyVector:
    """Return the stable lexicographic vector used by production ranking."""
    return semantic_composition_penalty_breakdown(plan, packing).vector()


def compactness_whitespace_penalties(packing) -> CompactnessPenaltyVector:
    """Return integer page-use penalties after semantic and routing quality."""

    rects = tuple(_placed_rects(packing).values())
    if not rects:
        return (0, 0, 0)
    left = min(rect[0] for rect in rects)
    top = min(rect[1] for rect in rects)
    right = max(rect[2] for rect in rects)
    bottom = max(rect[3] for rect in rects)
    width_units = _grid_units(right - left)
    height_units = _grid_units(bottom - top)
    area_units = width_units * height_units

    page_center_x = (LEFT + RIGHT) // 2
    page_center_y = (TOP + BOTTOM) // 2
    content_center_x = (left + right) // 2
    content_center_y = (top + bottom) // 2
    edge_bias = abs(content_center_x - page_center_x) + abs(content_center_y - page_center_y)

    left_margin = max(0, left - LEFT)
    right_margin = max(0, RIGHT - right)
    top_margin = max(0, top - TOP)
    bottom_margin = max(0, BOTTOM - bottom)
    whitespace_imbalance = abs(left_margin - right_margin) + abs(top_margin - bottom_margin)
    return area_units, _grid_units(edge_bias), _grid_units(whitespace_imbalance)


def _field_slot_consistency_penalty(packing) -> int:
    """Prefer consistent reference/value slots for semantically comparable cells.

    Only compare symbol-relative field offsets with matching functional kind,
    terminal-role footprint and symbol rotation. Do not compare differently
    rotated symbols, unrelated functional roles or unmeasured field locations.
    This is a soft *aesthetic* tie-breaker, below routing and whitespace in the
    candidate key; legal field clearance always takes precedence.
    """
    groups: dict[tuple[str, tuple[str, ...], int], list[Point]] = defaultdict(list)
    for item in packing.fragments:
        fragment = item.fragment
        block = fragment.block
        if block.kind == "interface":
            continue
        roles_by_component: dict[str, set[str]] = defaultdict(set)
        for port in block.ports:
            for terminal in getattr(port, "terminals", ()):
                roles_by_component[terminal[0]].add(port.role)
        positions = getattr(fragment, "positions", {})
        text_positions = getattr(fragment, "text_positions", {})
        angles = getattr(fragment, "angles", {})
        for occurrence, center in sorted(positions.items()):
            text = text_positions.get(occurrence)
            roles = roles_by_component.get(occurrence[0])
            if text is None or not roles:
                continue
            angle = angles.get(occurrence, 0) % 360
            if angle not in {0, 90, 180, 270}:
                continue
            signature = (block.kind, tuple(sorted(roles)), angle)
            groups[signature].append((text[0] - center[0], text[1] - center[1]))

    drift = 0
    for offsets in groups.values():
        if len(offsets) < 2:
            continue
        midpoint = (len(offsets) - 1) // 2
        target_x = sorted(point[0] for point in offsets)[midpoint]
        target_y = sorted(point[1] for point in offsets)[midpoint]
        drift += sum(abs(x - target_x) + abs(y - target_y) for x, y in offsets)
    return _grid_units(drift)


def _coalesced_route_segments(segments):
    """Coalesce split collinear strokes before evaluating route backtracking."""
    spans = defaultdict(list)
    for first, second in segments:
        if first == second:
            continue
        if first[1] == second[1]:
            spans[(0, first[1])].append(tuple(sorted((first[0], second[0]))))
        elif first[0] == second[0]:
            spans[(1, first[0])].append(tuple(sorted((first[1], second[1]))))
        else:
            raise ValueError("canonical conductor geometry must be orthogonal")
    result = []
    for (axis, fixed), intervals in sorted(spans.items()):
        low, high = min(intervals)
        for left, right in sorted(intervals)[1:]:
            if left <= high:
                high = max(high, right)
            else:
                result.append(
                    ((low, fixed), (high, fixed)) if axis == 0 else ((fixed, low), (fixed, high))
                )
                low, high = left, right
        result.append(((low, fixed), (high, fixed)) if axis == 0 else ((fixed, low), (fixed, high)))
    return tuple(result)


def route_backtracking_penalty(canonical_trees) -> int:
    """Count same-side return legs across continuous rectilinear conductor runs."""
    penalty = 0
    for tree in canonical_trees:
        spans = _coalesced_route_segments(tree.geometry_signature)
        for first, second in spans:
            axis = 0 if first[1] == second[1] else 1
            across = 1 - axis
            low_legs = set()
            high_legs = set()
            for leg_first, leg_second in spans:
                if leg_first[axis] != leg_second[axis]:
                    continue
                position = leg_first[axis]
                fixed = first[across]
                if not (
                    first[axis] <= position <= second[axis]
                    and leg_first[across] <= fixed <= leg_second[across]
                ):
                    continue
                if leg_first[across] < fixed:
                    low_legs.add(position)
                if leg_second[across] > fixed:
                    high_legs.add(position)
            for legs in (low_legs, high_legs):
                positions = sorted(legs)
                # Each gap between neighboring same-side legs represents
                # one distinct return interval. Counting *every* pair also
                # charges nested spans that are not separate detours, so a
                # legitimate N-way fanout grows quadratically in the score.
                # Neighbor-only gaps are additive and remain invariant to
                # segmentation, branch order and conductor direction.
                for left, right in itertools.pairwise(positions):
                    penalty += max(1, _grid_units(right - left))
    return penalty


def route_branch_arm_spread(canonical_trees) -> int:
    """Measure the largest unequal straight-arm spread at a route junction.

    This favors balanced, legible fanouts after semantic layout and return-leg
    clarity have tied. It is computed from the candidate's own proved geometry.
    """
    worst = 0
    for tree in canonical_trees:
        segments = _coalesced_route_segments(tree.geometry_signature)
        arms: dict[Point, set[str]] = defaultdict(set)
        for first, second in tree.geometry_signature:
            if first[1] == second[1]:
                left, right = sorted((first, second))
                arms[left].add("right")
                arms[right].add("left")
            else:
                top, bottom = sorted((first, second), key=lambda point: point[1])
                arms[top].add("down")
                arms[bottom].add("up")
        endpoints = {point for segment in segments for point in segment}
        for point, directions in arms.items():
            if len(directions) < 3:
                continue
            lengths = []
            for direction in sorted(directions):
                axis = 0 if direction in {"left", "right"} else 1
                start = point[axis]
                forward = direction in {"right", "down"}
                intervals = [
                    tuple(sorted((first[axis], second[axis])))
                    for first, second in segments
                    if first[1 - axis] == second[1 - axis] == point[1 - axis]
                ]
                reach = start
                while True:
                    if forward:
                        farther = max(
                            (high for low, high in intervals if low <= reach < high), default=reach
                        )
                    else:
                        farther = min(
                            (low for low, high in intervals if low < reach <= high), default=reach
                        )
                    if farther == reach:
                        break
                    reach = farther
                straight = {"left", "right"} if axis == 0 else {"up", "down"}
                stops = [
                    abs(other[axis] - start)
                    for other in endpoints
                    if other[1 - axis] == point[1 - axis]
                    and (
                        (start < other[axis] <= reach)
                        if forward
                        else (reach <= other[axis] < start)
                    )
                    and arms[other] != straight
                ]
                lengths.append(min(stops, default=abs(reach - start)))
            worst = max(worst, _grid_units(max(lengths) - min(lengths)))
    return worst


def composition_candidate_key(
    plan,
    packing,
    routing_compactness,
    *,
    routing_backtracking: int = 0,
    branch_arm_spread: int = 0,
) -> CandidateKey:
    """Build the production lexicographic key for a fully proved candidate."""

    if len(routing_compactness) != 6:
        raise ValueError("routing_compactness must contain six deterministic fields")
    union_length, worst_length, bend_count, _legacy_area, seed_index, round_index = (
        routing_compactness
    )
    breakdown = semantic_composition_penalty_breakdown(plan, packing)
    semantic = breakdown.vector()
    area, edge_bias, whitespace_imbalance = compactness_whitespace_penalties(packing)
    return (
        # Keep flow direction, interface-side correctness, ownership,
        # grouping, repetition and primary-stage alignment above route shape.
        # Once those higher-priority obligations are equal, a shorter return
        # leg is preferable to minor connector-row/support-axis refinements.
        # This is a generic choice among already electrically proved routes;
        # it changes neither hard length gates nor frozen observer tolerances.
        *semantic[:16],
        # Escaped owner rows are a material visual-disconnection risk, but
        # small connector-row adjustments remain secondary to route clarity.
        breakdown.material_interface_row_dislocation,
        # Independent final-output ownership takes priority over cosmetic
        # route-backtracking: an output on an unrelated chain's row is
        # harder to trace even when its conductor has a slightly shorter jog.
        # Shared-producer fanout and single-output layouts remain exempt.
        _independent_output_owner_row_drift(plan, packing),
        int(routing_backtracking),
        *semantic[16:],
        # Prefer a short, legible route rather than letting one saved bend
        # dominate an arbitrarily long detour. One bend costs eight grid
        # pitches of wire; backtracking and semantic obligations remain higher
        # priorities, and the independent length/clearance gates are unchanged.
        int(union_length) + 8 * PITCH * int(bend_count),
        # Balanced fanout arms break ties between otherwise equally short and
        # legible routes; they never buy extra conductor or connector drift.
        int(branch_arm_spread),
        int(bend_count),
        int(union_length),
        int(worst_length),
        # Within the compactness tier, page balance precedes minimum area.
        # Avoid rewarding pathological corner packing when routing ties.
        edge_bias,
        area,
        whitespace_imbalance,
        _field_slot_consistency_penalty(packing),
        int(seed_index),
        int(round_index),
    )
