from ai_kicad.m2_page_composition_observer import (
    measure_page_utilization,
    semantic_complexity_band,
)


def test_page_utilization_reports_empty_tiny_probe() -> None:
    metrics = measure_page_utilization(
        (),
        block_count=1,
        visible_symbol_count=1,
        edge_count=0,
    )

    assert metrics.content_bbox is None
    assert metrics.occupied_area_ratio == 0.0
    assert metrics.complexity_band == "tiny"


def test_page_utilization_reports_bbox_ratio_centroid_and_edge_bias() -> None:
    metrics = measure_page_utilization(
        ((0, 0, 10, 10), (40, 20, 50, 30)),
        block_count=3,
        visible_symbol_count=4,
        edge_count=3,
        envelope_width=100,
        envelope_height=60,
    )

    assert metrics.content_bbox == (0, 0, 50, 30)
    assert metrics.content_bbox_width == 50
    assert metrics.content_bbox_height == 30
    assert metrics.content_bbox_area == 1500
    assert metrics.occupied_area_ratio == 0.25
    assert metrics.content_centroid_offset == 40
    assert metrics.horizontal_whitespace_imbalance == 0.5
    assert metrics.vertical_whitespace_imbalance == 0.5
    assert metrics.complexity_band == "medium"


def test_largest_internal_void_uses_empty_grid_cells_inside_content_bbox() -> None:
    metrics = measure_page_utilization(
        ((0, 0, 10, 10), (30, 0, 40, 10)),
        block_count=2,
        visible_symbol_count=2,
        edge_count=1,
        envelope_width=40,
        envelope_height=10,
    )

    assert metrics.largest_internal_void_area == 200


def test_semantic_complexity_bands_are_thresholded_by_semantic_counts() -> None:
    assert semantic_complexity_band(block_count=1, visible_symbol_count=1, edge_count=0) == "tiny"
    assert semantic_complexity_band(block_count=2, visible_symbol_count=6, edge_count=2) == "small"
    assert semantic_complexity_band(block_count=5, visible_symbol_count=10, edge_count=4) == "medium"
    assert semantic_complexity_band(block_count=8, visible_symbol_count=16, edge_count=8) == "dense"
