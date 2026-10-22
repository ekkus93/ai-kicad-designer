"""Typed, revision-bound evidence records for MCP pivot tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject implicit coercion and unknown evidence fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceStatus(StrEnum):
    """Possible outcomes for one task or one verification check."""

    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"
    WAIVED_WITH_APPROVAL = "WAIVED_WITH_APPROVAL"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceArtifact(StrictModel):
    """A content-hashed output used as evidence."""

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    role: str = Field(min_length=1)


class EvidenceCheck(StrictModel):
    """A named verification result tied to one or more artifacts."""

    check_id: str = Field(min_length=1)
    status: EvidenceStatus
    summary: str = Field(min_length=1)
    evidence_paths: list[str] = Field(min_length=1)
    independent: bool


class EvidenceAction(StrictModel):
    """The operation and exact implementation that produced the evidence."""

    summary: str = Field(min_length=1)
    command: str | None = None
    backend: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    toolchain: str = Field(min_length=1)


class EvidenceBlocker(StrictModel):
    """A specific unresolved condition and its next owner or engineering action."""

    code: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    requires_owner_input: bool


class EvidenceRecord(StrictModel):
    """Single source of truth for a TODO task's implementation evidence."""

    schema_version: Literal["pivot-evidence.v1"]
    evidence_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
    task_id: str = Field(pattern=r"^(?:G|P[0-7]|X)-[0-9]{3}$")
    recorded_at_utc: datetime
    source_commit: str = Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
    revision_kind: Literal["git_commit", "design_revision", "other"]
    revision_id: str = Field(min_length=1)
    action: EvidenceAction
    status: EvidenceStatus
    artifacts: list[EvidenceArtifact]
    checks: list[EvidenceCheck]
    ci_links: list[str]
    blockers: list[EvidenceBlocker]
    notes: list[str]

    @model_validator(mode="after")
    def validate_evidence_references(self) -> EvidenceRecord:
        if self.recorded_at_utc.tzinfo is None:
            raise ValueError("recorded_at_utc must include a timezone")
        if self.recorded_at_utc.utcoffset() != timezone.utc.utcoffset(self.recorded_at_utc):
            raise ValueError("recorded_at_utc must be normalized to UTC")

        artifact_paths = {artifact.path for artifact in self.artifacts}
        for check in self.checks:
            missing = set(check.evidence_paths) - artifact_paths
            if missing:
                raise ValueError(
                    f"check {check.check_id!r} references missing artifacts: {sorted(missing)}"
                )

        if self.status is EvidenceStatus.PASS:
            if not self.artifacts:
                raise ValueError("PASS requires at least one content-hashed artifact")
            if not any(
                check.status is EvidenceStatus.PASS and check.independent for check in self.checks
            ):
                raise ValueError(
                    "PASS requires at least one independent passing verification check"
                )
        if (
            self.status in {EvidenceStatus.BLOCKED, EvidenceStatus.UNSUPPORTED}
            and not self.blockers
        ):
            raise ValueError(f"{self.status.value} requires a blocker with a next action")

        for link in self.ci_links:
            if not link.startswith(("https://", "http://")):
                raise ValueError("CI links must use http or https")
        return self
