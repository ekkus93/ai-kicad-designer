"""Guard the final qualification gate against omitted case families."""

import pytest

from ai_kicad.m2_composition_qualification_matrix import (
    build_required_matrix,
    matrix_gaps,
)
from ai_kicad.m2_composition_qualification_observation import (
    QualificationObservation,
    build_observation_report,
)

SOURCE = "a" * 40
BASE = tuple(f"base-{index:02d}" for index in range(56))


def _matrix(interactions: tuple[str, ...], structural: tuple[str, ...], targeted: tuple[str, ...]):
    return build_required_matrix(
        source_sha=SOURCE,
        base_case_ids=BASE,
        interaction_case_ids=interactions,
        structural_case_ids=structural,
        targeted_case_ids=targeted,
    )


def _passing_observations(matrix):
    observations = []
    all_cases = (
        matrix.base_cases
        + matrix.interaction_cases
        + matrix.structural_cases
        + matrix.targeted_composition_cases
        + matrix.preserved_negative_cases
    )
    for case in all_cases:
        for repetition in range(1, case.repetitions + 1):
            negative = case.family == "preserved_negative"
            observations.append(
                QualificationObservation(
                    case_id=case.case_id,
                    repetition=repetition,
                    source_sha=SOURCE,
                    toolchain="KiCad 10.0.6",
                    status="expected_rejection" if negative else "passed",
                    native_kicad=True,
                    composition_observer_passed=not negative,
                    electrical_passed=not negative,
                    serialized_scene_verified=not negative,
                    rejection_witness="typed invalid-design build" if negative else None,
                )
            )
    return tuple(observations)


def test_fully_passing_subset_cannot_claim_final_matrix_complete() -> None:
    subset = _matrix(("i1__a", "i6__f"), ("structural__one_band",), ())
    report = build_observation_report(subset, _passing_observations(subset))
    assert report.gaps() == ()
    assert not report.is_complete()
    assert subset.scope_gaps() == (
        "interaction:I2",
        "interaction:I3",
        "interaction:I4",
        "interaction:I5",
        "structural:at_least_two_classes",
        "targeted:nonempty",
    )


def test_minimum_governed_families_have_no_scope_gaps() -> None:
    full = _matrix(
        tuple(f"i{index}__case" for index in range(1, 7)),
        ("structural__one_band", "structural__multiple"),
        ("mixed_regression",),
    )
    assert full.scope_gaps() == ()
    assert build_observation_report(full, _passing_observations(full)).is_complete()


def test_interaction_family_names_must_be_anchored_not_substrings() -> None:
    incomplete = _matrix(
        ("not_i1__example", "i2__case", "i3__case", "i4__case", "i5__case", "i6__case"),
        ("s1", "s2"),
        ("target",),
    )
    assert incomplete.scope_gaps() == ("interaction:I1",)


def test_success_count_above_required_repetitions_is_invalid() -> None:
    matrix = _matrix((), (), ())
    for item in (("base-00", 6), ("V3-8", 2)):
        with pytest.raises(ValueError, match="invalid successful repetition count"):
            matrix_gaps(matrix, (item,))
