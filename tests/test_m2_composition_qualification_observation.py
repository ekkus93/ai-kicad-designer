from ai_kicad.m2_composition_qualification_matrix import (
    LOCKED_KICAD_VERSION,
    build_required_matrix,
)
from ai_kicad.m2_composition_qualification_observation import (
    QualificationObservation,
    build_observation_report,
)

SOURCE = "a" * 40
BASE_CASES = tuple(f"base-{index:02d}" for index in range(56))


def _matrix():
    return build_required_matrix(
        source_sha=SOURCE,
        base_case_ids=BASE_CASES,
        interaction_case_ids=("I1",),
        structural_case_ids=("one-band",),
        targeted_case_ids=("targeted",),
    )


def _observation(case_id: str, repetition: int, **overrides) -> QualificationObservation:
    values = {
        "case_id": case_id,
        "repetition": repetition,
        "source_sha": SOURCE,
        "toolchain": LOCKED_KICAD_VERSION,
        "status": "passed",
        "native_kicad": True,
        "composition_observer_passed": True,
        "electrical_passed": True,
        "serialized_scene_verified": True,
    }
    values.update(overrides)
    return QualificationObservation(**values)


def test_successful_repetitions_count_unique_passing_repetition_ids() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1),
        _observation("base-00", 1),
        _observation("base-00", 2),
        _observation("base-00", 3, status="failed"),
    )

    report = build_observation_report(matrix, observations)

    assert ("base-00", 2) in report.successful_repetitions()
    assert ("base-00", 5, 2) in report.gaps()
    assert report.rejected_observation_count() == 1


def test_wrong_source_wrong_toolchain_and_pending_runs_do_not_count() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1, source_sha="b" * 40),
        _observation("base-00", 2, toolchain="KiCad 9.0.0"),
        _observation("base-00", 3, status="queued"),
    )

    report = build_observation_report(matrix, observations)

    assert report.successful_repetitions() == ()
    assert ("base-00", 5, 0) in report.gaps()
    assert report.rejected_observation_count() == 3


def test_required_native_kicad_observer_electrical_and_serialization_gates() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1, native_kicad=False),
        _observation("base-00", 2, composition_observer_passed=False),
        _observation("base-00", 3, electrical_passed=False),
        _observation("base-00", 4, serialized_scene_verified=False),
        _observation("base-00", 5),
    )

    report = build_observation_report(matrix, observations)

    assert ("base-00", 1) in report.successful_repetitions()
    assert report.rejected_observation_count() == 4


def test_preserved_negative_does_not_require_composition_observer() -> None:
    matrix = _matrix()
    observation = _observation("V3-8", 1, composition_observer_passed=False)

    report = build_observation_report(matrix, (observation,))

    assert ("V3-8", 1) in report.successful_repetitions()
    assert all(case_id != "V3-8" for case_id, _, _ in report.gaps())


def test_unknown_case_and_out_of_range_repetition_are_rejected() -> None:
    matrix = _matrix()
    observations = (
        _observation("not-in-matrix", 1),
        _observation("base-00", 0),
        _observation("base-00", 6),
    )

    report = build_observation_report(matrix, observations)

    assert report.successful_repetitions() == ()
    assert report.rejected_observation_count() == 3
