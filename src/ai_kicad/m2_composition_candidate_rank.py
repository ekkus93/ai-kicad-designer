"""Deterministic semantic-first ranking for fully proved composition candidates.

This module is production scoring, not independent qualification evidence.  It
uses only generic semantic-plan roles and measured placement geometry.  Hard
electrical and M2h2 invariants are established before a candidate is ranked.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .m2a import PITCH
from .m2_pack import BOTTOM, LEFT, RIGHT, TOP
from .m2_terminal_interface_flow import inferred_passive_interface_signal_relations

Rect = tuple[int, int, int, int]
Point = tuple[int, int]
SemanticPenaltyVector = tuple[int, ...]
CompactnessPenaltyVector = tuple[int, int, int]
CandidateKey = tuple[int, ...]


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
    relations.update(inferred_passive_interface_signal_relations(plan))
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


def _signal_reachability(plan, signal_relations) -> set[tuple[str, str]]:
    blocks = {block.id for block in plan.blocks}
    outgoing: dict[str, set[str]] = {block_id: set() for block_id in blocks}
    for source, target, _net in signal_relations:
        if source in outgoing and target in blocks and source != target:
            outgoing[source].add(target)
    reachable: set[tuple[str, str]] = set()
    for source in sorted(blocks):
        pending = list(sorted(outgoing[source]))
        seen: set[str] = set()
        while pending:
            target = pending.pop()
            if target in seen:
                continue
            seen.add(target)
            reachable.add((source, target))
            pending.extend(sorted(outgoing.get(target, ())))
    return reachable


def _block_semantic_signature(plan, block_id: str) -> tuple:
    by_id = {block.id: block for block in plan.blocks}
    block = by_id[block_id]
    port_roles = tuple(sorted(port.role for port in block.ports))
    incident = []
    for edge in plan.edges:
        if edge.source == block_id:
            incident.append(
                (
                    "out",
                    edge.kind,
                    by_id.get(edge.target).kind if edge.target in by_id else "unknown",
                )
            )
        elif edge.target == block_id:
            incident.append(
                (
                    "in",
                    edge.kind,
                    by_id.get(edge.source).kind if edge.source in by_id else "unknown",
                )
            )
    return block.kind, port_roles, tuple(sorted(incident))


def _repeated_alignment_penalty(plan, centers, signal_relations) -> int:
    """Penalize off-axis drift among semantically equivalent incomparable peers.

    A repeated peer must share a generic semantic signature and have no directed
    primary-flow path to the other peer. This keeps serial same-kind stages out
    of the repeated-channel metric while allowing either row- or column-oriented
    repeated-channel grammars.
    """

    reachable = _signal_reachability(plan, signal_relations)
    groups: dict[tuple, list[str]] = defaultdict(list)
    for block in plan.blocks:
        if block.id in centers and block.kind != "interface":
            groups[_block_semantic_signature(plan, block.id)].append(block.id)

    penalty = 0
    for members in groups.values():
        ordered_members = sorted(members)
        for index, first in enumerate(ordered_members):
            for second in ordered_members[index + 1 :]:
                if (first, second) in reachable or (second, first) in reachable:
                    continue
                first_point = centers[first]
                second_point = centers[second]
                # Either a shared row or a shared column is a valid repeated
                # grammar. Penalize only the smaller off-axis displacement.
                penalty += min(
                    abs(first_point[0] - second_point[0]),
                    abs(first_point[1] - second_point[1]),
                )
    return _grid_units(penalty)


def _intra_block_dispersion(packing) -> int:
    """Penalize full X-plus-Y spread of every functional cell's occurrences.

    The maximum distance between a *single pair* can undercount fragmentation
    when horizontal and vertical extrema belong to different occurrences.
    Measure the complete bounding span instead, using only selected fragment
    geometry; a rigid page translation cannot change this penalty.
    """
    penalty = 0
    for item in packing.fragments:
        delta = getattr(item, "delta", (0, 0))
        points = tuple(
            (point[0] + delta[0], point[1] + delta[1])
            for point in getattr(item.fragment, "positions", {}).values()
        )
        if len(points) < 2:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        penalty += max(xs) - min(xs) + max(ys) - min(ys)
    return _grid_units(penalty)


def _rect_gap(first: Rect, second: Rect) -> int:
    horizontal = max(0, max(first[0] - second[2], second[0] - first[2]))
    vertical = max(0, max(first[1] - second[3], second[1] - first[3]))
    return horizontal + vertical


def _unrelated_block_proximity(plan, rects: dict[str, Rect]) -> int:
    """Penalize unrelated functional cells that visually collapse together."""
    by_id = {block.id: block for block in plan.blocks}
    related: set[frozenset[str]] = set()
    for edge in plan.edges:
        if edge.source != edge.target:
            related.add(frozenset((edge.source, edge.target)))
    for item in plan.precedence:
        if item.source_fragment != item.target_fragment:
            related.add(frozenset((item.source_fragment, item.target_fragment)))

    eligible = sorted(
        block_id for block_id in rects if block_id in by_id and by_id[block_id].kind != "interface"
    )
    penalty = 0
    for index, first_id in enumerate(eligible):
        for second_id in eligible[index + 1 :]:
            if frozenset((first_id, second_id)) in related:
                continue
            gap = _rect_gap(rects[first_id], rects[second_id])
            penalty += max(0, PITCH - gap)
    return _grid_units(penalty)


def _local_signal_neighbor_gap(plan, rects: dict[str, Rect]) -> int:
    """Prefer nearby members of label-eligible two-fragment signal nets.

    Shared distribution, mandatory explicit geometry, interfaces, and fanout
    are excluded. This is placement preference, not emitted-route proof.
    """
    blocks = {block.id: block for block in plan.blocks}
    pairs = {
        tuple(sorted(set(net.fragments)))
        for net in getattr(plan, "presentation_nets", ())
        if net.role == "signal"
        and not net.explicit_geometry_required
        and len(set(net.fragments)) == 2
        and all(
            fragment in rects and fragment in blocks and blocks[fragment].kind != "interface"
            for fragment in net.fragments
        )
    }
    return sum(
        _grid_units(max(0, _rect_gap(rects[first], rects[second]) - 2 * PITCH))
        for first, second in sorted(pairs)
    )


def _power_interface_distance(plan, centers: dict[str, Point]) -> int:
    """Keep external power inputs near semantically connected supply/reference infrastructure."""
    by_id = {block.id: block for block in plan.blocks}
    power_interfaces = {
        block.id
        for block in plan.blocks
        if block.kind == "interface" and any(port.role == "power_in" for port in block.ports)
    }
    infrastructure = {
        block_id
        for edge in plan.edges
        if edge.kind in {"power", "reference"}
        for block_id in (edge.source, edge.target)
        if block_id in by_id and by_id[block_id].kind != "interface"
    }
    total = 0
    for interface_id in sorted(power_interfaces):
        interface = centers.get(interface_id)
        if interface is None:
            continue
        connected = {
            edge.target if edge.source == interface_id else edge.source
            for edge in plan.edges
            if edge.kind in {"power", "reference"}
            and interface_id in {edge.source, edge.target}
            and (edge.target if edge.source == interface_id else edge.source) in infrastructure
        }
        candidates = connected or infrastructure
        distances = [
            abs(interface[0] - centers[owner][0]) + abs(interface[1] - centers[owner][1])
            for owner in sorted(candidates)
            if owner in centers
        ]
        if distances:
            total += min(distances)
    return _grid_units(total)


def _infrastructure_primary_row_intrusion(plan, centers: dict[str, Point]) -> int:
    """Penalize supply/reference infrastructure that occupies the primary signal row."""
    signal_ids = {
        block_id
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
        for block_id in (edge.source, edge.target)
        if block_id in centers
    }
    signal_rows = sorted(
        centers[block_id][1]
        for block_id in signal_ids
        if next((block for block in plan.blocks if block.id == block_id), None) is not None
    )
    if not signal_rows:
        return 0
    primary_row = signal_rows[len(signal_rows) // 2]
    infrastructure_ids = {
        block_id
        for edge in plan.edges
        if edge.kind in {"power", "reference"}
        for block_id in (edge.source, edge.target)
        if block_id in centers and block_id not in signal_ids
    }
    penalty = sum(
        max(0, 2 * PITCH - abs(centers[block_id][1] - primary_row))
        for block_id in sorted(infrastructure_ids)
    )
    return _grid_units(penalty)


def _branch_readability_penalty(
    plan, centers: dict[str, Point], rects: dict[str, Rect], signal_relations
) -> int:
    """Prefer a visible, centered fanout with equally deep forward branches.

    Group targets by source and net, not a case/fixture name. Reuse the same
    directed signal relations as frontier ranking, including terminal-inferred
    and precedence-inferred relationships. Deduplicate mixed annotations. A
    source should sit between its branch rows; sibling targets should occupy
    a consistent column. Penalize unrelated obstacles intersecting both short
    orthogonal corridors to a branch target. This is a *placement proxy*, not
    evidence of actual routed-wire crossings. Single-target and non-signal
    connections are exempt.
    """
    fanouts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for source, target, net in signal_relations:
        if source != target and source in centers and target in centers:
            fanouts[(source, net)].add(target)

    known_blocks = {block.id for block in plan.blocks if block.kind != "interface"}
    penalty = 0
    for (source_id, _net), target_ids in sorted(fanouts.items()):
        if len(target_ids) < 2:
            continue
        source_x, source_y = centers[source_id]
        targets = [centers[target_id] for target_id in sorted(target_ids)]
        target_ys = [point[1] for point in targets]
        target_xs = [point[0] for point in targets]
        # The doubled midpoint avoids truncation bias for odd grid pitches.
        penalty += abs(2 * source_y - min(target_ys) - max(target_ys)) // 2
        penalty += max(target_xs) - min(target_xs)
        # The forward branch should remain visually attributable to its origin.
        penalty += sum(max(0, source_x - target_x) for target_x in target_xs)

        # Sibling branch targets and explicitly local support/package cells
        # belong to the fanout family, not to the unrelated-obstacle set.
        family = {source_id, *target_ids}
        related = set(family)
        for edge in plan.edges:
            if edge.kind in {"support", "package"} and (
                edge.source in family or edge.target in family
            ):
                related.update((edge.source, edge.target))
        obstacles = tuple(
            rect
            for block_id, rect in sorted(rects.items())
            if block_id not in related and block_id in known_blocks
        )
        for target_id in sorted(target_ids):
            penalty += PITCH * _shortest_elbow_intrusion_count(
                centers[source_id], centers[target_id], obstacles
            )
    return penalty


def _segment_crosses_block(start: Point, end: Point, rect: Rect) -> bool:
    """Return whether a rectilinear centerline crosses a block's interior."""
    if start[0] == end[0]:
        low_y, high_y = sorted((start[1], end[1]))
        overlaps_y = min(high_y, rect[3]) > max(low_y, rect[1])
        return rect[0] < start[0] < rect[2] and overlaps_y
    if start[1] == end[1]:
        low_x, high_x = sorted((start[0], end[0]))
        overlaps_x = min(high_x, rect[2]) > max(low_x, rect[0])
        return rect[1] < start[1] < rect[3] and overlaps_x
    raise ValueError("feedback corridor segments must be orthogonal")


