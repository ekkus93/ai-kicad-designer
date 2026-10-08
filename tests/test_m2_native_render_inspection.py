from ai_kicad import m2_native_render_inspection as inspection


def test_complete_inspection_requires_every_visual_assertion() -> None:
    artifact = inspection.RenderArtifact("case-a", "feedback", "renders/a.svg", "1" * 64)
    record = inspection.build_inspection(
        artifact,
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS,
    )

    assert record.is_complete()
    assert record.hard_visual_defects() == ()
    assert record.user_approval is False


def test_missing_assertion_prevents_completion() -> None:
    artifact = inspection.RenderArtifact("case-b", "branch", "renders/b.svg", "2" * 64)
    record = inspection.build_inspection(
        artifact,
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS[:-1],
    )

    assert not record.is_complete()


def test_failed_assertion_is_a_hard_visual_defect() -> None:
    artifact = inspection.RenderArtifact(
        "case-c", "shared-rail", "renders/c.svg", "3" * 64
    )
    record = inspection.build_inspection(
        artifact,
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS,
        failed_assertions=(
            (
                "power_reference_subordinate_and_coherent",
                "supply rail dominates primary signal row",
            ),
        ),
    )

    defects = record.hard_visual_defects()
    assert not record.is_complete()
    assert defects[0].assertion_id == "power_reference_subordinate_and_coherent"
    assert "dominates" in defects[0].witness


def test_archive_reports_missing_required_families_and_failing_cases() -> None:
    complete = inspection.build_inspection(
        inspection.RenderArtifact("case-d", "feedback", "renders/d.svg", "4" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS,
    )
    incomplete = inspection.build_inspection(
        inspection.RenderArtifact("case-e", "long-field", "renders/e.svg", "5" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS[:-1],
    )
    archive = inspection.InspectionArchive("a" * 40, (incomplete, complete))

    assert archive.missing_required_families(("feedback", "branch", "long-field")) == (
        "branch",
    )
    assert archive.failing_cases() == ("case-e",)


def test_archive_json_is_deterministic_by_case_and_path() -> None:
    first = inspection.build_inspection(
        inspection.RenderArtifact("z", "branch", "renders/z.svg", "6" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS,
    )
    second = inspection.build_inspection(
        inspection.RenderArtifact("a", "feedback", "renders/a.svg", "7" * 64),
        inspector="agent-engineering-inspection",
        passed_assertions=inspection.REQUIRED_ASSERTIONS,
    )

    assert inspection.InspectionArchive("b" * 40, (first, second)).canonical_json() == (
        inspection.InspectionArchive("b" * 40, (second, first)).canonical_json()
    )
