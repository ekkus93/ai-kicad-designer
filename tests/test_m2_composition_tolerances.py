from ai_kicad.m2_composition_tolerances import (
    FROZEN_TOLERANCES,
    Complexity,
    complexity_band,
    tolerance_for,
    within_lower_bound,
    within_upper_bound,
)


def test_complexity_bands_are_monotone_at_boundaries() -> None:
    assert complexity_band(Complexity(1, 3, 2)) == "tiny"
    assert complexity_band(Complexity(2, 10, 8)) == "small"
    assert complexity_band(Complexity(4, 24, 24)) == "medium"
    assert complexity_band(Complexity(8, 40, 30)) == "dense"


def test_tiny_probe_has_only_utilization_exemption() -> None:
    tolerance = tolerance_for(Complexity(1, 2, 1))
    assert tolerance.minimum_occupied_ratio is None
    assert tolerance.maximum_centroid_offset_mm > 0
    assert tolerance.maximum_normalized_bend_excess > 0


def test_non_tiny_bands_have_increasing_utilization_pressure() -> None:
    ratios = [
        FROZEN_TOLERANCES[name].minimum_occupied_ratio for name in ("small", "medium", "dense")
    ]
    assert ratios == sorted(ratios)
    assert all(value is not None for value in ratios)


def test_upper_tolerance_accepts_exact_boundary_and_rejects_one_grid_over() -> None:
    bound = FROZEN_TOLERANCES["medium"].maximum_centroid_offset_mm
    assert within_upper_bound(bound, bound)
    assert not within_upper_bound(bound + 0.5, bound)


def test_alignment_boundary_has_off_by_one_grid_test() -> None:
    bound = FROZEN_TOLERANCES["dense"].maximum_repeated_alignment_variance_mm
    assert within_upper_bound(bound, bound)
    assert not within_upper_bound(bound + 0.5, bound)


def test_routing_boundaries_have_off_by_one_grid_tests() -> None:
    tolerance = FROZEN_TOLERANCES["small"]
    assert within_upper_bound(
        tolerance.maximum_normalized_bend_excess,
        tolerance.maximum_normalized_bend_excess,
    )
    assert not within_upper_bound(
        tolerance.maximum_normalized_bend_excess + 0.5,
        tolerance.maximum_normalized_bend_excess,
    )
    assert within_upper_bound(
        tolerance.maximum_normalized_length_excess,
        tolerance.maximum_normalized_length_excess,
    )
    assert not within_upper_bound(
        tolerance.maximum_normalized_length_excess + 0.5,
        tolerance.maximum_normalized_length_excess,
    )


def test_lower_tolerance_accepts_boundary_and_rejects_below() -> None:
    bound = FROZEN_TOLERANCES["small"].minimum_occupied_ratio
    assert bound is not None
    assert within_lower_bound(bound, bound)
    assert not within_lower_bound(bound - 0.001, bound)


def test_invalid_complexity_and_grid_are_rejected() -> None:
    try:
        Complexity(-1, 1, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative complexity must fail")

    try:
        within_upper_bound(1.0, 1.0, grid_mm=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("non-positive grid must fail")