def _shortest_elbow_intrusion_count(
    source: Point, target: Point, obstacles: tuple[Rect, ...]
) -> int:
    """Conservative minimum unrelated obstacles across two Manhattan elbows."""
    if not obstacles:
        return 0
    elbow_at_target_x = (target[0], source[1])
    elbow_at_source_x = (source[0], target[1])
    alternative_paths = (
        ((source, elbow_at_target_x), (elbow_at_target_x, target)),
        ((source, elbow_at_source_x), (elbow_at_source_x, target)),
    )
    return min(
        sum(any(_segment_crosses_block(a, b, rect) for a, b in segments) for rect in obstacles)
        for segments in alternative_paths
    )


def _feedback_corridor_intrusions(plan, rects: dict[str, Rect], centers: dict[str, Point]) -> int:
    """Score unrelated obstacles that intersect both shortest feedback elbows.

    This conservative pre-route proxy never assumes a wire was routed through a
    block. If either shortest Manhattan elbow is clear, the penalty is zero;
    actual routed intrusions remain the independent observer's responsibility.
    Support/package/feedback relatives of either endpoint are not unrelated.
    """
    by_id = {block.id: block for block in plan.blocks}
    edges = {
        (edge.source, edge.target, edge.net)
        for edge in plan.edges
        if edge.kind == "feedback" and edge.source != edge.target
    }
    penalty = 0
    for source_id, target_id, _net in sorted(edges):
        source = centers.get(source_id)
        target = centers.get(target_id)
        if source is None or target is None:
            continue
        related = {source_id, target_id}
        for edge in plan.edges:
            if edge.kind not in {"feedback", "support", "package"}:
                continue
            if edge.source in {source_id, target_id}:
                related.add(edge.target)
            if edge.target in {source_id, target_id}:
                related.add(edge.source)
        obstacles = tuple(
            rect
            for block_id, rect in sorted(rects.items())
            if block_id not in related and block_id in by_id and by_id[block_id].kind != "interface"
        )
        if not obstacles:
            continue
        penalty += _shortest_elbow_intrusion_count(source, target, obstacles)
    return penalty


