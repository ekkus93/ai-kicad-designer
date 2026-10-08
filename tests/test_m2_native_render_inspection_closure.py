from dataclasses import replace

from ai_kicad.m2_native_render_inspection import (
    REQUIRED_ASSERTIONS,
    InspectionArchive,
    RenderArtifact,
    build_inspection,
)
from ai_kicad.m2_native_render_inspection_closure import inspect_native_render_closure


def _complete(case_id: str, family: str):
    return build_inspection(
        RenderArtifact(case_id, family, f"renders/{case_id}.svg", "a" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=REQUIRED_ASSERTIONS,
    )


def test_complete_required_families_and_cases_are_pass_eligible() -> None:
    archive = InspectionArchive(
        "1" * 40,
        (
            _complete("case-feedback", "feedback"),
            _complete("case-branch", "branch"),
        ),
    )

    closure = inspect_native_render_closure(
        archive,
        expected_source_sha="1" * 40,
        required_families=("branch", "feedback"),
        required_case_ids=("case-branch", "case-feedback"),
    )

    assert closure.is_pass_eligible()
    assert closure.missing_families == ()
    assert closure.missing_cases == ()


def test_missing_family_and_case_prevent_pass_eligibility() -> None:
    archive = InspectionArchive("1" * 40, (_complete("case-feedback", "feedback"),))

    closure = inspect_native_render_closure(
        archive,
        expected_source_sha="1" * 40,
        required_families=("branch", "feedback"),
        required_case_ids=("case-branch", "case-feedback"),
    )

    assert not closure.is_pass_eligible()
    assert closure.missing_families == ("branch",)
    assert closure.missing_cases == ("case-branch",)


def test_source_mismatch_and_hard_visual_defect_prevent_pass() -> None:
    failed = build_inspection(
        RenderArtifact("case-shared-rail", "shared-rail", "renders/rail.svg", "b" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=REQUIRED_ASSERTIONS[:-1],
        failed_assertions=(("no_unmodelled_computer_generated_defect", "wire label overlap"),),
    )
    archive = InspectionArchive("2" * 40, (failed,))

    closure = inspect_native_render_closure(
        archive,
        expected_source_sha="1" * 40,
        required_families=("shared-rail",),
        required_case_ids=("case-shared-rail",),
    )

    assert not closure.is_pass_eligible()
    assert closure.source_mismatch
    assert closure.failing_cases == ("case-shared-rail",)


def test_user_approval_is_not_accepted_as_engineering_inspection() -> None:
    user_approved = replace(_complete("case-long-field", "long-field"), user_approval=True)
    archive = InspectionArchive("1" * 40, (user_approved,))

    closure = inspect_native_render_closure(
        archive,
        expected_source_sha="1" * 40,
        required_families=("long-field",),
        required_case_ids=("case-long-field",),
    )

    assert not closure.is_pass_eligible()
    assert closure.user_approval_cases == ("case-long-field",)
