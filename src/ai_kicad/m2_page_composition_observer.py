"""Page-utilization and whitespace observer for M2h2 composition evidence."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

Rect = tuple[int, int, int, int]
Point = tuple[int, int]

DEFAULT_ENVELOPE_WIDTH = 210_000_000
DEFAULT_ENVELOPE_HEIGHT = 140_000_000


@dataclass(frozen=True)
class PageUtilizationMetrics:
    content_bbox: Rect | None
    content_bbox_width: int
    content_bbox_height: int
    content_bbox_area: int
    occupied_area_ratio: float
    content_centroid_offset: int
    horizontal_whitespace_imbalance: float
    vertical_whitespace_imbalance: float
    largest_internal_void_area: int
    complexity_band: str


def semantic_complexity_band(block_count: int, visible_symbol_count: int, edge_count: int) -> str:
    """Assign the frozen-input complexity band used by utilization evidence."""
    score = block_count * 3 + visible_symbol_count + edge_count * 2
    if score <= 6:
        return "tiny"
    if score <= 18:
        return "small"
    if score <= 42:
        return "medium"
    return "dense"


def measure_page_utilization(
    rects: tuple[Rect, ...],
    *,
    block_count: int,
    visible_symbol_count: int,
    edge_count: int,
    envelope_width: int = DEFAULT_ENVELOPE_WIDTH,
    envelope_height: int = DEFAULT_ENVELOPE_HEIGHT,
) -> PageUtilizationMetrics:
    """Measure content spread and whitespace without making acceptance claims."""
    complexity_band = semantic_complexity_band(block_count, visible_symbol_count, edge_count)
    if not rects:
        return PageUtilizationMetrics(
            content_bbox=None,
            content_bbox_width=0,
            content_bbox_height=0,
            content_bbox_area=0,
            occupied_area_ratio=0.0,
            content_centroid_offset=0,
            horizontal_whitespace_imbalance=0.0,
            vertical_whitespace_imbalance=0.0,
            largest_internal_void_area=0,
            complexity_band=complexity_band,
        )

    bbox = _union(rects)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    area = width * height
    envelope_area = envelope_width * envelope_height
    centroid = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
    envelope_centroid = (envelope_width // 2, envelope_height // 2)
    left_margin = bbox[0]
    right_margin = envelope_width - bbox[2]
    top_margin = bbox[1]
    bottom_margin = envelope_height - bbox[3]
    return PageUtilizationMetrics(
        content_bbox=bbox,
        content_bbox_width=width,
        content_bbox_height=height,
        content_bbox_area=area,
        occupied_area_ratio=0.0 if envelope_area == 0 else area / envelope_area,
        content_centroid_offset=_manhattan(centroid, envelope_centroid),
        horizontal_whitespace_imbalance=_imbalance(left_margin, right_margin, envelope_width),
        vertical_whitespace_imbalance=_imbalance(top_margin, bottom_margin, envelope_height),
        largest_internal_void_area=_largest_internal_void_area(rects, bbox),
        complexity_band=complexity_band,
    )


def _union(rects: tuple[Rect, ...]) -> Rect:
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _imbalance(first_margin: int, second_margin: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    value = abs(first_margin - second_margin) / denominator
    return 0.0 if isclose(value, 0.0, abs_tol=1e-12) else value


def _largest_internal_void_area(rects: tuple[Rect, ...], bbox: Rect) -> int:
    if len(rects) < 2:
        return 0
    x_edges = sorted({bbox[0], bbox[2], *(rect[0] for rect in rects), *(rect[2] for rect in rects)})
    y_edges = sorted({bbox[1], bbox[3], *(rect[1] for rect in rects), *(rect[3] for rect in rects)})
    largest = 0
    for left, right in zip(x_edges, x_edges[1:], strict=True):
        if left == right:
            continue
        for top, bottom in zip(y_edges, y_edges[1:], strict=True):
            if top == bottom:
                continue
            cell = (left, top, right, bottom)
            if not any(_overlaps(cell, rect) for rect in rects):
                largest = max(largest, (right - left) * (bottom - top))
    return largest


def _overlaps(first: Rect, second: Rect) -> bool:
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]
