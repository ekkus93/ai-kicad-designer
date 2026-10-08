import pytest

from ai_kicad.m2_composition_baseline_comparison import (
    CaseMetrics,
    compare_baseline,
)


def _case(
    case_id: str,
    *,
    defects: tuple[str, ...] = (),
    stage: float = 0,
    interface: float = 0,
    fragmentation: float = 0,
    edge: float = 0,
    routing: float = 0,
    repeated: float = 0,
) -> CaseMetrics:
    return CaseMetrics(
        case_id,
        defects,
        stage,
        interface,
        fragmentation,
        edge,
        routing,
        repeated,
    )


def test_hard_defect_must_be_fixed_per_case() -> None:
    before = (_case("i4__b2_mixed", defects=("wrong_frontier",)),)
    after = (_case("i4__b2_mixed", defects=("wrong_frontier",)),)

    result = compare_baseline(before, after)

    assert not result.hard_defect_free
    assert result.cases[0].unresolved_hard_defects == ("wrong_frontier",)


def test_new_hard_defect_cannot_be_hidden_by_metric_improvement() -> None:
    before = (_case("strong", edge=5, routing=5),)
    after = (
        _case(
            "strong",
            defects=("detached_output",),
            edge=1,
            routing=1,
        ),
    )

    result = compare_baseline(before, after)

    assert not result.hard_defect_free
    assert result.cases[0].improvements == ("edge_bias", "routing_excess")
    assert result.cases[0].new_hard_defects == ("detached_output",)


def test_metric_regression_is_reported_per_case_not_averaged_away() -> None:
    before = (
        _case("a", interface=10),
        _case("b", interface=1),
    )
    after = (
        _case("a", interface=0),
        _case("b", interface=2),
    )

    result = compare_baseline(before, after)

    assert not result.no_material_regressions
    b = next(case for case in result.cases if case.case_id == "b")
    assert b.regressions == ("interface_side_penalty",)


def test_all_composition_metric_families_are_compared() -> None:
    before = (_case("x", stage=2, interface=2, fragmentation=2, edge=2, routing=2, repeated=2),)
    after = (_case("x", stage=1, interface=1, fragmentation=1, edge=1, routing=1, repeated=1),)

    result = compare_baseline(before, after)

    assert result.hard_defect_free
    assert result.no_material_regressions
    assert result.cases[0].improvements == (
        "stage_order_reversal",
        "interface_side_penalty",
        "block_fragmentation",
        "edge_bias",
        "routing_excess",
        "repeated_alignment_variance",
    )


def test_case_sets_must_match_exactly() -> None:
    with pytest.raises(ValueError, match="case sets"):
        compare_baseline((_case("a"),), (_case("b"),))


def test_duplicate_case_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate case id"):
        compare_baseline((_case("a"), _case("a")), (_case("a"),))


def test_empty_comparison_cannot_be_reported_as_defect_free() -> None:
    with pytest.raises(ValueError, match="non-empty case evidence"):
        compare_baseline((), ())


@pytest.mark.parametrize("invalid", (float("nan"), float("inf"), -float("inf")))
def test_non_finite_metrics_cannot_hide_comparative_regressions(invalid: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        compare_baseline((_case("a", routing=3),), (_case("a", routing=invalid),))


@pytest.mark.parametrize("epsilon", (-1.0, float("nan"), float("inf")))
def test_invalid_regression_epsilon_is_rejected(epsilon: float) -> None:
    with pytest.raises(ValueError, match="comparison epsilon"):
        compare_baseline((_case("a"),), (_case("a"),), epsilon=epsilon)
