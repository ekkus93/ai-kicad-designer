"""Implementation details for m2 pack distribution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_fragments_base import FragmentVariant
from .m2_fragments_types import Point
from .m2_geometry import ConductorSegment, canonical_conductor_tree
from .m2_pack_constants import (
    BOTTOM,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    PLACEMENT_LEFT,
    RIGHT,
    TOP,
)
from .m2_pack_core import (
    Packing,
    PlacedFragment,
    _place,
)
from .m2_transform import transform_library_point
from .m2_semantics_core import PlacementConflict, check_placement_constraints
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


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
    width = max(item.content_envelope[2] for item in items) - min(
        item.content_envelope[0] for item in items
    )
    height = max(item.content_envelope[3] for item in items) - min(
        item.content_envelope[1] for item in items
    )
    return Packing(
        items,
        baseline.attempts + (f"distribution-column:{net.id}:pass:measured={width}x{height}",),
    )


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
        dx, dy = transform_library_point(
            obligation.pin_x,
            obligation.pin_y,
            angle,
            item.fragment.mirrors.get(obligation.occurrence),
        )
        return origin[0] + item.delta[0] + dx, origin[1] + item.delta[1] + dy

    try:
        check_placement_constraints(plan, point)
    except PlacementConflict:
        return None
    return Packing(
        tuple(sorted(items, key=lambda item: item.fragment.block.id)), baseline.attempts + (label,)
    )
