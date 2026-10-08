"""Deterministic qualification matrix for human-readable M2h2 composition.

This module describes required current-source qualification runs.  It does not
claim a PASS; it records the exact matrix shape needed before final closure.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

LOCKED_KICAD_VERSION = "KiCad 10.0.6"
REQUIRED_REPETITIONS = 5
POSITIVE_BASE_CASE_COUNT = 56


@dataclass(frozen=True)
class QualificationCase:
    case_id: str
    family: str
    repetitions: int = REQUIRED_REPETITIONS
    requires_native_kicad: bool = True
    requires_composition_observer: bool = True


@dataclass(frozen=True)
class QualificationMatrix:
    source_sha: str
    locked_toolchain: str
    base_cases: tuple[QualificationCase, ...]
    interaction_cases: tuple[QualificationCase, ...]
    structural_cases: tuple[QualificationCase, ...]
    targeted_composition_cases: tuple[QualificationCase, ...]
    preserved_negative_cases: tuple[QualificationCase, ...]

    def total_required_runs(self) -> int:
        cases = (
            self.base_cases
            + self.interaction_cases
            + self.structural_cases
            + self.targeted_composition_cases
            + self.preserved_negative_cases
        )
        return sum(case.repetitions for case in cases)

    def canonical_json(self) -> str:
        return json.dumps(_matrix_dict(self), sort_keys=True, separators=(",", ":"))


def build_required_matrix(
    *,
    source_sha: str,
    base_case_ids: tuple[str, ...],
    interaction_case_ids: tuple[str, ...],
    structural_case_ids: tuple[str, ...],
    targeted_case_ids: tuple[str, ...],
) -> QualificationMatrix:
    """Build the governed final-qualification run matrix."""
    if len(base_case_ids) != POSITIVE_BASE_CASE_COUNT:
        raise ValueError("expected exactly 56 positive M2h2 base cases")
    return QualificationMatrix(
        source_sha=source_sha,
        locked_toolchain=LOCKED_KICAD_VERSION,
        base_cases=_cases("base_positive", base_case_ids),
        interaction_cases=_cases("interaction", interaction_case_ids),
        structural_cases=_cases("structural", structural_case_ids),
        targeted_composition_cases=_cases("targeted_composition", targeted_case_ids),
        preserved_negative_cases=(
            QualificationCase(
                "V3-8",
                "preserved_negative",
                repetitions=1,
                requires_native_kicad=True,
                requires_composition_observer=False,
            ),
        ),
    )


def matrix_gaps(
    matrix: QualificationMatrix,
    observed_successes: tuple[tuple[str, int], ...],
) -> tuple[tuple[str, int, int], ...]:
    """Return cases whose observed successful repetitions do not satisfy the matrix."""
    observed = dict(observed_successes)
    gaps: list[tuple[str, int, int]] = []
    for case in _all_cases(matrix):
        actual = observed.get(case.case_id, 0)
        if actual < case.repetitions:
            gaps.append((case.case_id, case.repetitions, actual))
    return tuple(gaps)


def _cases(family: str, case_ids: tuple[str, ...]) -> tuple[QualificationCase, ...]:
    return tuple(QualificationCase(case_id, family) for case_id in sorted(case_ids))


def _all_cases(matrix: QualificationMatrix) -> tuple[QualificationCase, ...]:
    return (
        matrix.base_cases
        + matrix.interaction_cases
        + matrix.structural_cases
        + matrix.targeted_composition_cases
        + matrix.preserved_negative_cases
    )


def _matrix_dict(matrix: QualificationMatrix) -> dict[str, object]:
    return {
        "source_sha": matrix.source_sha,
        "locked_toolchain": matrix.locked_toolchain,
        "base_cases": [case.__dict__ for case in matrix.base_cases],
        "interaction_cases": [case.__dict__ for case in matrix.interaction_cases],
        "structural_cases": [case.__dict__ for case in matrix.structural_cases],
        "targeted_composition_cases": [case.__dict__ for case in matrix.targeted_composition_cases],
        "preserved_negative_cases": [case.__dict__ for case in matrix.preserved_negative_cases],
    }