def _signal_row_alignment_penalties(
    plan, centers: dict[str, Point], signal_relations: tuple[tuple[str, str, str], ...]
) -> tuple[int, int]:
    """Prefer legible serial signal rows and connector-to-owner row alignment.

    Only a one-to-one directed relation between signal-processing blocks is
    treated as a serial stage alignment. Branches and convergences may occupy
    different rows; supply, feedback and support edges do not define signal
    baselines. An interface with multiple consumers needs to align with at
    least one connected signal row, not all fanout rows simultaneously.
    """
    blocks = {block.id: block for block in plan.blocks}
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for source, target, _net in signal_relations:
        if source == target or source not in centers or target not in centers:
            continue
        outgoing[source].add(target)
        incoming[target].add(source)

    def is_signal_stage(block_id: str) -> bool:
        block = blocks.get(block_id)
        return bool(
            block is not None
            and block.kind != "interface"
            and {"signal_in", "signal_out"}.issubset({port.role for port in block.ports})
        )

    stage_drift = 0
    for source_id, targets in sorted(outgoing.items()):
        if len(targets) != 1 or not is_signal_stage(source_id):
            continue
        target_id = next(iter(targets))
        if len(incoming[target_id]) != 1 or not is_signal_stage(target_id):
            continue
        stage_drift += abs(centers[source_id][1] - centers[target_id][1])

    interface_drift = 0
    # Match interface-side ranking: unique inferred/precedence-backed signal
    # polarity is meaningful even when authored ports are not explicitly typed
    # signal_in or signal_out. Preserve the bidirectional ambiguity exemption.
    interface_roles = _interface_roles(plan, signal_relations)
    for block_id, block in sorted(blocks.items()):
        if block.kind != "interface" or block_id not in centers:
            continue
        roles = interface_roles[block_id]
        # A genuinely bidirectional or ambiguous interface has no prescribed
        # signal-row polarity.
        if "signal_in" in roles and "signal_out" in roles:
            continue
        if "signal_in" in roles:
            neighbors = outgoing[block_id]
        elif "signal_out" in roles:
            neighbors = incoming[block_id]
        else:
            continue
        rows = [
            centers[neighbor][1]
            for neighbor in sorted(neighbors)
            if neighbor in centers and blocks[neighbor].kind != "interface"
        ]
        if rows:
            interface_drift += min(abs(centers[block_id][1] - row) for row in rows)
    return _grid_units(stage_drift), _grid_units(interface_drift)


