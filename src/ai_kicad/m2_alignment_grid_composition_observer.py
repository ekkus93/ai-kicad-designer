"""Independent alignment, grid, and field-composition observer."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

Point = tuple[int, int]


@dataclass(frozen=True)
class PlacedItem:
    item_id: str
    role: str
    center: Point
    owner_id: str | None = None
    signal_row_id: str | None = None
    orientation: str = "east"
    field_orientation: str = "east"
    field_length: int = 0
    field_slot: str = "default"


@dataclass(frozen=True)
class OwnerDistance:
    item_id: str
    owner_id: str
    distance: int


@dataclass(frozen=True)
class AlignmentGridMetrics:
    meaningful_horizontal_alignment_lines: int
    meaningful_vertical_alignment_lines: int
    sequential_stage_baseline_deviation: int
    role_passive_alignment_deviation: int
    connector_signal_row_distance: tuple[OwnerDistance, ...]
    support_owner_offset: tuple[OwnerDistance, ...]
    grid_violations: tuple[str, ...]
    inconsistent_field_orientation_ids: tuple[str, ...]
    inconsistent_orientation_ids: tuple[str, ...]
    long_field_default_slot_ids: tuple[str, ...]


def measure_alignment_grid_composition(
    items: tuple[PlacedItem, ...],
    *,
    grid_step: int = 5,
    alignment_tolerance: int = 1,
    long_field_threshold: int = 24,
) -> AlignmentGridMetrics:
    """Measure role-aware alignment and KiCad-grid-compatible placement."""
    by_id = {item.item_id: item for item in items}
    horizontal_lines = _alignment_line_count(
        tuple(item.center[1] for item in items), alignment_tolerance
    )
    vertical_lines = _alignment_line_count(
        tuple(item.center[0] for item in items), alignment_tolerance
    )
    stage_deviation = _row_deviation(
        tuple(item for item in items if item.role == "stage" or item.role == "active")
    )
    passive_deviation = _row_deviation(tuple(item for item in items if item.role == "passive"))
    connector_distances = _owner_distances(
        tuple(item for item in items if item.role == "connector"), by_id
    )
    support_distances = _owner_distances(
        tuple(item for item in items if item.role == "support"), by_id
    )
    grid_violations = tuple(
        sorted(
            item.item_id
            for item in items
            if grid_step > 0
            and (item.center[0] % grid_step != 0 or item.center[1] % grid_step != 0)
        )
    )
    field_inconsistent = _inconsistent_by_role(items, attribute="field_orientation")
    orientation_inconsistent = _inconsistent_by_role(items, attribute="orientation")
    long_default = tuple(
        sorted(
            item.item_id
            for item in items
            if item.field_length >= long_field_threshold and item.field_slot == "default"
        )
    )
    return AlignmentGridMetrics(
        horizontal_lines,
        vertical_lines,
        stage_deviation,
        passive_deviation,
        connector_distances,
        support_distances,
        grid_violations,
        field_inconsistent,
        orientation_inconsistent,
        long_default,
    )


def _alignment_line_count(values: tuple[int, ...], tolerance: int) -> int:
    remaining = sorted(values)
    lines = 0
    while remaining:
        seed = remaining[0]
        group = [value for value in remaining if abs(value - seed) <= tolerance]
        if len(group) >= 2:
            lines += 1
        remaining = [value for value in remaining if abs(value - seed) > tolerance]
    return lines


def _row_deviation(items: tuple[PlacedItem, ...]) -> int:
    if len(items) < 2:
        return 0
    ys = [item.center[1] for item in items]
    return max(ys) - min(ys)


def _owner_distances(
    items: tuple[PlacedItem, ...], by_id: dict[str, PlacedItem]
) -> tuple[OwnerDistance, ...]:
    witnesses: list[OwnerDistance] = []
    for item in sorted(items, key=lambda value: value.item_id):
        if item.owner_id is None or item.owner_id not in by_id:
            continue
        owner = by_id[item.owner_id]
        witnesses.append(
            OwnerDistance(item.item_id, owner.item_id, abs(item.center[1] - owner.center[1]))
        )
    return tuple(witnesses)


def _inconsistent_by_role(items: tuple[PlacedItem, ...], *, attribute: str) -> tuple[str, ...]:
    by_role: dict[str, list[PlacedItem]] = defaultdict(list)
    for item in items:
        by_role[item.role].append(item)

    inconsistent: list[str] = []
    for role_items in by_role.values():
        if len(role_items) < 2:
            continue
        values = [getattr(item, attribute) for item in role_items]
        expected = Counter(values).most_common(1)[0][0]
        inconsistent.extend(
            item.item_id for item in role_items if getattr(item, attribute) != expected
        )
    return tuple(sorted(inconsistent))
