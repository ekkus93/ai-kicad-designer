"""Final evidence binder for M2h2 human-readable composition closure.

This module intentionally records only evidence identities and exact outcomes. It
must not infer PASS from screenshots, aggregate scores, or stale artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256


LOCKED_TOOLCHAIN = "KiCad 10.0.6"
SCHEMA_NAME = "m2h2-human-readable-composition-closure"
SCHEMA_VERSION = "2026-10-07.1"


@dataclass(frozen=True)
class EvidenceRoot:
    """Immutable evidence location plus purpose and content digest."""

    root_id: str
    path: str
    purpose: str
    sha256: str

    def __post_init__(self) -> None:
        _require_nonempty("root_id", self.root_id)
        _require_nonempty("path", self.path)
        _require_nonempty("purpose", self.purpose)
        _require_sha(self.sha256)
        if ".local/" in self.path or self.path.startswith(".local/"):
            raise ValueError("closure evidence cannot be sourced from .local")


@dataclass(frozen=True)
class QualificationOutcome:
    """Exact current-source qualification count for one governed family."""

    family: str
    required_runs: int
    passed_runs: int
    failed_runs: int = 0

    def __post_init__(self) -> None:
        _require_nonempty("family", self.family)
        if self.required_runs < 0 or self.passed_runs < 0 or self.failed_runs < 0:
            raise ValueError("qualification run counts must be non-negative")
        if self.passed_runs + self.failed_runs > self.required_runs:
            raise ValueError("observed qualification runs exceed required runs")

    @property
    def complete(self) -> bool:
        return self.passed_runs == self.required_runs and self.failed_runs == 0


@dataclass(frozen=True)
class ClosureRecord:
    """Canonical final-composition closure manifest."""

    production_sha: str
    qualification_sha: str
    observer_manifest_sha: str
    oracle_manifest_sha: str
    source_manifest_sha: str
    evidence_roots: tuple[EvidenceRoot, ...]
    qualification_outcomes: tuple[QualificationOutcome, ...]
    native_render_inspection_count: int
    todo_path: str = "docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md"
    toolchain: str = LOCKED_TOOLCHAIN

    def __post_init__(self) -> None:
        for field_name in (
            "production_sha",
            "qualification_sha",
            "observer_manifest_sha",
            "oracle_manifest_sha",
            "source_manifest_sha",
        ):
            _require_sha(getattr(self, field_name))
        if self.toolchain != LOCKED_TOOLCHAIN:
            raise ValueError("closure record must bind locked KiCad 10.0.6")
        if self.native_render_inspection_count < 0:
            raise ValueError("inspection count must be non-negative")
        root_ids = [root.root_id for root in self.evidence_roots]
        if len(root_ids) != len(set(root_ids)):
            raise ValueError("duplicate evidence root id")
        families = [outcome.family for outcome in self.qualification_outcomes]
        if len(families) != len(set(families)):
            raise ValueError("duplicate qualification family")

    @property
    def pass_eligible(self) -> bool:
        """Return whether the manifest is eligible for TODO PASS reconciliation."""
        return (
            bool(self.evidence_roots)
            and bool(self.qualification_outcomes)
            and self.native_render_inspection_count > 0
            and all(outcome.complete for outcome in self.qualification_outcomes)
        )

    def canonical_json(self) -> str:
        payload = {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "production_sha": self.production_sha,
            "qualification_sha": self.qualification_sha,
            "observer_manifest_sha": self.observer_manifest_sha,
            "oracle_manifest_sha": self.oracle_manifest_sha,
            "source_manifest_sha": self.source_manifest_sha,
            "toolchain": self.toolchain,
            "todo_path": self.todo_path,
            "native_render_inspection_count": self.native_render_inspection_count,
            "evidence_roots": [
                {
                    "root_id": root.root_id,
                    "path": root.path,
                    "purpose": root.purpose,
                    "sha256": root.sha256,
                }
                for root in sorted(self.evidence_roots, key=lambda item: item.root_id)
            ],
            "qualification_outcomes": [
                {
                    "family": outcome.family,
                    "required_runs": outcome.required_runs,
                    "passed_runs": outcome.passed_runs,
                    "failed_runs": outcome.failed_runs,
                    "complete": outcome.complete,
                }
                for outcome in sorted(
                    self.qualification_outcomes, key=lambda item: item.family
                )
            ],
            "pass_eligible": self.pass_eligible,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def manifest_sha256(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _require_sha(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("expected lowercase sha256 digest")


def _require_nonempty(field_name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