def _support_axis_alignment_penalty(plan, centers: dict[str, Point]) -> int:
    """Prefer a shared row or column for explicitly owned local support.

    Support and package links encode local visual ownership. Shared supply and
    reference edges, feedback paths, and ordinary signal flow do not imply this
    alignment. Deduplicate equivalent edges to keep the score independent of
    semantic annotation order and repeated declarations.
    """
    pairs = {
        tuple(sorted((edge.source, edge.target)))
        for edge in plan.edges
        if edge.kind in {"support", "package"}
        and edge.source != edge.target
        and edge.source in centers
        and edge.target in centers
    }
    drift = sum(
        min(
            abs(centers[source][0] - centers[target][0]),
            abs(centers[source][1] - centers[target][1]),
        )
        for source, target in sorted(pairs)
    )
    return _grid_units(drift)


def _passive_reference_axis_alignment_penalty(packing) -> int:
    """Align locally owned reference legs by terminal roles, not component names.

    If a signal-through stage has one distinct reference/shunt component,
    prefer that leg vertically aligned with the primary signal component.
    Shared, missing, multi-unit, or ambiguous ownership is exempt.
    """
    drift = 0
    for item in packing.fragments:
        block = item.fragment.block
        ports = getattr(block, "ports", ())

        def component_ids(role: str) -> set[str]:
            return {
                terminal[0]
                for port in ports
                if port.role == role
                for terminal in getattr(port, "terminals", ())
            }

        main_ids = component_ids("signal_in") & component_ids("signal_out")
        reference_ids = component_ids("reference") - main_ids
        if len(main_ids) != 1 or len(reference_ids) != 1:
            continue
        main_id = next(iter(main_ids))
        reference_id = next(iter(reference_ids))
        positions = getattr(item.fragment, "positions", {})
        main = [point for occurrence, point in positions.items() if occurrence[0] == main_id]
        reference = [
            point for occurrence, point in positions.items() if occurrence[0] == reference_id
        ]
        if len(main) != 1 or len(reference) != 1:
            continue
        drift += abs(main[0][0] - reference[0][0])
    return _grid_units(drift)


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

    frontier_distance = 0
    if centers:
        min_x = min(point[0] for point in centers.values())
        max_x = max(point[0] for point in centers.values())
        for block_id, block_roles in roles.items():
            point = centers.get(block_id)
            if point is None:
                continue
            if "signal_in" in block_roles and "signal_out" in block_roles:
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

    branch_alignment = _branch_readability_penalty(plan, centers, rects, signal_relations)
    repeated_alignment = _repeated_alignment_penalty(plan, centers, signal_relations)
    intra_block_dispersion = _intra_block_dispersion(packing)
    unrelated_block_proximity = _unrelated_block_proximity(plan, rects)
    power_interface_distance = _power_interface_distance(plan, centers)
    infrastructure_primary_row_intrusion = _infrastructure_primary_row_intrusion(plan, centers)
    feedback_intrusion = _feedback_corridor_intrusions(plan, rects, centers)
    sequential_stage_row_drift, directed_interface_row_drift = _signal_row_alignment_penalties(
        plan, centers, signal_relations
    )
    support_axis_drift = _support_axis_alignment_penalty(plan, centers)
    passive_reference_axis_drift = _passive_reference_axis_alignment_penalty(packing)
    local_signal_neighbor_gap = _local_signal_neighbor_gap(plan, rects)

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
        low, high = sorted(intervals)[0]
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
                for index, left in enumerate(positions):
                    for right in positions[index + 1 :]:
                        # Prefer a short, local return to an equally legible
                        # but unnecessarily wide U-shaped conductor detour.
                        penalty += max(1, _grid_units(right - left))
    return penalty


def composition_candidate_key(
    plan, packing, routing_compactness, *, routing_backtracking: int = 0
) -> CandidateKey:
    """Build the production lexicographic key for a fully proved candidate."""

    if len(routing_compactness) != 6:
        raise ValueError("routing_compactness must contain six deterministic fields")
    union_length, worst_length, bend_count, _legacy_area, seed_index, round_index = (
        routing_compactness
    )
    semantic = semantic_composition_penalties(plan, packing)
    area, edge_bias, whitespace_imbalance = compactness_whitespace_penalties(packing)
    return (
        *semantic,
        # Both candidates have already passed electrical/hard-routing proof.
        # Prefer a legible low-bend route over a shorter maze when all
        # higher-priority semantic obligations are identical.  This ranking
        # tier is generic and does not alter any length or ERC hard gate.
        # Penalize direction-reversing detours before bend/length tie-breaks.
        # Every ranked candidate has already passed independent hard proofs.
        int(routing_backtracking),
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
