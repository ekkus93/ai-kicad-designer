import pytest

from ai_kicad.m2_composition_closure_record import (
    LOCKED_TOOLCHAIN,
    ClosureRecord,
    EvidenceRoot,
    QualificationOutcome,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64


def _root(root_id: str = "qualification") -> EvidenceRoot:
    return EvidenceRoot(root_id, f"evidence/{root_id}", "governed evidence", DIGEST_F)


def test_complete_current_source_outcomes_are_pass_eligible() -> None:
    record = ClosureRecord(
        production_sha=DIGEST_A,
        qualification_sha=DIGEST_A,
        observer_manifest_sha=DIGEST_B,
        oracle_manifest_sha=DIGEST_C,
        source_manifest_sha=DIGEST_D,
        evidence_roots=(_root(),),
        qualification_outcomes=(
            QualificationOutcome("base-56x5", 280, 280),
            QualificationOutcome("V3-8-negative", 1, 1),
        ),
        native_render_inspection_count=56,
    )

    assert record.pass_eligible
    assert record.toolchain == LOCKED_TOOLCHAIN
    assert record.manifest_sha256() == record.manifest_sha256()


def test_incomplete_or_failed_outcome_prevents_pass_eligibility() -> None:
    incomplete = ClosureRecord(
        production_sha=DIGEST_A,
        qualification_sha=DIGEST_A,
        observer_manifest_sha=DIGEST_B,
        oracle_manifest_sha=DIGEST_C,
        source_manifest_sha=DIGEST_D,
        evidence_roots=(_root(),),
        qualification_outcomes=(QualificationOutcome("base-56x5", 280, 279),),
        native_render_inspection_count=56,
    )
    failed = ClosureRecord(
        production_sha=DIGEST_A,
        qualification_sha=DIGEST_A,
        observer_manifest_sha=DIGEST_B,
        oracle_manifest_sha=DIGEST_C,
        source_manifest_sha=DIGEST_D,
        evidence_roots=(_root(),),
        qualification_outcomes=(QualificationOutcome("base-56x5", 280, 279, 1),),
        native_render_inspection_count=56,
    )

    assert not incomplete.pass_eligible
    assert not failed.pass_eligible


def test_record_rejects_stale_or_unsafe_evidence_sources() -> None:
    with pytest.raises(ValueError, match="locked KiCad"):
        ClosureRecord(
            production_sha=DIGEST_A,
            qualification_sha=DIGEST_A,
            observer_manifest_sha=DIGEST_B,
            oracle_manifest_sha=DIGEST_C,
            source_manifest_sha=DIGEST_D,
            evidence_roots=(_root(),),
            qualification_outcomes=(QualificationOutcome("base", 1, 1),),
            native_render_inspection_count=1,
            toolchain="KiCad 9.0.0",
        )
    with pytest.raises(ValueError, match=".local"):
        EvidenceRoot("bad", ".local/evidence", "private scratch", DIGEST_E)


def test_canonical_json_is_order_deterministic() -> None:
    first = ClosureRecord(
        production_sha=DIGEST_A,
        qualification_sha=DIGEST_A,
        observer_manifest_sha=DIGEST_B,
        oracle_manifest_sha=DIGEST_C,
        source_manifest_sha=DIGEST_D,
        evidence_roots=(_root("z"), _root("a")),
        qualification_outcomes=(
            QualificationOutcome("targeted", 5, 5),
            QualificationOutcome("base", 280, 280),
        ),
        native_render_inspection_count=57,
    )
    second = ClosureRecord(
        production_sha=DIGEST_A,
        qualification_sha=DIGEST_A,
        observer_manifest_sha=DIGEST_B,
        oracle_manifest_sha=DIGEST_C,
        source_manifest_sha=DIGEST_D,
        evidence_roots=(_root("a"), _root("z")),
        qualification_outcomes=(
            QualificationOutcome("base", 280, 280),
            QualificationOutcome("targeted", 5, 5),
        ),
        native_render_inspection_count=57,
    )

    assert first.canonical_json() == second.canonical_json()


def test_duplicate_root_or_family_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate evidence root"):
        ClosureRecord(
            production_sha=DIGEST_A,
            qualification_sha=DIGEST_A,
            observer_manifest_sha=DIGEST_B,
            oracle_manifest_sha=DIGEST_C,
            source_manifest_sha=DIGEST_D,
            evidence_roots=(_root("same"), _root("same")),
            qualification_outcomes=(QualificationOutcome("base", 1, 1),),
            native_render_inspection_count=1,
        )
    with pytest.raises(ValueError, match="duplicate qualification family"):
        ClosureRecord(
            production_sha=DIGEST_A,
            qualification_sha=DIGEST_A,
            observer_manifest_sha=DIGEST_B,
            oracle_manifest_sha=DIGEST_C,
            source_manifest_sha=DIGEST_D,
            evidence_roots=(_root(),),
            qualification_outcomes=(
                QualificationOutcome("base", 1, 1),
                QualificationOutcome("base", 1, 1),
            ),
            native_render_inspection_count=1,
        )
