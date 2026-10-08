"""Evidence gate for comparative M2h2 composition baseline closure.

This module intentionally does not compute visual metrics. It consumes the
independent per-case comparison and records whether a current-source baseline
closure claim is structurally eligible. Aggregate improvements cannot hide a
remaining hard defect, a new defect, or a per-case regression.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

from .m2_composition_baseline_comparison import BaselineComparison

_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class RequiredCaseImprovement:
    case_id: str
    metric: str


@dataclass(frozen=True)
class BaselineClosureRecord:
    source_sha: str
    baseline_evidence_root: str
    after_evidence_root: str
    comparison: BaselineComparison
    required_improvements: tuple[RequiredCaseImprovement, ...]
    missing_required_improvements: tuple[RequiredCaseImprovement, ...]
    failing_cases: tuple[str, ...]

    @property
    def eligible_for_closure(self) -> bool:
        return (
            bool(self.comparison.cases)
            and bool(self.required_improvements)
            and self.comparison.hard_defect_free
            and self.comparison.no_material_regressions
            and not self.missing_required_improvements
            and not self.failing_cases
        )

    def canonical_json(self) -> str:
        return json.dumps(_record_dict(self), sort_keys=True, separators=(",", ":"))


def build_baseline_closure_record(
    *,
    source_sha: str,
    baseline_evidence_root: str,
    after_evidence_root: str,
    comparison: BaselineComparison,
    required_improvements: tuple[RequiredCaseImprovement, ...],
) -> BaselineClosureRecord:
    """Build a deterministic closure record without claiming PASS prematurely."""
    for value, label in (
        (source_sha, "source_sha"),
        (baseline_evidence_root, "baseline_evidence_root"),
        (after_evidence_root, "after_evidence_root"),
    ):
        _require_sha256_like(value, label)
    if baseline_evidence_root == after_evidence_root:
        raise ValueError("baseline and final composition evidence roots must be distinct")
    by_case = {case.case_id: case for case in comparison.cases}
    missing = []
    for required in sorted(required_improvements, key=lambda item: (item.case_id, item.metric)):
        case = by_case.get(required.case_id)
        if case is None or required.metric not in case.improvements:
            missing.append(required)
    failing = tuple(
        case.case_id
        for case in comparison.cases
        if case.unresolved_hard_defects or case.new_hard_defects or case.regressions
    )
    return BaselineClosureRecord(
        source_sha=source_sha,
        baseline_evidence_root=baseline_evidence_root,
        after_evidence_root=after_evidence_root,
        comparison=comparison,
        required_improvements=tuple(
            sorted(required_improvements, key=lambda item: (item.case_id, item.metric))
        ),
        missing_required_improvements=tuple(missing),
        failing_cases=failing,
    )


def _require_sha256_like(value: str, label: str) -> None:
    required_length = 40 if label == "source_sha" else 64
    if len(value) != required_length or any(character not in _HEX for character in value):
        raise ValueError(f"{label} must be a lowercase {required_length}-character hex digest")


def _record_dict(record: BaselineClosureRecord) -> dict[str, object]:
    return {
        "source_sha": record.source_sha,
        "baseline_evidence_root": record.baseline_evidence_root,
        "after_evidence_root": record.after_evidence_root,
        "eligible_for_closure": record.eligible_for_closure,
        "hard_defect_free": record.comparison.hard_defect_free,
        "no_material_regressions": record.comparison.no_material_regressions,
        "required_improvements": [item.__dict__ for item in record.required_improvements],
        "missing_required_improvements": [
            item.__dict__ for item in record.missing_required_improvements
        ],
        "failing_cases": list(record.failing_cases),
        "cases": [
            case.__dict__ for case in sorted(record.comparison.cases, key=lambda item: item.case_id)
        ],
    }
