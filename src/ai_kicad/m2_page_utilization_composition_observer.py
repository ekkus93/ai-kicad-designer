"""Independent page-utilization and whitespace composition observer.

The observer consumes emitted element geometry only. It does not depend on
production placement scores, candidate ranks, or aesthetic tie-breakers.
"""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class PageEnvelope:
    width: int = 210
    height: int = 140


@dataclass(frozen=True)
class VisualElement:
    element_id: str
    center: Point
    width: int = 10
    height: int = 10
    semantic_role: str = "symbol"
    complexity_weight: int = 1


@dataclass(frozen=True)
class PageUtilizationMetrics:
    content_width: int
    content_height: int
    content_area: int
    occupied_area_ratio: float
    content_centroid_offset: tuple[float, float]
    horizontal_whitespace_imbalance: int
    vertical_whitespace_imbalance: int
    largest_accidental_internal_void: int
    complexity_band: str
    tiny_probe_exempt_from_minimum_utilization: bool
    edge_bias_detected: bool
    dominant_void_witness: str | None


def measure_page_utilization(
    elements: tuple[VisualElement, ...],
    *,
    envelope: PageEnvelope | None = None,
    tiny_probe_max_complexity: int = 3,
    edge_bias_threshold: float = 0.35,
) -> PageUtilizationMetrics:
    """Report page use, whitespace imbalance, edge bias, and large empty corridors."""
    if envelope is None:
        envelope = PageEnvelope()
    if not elements:
        return PageUtilizationMetrics(0, 0, 0, 0.0, (0.0, 0.0), 0, 0, 0, "tiny", True, False, None)

    rects = tuple(_rect(element) for element in elements)
    left = min(rect[0] for rect in rects)
    top = min(rect[1] for rect in rects)
    right = max(rect[2] for rect in rects)
    bottom = max(rect[3] for rect in rects)
    content_width = right - left
    content_height = bottom - top
    content_area = content_width * content_height
    page_area = envelope.width * envelope.height
    occupied_ratio = content_area / page_area if page_area else 0.0

    centroid_x = sum(element.center[0] for element in elements) / len(elements)
    centroid_y = sum(element.center[1] for element in elements) / len(elements)
    offset_x = (centroid_x - envelope.width / 2) / envelope.width
    offset_y = (centroid_y - envelope.height / 2) / envelope.height

    left_margin = max(0, left)
    right_margin = max(0, envelope.width - right)
    top_margin = max(0, top)
    bottom_margin = max(0, envelope.height - bottom)
    horizontal_imbalance = abs(left_margin - right_margin)
    vertical_imbalance = abs(top_margin - bottom_margin)

    internal_void, witness = _largest_internal_void(rects, left, top, right, bottom)
    complexity = sum(max(1, element.complexity_weight) for element in elements)
    band = _complexity_band(complexity, len(elements))
    tiny_exempt = complexity <= tiny_probe_max_complexity
    edge_bias = max(abs(offset_x), abs(offset_y)) > edge_bias_threshold and not tiny_exempt

    return PageUtilizationMetrics(
        content_width,
        content_height,
        content_area,
        occupied_ratio,
        (round(offset_x, 4), round(offset_y, 4)),
        horizontal_imbalance,
        vertical_imbalance,
        internal_void,
        band,
        tiny_exempt,
        edge_bias,
        witness,
    )


def _rect(element: VisualElement) -> Rect:
    half_width = max(1, element.width) // 2
    half_height = max(1, element.height) // 2
    return (
        element.center[0] - half_width,
        element.center[1] - half_height,
        element.center[0] + half_width,
        element.center[1] + half_height,
    )


def _complexity_band(complexity: int, count: int) -> str:
    if complexity <= 3 or count <= 2:
        return "tiny"
    if complexity <= 10 or count <= 6:
        return "medium"
    return "dense"


def _largest_internal_void(
    rects: tuple[Rect, ...], left: int, top: int, right: int, bottom: int
) -> tuple[int, str | None]:
    vertical_gaps = _axis_gaps(tuple((rect[0], rect[2]) for rect in rects), left, right)
    horizontal_gaps = _axis_gaps(tuple((rect[1], rect[3]) for rect in rects), top, bottom)
    widest_column = max(vertical_gaps, default=0)
    tallest_row = max(horizontal_gaps, default=0)
    if widest_column >= tallest_row and widest_column > 0:
        return widest_column * max(0, bottom - top), "vertical_corridor"
    if tallest_row > 0:
        return tallest_row * max(0, right - left), "horizontal_corridor"
    return 0, None


def _axis_gaps(intervals: tuple[tuple[int, int], ...], low: int, high: int) -> tuple[int, ...]:
    clipped = tuple(sorted((max(low, start), min(high, stop)) for start, stop in intervals))
    gaps: list[int] = []
    cursor = low
    for start, stop in clipped:
        if start > cursor:
            gaps.append(start - cursor)
        cursor = max(cursor, stop)
    if high > cursor:
        gaps.append(high - cursor)
    return tuple(gaps)
