# fmt: off
from fractions import Fraction

import pytest

from ai_kicad.m2_repeated_composition_observer import (
    RepeatedMember,
    measure_repeated_composition,
)


def test_single_channel_has_zero_repeated_variance() -> None:
    metrics = measure_repeated_composition(
        (RepeatedMember("amp", "channel-a", (10, 20)),)
    )
    assert metrics.channel_count == 1
    assert metrics.corresponding_symbol_count == 0
    assert metrics.pitch_variance == 0


def test_aligned_repeated_channels_report_consistent_orientation_and_pitch() -> None:
    members = (
        RepeatedMember("input", 3, (0, 0)),
        RepeatedMember("amp", 3, (10, 0)),
        RepeatedMember("input", 1, (0, 20)),
        RepeatedMember("amp", 1, (10, 20)),
        RepeatedMember("input", 2, (0, 40)),
        RepeatedMember("amp", 2, (10, 40)),
    )
    metrics = measure_repeated_composition(members)
    assert metrics.channel_count == 3
    assert metrics.corresponding_symbol_count == 2
    assert metrics.orientation_variance == 0
    assert metrics.pitch_variance == 0


def test_orientation_and_pitch_mutations_are_detected() -> None:
    members = (
        RepeatedMember("amp", "a", (0, 0), 0),
        RepeatedMember("amp", "b", (0, 10), 90),
        RepeatedMember("amp", "c", (0, 30), 0),
    )
    metrics = measure_repeated_composition(members)
    assert metrics.orientation_variance == 1
    assert metrics.pitch_variance > 0


def test_declaration_order_and_channel_names_do_not_change_metrics() -> None:
    first = (
        RepeatedMember("input", "left", (0, 0)),
        RepeatedMember("amp", "left", (10, 0)),
        RepeatedMember("input", "right", (0, 20)),
        RepeatedMember("amp", "right", (10, 20)),
    )
    renamed_permuted = (
        RepeatedMember("amp", 900, (10, 20)),
        RepeatedMember("input", 900, (0, 20)),
        RepeatedMember("amp", -7, (10, 0)),
        RepeatedMember("input", -7, (0, 0)),
    )
    assert measure_repeated_composition(first) == measure_repeated_composition(
        renamed_permuted
    )


def test_duplicate_semantic_role_in_channel_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate semantic role"):
        measure_repeated_composition(
            (
                RepeatedMember("amp", "a", (0, 0)),
                RepeatedMember("amp", "a", (1, 0)),
            )
        )


def test_displacement_variance_detects_inconsistent_correspondence() -> None:
    metrics = measure_repeated_composition(
        (
            RepeatedMember("amp", "a", (0, 0)),
            RepeatedMember("amp", "b", (0, 10)),
            RepeatedMember("amp", "c", (0, 30)),
        )
    )
    assert metrics.corresponding_displacement_variance == Fraction(100)

def test_three_channel_metrics_are_permutation_and_rename_invariant() -> None:
    members = (
        RepeatedMember("amp", "z", (5, 60)),
        RepeatedMember("amp", "x", (5, 0)),
        RepeatedMember("amp", "y", (5, 20)),
    )
    renamed = (
        RepeatedMember("amp", 42, (5, 20)),
        RepeatedMember("amp", 3, (5, 60)),
        RepeatedMember("amp", 9, (5, 0)),
    )
    first = measure_repeated_composition(members)
    assert first == measure_repeated_composition(renamed)
    assert first.pitch_variance == Fraction(100)
    assert first.corresponding_displacement_variance == Fraction(400)


def test_repeated_channel_order_follows_horizontal_geometry_too() -> None:
    members = (
        RepeatedMember("amp", "far", (60, 5)),
        RepeatedMember("amp", "left", (0, 5)),
        RepeatedMember("amp", "middle", (20, 5)),
    )
    assert measure_repeated_composition(members).pitch_variance == Fraction(100)
