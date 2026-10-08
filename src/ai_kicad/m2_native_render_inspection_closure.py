"""Closure gate for native-render engineering inspection evidence.

The native-render archive is a hard final-closure input.  This module keeps the
closure decision separate from ad-hoc visual review by requiring an exact source
SHA, explicit governed family coverage, explicit case coverage when supplied,
engineering inspection records rather than user approval, and zero hard visual
defects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .m2_native_render_inspection import InspectionArchive


@dataclass(frozen=True)
class NativeRenderInspectionClosure:
    source_sha: str
    missing_families: tuple[str, ...]
    missing_cases: tuple[str, ...]
    failing_cases: tuple[str, ...]
    user_approval_cases: tuple[str, ...]
    source_mismatch: bool

    def is_pass_eligible(self) -> bool:
        return not (
            self.source_mismatch
            or self.missing_families
            or self.missing_cases
            or self.failing_cases
            or self.user_approval_cases
        )


def inspect_native_render_closure(
    archive: InspectionArchive,
    *,
    expected_source_sha: str,
    required_families: tuple[str, ...],
    required_case_ids: tuple[str, ...] = (),
) -> NativeRenderInspectionClosure:
    """Validate final native-render inspection coverage without user approval.

    User approval is intentionally not accepted as a substitute for engineering
    inspection evidence.  Any record marked as user approval keeps the archive
    out of PASS eligibility even if all visual assertions are present.
    """
    inspected_cases = {inspection.artifact.case_id for inspection in archive.inspections}
    source_mismatch = archive.source_sha != expected_source_sha
    user_approval_cases = tuple(
        sorted(
            inspection.artifact.case_id
            for inspection in archive.inspections
            if inspection.user_approval
        )
    )
    return NativeRenderInspectionClosure(
        source_sha=archive.source_sha,
        missing_families=archive.missing_required_families(required_families),
        missing_cases=tuple(
            case_id for case_id in sorted(required_case_ids) if case_id not in inspected_cases
        ),
        failing_cases=archive.failing_cases(),
        user_approval_cases=user_approval_cases,
        source_mismatch=source_mismatch,
    )
