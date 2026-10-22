"""Contract tests for revision-bound pivot evidence."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.evidence import EvidenceRecord, EvidenceStatus

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "fixtures/pivot/evidence_record.schema.json"


def passing_record() -> dict:
    return {
        "schema_version": "pivot-evidence.v1",
        "evidence_id": "G-003-contract-test",
        "task_id": "G-003",
        "recorded_at_utc": datetime(2026, 10, 21, tzinfo=timezone.utc),
        "source_commit": "f14a02c3140fd455ded8391ea65b8416b5d6e170",
        "revision_kind": "git_commit",
        "revision_id": "f14a02c3140fd455ded8391ea65b8416b5d6e170",
        "action": {
            "summary": "Validate an evidence contract record",
            "command": "pytest tests/pivot/test_evidence.py",
            "backend": "pytest",
            "backend_version": "9.0.2",
            "toolchain": "Python 3.12.12",
        },
        "status": EvidenceStatus.PASS,
        "artifacts": [
            {
                "path": "fixtures/pivot/evidence_record.schema.json",
                "sha256": "a" * 64,
                "media_type": "application/schema+json",
                "role": "schema",
            }
        ],
        "checks": [
            {
                "check_id": "contract-round-trip",
                "status": EvidenceStatus.PASS,
                "summary": "The record validates and round-trips without data loss.",
                "evidence_paths": ["fixtures/pivot/evidence_record.schema.json"],
                "independent": True,
            }
        ],
        "ci_links": [],
        "blockers": [],
        "notes": [],
    }


def test_evidence_schema_matches_typed_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    expected = EvidenceRecord.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/pivot-evidence.v1.json"
    assert schema == expected
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_valid_evidence_round_trips() -> None:
    original = passing_record()
    record = EvidenceRecord.model_validate(original)
    restored = EvidenceRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.status is EvidenceStatus.PASS


def test_pass_without_a_verified_check_is_rejected() -> None:
    record = passing_record()
    record["checks"] = []
    with pytest.raises(ValidationError, match="independent passing verification check"):
        EvidenceRecord.model_validate(record)


def test_pass_from_only_a_producer_check_is_rejected() -> None:
    record = passing_record()
    record["checks"][0]["independent"] = False
    with pytest.raises(ValidationError, match="independent passing verification check"):
        EvidenceRecord.model_validate(record)


def test_check_cannot_cite_an_unregistered_artifact() -> None:
    record = passing_record()
    record["checks"][0]["evidence_paths"] = ["missing.json"]
    with pytest.raises(ValidationError, match="references missing artifacts"):
        EvidenceRecord.model_validate(record)


def test_blocked_record_requires_a_specific_next_action() -> None:
    record = passing_record()
    record["status"] = EvidenceStatus.BLOCKED
    record["checks"] = []
    with pytest.raises(ValidationError, match="requires a blocker"):
        EvidenceRecord.model_validate(record)


def test_timestamp_must_be_utc() -> None:
    record = passing_record()
    record["recorded_at_utc"] = datetime.fromisoformat("2026-10-21T12:00:00+03:00")
    with pytest.raises(ValidationError, match="normalized to UTC"):
        EvidenceRecord.model_validate(record)
