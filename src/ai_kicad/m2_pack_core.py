"""Implementation details for m2 pack core."""

from __future__ import annotations

from dataclasses import dataclass, replace


from .ir import InputError
from .m2_fragments import FragmentVariant, Point, PortAnchor, Rect
from .m2_geometry import Gateway, Reservation
from .m2_pack import (
    BOTTOM,
    CHANNEL_GAP,
    LEFT,
    RIGHT,
    TOP,
)
from .m2_semantics import SemanticPlan
from .m2a import PITCH


@dataclass(frozen=True)
class PlacedFragment:
    fragment: FragmentVariant
    delta: Point
    envelope: Rect
    ports: tuple[PortAnchor, ...]
    content_envelope: Rect | None = None
    reservations: tuple[Reservation, ...] = ()
    gateways: tuple[Gateway, ...] = ()


@dataclass(frozen=True)
class Packing:
    fragments: tuple[PlacedFragment, ...]
    attempts: tuple[str, ...]


@dataclass(frozen=True)
class _Unit:
    """One shelf item whose members have genuine signal-stage ordering."""

    ids: tuple[str, ...]
    offsets: tuple[tuple[str, int, int], ...]
    width: int
    height: int
    serial: bool
    parallel_fanout: bool = False
    affinity_source: str | None = None


def _worksheet_clearance_packing(packing: Packing) -> Packing:
    """Translate a colliding whole packing on-grid; preserve all relative geometry."""
    worksheet = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
    boxes = [
        (
            item.rect[0] + placed.delta[0],
            item.rect[1] + placed.delta[1],
            item.rect[2] + placed.delta[0],
            item.rect[3] + placed.delta[1],
        )
        for placed in packing.fragments
        for item in placed.fragment.occupied_geometry
    ]

    def overlaps(box):
        return (
            box[0] < worksheet[2]
            and box[2] > worksheet[0]
            and box[1] < worksheet[3]
            and box[3] > worksheet[1]
        )

    if not any(overlaps(box) for box in boxes):
        return packing
    for shift in (-2 * PITCH, -4 * PITCH):
        shifted = [(x0, y0 + shift, x1, y1 + shift) for x0, y0, x1, y1 in boxes]
        if any(box[1] < 25_400_000 or overlaps(box) for box in shifted):
            continue
        return Packing(
            tuple(
                _place(item.fragment, item.envelope[0], item.envelope[1] + shift)
                for item in packing.fragments
            ),
            packing.attempts + (f"worksheet-clearance-translation:{shift}",),
        )
    return packing


def _translate_point(point: Point, delta: Point) -> Point:
    return point[0] + delta[0], point[1] + delta[1]


