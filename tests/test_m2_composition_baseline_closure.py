import pytest

from ai_kicad.m2_composition_baseline_closure import (
    RequiredCaseImprovement,
    build_baseline_closure_record,
)
from ai_kicad.m2_composition_baseline_comparison import CaseMetrics, compare_baseline

_SHA = "a" * 40
_ROOT = "b" * 64
_AFTER = "c" * 64


def _case(
    case_id: str,
    *,
    defects: tuple[str, ...] = (),
    interface: float = 0,
    edge: float = 0,
    routing: float = 0,
) -> CaseMetrics:
    return CaseMetrics(
        case_id,
        defects,
        stage_order_reversal=0,
        interface_side_penalty=interface,
        block_fragmentation=0,
        edge_bias=edge,
        routing_excess=routing,
        repeated_alignment_variance=0,
    )


def test_closure_requires_per_case_hard_defect_resolution() -> None:
    comparison = compare_baseline(
        (_case("strong"), _case("i4__b2_mixed", defects=("wrong_frontier",))),
        (_case("strong", interface=-5), _case("i4__b2_mixed", defects=("wrong_frontier",))),
    )

    record = build_baseline_closure_record(
        source_sha=_SHA,
        baseline_evidence_root=_ROOT,
        after_evidence_root=_AFTER,
        comparison=comparison,
        required_improvements=(RequiredCaseImprovement("strong", "interface_side_penalty"),),
    )

    assert not record.eligible_for_closure
    assert record.failing_cases == ("i4__b2_mixed",)


def test_required_targeted_improvement_must_be_present() -> None:
    comparison = compare_baseline(
        (_case("i4__b2_mixed", interface=5, edge=5),),
        (_case("i4__b2_mixed", interface=5, edge=1),),
    )

    record = build_baseline_closure_record(
        source_sha=_SHA,
        baseline_evidence_root=_ROOT,
        after_evidence_root=_AFTER,
        comparison=comparison,
        required_improvements=(
            RequiredCaseImprovement("i4__b2_mixed", "interface_side_penalty"),
        ),
    )

    assert not record.eligible_for_closure
    assert record.missing_required_improvements == (
        RequiredCaseImprovement("i4__b2_mixed", "interface_side_penalty"),
    )


def test_clean_per_case_closure_is_eligible_and_deterministic() -> None:
    comparison = compare_baseline(
        (_case("i4__b2_mixed", interface=5, edge=5, routing=3),),
        (_case("i4__b2_mixed", interface=0, edge=1, routing=1),),
    )

    first = build_baseline_closure_record(
        source_sha=_SHA,
        baseline_evidence_root=_ROOT,
        after_evidence_root=_AFTER,
        comparison=comparison,
        required_improvements=(
            RequiredCaseImprovement("i4__b2_mixed", "interface_side_penalty"),
        ),
    )
    second = build_baseline_closure_record(
        source_sha=_SHA,
        baseline_evidence_root=_ROOT,
        after_evidence_root=_AFTER,
        comparison=comparison,
        required_improvements=(
            RequiredCaseImprovement("i4__b2_mixed", "interface_side_penalty"),
        ),
    )

    assert first.eligible_for_closure
    assert first.canonical_json() == second.canonical_json()


def test_source_and_evidence_roots_are_validated() -> None:
    comparison = compare_baseline((_case("a"),), (_case("a"),))

    with pytest.raises(ValueError, match="source_sha"):
        build_baseline_closure_record(
            source_sha="not-a-sha",
            baseline_evidence_root=_ROOT,
            after_evidence_root=_AFTER,
            comparison=comparison,
            required_improvements=(),
        )
