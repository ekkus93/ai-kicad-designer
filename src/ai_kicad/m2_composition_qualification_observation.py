"""Observed-run checks for final M2h2 composition qualification.

The qualification matrix defines what must be run.  This module validates the
observed current-source outcomes that are allowed to satisfy that matrix.
Pending, skipped, wrong-source, wrong-toolchain, or failed observations are not
counted as successful qualification evidence.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping

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
    rejection_witness: str | None = None

    def counts_as_success(self, matrix: QualificationMatrix) -> bool:
        case = _case_by_id(matrix).get(self.case_id)
        if case is None:
            return False
        if self.source_sha != matrix.source_sha:
            return False
        if self.toolchain != LOCKED_KICAD_VERSION or self.toolchain != matrix.locked_toolchain:
            return False
        if self.repetition < 1 or self.repetition > case.repetitions:
            return False
        if case.requires_native_kicad and not self.native_kicad:
            return False
        if case.family == "preserved_negative":
            # Negative controls prove continued rejection, not acceptance.
            # A normal positive PASS, a failed CI job, or a missing artifact
            # cannot stand in for a witnessed expected rejection.
            return (
                self.status == "expected_rejection"
                and isinstance(self.rejection_witness, str)
                and bool(self.rejection_witness.strip())
                and not self.electrical_passed
                and not self.serialized_scene_verified
            )
        if self.status != "passed":
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


def observe_native_pin_composition(
    plan: SemanticPlan,
    design: Mapping,
    observed_schematic: Mapping,
) -> CompositionReport:
    """Measure semantic block centers from parsed native KiCad pin positions.

    This independent diagnostic never consumes the generator's composition JSON
    or candidate scores. Its terminal-only bounds are not full symbol/page
    envelopes, so utilization and whitespace remain preliminary diagnostics.
    """
    reference_by_component = {item["id"]: item["refdes"] for item in design["components"]}
    pins = observed_schematic["pin_positions"]
    positions: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for obligation in plan.terminals:
        component_id, pin = obligation.terminal
        refdes = reference_by_component.get(component_id)
        point = pins.get((refdes, pin))
        if point is not None:
            positions[obligation.owner].append((int(point[0]), int(point[1])))
    boxes = {
        block_id: (
            min(point[0] for point in points),
            min(point[1] for point in points),
            max(point[0] for point in points),
            max(point[1] for point in points),
        )
        for block_id, points in positions.items()
    }
    return observe_human_composition(plan, boxes)


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


def witnessed_invalid_build_rejection(
    *, returncode: int, failure: Mapping[str, object] | None, expected_input_sha256: str
) -> bool:
    """Accept a preserved negative only from a real invalid-design build witness.

    A nonzero process exit alone may mean missing tooling, infrastructure
    failure, or stale artifacts. The locked builder returns 2 for a typed
    InputError and writes a design-bound invalid failure report; tool failures
    return 4 and cannot demonstrate that the negative design was rejected.
    """
    if type(returncode) is not int or returncode != 2 or not isinstance(failure, Mapping):
        return False
    message = failure.get("message")
    failure_class = failure.get("failure_class")
    return (
        failure.get("status") == "invalid"
        and isinstance(expected_input_sha256, str)
        and len(expected_input_sha256) == 64
        and all(character in "0123456789abcdef" for character in expected_input_sha256)
        and failure.get("input_sha256") == expected_input_sha256
        and isinstance(message, str)
        and bool(message.strip())
        and isinstance(failure_class, str)
        and bool(failure_class.strip())
    )


def _case_by_id(matrix: QualificationMatrix) -> dict[str, object]:
    cases = (
        matrix.base_cases
        + matrix.interaction_cases
        + matrix.structural_cases
        + matrix.targeted_composition_cases
        + matrix.preserved_negative_cases
    )
    return {case.case_id: case for case in cases}
