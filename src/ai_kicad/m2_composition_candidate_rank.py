"""Deterministic semantic-first ranking for fully proved composition candidates.

This module is production scoring, not independent qualification evidence.  It
uses only generic semantic-plan roles and measured placement geometry.  Hard
electrical and M2h2 invariants are established before a candidate is ranked.
"""

from __future__ import annotations

from collections import defaultdict

from .m2a import PITCH
from .m2_pack import BOTTOM, LEFT, RIGHT, TOP

Rect = tuple[int, int, int, int]
Point = tuple[int, int]
SemanticPenaltyVector = tuple[int, int, int, int, int, int, int, int, int]
CompactnessPenaltyVector = tuple[int, int, int]
CandidateKey = tuple[int, ...]


def _grid_units(distance: int) -> int:
    """Convert a non-negative nanometre distance to deterministic grid units."""
    value = max(0, int(distance))
    return (value + PITCH - 1) // PITCH


def _center(rect: Rect) -> Point:
    return (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2


def _placed_rects(packing) -> dict[str, Rect]:
    rects: dict[str, Rect] = {}
    for item in packing.fragments:
        block_id = item.fragment.block.id
        rect = item.content_envelope or item.envelope
        if block_id in rects:
            prior = rects[block_id]
            rects[block_id] = (
                min(prior[0], rect[0]),
                min(prior[1], rect[1]),
                max(prior[2], rect[2]),
                max(prior[3], rect[3]),
            )
        else:
            rects[block_id] = rect
    return rects


def _signal_relations(plan) -> tuple[tuple[str, str, str], ...]:
    relations: set[tuple[str, str, str]] = set()
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"}:
            relations.add((edge.source, edge.target, edge.net))
    for item in plan.precedence:
        relations.add((item.source_fragment, item.target_fragment, item.net))
    return tuple(sorted(relations))


def _interface_roles(plan, signal_relations) -> dict[str, set[str]]:
    roles = {block.id: set() for block in plan.blocks if block.kind == "interface"}
    for block in plan.blocks:
        if block.kind != "interface":
            continue
        for port in block.ports:
            if port.role == "signal_in":
                roles[block.id].add("signal_in")
            elif port.role == "signal_out":
                roles[block.id].add("signal_out")
    for source, target, _net in signal_relations:
        if source in roles:
            roles[source].add("signal_in")
        if target in roles:
            roles[target].add("signal_out")
    return roles


def semantic_composition_penalties(plan, packing) -> SemanticPenaltyVector:
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
    for source, target, _net in signal_relations:
        if source not in centers or target not in centers:
            continue
        source_x = centers[source][0]
        target_x = centers[target][0]
        if "signal_in" in roles.get(source, set()) and source_x > target_x:
            interface_side_violations += 1
            interface_owner_distance += source_x - target_x
        if "signal_out" in roles.get(target, set()) and target_x < source_x:
            interface_side_violations += 1
            interface_owner_distance += source_x - target_x

    frontier_distance = 0
    if centers:
        min_x = min(point[0] for point in centers.values())
        max_x = max(point[0] for point in centers.values())
        for block_id, block_roles in roles.items():
            point = centers.get(block_id)
            if point is None:
                continue
            if "signal_in" in block_roles:
                frontier_distance += max(0, point[0] - min_x)
            if "signal_out" in block_roles:
                frontier_distance += max(0, max_x - point[0])

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

    branch_targets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for edge in plan.edges:
        if edge.kind != "branch":
            continue
        target = centers.get(edge.target)
        if edge.source in centers and target is not None:
            branch_targets[(edge.source, edge.net)].append(target[0])
    branch_alignment = sum(
        max(values) - min(values) for values in branch_targets.values() if len(values) > 1
    )

    return (
        missing_geometry,
        stage_order_violations,
        _grid_units(reversal_distance),
        interface_side_violations,
        _grid_units(interface_owner_distance),
        _grid_units(frontier_distance),
        _grid_units(feedback_distance),
        _grid_units(support_distance),
        _grid_units(branch_alignment),
    )


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


def composition_candidate_key(plan, packing, routing_compactness) -> CandidateKey:
    """Build the production lexicographic key for a fully proved candidate."""

    if len(routing_compactness) != 6:
        raise ValueError("routing_compactness must contain six deterministic fields")
    union_length, worst_length, bend_count, _legacy_area, seed_index, round_index = (
        routing_compactness
    )
    semantic = semantic_composition_penalties(plan, packing)
    compactness = compactness_whitespace_penalties(packing)
    return (
        *semantic,
        int(union_length),
        int(worst_length),
        int(bend_count),
        *compactness,
        int(seed_index),
        int(round_index),
    )
