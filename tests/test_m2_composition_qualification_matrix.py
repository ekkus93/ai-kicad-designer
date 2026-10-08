import pytest

from ai_kicad import m2_composition_qualification_matrix as matrix


def test_required_matrix_requires_exactly_56_base_cases() -> None:
    with pytest.raises(ValueError, match="56 positive"):
        matrix.build_required_matrix(
            source_sha="a" * 40,
            base_case_ids=("only-one",),
            interaction_case_ids=(),
            structural_case_ids=(),
            targeted_case_ids=(),
        )


def test_required_matrix_records_locked_toolchain_and_repetition_policy() -> None:
    base_cases = tuple(f"base-{index:02d}" for index in range(56))
    result = matrix.build_required_matrix(
        source_sha="b" * 40,
        base_case_ids=base_cases,
        interaction_case_ids=("I1", "I6"),
        structural_case_ids=("one-band", "multi-band"),
        targeted_case_ids=("i4__b2_mixed", "feedback-local"),
    )

    assert result.locked_toolchain == "KiCad 10.0.6"
    assert len(result.base_cases) == 56
    assert all(case.repetitions == 5 for case in result.base_cases)
    assert result.preserved_negative_cases[0].case_id == "V3-8"
    assert result.preserved_negative_cases[0].repetitions == 1
    assert result.preserved_negative_cases[0].requires_composition_observer is False


def test_total_required_runs_includes_all_case_families() -> None:
    result = matrix.build_required_matrix(
        source_sha="c" * 40,
        base_case_ids=tuple(f"base-{index:02d}" for index in range(56)),
        interaction_case_ids=("I1", "I2", "I3"),
        structural_case_ids=("s1",),
        targeted_case_ids=("t1", "t2"),
    )

    assert result.total_required_runs() == (56 * 5) + (3 * 5) + (1 * 5) + (2 * 5) + 1


def test_matrix_gaps_report_missing_repetitions_exactly() -> None:
    result = matrix.build_required_matrix(
        source_sha="d" * 40,
        base_case_ids=tuple(f"base-{index:02d}" for index in range(56)),
        interaction_case_ids=("I1",),
        structural_case_ids=(),
        targeted_case_ids=(),
    )
    observed = tuple((case.case_id, case.repetitions) for case in result.base_cases)

    gaps = matrix.matrix_gaps(result, observed)

    assert ("I1", 5, 0) in gaps
    assert ("V3-8", 1, 0) in gaps
    assert all(not case_id.startswith("base-") for case_id, _, _ in gaps)


def test_canonical_matrix_json_is_order_deterministic() -> None:
    base_cases = tuple(f"base-{index:02d}" for index in reversed(range(56)))
    first = matrix.build_required_matrix(
        source_sha="e" * 40,
        base_case_ids=base_cases,
        interaction_case_ids=("I6", "I1"),
        structural_case_ids=("z", "a"),
        targeted_case_ids=("t2", "t1"),
    )
    second = matrix.build_required_matrix(
        source_sha="e" * 40,
        base_case_ids=tuple(sorted(base_cases)),
        interaction_case_ids=("I1", "I6"),
        structural_case_ids=("a", "z"),
        targeted_case_ids=("t1", "t2"),
    )

    assert first.canonical_json() == second.canonical_json()


def test_matrix_rejects_duplicate_positive_and_cross_family_case_ids() -> None:
    positive = tuple(f"base-{index:02d}" for index in range(56))
    with pytest.raises(ValueError, match="unique across all families"):
        matrix.build_required_matrix(
            source_sha="a" * 40,
            base_case_ids=(positive[0], positive[0], *positive[2:]),
            interaction_case_ids=(),
            structural_case_ids=(),
            targeted_case_ids=(),
        )
    with pytest.raises(ValueError, match="unique across all families"):
        matrix.build_required_matrix(
            source_sha="a" * 40,
            base_case_ids=positive,
            interaction_case_ids=(positive[0],),
            structural_case_ids=(),
            targeted_case_ids=(),
        )


def test_matrix_rejects_invalid_case_identifiers_and_source_sha() -> None:
    positive = tuple(f"base-{index:02d}" for index in range(56))
    with pytest.raises(ValueError, match="source_sha"):
        matrix.build_required_matrix(
            source_sha="bad",
            base_case_ids=positive,
            interaction_case_ids=(),
            structural_case_ids=(),
            targeted_case_ids=(),
        )
    with pytest.raises(ValueError, match="non-empty"):
        matrix.build_required_matrix(
            source_sha="a" * 40,
            base_case_ids=positive,
            interaction_case_ids=("",),
            structural_case_ids=(),
            targeted_case_ids=(),
        )


def test_matrix_gaps_reject_ambiguous_unknown_and_negative_success_counts() -> None:
    result = matrix.build_required_matrix(
        source_sha="a" * 40,
        base_case_ids=tuple(f"base-{index:02d}" for index in range(56)),
        interaction_case_ids=(),
        structural_case_ids=(),
        targeted_case_ids=(),
    )
    with pytest.raises(ValueError, match="duplicate qualification result"):
        matrix.matrix_gaps(result, (("base-00", 5), ("base-00", 4)))
    with pytest.raises(ValueError, match="unknown qualification case"):
        matrix.matrix_gaps(result, (("fabricated-case", 5),))
    with pytest.raises(ValueError, match="invalid successful repetition"):
        matrix.matrix_gaps(result, (("base-00", -1),))
    with pytest.raises(ValueError, match="invalid successful repetition"):
        matrix.matrix_gaps(result, (("base-00", True),))