def _place(fragment: FragmentVariant, left: int, top: int) -> PlacedFragment:
    old = fragment.envelope
    delta = (
        ((left - old[0] + PITCH - 1) // PITCH) * PITCH,
        ((top - old[1] + PITCH - 1) // PITCH) * PITCH,
    )
    envelope = tuple(value + shift for value, shift in zip(old, (*delta, *delta), strict=True))
    ports = tuple(
        PortAnchor(anchor.port, _translate_point(anchor.point, delta), anchor.direction)
        for anchor in fragment.ports
    )
    content = tuple(
        value + shift
        for value, shift in zip(
            fragment.content_envelope or fragment.envelope,
            (*delta, *delta),
            strict=True,
        )
    )
    reservations = tuple(
        replace(
            reservation,
            rect=tuple(
                value + shift
                for value, shift in zip(reservation.rect, (*delta, *delta), strict=True)
            ),
        )
        for reservation in fragment.reservations
    )
    gateways = tuple(
        replace(
            gateway,
            anchor=_translate_point(gateway.anchor, delta),
            escape_polyline=tuple(
                _translate_point(point, delta) for point in gateway.escape_polyline
            ),
            tap_windows=tuple(
                replace(
                    window,
                    rect=tuple(
                        value + shift
                        for value, shift in zip(window.rect, (*delta, *delta), strict=True)
                    ),
                )
                for window in gateway.tap_windows
            ),
        )
        for gateway in fragment.gateways
    )
    return PlacedFragment(
        fragment,
        delta,
        envelope,
        ports,
        content,
        reservations,
        gateways,
    )


def _centroid_balanced_packing(packing: Packing) -> Packing | None:
    """Translate an entire valid arrangement toward the frozen page center.

    Only a rigid on-grid translation is considered: block order, proximity,
    fragment variants, and routed-port relative geometry remain unchanged.
    This is one optional seed, not an acceptance bypass. The subsequent
    placement/route/conductor/observer gates retain authority.
    """
    if not packing.fragments:
        return None
    rects = tuple(item.content_envelope or item.envelope for item in packing.fragments)
    content_left = min(rect[0] for rect in rects)
    content_top = min(rect[1] for rect in rects)
    content_right = max(rect[2] for rect in rects)
    content_bottom = max(rect[3] for rect in rects)
    # The physical placement envelope, not the independent maximum-spread
    # limit, defines the feasible page center used by candidate ranking.
    # Keep this target identical to compactness_whitespace_penalties().
    target_x = (LEFT + RIGHT) // 2
    target_y = (TOP + BOTTOM) // 2
    actual_x = (content_left + content_right) // 2
    actual_y = (content_top + content_bottom) // 2

    # Clamp the proposed rigid translation to the existing physical sheet
    # boundaries.  No fragment may leave its governed placement envelope.
    min_dx = LEFT - min(item.envelope[0] for item in packing.fragments)
    max_dx = RIGHT - max(item.envelope[2] for item in packing.fragments)
    min_dy = TOP - min(item.envelope[1] for item in packing.fragments)
    max_dy = BOTTOM - max(item.envelope[3] for item in packing.fragments)

    def snapped_clamped(target: int, minimum: int, maximum: int) -> int:
        desired = ((target + PITCH // 2) // PITCH) * PITCH
        lower = ((minimum + PITCH - 1) // PITCH) * PITCH
        upper = (maximum // PITCH) * PITCH
        return max(lower, min(desired, upper)) if lower <= upper else 0

    dx = snapped_clamped(target_x - actual_x, min_dx, max_dx)
    dy = snapped_clamped(target_y - actual_y, min_dy, max_dy)
    original_error = abs(actual_x - target_x) + abs(actual_y - target_y)
    # A fully centered placement can intrude on the lower-right worksheet
    # even when an independently centered horizontal or vertical shift is
    # legal. Try both one-axis fallbacks without altering relative geometry.
    worksheet = (177_000_000, 165_900_000, 285_100_000, 198_100_000)
    proposals: list[tuple[int, int, int, int, Packing]] = []
    for shift_x, shift_y in dict.fromkeys(((dx, dy), (dx, 0), (0, dy))):
        if shift_x == shift_y == 0:
            continue
        error = abs(actual_x + shift_x - target_x) + abs(actual_y + shift_y - target_y)
        if error >= original_error:
            continue
        changed = tuple(
            _place(item.fragment, item.envelope[0] + shift_x, item.envelope[1] + shift_y)
            for item in packing.fragments
        )
        if any(
            rect[0] < worksheet[2]
            and rect[2] > worksheet[0]
            and rect[1] < worksheet[3]
            and rect[3] > worksheet[1]
            for item in changed
            for geometry in item.fragment.occupied_geometry
            for rect in (
                tuple(
                    value + offset
                    for value, offset in zip(geometry.rect, (*item.delta, *item.delta), strict=True)
                ),
            )
        ):
            continue
        proposals.append(
            (
                error,
                abs(shift_x) + abs(shift_y),
                shift_x,
                shift_y,
                Packing(changed, packing.attempts + ("centroid-balanced-page",)),
            )
        )
    return min(proposals, key=lambda proposal: proposal[:4])[-1] if proposals else None


def _best_centroid_balanced_packing(packings: list[Packing]) -> Packing | None:
    """Choose the best legal rigid page-balance seed across shelf variants.

    The first shelf variant may already be centered or may have no legal
    translation. Searching the bounded existing variants adds no new geometry
    classes and keeps all later routing and electrical proofs authoritative.
    """
    options = [
        candidate
        for packing in packings
        if (candidate := _centroid_balanced_packing(packing)) is not None
    ]
    if not options:
        return None

    def key(packing: Packing) -> tuple:
        rects = tuple(item.content_envelope or item.envelope for item in packing.fragments)
        center_x = (min(rect[0] for rect in rects) + max(rect[2] for rect in rects)) // 2
        center_y = (min(rect[1] for rect in rects) + max(rect[3] for rect in rects)) // 2
        return (
            abs(center_x - (LEFT + RIGHT) // 2) + abs(center_y - (TOP + BOTTOM) // 2),
            tuple((item.fragment.id, item.delta) for item in packing.fragments),
        )

    return min(options, key=key)


def _topological(nodes: set[str], pairs: set[tuple[str, str]]) -> tuple[str, ...]:
    remaining = set(nodes)
    result: list[str] = []
    while remaining:
        ready = sorted(
            node
            for node in remaining
            if not any(source in remaining and target == node for source, target in pairs)
        )
        if not ready:
            raise InputError(f"PACK_SIGNAL_ORDER_CYCLE: {sorted(remaining)}")
        result.extend(ready)
        remaining.difference_update(ready)
    return tuple(result)


def _signal_chains(plan: SemanticPlan) -> tuple[tuple[str, ...], ...]:
    """Return independent shelves from the signal-only graph projection."""
    by_id = {block.id: block for block in plan.blocks}
    nodes = {
        block.id
        for block in plan.blocks
        if block.kind
        not in {
            "interface",
            "package_power",
            "power_stage",
            "unused_amplifier",
        }
    }
    pairs = {
        (edge.source, edge.target)
        for edge in plan.edges
        if edge.kind in {"signal", "branch"} and edge.source in nodes and edge.target in nodes
    } | {
        (edge.source_fragment, edge.target_fragment)
        for edge in plan.precedence
        if edge.source_fragment in nodes and edge.target_fragment in nodes
    }
    neighbors = {node: set() for node in nodes}
    for source, target in pairs:
        neighbors[source].add(target)
        neighbors[target].add(source)
    components: list[tuple[str, ...]] = []
    unseen = set(nodes)
    while unseen:
        seed = min(unseen)
        component: set[str] = set()
        pending = [seed]
        while pending:
            node = pending.pop()
            if node in component:
                continue
            component.add(node)
            pending.extend(sorted(neighbors[node] - component, reverse=True))
        unseen.difference_update(component)
        components.append(_topological(component, pairs))
    if any(source not in by_id or target not in by_id for source, target in pairs):
        raise InputError("PACK_SIGNAL_ENDPOINT_MISSING")
    return tuple(sorted(components, key=lambda component: component[0]))


def _reference_escape_directions(fragment: FragmentVariant) -> set[str]:
    roles = {port.port.id: port.port.role for port in fragment.ports}
    return {
        gateway.escape_direction
        for gateway in fragment.gateways
        if roles.get(gateway.id) == "reference"
    }


def _fanout_column_groups(
    chosen: dict[str, FragmentVariant], column: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Order one fanout column so reference-free stages sit away from the rail.

    Sibling stages of one rank share a column. When the column's references
    all escape downward, a sibling without a reference is stacked above the
    siblings that own one; otherwise a downward reference rail would have to
    cross the reference-free sibling's signal row. The mirrored case keeps the
    reference-free sibling below. Columns with uniform reference ownership
    keep their deterministic declaration order.
    """
    free = tuple(
        fragment_id
        for fragment_id in column
        if not _reference_escape_directions(chosen[fragment_id])
    )
    bound = tuple(fragment_id for fragment_id in column if fragment_id not in free)
    if len(column) < 2 or not free or not bound:
        return (), column
    directions = set()
    for fragment_id in bound:
        directions |= _reference_escape_directions(chosen[fragment_id])
    if directions == {"down"}:
        return free, bound
    if directions == {"up"}:
        return (), (*bound, *free)
    return (), column


def _make_units(
    plan: SemanticPlan,
    chosen: dict[str, FragmentVariant],
    *,
    attach_branches: bool,
    branches_beside: bool,
    stack_interfaces: bool,
) -> list[_Unit]:
    chains = _signal_chains(plan)
    assigned = {fragment_id for chain in chains for fragment_id in chain}
    attachments: dict[str, list[str]] = {}
    attached: set[str] = set()
    if attach_branches:
        for edge in sorted(plan.edges, key=lambda item: (item.source, item.target, item.net)):
            if (
                edge.kind != "branch"
                or edge.source not in assigned
                or edge.target in assigned
                or edge.target in attached
            ):
                continue
            attachments.setdefault(edge.source, []).append(edge.target)
            attached.add(edge.target)
    package_sources: dict[str, set[str]] = {}
    if attach_branches:
        for edge in plan.edges:
            if edge.kind == "package" and edge.source in assigned:
                package_sources.setdefault(edge.target, set()).add(edge.source)

    units: list[_Unit] = []
    for chain in chains:
        offsets: list[tuple[str, int, int]] = []
        chain_set = set(chain)
        predecessors = {
            node: {
                edge.source
                for edge in plan.edges
                if edge.kind in {"signal", "branch"}
                and edge.target == node
                and edge.source in chain_set
            }
            for node in chain
        }
        rank: dict[str, int] = {}
        for node in chain:
            rank[node] = max((rank[parent] + 1 for parent in predecessors[node]), default=0)
        by_rank: dict[int, list[str]] = {}
        for node in chain:
            by_rank.setdefault(rank[node], []).append(node)
        rank_columns = {
            value: (
                (
                    tuple(sorted(nodes[: (len(nodes) + 1) // 2])),
                    tuple(sorted(nodes[(len(nodes) + 1) // 2 :])),
                )
                if len(nodes) >= 3
                else (tuple(sorted(nodes)),)
            )
            for value, nodes in by_rank.items()
        }
        rank_widths = {
            value: sum(
                max(chosen[node].envelope[2] - chosen[node].envelope[0] for node in column)
                for column in columns
            )
            + CHANNEL_GAP * (len(columns) - 1)
            for value, columns in rank_columns.items()
        }
        rank_x = {}
        x = 0
        for value in sorted(by_rank):
            rank_x[value] = x
            next_rank = value + 1
            branch_only_next = next_rank in by_rank and all(
                edge.kind == "branch"
                for edge in plan.edges
                if edge.target in by_rank[next_rank] and edge.source in chain_set
            )
            x += rank_widths[value] + (0 if branch_only_next else CHANNEL_GAP)
        if x:
            x -= CHANNEL_GAP
        main_height = 0
        source_x: dict[str, int] = {}
        source_width: dict[str, int] = {}
        column_groups = {
            column: _fanout_column_groups(chosen, column)
            for columns in rank_columns.values()
            for column in columns
        }

        def stack_height(nodes: tuple[str, ...]) -> int:
            return sum(
                chosen[node].envelope[3] - chosen[node].envelope[1] for node in nodes
            ) + CHANNEL_GAP * max(0, len(nodes) - 1)

        upper_band = max((stack_height(upper) for upper, _ in column_groups.values()), default=0)
        band_top = upper_band + CHANNEL_GAP if upper_band else 0
        for value, columns in sorted(rank_columns.items()):
            column_x = rank_x[value]
            for column in columns:
                upper, lower = column_groups[column]
                y = band_top - (stack_height(upper) + CHANNEL_GAP if upper else 0)
                column_width = 0
                for fragment_id in (*upper, *lower):
                    fragment = chosen[fragment_id]
                    width = fragment.envelope[2] - fragment.envelope[0]
                    height = fragment.envelope[3] - fragment.envelope[1]
                    offsets.append((fragment_id, column_x, y))
                    source_x[fragment_id] = column_x
                    source_width[fragment_id] = width
                    column_width = max(column_width, width)
                    y += height + CHANNEL_GAP
                if y:
                    y -= CHANNEL_GAP
                main_height = max(main_height, y)
                column_x += column_width + CHANNEL_GAP
        width, height = x, main_height
        # A physical package support unit belongs near its owned functional
        # units, but it is not a serial signal stage.  Backfill a genuinely
        # measured empty rank band when it fits; otherwise leave it for the
        # independent shelf placer.
        for target, related in sorted(package_sources.items()):
            if target in attached or not (related & chain_set):
                continue
            fragment = chosen[target]
            target_width = fragment.envelope[2] - fragment.envelope[0]
            target_height = fragment.envelope[3] - fragment.envelope[1]
            candidates = []
            for source in sorted(related & chain_set):
                source_fragment = chosen[source]
                source_height = source_fragment.envelope[3] - source_fragment.envelope[1]
                source_rank = rank[source]
                # Measured reservation envelopes may share a boundary; their
                # occupied interiors remain disjoint and no routing channel is
                # required between a functional unit and its own package cell.
                source_y = next(dy for owner, _, dy in offsets if owner == source)
                local_x = rank_x[source_rank]
                local_y = max(
                    source_y + source_height,
                    *(
                        dy + chosen[owner].envelope[3] - chosen[owner].envelope[1]
                        for owner, dx, dy in offsets
                        if max(local_x, dx)
                        < min(
                            local_x + target_width,
                            dx + chosen[owner].envelope[2] - chosen[owner].envelope[0],
                        )
                    ),
                )
                # Reserve one pitch for independently snapped envelope origins.
                local_y = ((local_y + PITCH - 1) // PITCH + 1) * PITCH
                candidate_box = (local_x, local_y, local_x + target_width, local_y + target_height)
                if any(
                    max(candidate_box[0], dx)
                    < min(
                        candidate_box[2], dx + chosen[owner].envelope[2] - chosen[owner].envelope[0]
                    )
                    and max(candidate_box[1], dy)
                    < min(
                        candidate_box[3], dy + chosen[owner].envelope[3] - chosen[owner].envelope[1]
                    )
                    for owner, dx, dy in offsets
                ):
                    continue
                if target_width <= rank_widths[source_rank]:
                    candidates.append(
                        (
                            max(0, local_y + target_height - main_height),
                            rank_x[source_rank],
                            source,
                            local_y,
                        )
                    )
            if candidates:
                _, local_x, _, local_y = min(candidates)
                offsets.append((target, local_x, local_y))
                height = max(height, local_y + target_height)
                attached.add(target)
        if branches_beside and len(attachments.get(chain[-1], ())) > 1:
            side_height = sum(
                chosen[target].envelope[3] - chosen[target].envelope[1]
                for target in attachments[chain[-1]]
            ) + CHANNEL_GAP * (len(attachments[chain[-1]]) - 1)
            if side_height > height:
                shift = (side_height - height) // 2
                offsets = [(fragment_id, dx, dy + shift) for fragment_id, dx, dy in offsets]
                height = side_height
        for source in chain:
            branch_y = height
            branch_band_right = 0
            side_x = width
            side_y = 0
            for target in attachments.get(source, []):
                fragment = chosen[target]
                target_width = fragment.envelope[2] - fragment.envelope[0]
                target_height = fragment.envelope[3] - fragment.envelope[1]
                if branches_beside and source == chain[-1]:
                    offsets.append((target, side_x, side_y))
                    width = max(width, side_x + target_width)
                    side_y += target_height + CHANNEL_GAP
                    height = max(height, side_y - CHANNEL_GAP)
                else:
                    branch_edge = next(
                        edge
                        for edge in plan.edges
                        if edge.kind == "branch" and edge.source == source and edge.target == target
                    )
                    source_roles = {port.port.id: port.port.role for port in chosen[source].ports}
                    target_roles = {port.port.id: port.port.role for port in chosen[target].ports}
                    source_gateway = next(
                        (
                            gateway
                            for gateway in chosen[source].gateways
                            if gateway.net == branch_edge.net
                            and source_roles[gateway.id] in {"signal_out", "power_out"}
                        ),
                        None,
                    )
                    target_gateway = next(
                        (
                            gateway
                            for gateway in chosen[target].gateways
                            if gateway.net == branch_edge.net
                            and target_roles[gateway.id] in {"signal_in", "power_in"}
                        ),
                        None,
                    )
                    if source_gateway is None or target_gateway is None:
                        source_relative_x = source_width[source] // 2
                        target_relative_x = target_width // 2
                    else:
                        source_relative_x = source_gateway.point[0] - chosen[source].envelope[0]
                        target_relative_x = target_gateway.point[0] - chosen[target].envelope[0]
                    # A shared reference is a distribution demand, never a
                    # replacement for the branch's signal entrance/exit
                    # inequality. Keep the signal gateways as the alignment
                    # anchors; reference routing is handled separately.
                    local_x = max(
                        0,
                        source_x[source] + source_relative_x - target_relative_x,
                    )
                    # Incomparable fanout children share one lower band.  They are
                    # independent branches, not additional serial signal stages.
                    # Keep their preferred source alignment when possible and
                    # deterministically slide later siblings right on collision.
                    local_x = max(local_x, branch_band_right)
                    offsets.append((target, local_x, branch_y))
                    width = max(width, local_x + target_width)
                    branch_band_right = local_x + target_width + CHANNEL_GAP
                    height = max(height, branch_y + target_height)
        ids = tuple(fragment_id for fragment_id, _, _ in offsets)
        units.append(
            _Unit(
                ids,
                tuple(offsets),
                width,
                height,
                len(by_rank) > 1,
                parallel_fanout=any(len(nodes) > 1 for nodes in by_rank.values()),
            )
        )

    remaining = set(chosen) - assigned - attached
    interface_ids = sorted(
        fragment_id for fragment_id in remaining if chosen[fragment_id].block.kind == "interface"
    )
    if stack_interfaces and interface_ids:
        offsets = []
        y = width = 0
        for fragment_id in interface_ids:
            fragment = chosen[fragment_id]
            fragment_width = fragment.envelope[2] - fragment.envelope[0]
            fragment_height = fragment.envelope[3] - fragment.envelope[1]
            offsets.append((fragment_id, 0, y))
            width = max(width, fragment_width)
            y += fragment_height
        units.append(_Unit(tuple(interface_ids), tuple(offsets), width, y, False))
        remaining.difference_update(interface_ids)

    for fragment_id in sorted(remaining):
        fragment = chosen[fragment_id]
        affinity_source = (
            max(package_sources.get(fragment_id, ())) if package_sources.get(fragment_id) else None
        )
        units.append(
            _Unit(
                (fragment_id,),
                ((fragment_id, 0, 0),),
                fragment.envelope[2] - fragment.envelope[0],
                fragment.envelope[3] - fragment.envelope[1],
                False,
                affinity_source=affinity_source,
            )
        )
    return _group_parallel_branch_columns(
        plan,
        _group_power_fanout(plan, units),
        chosen,
    )


def _group_power_fanout(plan: SemanticPlan, units: list[_Unit]) -> list[_Unit]:
    grouped_units: set[int] = set()
    fanout_units: list[_Unit] = []
    power_sources = sorted({edge.source for edge in plan.edges if edge.kind == "power"})
    for source in power_sources:
        targets = sorted(
            edge.target for edge in plan.edges if edge.kind == "power" and edge.source == source
        )
        matches = [
            (index, unit)
            for index, unit in enumerate(units)
            if not unit.serial and unit.offsets[0][0] in targets
        ]
        if len(matches) < 2 or any(index in grouped_units for index, _ in matches):
            continue
        offsets: list[tuple[str, int, int]] = []
        ids: list[str] = []
        x = height = 0
        for index, unit in sorted(matches, key=lambda item: item[1].offsets[0][0]):
            grouped_units.add(index)
            ids.extend(unit.ids)
            offsets.extend((fragment_id, dx + x, dy) for fragment_id, dx, dy in unit.offsets)
            x += unit.width + CHANNEL_GAP
            height = max(height, unit.height)
        fanout_units.append(
            _Unit(
                tuple(ids),
                tuple(offsets),
                x,
                height,
                False,
                parallel_fanout=True,
                affinity_source=source,
            )
        )
    result = [unit for index, unit in enumerate(units) if index not in grouped_units]
    result.extend(fanout_units)
    return result


def _group_parallel_branch_columns(
    plan: SemanticPlan,
    units: list[_Unit],
    chosen: dict[str, FragmentVariant],
) -> list[_Unit]:
    """Interleave empty bands of incomparable source/branch columns."""
    branch_pairs = {(edge.source, edge.target) for edge in plan.edges if edge.kind == "branch"}
    matches = [
        (index, unit)
        for index, unit in enumerate(units)
        if not unit.serial
        and any(source in unit.ids and target in unit.ids for source, target in branch_pairs)
        and any(dy > 0 for _, _, dy in unit.offsets)
    ]
    if len(matches) < 2:
        return units
    offsets: list[tuple[str, int, int]] = []
    ids: list[str] = []
    x = width = height = 0
    grouped = {index for index, _ in matches}
    for _, unit in sorted(matches, key=lambda item: item[1].ids[0]):
        source = next(
            source
            for source, target in sorted(branch_pairs)
            if source in unit.ids and target in unit.ids
        )
        source_dx = next(dx for fragment_id, dx, _ in unit.offsets if fragment_id == source)
        shift = x - source_dx
        for fragment_id, dx, dy in unit.offsets:
            translated_x = dx + shift
            offsets.append((fragment_id, translated_x, dy))
            fragment = chosen[fragment_id]
            width = max(width, translated_x + fragment.envelope[2] - fragment.envelope[0])
            height = max(height, dy + fragment.envelope[3] - fragment.envelope[1])
            ids.append(fragment_id)
        source_fragment = chosen[source]
        x += source_fragment.envelope[2] - source_fragment.envelope[0] + CHANNEL_GAP
    result = [unit for index, unit in enumerate(units) if index not in grouped]
    result.append(
        _Unit(
            tuple(ids),
            tuple(offsets),
            width,
            height,
            False,
            parallel_fanout=True,
        )
    )
    return result


def _typed_unit_order(plan: SemanticPlan, units: list[_Unit]) -> list[_Unit]:
    """Order shelf items by typed roles without inventing stage progression."""
    by_id = {block.id: block for block in plan.blocks}
    power_sources = {edge.source for edge in plan.edges if edge.kind == "power"}
    power_consumers = {edge.target for edge in plan.edges if edge.kind == "power"}
    branch_sources = {edge.source for edge in plan.edges if edge.kind == "branch"}
    branch_targets = {edge.target for edge in plan.edges if edge.kind == "branch"}
    signal_interfaces = {
        edge.source_fragment
        for edge in plan.precedence
        if by_id[edge.source_fragment].kind == "interface"
    }

    def category(unit: _Unit) -> tuple[int, str]:
        kinds = {by_id[item].kind for item in unit.ids}
        if set(unit.ids) & signal_interfaces:
            rank = -1
        elif unit.serial:
            rank = 0
        elif set(unit.ids) & (power_sources | branch_sources):
            rank = 1
        elif set(unit.ids) & power_consumers:
            rank = 2
        elif kinds <= {"interface"}:
            rank = 3
        elif kinds <= {"package_power"}:
            rank = 4
        elif set(unit.ids) & branch_targets:
            rank = 5
        else:
            rank = 6
        return rank, unit.ids[0]

    return sorted(units, key=category)
