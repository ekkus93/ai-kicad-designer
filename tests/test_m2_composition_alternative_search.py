import pytest

from ai_kicad.m2_composition_alternative_search import (
    AlternativeAxis,
    enumerate_alternatives,
)


def test_search_covers_all_required_meaningful_axes() -> None:
    axes = (
        AlternativeAxis("interface_frontier", ("left", "right")),
        AlternativeAxis("semantic_block_order", ("forward", "sibling_swap")),
        AlternativeAxis("repeated_channel_grammar", ("rows", "columns")),
        AlternativeAxis("support_placement", ("local", "shared")),
        AlternativeAxis("field_slot", ("default", "alternate")),
        AlternativeAxis("branch_route", ("direct", "dogleg")),
    )

    evidence = enumerate_alternatives(axes, budget=64)

    assert evidence.theoretical_count == 64
    assert evidence.attempted_count == 64
    assert evidence.emitted_count == 64
    assert not evidence.budget_exhausted


def test_search_is_bounded_with_exact_attempt_accounting() -> None:
    axes = (
        AlternativeAxis("interface_frontier", ("left", "right")),
        AlternativeAxis("field_slot", ("a", "b", "c")),
    )

    evidence = enumerate_alternatives(axes, budget=4)

    assert evidence.theoretical_count == 6
    assert evidence.attempted_count == 4
    assert evidence.emitted_count == 4
    assert evidence.budget_exhausted


def test_value_duplicates_are_removed_before_budget_accounting() -> None:
    axes = (
        AlternativeAxis("field_slot", ("alternate", "default", "alternate")),
    )

    evidence = enumerate_alternatives(axes, budget=5)

    assert evidence.theoretical_count == 2
    assert evidence.attempted_count == 2
    assert evidence.emitted_count == 2
    assert evidence.duplicate_count == 0


def test_axis_and_value_order_do_not_change_candidate_sequence() -> None:
    first = (
        AlternativeAxis("field_slot", ("z", "a")),
        AlternativeAxis("interface_frontier", ("right", "left")),
    )
    second = (
        AlternativeAxis("interface_frontier", ("left", "right")),
        AlternativeAxis("field_slot", ("a", "z")),
    )

    assert enumerate_alternatives(first, budget=4) == enumerate_alternatives(
        second,
        budget=4,
    )


def test_unknown_axis_is_rejected_instead_of_silently_expanding_search() -> None:
    with pytest.raises(ValueError, match="unsupported composition axis"):
        enumerate_alternatives(
            (AlternativeAxis("fixture_specific_offset", ("x",)),),
            budget=1,
        )


def test_zero_budget_and_duplicate_axis_are_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        enumerate_alternatives(
            (AlternativeAxis("field_slot", ("default",)),),
            budget=0,
        )

    with pytest.raises(ValueError, match="duplicate composition axis"):
        enumerate_alternatives(
            (
                AlternativeAxis("field_slot", ("default",)),
                AlternativeAxis("field_slot", ("alternate",)),
            ),
            budget=2,
        )
