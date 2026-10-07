from ai_kicad import m2_page_utilization_composition_observer as obs


def test_reports_content_bounding_box_and_occupied_ratio() -> None:
    elements = (
        obs.VisualElement("a", (20, 20), 10, 10),
        obs.VisualElement("b", (80, 60), 10, 10),
    )
    metrics = obs.measure_page_utilization(elements)
    assert metrics.content_width == 70
    assert metrics.content_height == 50
    assert metrics.content_area == 3500
    assert round(metrics.occupied_area_ratio, 4) == round(3500 / (210 * 140), 4)


def test_detects_non_tiny_upper_left_edge_bias() -> None:
    elements = tuple(
        obs.VisualElement(f"e{index}", (10 + index * 4, 10 + index * 3), complexity_weight=2)
        for index in range(5)
    )
    metrics = obs.measure_page_utilization(elements)
    assert metrics.complexity_band == "medium"
    assert not metrics.tiny_probe_exempt_from_minimum_utilization
    assert metrics.edge_bias_detected
    assert metrics.horizontal_whitespace_imbalance > 0
    assert metrics.vertical_whitespace_imbalance > 0


def test_tiny_probe_is_exempt_from_minimum_utilization_edge_bias() -> None:
    elements = (
        obs.VisualElement("probe", (10, 10)),
        obs.VisualElement("pin", (20, 10)),
    )
    metrics = obs.measure_page_utilization(elements)
    assert metrics.complexity_band == "tiny"
    assert metrics.tiny_probe_exempt_from_minimum_utilization
    assert not metrics.edge_bias_detected


def test_large_internal_void_has_exact_witness() -> None:
    elements = (
        obs.VisualElement("left_top", (20, 20), 10, 10),
        obs.VisualElement("left_bottom", (20, 100), 10, 10),
        obs.VisualElement("right_top", (180, 20), 10, 10),
        obs.VisualElement("right_bottom", (180, 100), 10, 10),
    )
    metrics = obs.measure_page_utilization(elements)
    assert metrics.largest_accidental_internal_void == 150 * 90
    assert metrics.dominant_void_witness == "vertical_corridor"


def test_spreading_content_reduces_edge_bias_without_hard_gate_changes() -> None:
    packed = tuple(
        obs.VisualElement(f"p{index}", (12 + index * 3, 12 + index * 2), complexity_weight=2)
        for index in range(5)
    )
    spread = tuple(
        obs.VisualElement(f"s{index}", (50 + index * 28, 45 + (index % 2) * 35), complexity_weight=2)
        for index in range(5)
    )
    packed_metrics = obs.measure_page_utilization(packed)
    spread_metrics = obs.measure_page_utilization(spread)
    assert packed_metrics.edge_bias_detected
    assert not spread_metrics.edge_bias_detected
    assert spread_metrics.occupied_area_ratio > packed_metrics.occupied_area_ratio


def test_metric_values_are_refdes_and_input_order_invariant() -> None:
    original = (
        obs.VisualElement("r1", (40, 40), 10, 10),
        obs.VisualElement("c1", (100, 80), 10, 10),
    )
    renamed_reordered = (
        obs.VisualElement("zzz", (100, 80), 10, 10),
        obs.VisualElement("aaa", (40, 40), 10, 10),
    )
    first = obs.measure_page_utilization(original)
    second = obs.measure_page_utilization(renamed_reordered)
    assert first.content_width == second.content_width
    assert first.content_height == second.content_height
    assert first.largest_accidental_internal_void == second.largest_accidental_internal_void
