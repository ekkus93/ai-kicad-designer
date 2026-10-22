"""Geometry helpers for deterministic schematic property placement."""

from __future__ import annotations

from collections.abc import Iterable

from .m2_geometry import label_text_width
from .m2_fragments_types import Rect
from .m2a_constants import PITCH

FONT_HEIGHT = 1_700_000
TEXT_CLEARANCE = 1_000_000
_MIN_HALF_WIDTH = 635_000
MAX_LOCAL_SEARCH_RADIUS = 80


def readable_property_angle(symbol_angle: int) -> int:
    """Return a page-readable property angle for an orthogonal symbol turn."""
    normalized = symbol_angle % 360
    if normalized not in (0, 90, 180, 270):
        raise ValueError(f"unsupported symbol angle for property text: {symbol_angle}")
    return 90 if normalized in (90, 270) else 0


def readable_property_angles(
    symbol_angles: dict[tuple[str, int], int],
) -> dict[tuple[str, int], int]:
    """Normalize every rotated symbol occurrence without asset/refdes exceptions."""
    return {
        occurrence: text_angle
        for occurrence, angle in sorted(symbol_angles.items())
        if (text_angle := readable_property_angle(angle))
    }


def property_page_angle(symbol_angle: int, property_angle: int | None = None) -> int:
    """Resolve KiCad's symbol-relative field angle to its page orientation."""
    field_angle = (
        readable_property_angle(symbol_angle) if property_angle is None else property_angle
    )
    return (field_angle - symbol_angle) % 180


def text_half_width(value: str) -> int:
    """Conservative centered-field half-width for KiCad's pinned stroke font."""
    width = max(label_text_width(line) for line in value.splitlines() or [""])
    return max(_MIN_HALF_WIDTH, (width + 1) // 2)


def text_height(value: str) -> int:
    """Conservative height including explicit multiline property text."""
    return FONT_HEIGHT * max(1, len(value.splitlines()))


def property_positions(
    reference: str, value: str, anchor: tuple[int, int], angle: int = 0
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return independent field anchors, separating multiline fields vertically."""
    x, y = anchor
    ref_height = text_extents(reference, angle)[1]
    value_height = text_extents(value, angle)[1]
    nominal_offset = 2 * PITCH
    collision_free_offset = (ref_height + value_height) // 2 + TEXT_CLEARANCE
    return (anchor, (x, y + max(nominal_offset, collision_free_offset)))


def text_extents(value: str, angle: int = 0) -> tuple[int, int]:
    """Return conservative axis-aligned width/height for a page-oriented field."""
    if angle % 180 == 0:
        return 2 * text_half_width(value), text_height(value)
    if angle % 180 == 90:
        return text_height(value), 2 * text_half_width(value)
    raise ValueError(f"unsupported text angle: {angle}")


def property_envelopes(
    reference: str, value: str, anchor: tuple[int, int], angle: int = 0
) -> tuple[Rect, Rect]:
    """Return unpadded envelopes for reference/value fields at their own anchors."""
    reference_position, value_position = property_positions(reference, value, anchor, angle)
    return tuple(
        (
            field_x - text_extents(text, angle)[0] // 2,
            field_y - text_extents(text, angle)[1] // 2,
            field_x + text_extents(text, angle)[0] // 2,
            field_y + text_extents(text, angle)[1] // 2,
        )
        for text, (field_x, field_y) in zip(
            (reference, value), (reference_position, value_position), strict=True
        )
    )  # type: ignore[return-value]


def padded(rect: Rect, clearance: int = TEXT_CLEARANCE) -> Rect:
    left, top, right, bottom = rect
    return left - clearance, top - clearance, right + clearance, bottom + clearance


def overlaps(first: Rect, second: Rect) -> bool:
    return max(first[0], second[0]) < min(first[2], second[2]) and max(first[1], second[1]) < min(
        first[3], second[3]
    )


def segment_intersects_rect(start: tuple[int, int], end: tuple[int, int], rect: Rect) -> bool:
    """Test an orthogonal wire against a closed text obstacle envelope."""
    left, top, right, bottom = rect
    if start[0] == end[0]:
        return left < start[0] < right and max(min(start[1], end[1]), top) < min(
            max(start[1], end[1]), bottom
        )
    if start[1] == end[1]:
        return top < start[1] < bottom and max(min(start[0], end[0]), left) < min(
            max(start[0], end[0]), right
        )
    raise ValueError("schematic text collision checks require orthogonal wires")


def candidate_text_anchors(
    origin: tuple[int, int],
    preferred: tuple[int, int],
    *,
    body: Rect | None = None,
    longest_field: str = "",
    pitch: int = PITCH,
) -> tuple[tuple[int, int], ...]:
    """Generate stable anchors just outside symbol geometry, then expand outward."""
    ox, oy = origin
    ordered = [preferred]
    offsets = [
        (0, -8),
        (8, -2),
        (-8, -2),
        (0, 5),
        (12, -2),
        (-12, -2),
        (12, -10),
        (-12, -10),
        (0, -12),
        (0, -16),
        (0, -20),
    ]
    # Bounded outward expansion gives crowded layouts room to clear obstacles.
    # Fragment reservations include the selected field envelope, so the packer
    # expands and repositions the owning block around this local placement.
    for radius in range(24, MAX_LOCAL_SEARCH_RADIUS + 1, 4):
        offsets.extend(
            (dx * radius, dy * radius)
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1))
        )
    ordered.extend((ox + dx * pitch, oy + dy * pitch) for dx, dy in offsets)
    if body is not None:
        left, top, right, bottom = body
        half_width = text_half_width(longest_field) + TEXT_CLEARANCE
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        ordered.extend(
            (
                (center_x, top - (2 * pitch + FONT_HEIGHT // 2 + TEXT_CLEARANCE)),
                (right + half_width, center_y - pitch),
                (left - half_width, center_y - pitch),
                (center_x, bottom + FONT_HEIGHT // 2 + TEXT_CLEARANCE),
            )
        )
    return tuple(dict.fromkeys(ordered))


def first_clear_text_anchor(
    candidates: Iterable[tuple[int, int]],
    envelopes_for_anchor,
    *,
    obstacles: Iterable[Rect],
    wires: Iterable[tuple[tuple[int, int], tuple[int, int]]],
    bounds: Rect | None = None,
) -> tuple[int, int] | None:
    """Select the first deterministic anchor clear of geometry and route segments."""
    fixed_obstacles = tuple(obstacles)
    fixed_wires = tuple(wires)
    for anchor in candidates:
        raw_fields = tuple(envelopes_for_anchor(anchor))
        if any(
            overlaps(first, second)
            for index, first in enumerate(raw_fields)
            for second in raw_fields[index + 1 :]
        ):
            continue
        fields = tuple(padded(rect) for rect in raw_fields)
        if bounds is not None and any(
            rect[0] < bounds[0] or rect[1] < bounds[1] or rect[2] > bounds[2] or rect[3] > bounds[3]
            for rect in fields
        ):
            continue
        if any(overlaps(field, obstacle) for field in fields for obstacle in fixed_obstacles):
            continue
        if any(
            segment_intersects_rect(start, end, field)
            for field in fields
            for start, end in fixed_wires
        ):
            continue
        return anchor
    return None
