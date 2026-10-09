"""Observed-run checks for final M2h2 composition qualification.

The qualification matrix defines what must be run.  This module validates the
observed current-source outcomes that are allowed to satisfy that matrix.
Pending, skipped, wrong-source, wrong-toolchain, or failed observations are not
counted as successful qualification evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .m2_composition_quality import (
    CompositionReport,
    block_envelopes_from_composition_evidence,
    observe_human_composition,
)
from .m2_composition_qualification_matrix import (
    LOCKED_KICAD_VERSION,
    QualificationMatrix,
    matrix_gaps,
)
from .m2_semantics import SemanticPlan


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
        return tuple(
            (case_id, len(repetitions)) for case_id, repetitions in sorted(counted.items())
        )

    def gaps(self) -> tuple[tuple[str, int, int], ...]:
        return matrix_gaps(self.matrix, self.successful_repetitions())

    def rejected_observation_count(self) -> int:
        return sum(
            1 for observation in self.observations if not observation.counts_as_success(self.matrix)
        )

    def is_complete(self) -> bool:
        return not self.gaps()


def build_observation_report(
    matrix: QualificationMatrix,
    observations: tuple[QualificationObservation, ...],
) -> QualificationObservationReport:
    return QualificationObservationReport(matrix, observations)


def observe_composition_evidence(
    plan: SemanticPlan,
    composition_evidence: dict,
) -> CompositionReport:
    """Run the independent human-composition observer over emitted evidence."""
    return observe_human_composition(
        plan,
        block_envelopes_from_composition_evidence(composition_evidence),
    )


def observe_composition_packing(plan: SemanticPlan, packing) -> CompositionReport:
    """Run the same observer over an independently selected measured packing."""
    envelopes: dict[str, tuple[int, int, int, int]] = {}
    for item in packing.fragments:
        block_id = item.fragment.block.id
        rect = item.content_envelope or item.envelope
        if block_id in envelopes:
            prior = envelopes[block_id]
            envelopes[block_id] = (
                min(prior[0], rect[0]),
                min(prior[1], rect[1]),
                max(prior[2], rect[2]),
                max(prior[3], rect[3]),
            )
        else:
            envelopes[block_id] = rect
    return observe_human_composition(plan, envelopes)


def _case_by_id(matrix: QualificationMatrix) -> dict[str, object]:
    cases = (
        matrix.base_cases
        + matrix.interaction_cases
        + matrix.structural_cases
        + matrix.targeted_composition_cases
        + matrix.preserved_negative_cases
    )
    return {case.case_id: case for case in cases}
