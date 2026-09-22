"""Deterministic measured-envelope packing for M2 fragments."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice, product

from .ir import InputError
from .m2a import PITCH
from .m2_fragments import FragmentVariant, Point, PortAnchor, Rect
from .m2_semantics import SemanticPlan


LEFT = 18 * PITCH
TOP = 23 * PITCH
RIGHT = 215 * PITCH
BOTTOM = 144 * PITCH
MAX_CONTENT_WIDTH = 210_000_000
MAX_CONTENT_HEIGHT = 140_000_000
ENVELOPE_OUTER_PADDING = 4 * PITCH
CANDIDATE_BUDGET = 8
PLACEMENT_LEFT = LEFT + 2 * PITCH


@dataclass(frozen=True)
class PlacedFragment:
    fragment: FragmentVariant
    delta: Point
    envelope: Rect
    ports: tuple[PortAnchor, ...]


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
    return PlacedFragment(fragment, delta, envelope, ports)


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
    branch_targets = {edge.target for edge in plan.edges if edge.kind == "branch"}
    nodes = {
        block.id
        for block in plan.blocks
        if block.kind not in {"interface", "package_power", "unused_amplifier", "led_branch"}
        and block.id not in branch_targets
    }
    pairs = {
        (edge.source, edge.target)
        for edge in plan.edges
        if edge.kind == "signal" and edge.source in nodes and edge.target in nodes
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
            if edge.kind != "branch" or edge.source not in assigned or edge.target in attached:
                continue
            attachments.setdefault(edge.source, []).append(edge.target)
            attached.add(edge.target)

    units: list[_Unit] = []
    for chain in chains:
        offsets: list[tuple[str, int, int]] = []
        x = 0
        main_height = 0
        source_x: dict[str, int] = {}
        source_width: dict[str, int] = {}
        for fragment_id in chain:
            fragment = chosen[fragment_id]
            width = fragment.envelope[2] - fragment.envelope[0]
            height = fragment.envelope[3] - fragment.envelope[1]
            offsets.append((fragment_id, x, 0))
            source_x[fragment_id] = x
            source_width[fragment_id] = width
            x += width
            main_height = max(main_height, height)
        width, height = x, main_height
        for source in chain:
            branch_y = main_height
            for target in attachments.get(source, []):
                fragment = chosen[target]
                target_width = fragment.envelope[2] - fragment.envelope[0]
                target_height = fragment.envelope[3] - fragment.envelope[1]
                if branches_beside and source == chain[-1]:
                    offsets.append((target, width, 0))
                    width += target_width
                    height = max(height, target_height)
                else:
                    local_x = source_x[source] + max(0, (source_width[source] - target_width) // 2)
                    offsets.append((target, local_x, branch_y))
                    width = max(width, local_x + target_width)
                    branch_y += target_height
                    height = max(height, branch_y)
        ids = tuple(fragment_id for fragment_id, _, _ in offsets)
        units.append(_Unit(ids, tuple(offsets), width, height, len(chain) > 1))

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
        units.append(
            _Unit(
                (fragment_id,),
                ((fragment_id, 0, 0),),
                fragment.envelope[2] - fragment.envelope[0],
                fragment.envelope[3] - fragment.envelope[1],
                False,
            )
        )
    return _group_power_fanout(plan, units)


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
            x += unit.width
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


def _typed_unit_order(plan: SemanticPlan, units: list[_Unit]) -> list[_Unit]:
    """Order shelf items by typed roles without inventing stage progression."""
    by_id = {block.id: block for block in plan.blocks}
    power_sources = {edge.source for edge in plan.edges if edge.kind == "power"}
    power_consumers = {edge.target for edge in plan.edges if edge.kind == "power"}
    branch_sources = {edge.source for edge in plan.edges if edge.kind == "branch"}
    branch_targets = {edge.target for edge in plan.edges if edge.kind == "branch"}

    def category(unit: _Unit) -> tuple[int, str]:
        kinds = {by_id[item].kind for item in unit.ids}
        if unit.serial:
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
    lower_affinity = _make_units(
        plan,
        chosen,
        attach_branches=True,
        branches_beside=False,
        stack_interfaces=True,
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
        ("lower-affinity", _typed_unit_order(plan, lower_affinity)),
        ("typed", _typed_unit_order(plan, flat)),
        ("height", sorted(flat, key=lambda unit: (-unit.height, -unit.width, unit.ids))),
    )


def _pack_shelves(
    ordered: list[_Unit], chosen: dict[str, FragmentVariant]
) -> tuple[list[PlacedFragment], int, int]:
    placed: list[PlacedFragment] = []
    x = y = 0
    row_height = 0
    used_width = 0
    serial_shelves = 0
    unit_positions: dict[str, tuple[int, int]] = {}
    backfill_limit = 0
    backfill_x = 0
    for unit in ordered:
        if unit.width > MAX_CONTENT_WIDTH or unit.height > MAX_CONTENT_HEIGHT:
            raise ValueError(
                f"unit-spread-overflow:{','.join(unit.ids)}:{unit.width}x{unit.height}"
            )
        if (unit.serial and serial_shelves) or (unit.parallel_fanout and x):
            x = 0
            y += row_height
            row_height = 0
            backfill_limit = 0
            backfill_x = 0
            if unit.affinity_source in unit_positions:
                source_x, source_width = unit_positions[unit.affinity_source]
                x = max(
                    0,
                    min(
                        max(0, MAX_CONTENT_WIDTH - unit.width - PITCH),
                        source_x + (source_width - unit.width) // 2,
                    ),
                )
                backfill_limit = x
            placement_x = x
        elif x and x + unit.width > MAX_CONTENT_WIDTH:
            if backfill_x + unit.width <= backfill_limit:
                placement_x = backfill_x
                backfill_x += unit.width
            else:
                x = 0
                y += row_height
                row_height = 0
                backfill_limit = 0
                backfill_x = 0
                placement_x = x
        else:
            placement_x = x
        if y + unit.height > MAX_CONTENT_HEIGHT:
            raise ValueError(
                f"content-spread-overflow:{','.join(unit.ids)}:"
                f"required-height={y + unit.height}:limit={MAX_CONTENT_HEIGHT}"
            )
        for fragment_id, dx, dy in unit.offsets:
            placed.append(
                _place(chosen[fragment_id], PLACEMENT_LEFT + placement_x + dx, TOP + y + dy)
            )
            unit_positions[fragment_id] = (placement_x + dx, unit.width)
        if placement_x == x:
            x += unit.width
        row_height = max(row_height, unit.height)
        used_width = max(used_width, placement_x + unit.width)
        serial_shelves += unit.serial
    used_height = y + row_height
    actual_width = max(item.envelope[2] for item in placed) - min(
        item.envelope[0] for item in placed
    )
    actual_height = max(item.envelope[3] for item in placed) - min(
        item.envelope[1] for item in placed
    )
    content_width_bound = max(0, actual_width - ENVELOPE_OUTER_PADDING)
    content_height_bound = max(0, actual_height - ENVELOPE_OUTER_PADDING)
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


def pack_fragments(plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]) -> Packing:
    """Pack typed projections with measured envelopes and bounded alternatives."""
    attempts: list[str] = []
    keys = sorted(variants)
    if set(keys) != {block.id for block in plan.blocks}:
        raise InputError("PACK_VARIANT_BLOCK_MISMATCH")
    if any(not choices or len(choices) > 8 for choices in variants.values()):
        raise InputError("PACK_VARIANT_INVENTORY: each block requires one to eight variants")

    combinations = product(*(variants[key] for key in keys))
    for combination in islice(combinations, CANDIDATE_BUDGET):
        chosen = dict(zip(keys, combination, strict=True))
        for arrangement_name, ordered in _arrangements(plan, chosen):
            candidate_index = len(attempts) + 1
            if candidate_index > CANDIDATE_BUDGET:
                break
            try:
                placed, width, height = _pack_shelves(ordered, chosen)
            except ValueError as exc:
                attempts.append(f"candidate-{candidate_index}:{arrangement_name}:{exc}")
                continue
            attempts.append(
                f"candidate-{candidate_index}:{arrangement_name}:pass:measured={width}x{height}"
            )
            return Packing(
                tuple(sorted(placed, key=lambda item: item.fragment.id)), tuple(attempts)
            )
        if len(attempts) >= CANDIDATE_BUDGET:
            break

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
    raise InputError(
        f"PACK_BUDGET_EXHAUSTED: candidates={len(attempts)}/{CANDIDATE_BUDGET} "
        f"spread_limit=210x140mm attempts={attempts}"
    )
