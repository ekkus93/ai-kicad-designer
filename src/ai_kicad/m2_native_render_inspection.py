"""Native-render engineering inspection records for M2h2 composition closure.

These records capture agent/engineering inspection evidence for native KiCad
renders.  They are not user approval records and do not replace observer gates.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

REQUIRED_ASSERTIONS = (
    "primary_signal_entry_obvious",
    "primary_signal_progression_obvious",
    "final_outputs_associated_with_final_producers",
    "branch_source_attribution_obvious",
    "feedback_recognizable",
    "power_reference_subordinate_and_coherent",
    "support_ownership_obvious",
    "repeated_structures_consistent",
    "compactness_appropriate",
    "whitespace_intentional",
    "fields_and_labels_readable",
    "no_unmodelled_computer_generated_defect",
)


@dataclass(frozen=True)
class RenderArtifact:
    case_id: str
    family: str
    path: str
    sha256: str


@dataclass(frozen=True)
class InspectionAssertion:
    assertion_id: str
    passed: bool
    witness: str


@dataclass(frozen=True)
class NativeRenderInspection:
    artifact: RenderArtifact
    inspector: str
    assertions: tuple[InspectionAssertion, ...]
    user_approval: bool = False

    def hard_visual_defects(self) -> tuple[InspectionAssertion, ...]:
        return tuple(assertion for assertion in self.assertions if not assertion.passed)

    def is_complete(self) -> bool:
        assertion_ids = {assertion.assertion_id for assertion in self.assertions}
        return set(REQUIRED_ASSERTIONS) <= assertion_ids and not self.hard_visual_defects()


@dataclass(frozen=True)
class InspectionArchive:
    source_sha: str
    inspections: tuple[NativeRenderInspection, ...]

    def missing_required_families(
        self,
        required_families: tuple[str, ...],
    ) -> tuple[str, ...]:
        inspected = {inspection.artifact.family for inspection in self.inspections}
        return tuple(family for family in sorted(required_families) if family not in inspected)

    def failing_cases(self) -> tuple[str, ...]:
        return tuple(
            inspection.artifact.case_id
            for inspection in self.inspections
            if not inspection.is_complete()
        )

    def canonical_json(self) -> str:
        return json.dumps(_archive_dict(self), sort_keys=True, separators=(",", ":"))


def build_inspection(
    artifact: RenderArtifact,
    *,
    inspector: str,
    passed_assertions: tuple[str, ...],
    failed_assertions: tuple[tuple[str, str], ...] = (),
) -> NativeRenderInspection:
    """Build one inspection record from explicit passed/failed assertion IDs."""
    passed = tuple(
        InspectionAssertion(assertion_id, True, "explicit engineering inspection")
        for assertion_id in sorted(passed_assertions)
    )
    failed = tuple(
        InspectionAssertion(assertion_id, False, witness)
        for assertion_id, witness in sorted(failed_assertions)
    )
    return NativeRenderInspection(
        artifact=artifact,
        inspector=inspector,
        assertions=passed + failed,
        user_approval=False,
    )


def _archive_dict(archive: InspectionArchive) -> dict[str, object]:
    return {
        "source_sha": archive.source_sha,
        "inspections": [
            {
                "artifact": inspection.artifact.__dict__,
                "inspector": inspection.inspector,
                "user_approval": inspection.user_approval,
                "assertions": [assertion.__dict__ for assertion in inspection.assertions],
            }
            for inspection in sorted(
                archive.inspections,
                key=lambda item: (item.artifact.case_id, item.artifact.path),
            )
        ],
    }
