"""Implementation details for m2 pack layout."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_fragments_base import FragmentVariant
from .m2_pack_constants import (
    BOTTOM,
    CHANNEL_GAP,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    MAX_PACKING_HEIGHT,
    MAX_PACKING_WIDTH,
    PLACEMENT_LEFT,
    RIGHT,
    TOP,
)
from .m2_pack_core import (
    PlacedFragment,
    _make_units,
    _place,
    _typed_unit_order,
    _Unit,
)

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


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
