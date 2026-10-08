"""Observed-run checks for final M2h2 composition qualification.

The qualification matrix defines what must be run.  This module validates the
observed current-source outcomes that are allowed to satisfy that matrix.
Pending, skipped, wrong-source, wrong-toolchain, or failed observations are not
counted as successful qualification evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .m2_composition_qualification_matrix import (
    LOCKED_KICAD_VERSION,
    QualificationMatrix,
    matrix_gaps,
)


@dataclass(frozen=True)
class QualificationObservation:
    case_id: str
    repetition: int
    source_sha: str
    toolchain: str
    status: str
    native_kicad: bool
    composition_observer_passed: bool
    electrical_passed: bool
    serialized_scene_verified: bool

    def counts_as_success(self, matrix: QualificationMatrix) -> bool:
        case = _case_by_id(matrix).get(self.case_id)
        if case is None:
            return False
        if self.source_sha != matrix.source_sha:
            return False
        if self.toolchain != LOCKED_KICAD_VERSION or self.toolchain != matrix.locked_toolchain:
            return False
        if self.status != "passed":
            return False
        if self.repetition < 1 or self.repetition > case.repetitions:
            return False
        if case.requires_native_kicad and not self.native_kicad:
            return False
        if case.requires_composition_observer and not self.composition_observer_passed:
            return False
        return self.electrical_passed and self.serialized_scene_verified


@dataclass(frozen=True)
class QualificationObservationReport:
    matrix: QualificationMatrix
    observations: tuple[QualificationObservation, ...]

    def successful_repetitions(self) -> tuple[tuple[str, int], ...]:
        counted: dict[str, set[int]] = {}
        for observation in self.observations:
            if observation.counts_as_success(self.matrix):
                counted.setdefault(observation.case_id, set()).add(observation.repetition)
        return tuple((case_id, len(repetitions)) for case_id, repetitions in sorted(counted.items()))

    def gaps(self) -> tuple[tuple[str, int, int], ...]:
        return matrix_gaps(self.matrix, self.successful_repetitions())

    def rejected_observation_count(self) -> int:
        return sum(
            1
            for observation in self.observations
            if not observation.counts_as_success(self.matrix)
        )

    def is_complete(self) -> bool:
        return not self.gaps()


def build_observation_report(
    matrix: QualificationMatrix,
    observations: tuple[QualificationObservation, ...],
) -> QualificationObservationReport:
    return QualificationObservationReport(matrix, observations)


def _case_by_id(matrix: QualificationMatrix) -> dict[str, object]:
    cases = (
        matrix.base_cases
        + matrix.interaction_cases
        + matrix.structural_cases
        + matrix.targeted_composition_cases
        + matrix.preserved_negative_cases
    )
    return {case.case_id: case for case in cases}
