"""Per-case comparative closure for M2h2 composition baselines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseMetrics:
    case_id: str
    hard_defects: tuple[str, ...]
    stage_order_reversal: float
    interface_side_penalty: float
    block_fragmentation: float
    edge_bias: float
    routing_excess: float
    repeated_alignment_variance: float


@dataclass(frozen=True)
class CaseComparison:
    case_id: str
    unresolved_hard_defects: tuple[str, ...]
    new_hard_defects: tuple[str, ...]
    regressions: tuple[str, ...]
    improvements: tuple[str, ...]


@dataclass(frozen=True)
class BaselineComparison:
    cases: tuple[CaseComparison, ...]
    hard_defect_free: bool
    no_material_regressions: bool


_METRICS = (
    "stage_order_reversal",
    "interface_side_penalty",
    "block_fragmentation",
    "edge_bias",
    "routing_excess",
    "repeated_alignment_variance",
)


def compare_baseline(
    before: tuple[CaseMetrics, ...],
    after: tuple[CaseMetrics, ...],
    *,
    epsilon: float = 1e-9,
) -> BaselineComparison:
    """Compare exact cases without allowing aggregate scores to mask defects."""
    before_by_id = _unique(before)
    after_by_id = _unique(after)
    if before_by_id.keys() != after_by_id.keys():
        raise ValueError("before/after case sets must match exactly")

    comparisons: list[CaseComparison] = []
    for case_id in sorted(before_by_id):
        old = before_by_id[case_id]
        new = after_by_id[case_id]
        unresolved = tuple(sorted(set(old.hard_defects) & set(new.hard_defects)))
        introduced = tuple(sorted(set(new.hard_defects) - set(old.hard_defects)))
        regressions: list[str] = []
        improvements: list[str] = []
        for name in _METRICS:
            old_value = getattr(old, name)
            new_value = getattr(new, name)
            if new_value > old_value + epsilon:
                regressions.append(name)
            elif new_value < old_value - epsilon:
                improvements.append(name)
        comparisons.append(
            CaseComparison(
                case_id=case_id,
                unresolved_hard_defects=unresolved,
                new_hard_defects=introduced,
                regressions=tuple(regressions),
                improvements=tuple(improvements),
            )
        )

    return BaselineComparison(
        cases=tuple(comparisons),
        hard_defect_free=all(
            not case.unresolved_hard_defects and not case.new_hard_defects
            for case in comparisons
        ),
        no_material_regressions=all(not case.regressions for case in comparisons),
    )


def _unique(cases: tuple[CaseMetrics, ...]) -> dict[str, CaseMetrics]:
    result: dict[str, CaseMetrics] = {}
    for case in cases:
        if case.case_id in result:
            raise ValueError(f"duplicate case id: {case.case_id}")
        result[case.case_id] = case
    return result
