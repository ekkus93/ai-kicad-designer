"""Deterministic measured-envelope packing for M2 fragments."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .ir import InputError
from .m2a import PITCH
from .m2_fragments import FragmentVariant, Point, PortAnchor, Rect
from .m2_geometry import ConductorSegment, Gateway, Reservation, canonical_conductor_tree
from .m2_semantics import PlacementConflict, SemanticPlan, check_placement_constraints


LEFT = 18 * PITCH
TOP = 23 * PITCH
RIGHT = 215 * PITCH
BOTTOM = 144 * PITCH
MAX_CONTENT_WIDTH = 210_000_000
MAX_CONTENT_HEIGHT = 140_000_000
ENVELOPE_OUTER_PADDING = 4 * PITCH
CANDIDATE_BUDGET = 8
PLACEMENT_LEFT = LEFT + 2 * PITCH
CHANNEL_GAP = PITCH
MAX_PACKING_WIDTH = RIGHT - LEFT
MAX_PACKING_HEIGHT = BOTTOM - TOP


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
        for value, columns in sorted(rank_columns.items()):
            column_x = rank_x[value]
            for column in columns:
                y = 0
                column_width = 0
                for fragment_id in column:
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
                local_y = source_y + source_height
                local_x = rank_x[source_rank]
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
            sorted(package_sources.get(fragment_id, ()))[-1]
            if package_sources.get(fragment_id)
            else None
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


def _arrangements(
    plan: SemanticPlan, chosen: dict[str, FragmentVariant]
) -> tuple[tuple[str, list[_Unit]], ...]:
    affinity = _make_units(
        plan,
        chosen,
        attach_branches=True,
        branches_beside=True,
        stack_interfaces=True,
    )
    open_interfaces = _make_units(
        plan,
        chosen,
        attach_branches=True,
        branches_beside=True,
        stack_interfaces=False,
    )
    flat = _make_units(
        plan,
        chosen,
        attach_branches=False,
        branches_beside=False,
        stack_interfaces=False,
    )
    return (
        ("side-affinity", _typed_unit_order(plan, affinity)),
        ("open-interface-band", _typed_unit_order(plan, open_interfaces)),
        ("typed", _typed_unit_order(plan, flat)),
        ("height", sorted(flat, key=lambda unit: (-unit.height, -unit.width, unit.ids))),
    )


def _pack_shelves(
    ordered: list[_Unit], chosen: dict[str, FragmentVariant]
) -> tuple[list[PlacedFragment], int, int]:
    placed: list[PlacedFragment] = []
    used_width = 0
    serial_shelves = 0
    unit_positions: dict[str, tuple[int, int]] = {}
    unit_shelves: dict[str, int] = {}
    shelves: list[dict[str, int]] = []
    for unit in ordered:
        if unit.width > MAX_PACKING_WIDTH or unit.height > MAX_PACKING_HEIGHT:
            raise ValueError(
                f"unit-spread-overflow:{','.join(unit.ids)}:{unit.width}x{unit.height}"
            )
        shelf_index = None
        affinity_shelf = unit_shelves.get(unit.affinity_source or "")
        if affinity_shelf is not None:
            shelf = shelves[affinity_shelf]
            if unit.height <= shelf["height"] and shelf["used"] + unit.width <= MAX_CONTENT_WIDTH:
                shelf_index = affinity_shelf
        if not (unit.serial and serial_shelves):
            for index, shelf in enumerate(shelves[:-1]):
                if shelf_index is not None:
                    break
                if (
                    unit.height <= shelf["height"]
                    and shelf["used"] + unit.width <= MAX_CONTENT_WIDTH
                ):
                    shelf_index = index
                    break
            if shelf_index is None and shelves:
                current = shelves[-1]
                if current["used"] + unit.width <= MAX_CONTENT_WIDTH:
                    shelf_index = len(shelves) - 1
        if shelf_index is None:
            shelf_y = 0 if not shelves else shelves[-1]["y"] + shelves[-1]["height"] + CHANNEL_GAP
            placement_x = 0
            if unit.affinity_source in unit_positions:
                source_x, source_width = unit_positions[unit.affinity_source]
                placement_x = max(
                    0,
                    min(
                        MAX_CONTENT_WIDTH - unit.width,
                        source_x + (source_width - unit.width) // 2,
                    ),
                )
            shelves.append(
                {
                    "y": shelf_y,
                    "height": unit.height,
                    "used": placement_x + unit.width + CHANNEL_GAP,
                }
            )
            shelf_index = len(shelves) - 1
        else:
            shelf = shelves[shelf_index]
            placement_x = shelf["used"]
            shelf["used"] += unit.width + CHANNEL_GAP
            if shelf_index == len(shelves) - 1:
                shelf["height"] = max(shelf["height"], unit.height)
        placement_y = shelves[shelf_index]["y"]
        if placement_y + unit.height > MAX_PACKING_HEIGHT:
            raise ValueError(
                f"content-spread-overflow:{','.join(unit.ids)}:"
                f"required-height={placement_y + unit.height}:limit={MAX_CONTENT_HEIGHT}"
            )
        for fragment_id, dx, dy in unit.offsets:
            placed.append(
                _place(
                    chosen[fragment_id],
                    PLACEMENT_LEFT + placement_x + dx,
                    TOP + placement_y + dy,
                )
            )
            unit_positions[fragment_id] = (placement_x + dx, unit.width)
            unit_shelves[fragment_id] = shelf_index
        used_width = max(used_width, placement_x + unit.width)
        serial_shelves += unit.serial
    used_height = max(shelf["y"] + shelf["height"] for shelf in shelves)
    content_rectangles = [
        tuple(
            value + shift
            for value, shift in zip(
                item.fragment.content_envelope or item.fragment.envelope,
                (*item.delta, *item.delta),
                strict=True,
            )
        )
        for item in placed
    ]
    actual_width = max(item.envelope[2] for item in placed) - min(
        item.envelope[0] for item in placed
    )
    actual_height = max(item.envelope[3] for item in placed) - min(
        item.envelope[1] for item in placed
    )
    content_width_bound = max(rect[2] for rect in content_rectangles) - min(
        rect[0] for rect in content_rectangles
    )
    content_height_bound = max(rect[3] for rect in content_rectangles) - min(
        rect[1] for rect in content_rectangles
    )
    if content_width_bound > MAX_CONTENT_WIDTH or content_height_bound > MAX_CONTENT_HEIGHT:
        raise ValueError(
            f"placed-envelope-spread-overflow:{actual_width}x{actual_height}:"
            f"content-bound={content_width_bound}x{content_height_bound}:"
            f"limit={MAX_CONTENT_WIDTH}x{MAX_CONTENT_HEIGHT}"
        )
    if (
        min(item.envelope[0] for item in placed) < LEFT
        or max(item.envelope[2] for item in placed) > RIGHT
        or min(item.envelope[1] for item in placed) < TOP
        or max(item.envelope[3] for item in placed) > BOTTOM
    ):
        raise ValueError(f"page-overflow:{used_width}x{used_height}")
    return placed, content_width_bound, content_height_bound


def _distribution_column_candidate(
    plan: SemanticPlan,
    variants: dict[str, tuple[FragmentVariant, ...]],
    packings: list[Packing],
) -> Packing | None:
    """Build a compact vertical tree band from measured producer/consumer cells.

    This is an alternative complete seed.  All coordinates come from measured
    envelopes and the presentation net inventory; its routes still undergo the
    ordinary placement, conductor, reservation and observer proofs.
    """
    producers = {
        net.id: tuple(
            sorted(
                set(net.producer_fragments)
                | {
                    port.fragment
                    for block in plan.blocks
                    for port in block.ports
                    if port.net == net.id and port.role == "power_out"
                }
            )
        )
        for net in plan.presentation_nets
    }
    demands = sorted(
        (
            net
            for net in plan.presentation_nets
            if net.role == "distributive"
            and net.internally_generated
            and len(producers[net.id]) == 1
            and len(net.fragments) >= 3
        ),
        key=lambda net: (-len(net.fragments), net.id),
    )
    if not demands or not packings:
        return None
    net = demands[0]
    producer_id = producers[net.id][0]
    consumers = tuple(fragment_id for fragment_id in net.fragments if fragment_id != producer_id)
    if len(consumers) < 2:
        return None

    def local_length(choice: FragmentVariant) -> int:
        segments = (
            ConductorSegment(first, second, net.id, choice.block.id)
            for (first, second), wire_net in zip(choice.wires, choice.wire_nets, strict=True)
            if wire_net == net.id
        )
        return canonical_conductor_tree(segments).length

    def approach(choice: FragmentVariant) -> tuple[str, ...]:
        return tuple(
            gateway.escape_direction for gateway in choice.gateways if gateway.net == net.id
        )

    def area(choice: FragmentVariant) -> int:
        return (choice.envelope[2] - choice.envelope[0]) * (choice.envelope[3] - choice.envelope[1])

    # Divide consumers by measured width.  Narrow consumers share a trunk
    # column; the remaining wider cells occupy the adjacent band.  This is a
    # structural placement class for arbitrary consumer counts.
    baseline = min(
        packings,
        key=lambda packing: (
            sum(
                local_length(item.fragment)
                for item in packing.fragments
                if item.fragment.block.id in net.fragments
            ),
            tuple(item.fragment.id for item in packing.fragments),
        ),
    )
    base = {item.fragment.block.id: item for item in baseline.fragments}
    if any(fragment_id not in base for fragment_id in net.fragments):
        return None
    ranked_consumers = sorted(
        consumers,
        key=lambda fragment_id: (
            base[fragment_id].envelope[2] - base[fragment_id].envelope[0],
            fragment_id,
        ),
    )
    narrow = ranked_consumers[: max(1, (len(consumers) + 1) // 2)]
    side = ranked_consumers[len(narrow) :]
    wide = side[-1]
    side_remainder = side[:-1]
    chosen = {key: item.fragment for key, item in base.items()}
    for fragment_id in (producer_id, *side_remainder):
        left_facing = [choice for choice in variants[fragment_id] if "left" in approach(choice)]
        if not left_facing:
            return None
        chosen[fragment_id] = min(
            left_facing,
            key=lambda choice: (
                local_length(choice),
                area(choice) if fragment_id != producer_id else 0,
                choice.id,
            ),
        )
    wide_choices = [choice for choice in variants[wide] if "left" in approach(choice)]
    if not wide_choices:
        wide_choices = [choice for choice in variants[wide] if "right" in approach(choice)]
    if not wide_choices:
        return None
    chosen[wide] = min(
        wide_choices,
        key=lambda choice: (
            choice.envelope[3] - choice.envelope[1],
            choice.id,
        ),
    )
    for fragment_id in narrow:
        chosen[fragment_id] = min(
            variants[fragment_id], key=lambda choice: (local_length(choice), choice.id)
        )

    unrelated = [
        item
        for item in baseline.fragments
        if item.fragment.block.id not in net.fragments and item.fragment.block.kind != "interface"
    ]
    anchor = (
        max(
            unrelated,
            key=lambda item: (
                (item.envelope[2] - item.envelope[0]) * (item.envelope[3] - item.envelope[1]),
                item.fragment.block.id,
            ),
        )
        if unrelated
        else None
    )
    interfaces = [item for item in baseline.fragments if item.fragment.block.kind == "interface"]
    placed = dict(base)
    placed[wide] = _place(
        chosen[wide],
        (anchor.envelope[2] + PITCH if anchor else LEFT + PITCH),
        (anchor.envelope[1] + PITCH if anchor else TOP + PITCH),
    )
    placed[producer_id] = _place(
        chosen[producer_id],
        placed[wide].envelope[2] + PITCH,
        max((item.envelope[3] for item in interfaces), default=TOP + PITCH),
    )
    # The consumer whose physical package also owns the wide function is the
    # first local tap below the producer.  This is a package affinity, not an
    # assumption about component names or the reference net spelling.
    wide_occurrences = {occurrence[0] for occurrence in chosen[wide].block.occurrences}
    ordered_narrow = sorted(
        narrow,
        key=lambda fragment_id: (
            not bool(
                wide_occurrences
                & {occurrence[0] for occurrence in chosen[fragment_id].block.occurrences}
            ),
            fragment_id,
        ),
    )
    prior = placed[producer_id]
    for fragment_id in ordered_narrow:
        placed[fragment_id] = _place(
            chosen[fragment_id],
            placed[producer_id].envelope[0],
            prior.envelope[3] + (PITCH if prior is placed[producer_id] else 0),
        )
        prior = placed[fragment_id]
    side_y = placed[wide].envelope[3] + PITCH
    for fragment_id in side_remainder:
        width = chosen[fragment_id].envelope[2] - chosen[fragment_id].envelope[0]
        placed[fragment_id] = _place(
            chosen[fragment_id],
            placed[producer_id].envelope[0] - width - PITCH,
            side_y,
        )
        side_y = placed[fragment_id].envelope[3] + PITCH
    if not net.explicit_geometry_required:
        # A generated power rail needs a compact producer beside a complete
        # consumer column, rather than below a pre-existing interface shelf.
        # Retain the independent envelope and terminal proofs below.
        chosen[producer_id] = min(
            variants[producer_id],
            key=lambda choice: (
                "up" not in approach(choice),
                local_length(choice),
                area(choice),
                choice.id,
            ),
        )
        column_y = TOP
        column_right = LEFT
        for fragment_id in consumers:
            chosen[fragment_id] = min(
                variants[fragment_id],
                key=lambda choice: (
                    "up" not in approach(choice),
                    area(choice),
                    local_length(choice),
                    choice.id,
                ),
            )
            placed[fragment_id] = _place(chosen[fragment_id], PLACEMENT_LEFT, column_y)
            column_y = placed[fragment_id].envelope[3] + PITCH
            column_right = max(column_right, placed[fragment_id].envelope[2])
        placed[producer_id] = _place(chosen[producer_id], column_right + PITCH, TOP)
        unrelated_left = placed[producer_id].envelope[0]
        unrelated_x = unrelated_left
        unrelated_y = TOP
        for obligation in plan.precedence:
            if obligation.source_fragment in consumers and obligation.target_fragment in {
                item.fragment.block.id for item in unrelated
            }:
                source = next(
                    (
                        g
                        for g in placed[obligation.source_fragment].gateways
                        if g.net == obligation.net
                    ),
                    None,
                )
                target = next(
                    (
                        g
                        for g in chosen[obligation.target_fragment].gateways
                        if g.net == obligation.net
                    ),
                    None,
                )
                if source is not None and target is not None:
                    unrelated_y = max(
                        TOP,
                        source.point[1]
                        - (target.point[1] - chosen[obligation.target_fragment].envelope[1]),
                    )
                    break
        row_bottom = unrelated_y
        unrelated_width = (
            sum(
                sorted((item.envelope[2] - item.envelope[0] for item in unrelated), reverse=True)[
                    :2
                ]
            )
            + PITCH
        )
        order = {fragment_id: index for index, fragment_id in enumerate(plan.signal_order)}
        for item in sorted(
            unrelated,
            key=lambda item: (
                order.get(item.fragment.block.id, len(order)),
                item.fragment.block.id,
            ),
        ):
            fragment_id = item.fragment.block.id
            width = chosen[fragment_id].envelope[2] - chosen[fragment_id].envelope[0]
            if unrelated_x + width > unrelated_left + unrelated_width:
                unrelated_x = unrelated_left
                unrelated_y = row_bottom + PITCH
            placed[fragment_id] = _place(chosen[fragment_id], unrelated_x, unrelated_y)
            unrelated_x = placed[fragment_id].envelope[2] + PITCH
            row_bottom = max(row_bottom, placed[fragment_id].envelope[3])
        placed[producer_id] = _place(chosen[producer_id], unrelated_left, row_bottom + PITCH)
        interface_x = (
            max(
                item.envelope[2]
                for item in placed.values()
                if item.fragment.block.kind != "interface"
            )
            + PITCH
        )
        interface_y = TOP
        for item in interfaces:
            fragment_id = item.fragment.block.id
            placed[fragment_id] = _place(chosen[fragment_id], interface_x, interface_y)
            interface_y = placed[fragment_id].envelope[3] + PITCH
    items = tuple(sorted(placed.values(), key=lambda item: item.fragment.block.id))
    if any(
        item.envelope[0] < LEFT
        or item.envelope[1] < TOP
        or item.envelope[2] > RIGHT
        or item.envelope[3] > BOTTOM
        for item in items
    ):
        return None
    if (
        max(item.content_envelope[2] for item in items)
        - min(item.content_envelope[0] for item in items)
        > MAX_CONTENT_WIDTH
        or max(item.content_envelope[3] for item in items)
        - min(item.content_envelope[1] for item in items)
        > MAX_CONTENT_HEIGHT
    ):
        return None
    if any(
        max(first.envelope[0], second.envelope[0]) < min(first.envelope[2], second.envelope[2])
        and max(first.envelope[1], second.envelope[1]) < min(first.envelope[3], second.envelope[3])
        for index, first in enumerate(items)
        for second in items[index + 1 :]
    ):
        return None
    return Packing(items, baseline.attempts + (f"distribution-column:{net.id}",))


def _measured_repack(
    plan: SemanticPlan,
    baseline: Packing,
    target: PlacedFragment,
    left: int,
    top: int,
    label: str,
    displaced: PlacedFragment | None = None,
    additional_moves: tuple[tuple[PlacedFragment, int, int], ...] = (),
) -> Packing | None:
    """Certify a changed measured placement before spending a route attempt."""
    moved = _place(target.fragment, left, top)
    if moved.delta == target.delta:
        return None
    replacement = (
        _place(displaced.fragment, target.envelope[0], target.envelope[1])
        if displaced is not None
        else None
    )
    replacements = {
        item.fragment.block.id: _place(item.fragment, x, y) for item, x, y in additional_moves
    }
    if displaced is not None:
        replacements[displaced.fragment.block.id] = replacement
    replacements[target.fragment.block.id] = moved
    items = tuple(replacements.get(item.fragment.block.id, item) for item in baseline.fragments)
    if any(
        item.envelope[0] < LEFT
        or item.envelope[1] < TOP
        or item.envelope[2] > RIGHT
        or item.envelope[3] > BOTTOM
        for item in items
    ):
        return None
    if (
        max(item.content_envelope[2] for item in items)
        - min(item.content_envelope[0] for item in items)
        > MAX_CONTENT_WIDTH
        or max(item.content_envelope[3] for item in items)
        - min(item.content_envelope[1] for item in items)
        > MAX_CONTENT_HEIGHT
    ):
        return None
    if any(
        max(first.envelope[0], second.envelope[0]) < min(first.envelope[2], second.envelope[2])
        and max(first.envelope[1], second.envelope[1]) < min(first.envelope[3], second.envelope[3])
        for index, first in enumerate(items)
        for second in items[index + 1 :]
    ):
        return None
    placed = {item.fragment.block.id: item for item in items}
    terminal = {item.terminal: item for item in plan.terminals}

    def point(component: str, pin: str) -> Point:
        obligation = terminal[(component, pin)]
        item = placed[obligation.owner]
        origin = item.fragment.positions[obligation.occurrence]
        angle = item.fragment.angles.get(obligation.occurrence, 0)
        x, y = obligation.pin_x, -obligation.pin_y
        dx, dy = {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[angle]
        return origin[0] + item.delta[0] + dx, origin[1] + item.delta[1] + dy

    try:
        check_placement_constraints(plan, point)
    except PlacementConflict:
        return None
    return Packing(
        tuple(sorted(items, key=lambda item: item.fragment.block.id)), baseline.attempts + (label,)
    )


def _structural_repack_candidates(plan: SemanticPlan, baseline: Packing) -> tuple[Packing, ...]:
    """Try functional row compaction and precedence-bound band staggering."""
    items = baseline.fragments
    by_id = {item.fragment.block.id: item for item in items}
    proposals = []
    functional = [item for item in items if item.fragment.block.function is not None]
    for target in functional:
        if target.fragment.block.unused:
            continue
        for row_top in sorted({item.envelope[1] for item in functional}):
            row = [item for item in items if item is not target and item.envelope[1] == row_top]
            if row:
                # A boundary interface or support cell need not force the
                # whole functional row past its rightmost endpoint. Enumerate
                # measured gaps and keep only complete legal transactions.
                origins = (
                    {LEFT + PITCH, target.envelope[0]}
                    | {item.envelope[2] + PITCH for item in row}
                    | {item.envelope[0] for item in row if item.fragment.block.unused}
                )
                for left in sorted(origins):
                    if row_top == target.envelope[1] and left >= target.envelope[0]:
                        continue
                    candidate = _measured_repack(
                        plan, baseline, target, left, row_top, "functional-row-compaction"
                    )
                    if candidate is not None:
                        proposals.append(candidate)
                    else:
                        # A parked function can occupy the only measured row
                        # gap. Exchange it into the vacated cell as one atomic
                        # transaction, then recheck every placement obligation.
                        for parked in row:
                            if not parked.fragment.block.unused or parked.envelope[0] != left:
                                continue
                            exchanged = _measured_repack(
                                plan,
                                baseline,
                                target,
                                left,
                                row_top,
                                "functional-row-compaction",
                                displaced=parked,
                            )
                            if exchanged is not None:
                                proposals.append(exchanged)
    # A row may contain several independently constrained active functions.
    # Compact the whole row transaction so an existing reversed sibling does
    # not make every single-fragment move fail before it can be repaired.
    active = sorted(
        (item for item in functional if not item.fragment.block.unused),
        key=lambda item: item.fragment.block.id,
    )
    for row_top in sorted({item.envelope[1] for item in active}):
        outside = [item for item in active if item.envelope[1] != row_top]
        parked = sorted(
            (
                item
                for item in functional
                if item.fragment.block.unused and item.envelope[1] == row_top
            ),
            key=lambda item: item.fragment.block.id,
        )
        if not outside or len(parked) > len(outside):
            continue
        moves = []
        left = LEFT + PITCH
        for item in active:
            moves.append((item, left, row_top))
            left += item.envelope[2] - item.envelope[0] + PITCH
        moves.extend(
            (item, vacant.envelope[0], vacant.envelope[1])
            for item, vacant in zip(parked, outside, strict=False)
        )
        target, x, y = next(move for move in moves if move[0] in outside)
        grouped = _measured_repack(
            plan,
            baseline,
            target,
            x,
            y,
            "functional-row-compaction",
            additional_moves=tuple(move for move in moves if move[0] is not target),
        )
        if grouped is not None:
            proposals.append(grouped)
    for obligation in plan.precedence:
        source = by_id.get(obligation.source_fragment)
        target = by_id.get(obligation.target_fragment)
        if source is None or target is None or source is target:
            continue
        target_height = target.envelope[3] - target.envelope[1]
        for numerator in (1, 2, 3):
            candidate = _measured_repack(
                plan,
                baseline,
                target,
                target.envelope[0],
                source.envelope[3] - numerator * target_height // 4,
                "precedence-staggered-band",
            )
            if candidate is not None:
                proposals.append(candidate)
    return tuple(proposals)


def _band_count(packing: Packing) -> int:
    tops = sorted(
        {item.envelope[1] for item in packing.fragments if item.fragment.block.kind != "interface"}
    )
    bands = []
    for top in tops:
        if not bands or top - bands[-1] > PITCH:
            bands.append(top)
    return len(bands)


def _partial_beam_candidates(
    plan: SemanticPlan,
    variants: dict[str, tuple[FragmentVariant, ...]],
) -> tuple[Packing, ...]:
    """Grow measured fragments through four bounded placement classes.

    This fallback keeps independent tall cores separable, so a successor and
    package cell may backfill beside either core instead of inheriting a rigid
    full-chain shelf rectangle.  Every retained partial state satisfies all
    obligations whose terminals have already been placed.
    """
    blocks = {block.id: block for block in plan.blocks}
    predecessors: dict[str, set[str]] = {key: set() for key in variants}
    for obligation in plan.precedence:
        # External interfaces use the reserved boundary column after core
        # placement. Their exact inequalities are checked when both endpoints
        # are assigned; they do not force a different core expansion schedule.
        if (
            obligation.source_fragment != obligation.target_fragment
            and blocks[obligation.source_fragment].kind != "interface"
        ):
            predecessors[obligation.target_fragment].add(obligation.source_fragment)
    priority = {
        "timer": 0,
        "power_stage": 0,
        "rc": 1,
        "series": 1,
        "led_branch": 1,
        "buffer": 2,
        "noninverting_amplifier": 2,
        "inverting_amplifier": 2,
        "sallen_key": 2,
        "package_power": 3,
        "reference_divider": 3,
        "unused_amplifier": 4,
        "interface": 5,
    }
    pending = set(variants)
    order = []
    while pending:
        ready = [key for key in pending if predecessors[key] <= set(order)]
        if not ready:
            return ()
        key = min(
            ready,
            key=lambda candidate: (
                priority.get(blocks[candidate].kind, 4),
                -max(
                    (choice.envelope[2] - choice.envelope[0])
                    * (choice.envelope[3] - choice.envelope[1])
                    for choice in variants[candidate]
                ),
                candidate,
            ),
        )
        order.append(key)
        pending.remove(key)

    terminal = {item.terminal: item for item in plan.terminals}

    def point(state: dict[str, PlacedFragment], key: tuple[str, str]) -> Point:
        item = terminal[key]
        placed = state[item.owner]
        origin = placed.fragment.positions[item.occurrence]
        angle = placed.fragment.angles.get(item.occurrence, 0)
        px, py = item.pin_x, -item.pin_y
        dx, dy = {
            0: (px, py),
            90: (py, -px),
            180: (-px, -py),
            270: (-py, px),
        }[angle]
        return origin[0] + placed.delta[0] + dx, origin[1] + placed.delta[1] + dy

    def partial_legal(state: dict[str, PlacedFragment]) -> bool:
        for obligation in plan.precedence:
            if {obligation.source_fragment, obligation.target_fragment} <= state.keys():
                first = point(state, obligation.source_terminal)
                second = point(state, obligation.target_terminal)
                if second[0] - first[0] < obligation.minimum_x_separation:
                    return False
        for obligation in plan.local_spans:
            owners = {terminal[obligation.first].owner, terminal[obligation.second].owner}
            if owners <= state.keys():
                first, second = point(state, obligation.first), point(state, obligation.second)
                span = abs(first[0] - second[0]) + (
                    abs(first[1] - second[1]) if obligation.metric == "manhattan" else 0
                )
                if span > obligation.maximum:
                    return False
        return True

    def fits(state: dict[str, PlacedFragment], item: PlacedFragment) -> bool:
        if (
            item.envelope[0] < LEFT
            or item.envelope[1] < TOP
            or item.envelope[2] > RIGHT
            or item.envelope[3] > BOTTOM
        ):
            return False
        if any(
            max(item.envelope[0], other.envelope[0]) < min(item.envelope[2], other.envelope[2])
            and max(item.envelope[1], other.envelope[1]) < min(item.envelope[3], other.envelope[3])
            for other in state.values()
        ):
            return False
        all_items = (*state.values(), item)
        if (
            max(value.content_envelope[2] for value in all_items)
            - min(value.content_envelope[0] for value in all_items)
            > MAX_CONTENT_WIDTH
            or max(value.content_envelope[3] for value in all_items)
            - min(value.content_envelope[1] for value in all_items)
            > MAX_CONTENT_HEIGHT
        ):
            return False
        return partial_legal({**state, item.fragment.block.id: item})

    def access_penalty(state: dict[str, PlacedFragment]) -> int:
        penalty = 0
        for obligation in plan.precedence:
            if not {obligation.source_fragment, obligation.target_fragment} <= state.keys():
                continue
            source = state[obligation.source_fragment]
            target = state[obligation.target_fragment]
            source_roles = {port.port.id: port.port.role for port in source.ports}
            target_roles = {port.port.id: port.port.role for port in target.ports}
            source_gateways = [
                gateway
                for gateway in source.gateways
                if gateway.net == obligation.net
                and source_roles[gateway.id] in {"signal_out", "power_out"}
            ]
            target_gateways = [
                gateway
                for gateway in target.gateways
                if gateway.net == obligation.net
                and target_roles[gateway.id] in {"signal_in", "power_in"}
            ]
            if not source_gateways or not target_gateways:
                continue
            first, second = source_gateways[0], target_gateways[0]
            if first.point[0] < second.point[0]:
                penalty += first.escape_direction == "left"
                penalty += second.escape_direction == "right"
            elif first.point[0] > second.point[0]:
                penalty += first.escape_direction == "right"
                penalty += second.escape_direction == "left"
        return penalty

    interface_width = max(
        (
            min(choice.envelope[2] - choice.envelope[0] for choice in variants[key])
            for key in variants
            if blocks[key].kind == "interface"
        ),
        default=0,
    )
    core_left = LEFT + interface_width + 2 * PITCH
    beam: list[tuple[dict[str, PlacedFragment], tuple[str, ...]]] = [({}, ())]
    for key in order:
        extensions = []
        choices = sorted(
            variants[key],
            key=lambda choice: (
                choice.envelope[3] - choice.envelope[1],
                (choice.envelope[2] - choice.envelope[0])
                * (choice.envelope[3] - choice.envelope[1]),
                choice.id,
            ),
        )[:8]
        for state, decisions in beam:
            related = [
                item
                for item in state.values()
                if {occurrence[0] for occurrence in item.fragment.block.occurrences}
                & {occurrence[0] for occurrence in blocks[key].occurrences}
            ]
            parents = [state[parent] for parent in sorted(predecessors[key]) if parent in state]
            for choice in choices:
                width = choice.envelope[2] - choice.envelope[0]
                height = choice.envelope[3] - choice.envelope[1]
                proposals: list[tuple[str, list[Point]]] = []
                proposals.append(
                    (
                        "aligned",
                        [(parent.envelope[2] + PITCH, parent.envelope[1]) for parent in parents],
                    )
                )
                noninterfaces = [
                    item for item in state.values() if item.fragment.block.kind != "interface"
                ]
                proposals.append(
                    (
                        "lower_band",
                        [
                            (
                                core_left if blocks[key].kind != "interface" else LEFT + PITCH,
                                max((item.envelope[3] for item in noninterfaces), default=TOP)
                                + PITCH,
                            ),
                            (core_left, TOP + 2 * PITCH),
                        ],
                    )
                )
                proposals.append(
                    (
                        "affinity",
                        [(item.envelope[0], item.envelope[3] + PITCH) for item in related]
                        + [
                            (item.envelope[0], item.envelope[1] - height - PITCH)
                            for item in related
                        ],
                    )
                )
                xs = {core_left, LEFT + PITCH} | {
                    coordinate
                    for item in state.values()
                    for coordinate in (item.envelope[0], item.envelope[2] + PITCH)
                }
                ys = {TOP + 2 * PITCH} | {
                    coordinate
                    for item in state.values()
                    for coordinate in (item.envelope[1], item.envelope[3] + PITCH)
                }
                proposals.append(
                    (
                        "backfill",
                        sorted(
                            ((x, y) for x in xs for y in ys),
                            key=lambda value: (
                                max(value[0] + width, value[1] + height),
                                value[1],
                                value[0],
                            ),
                        ),
                    )
                )
                for class_name, origins in proposals:
                    for left, top in origins:
                        item = _place(choice, left, top)
                        if fits(state, item):
                            extended = {**state, key: item}
                            new_decisions = (*decisions, f"{key}:{class_name}:{choice.id}")
                            box = (
                                max(part.content_envelope[2] for part in extended.values())
                                - min(part.content_envelope[0] for part in extended.values()),
                                max(part.content_envelope[3] for part in extended.values())
                                - min(part.content_envelope[1] for part in extended.values()),
                            )
                            score = (
                                access_penalty(extended),
                                max(box[0] / MAX_CONTENT_WIDTH, box[1] / MAX_CONTENT_HEIGHT),
                                box[0] * box[1],
                                box[0],
                                tuple(new_decisions),
                            )
                            extensions.append((score, extended, new_decisions))
                            break
        if not extensions:
            return ()
        deduplicated = {}
        for score, state, decisions in sorted(extensions, key=lambda item: item[0]):
            signature = tuple(
                (block_id, placed.fragment.id, placed.delta)
                for block_id, placed in sorted(state.items())
            )
            deduplicated.setdefault(signature, (score, state, decisions))
        ranked = list(deduplicated.values())
        diverse = []
        covered_structures = set()
        for candidate in ranked:
            _, state, _ = candidate
            cells = tuple(
                (key, item)
                for key, item in sorted(state.items())
                if item.fragment.block.kind != "interface"
            )
            structure = tuple(
                (
                    first_key,
                    second_key,
                    "same_band"
                    if max(first.envelope[1], second.envelope[1])
                    < min(first.envelope[3], second.envelope[3])
                    else (
                        "first_above" if first.envelope[3] <= second.envelope[1] else "second_above"
                    ),
                    "first_left"
                    if first.envelope[2] <= second.envelope[0]
                    else (
                        "second_left" if second.envelope[2] <= first.envelope[0] else "x_overlap"
                    ),
                )
                for index, (first_key, first) in enumerate(cells)
                for second_key, second in cells[index + 1 :]
            )
            if structure in covered_structures:
                continue
            covered_structures.add(structure)
            diverse.append(candidate)
            if len(diverse) == CANDIDATE_BUDGET:
                break
        if len(diverse) < CANDIDATE_BUDGET:
            diverse_ids = {id(item) for item in diverse}
            diverse.extend(item for item in ranked if id(item) not in diverse_ids)
        beam = [(state, decisions) for _, state, decisions in diverse[:CANDIDATE_BUDGET]]
    complete = []
    for state, decisions in beam:
        items = tuple(sorted(state.values(), key=lambda item: item.fragment.block.id))
        width = max(item.content_envelope[2] for item in items) - min(
            item.content_envelope[0] for item in items
        )
        height = max(item.content_envelope[3] for item in items) - min(
            item.content_envelope[1] for item in items
        )
        complete.append(
            Packing(
                items,
                ("partial-beam", *decisions, f"partial-beam:pass:measured={width}x{height}"),
            )
        )
    return tuple(complete)


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
        distribution = _distribution_column_candidate(plan, variants, successful)
        if distribution is not None and all(
            tuple((item.fragment.id, item.delta) for item in distribution.fragments)
            != tuple((item.fragment.id, item.delta) for item in candidate.fragments)
            for candidate in successful
        ):
            extras.append(distribution)
        structural = tuple(
            candidate
            for baseline in successful
            for candidate in _structural_repack_candidates(plan, baseline)
        )
        for label in ("functional-row-compaction", "precedence-staggered-band"):
            candidate = next((item for item in structural if item.attempts[-1] == label), None)
            if candidate is not None:
                extras.append(candidate)
        # Shelf success alone does not prove structural coverage.  A shared
        # internally generated net with several physical islands can need an
        # interleaved partial placement to meet its whole-net length bound.
        distribution_demand = any(
            net.internally_generated and net.explicit_geometry_required and len(net.fragments) >= 4
            for net in plan.presentation_nets
        )
        noninterface_count = sum(
            item.fragment.block.kind != "interface" for item in successful[0].fragments
        )
        needs_band_alternative = (
            noninterface_count >= 2
            and len({_band_count(item) for item in (*successful[:4], *extras)}) == 1
        )
        if distribution_demand or needs_band_alternative:
            partial = _partial_beam_candidates(plan, variants)
            if partial:
                baseline_bands = _band_count(successful[0])
                diverse = next(
                    (item for item in partial if _band_count(item) != baseline_bands), partial[0]
                )
                extras.append(diverse)
        ordered = [successful[0], *extras, *successful[1:]]
        seen = set()
        deduped = []
        for item in ordered:
            identity = tuple((placed.fragment.id, placed.delta) for placed in item.fragments)
            if identity not in seen:
                seen.add(identity)
                deduped.append(item)
            if len(deduped) == CANDIDATE_BUDGET:
                break
        return tuple(deduped)

    partial = _partial_beam_candidates(plan, variants)
    if partial:
        return partial

    raise InputError(
        f"PACK_BUDGET_EXHAUSTED: candidates={len(attempts)}/{CANDIDATE_BUDGET} "
        f"spread_limit=210x140mm attempts={attempts}"
    )


def pack_fragments(plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]) -> Packing:
    """Return the first bounded seed with a feasible route demand when observable."""
    candidates = pack_fragment_candidates(plan, variants)
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
