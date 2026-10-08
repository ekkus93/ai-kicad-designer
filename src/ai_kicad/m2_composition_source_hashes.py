"""Source-hash manifest helpers for M2h2 composition stabilization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

SCHEMA_VERSION = "m2h2.composition-source-hashes.1"
LOCKED_TOOLCHAIN = "KiCad 10.0.6"


@dataclass(frozen=True)
class SourceArtifactHash:
    """One behavior-affecting composition source artifact."""

    path: str
    sha256: str
    role: str

    def to_dict(self) -> dict[str, str]:
        """Return a deterministic JSON-compatible representation."""
        return {"path": self.path, "role": self.role, "sha256": self.sha256}


@dataclass(frozen=True)
class SourceHashManifest:
    """Frozen source-hash inventory for composition qualification."""

    source_sha: str
    artifacts: tuple[SourceArtifactHash, ...]
    locked_toolchain: str = LOCKED_TOOLCHAIN
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""
        return {
            "schema_version": self.schema_version,
            "source_sha": self.source_sha,
            "locked_toolchain": self.locked_toolchain,
            "artifact_count": len(self.artifacts),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

    def canonical_json(self) -> str:
        """Serialize the manifest with stable key ordering."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def manifest_sha256(self) -> str:
        """Hash the canonical manifest itself."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def classify_source_role(path: str) -> str:
    """Classify a source path without using fixture or case names."""
    if path.startswith(".local/") or "/.local/" in path:
        raise ValueError(".local paths are not qualification source artifacts")
    if path.startswith("research/legacy_openclaw/"):
        raise ValueError("legacy OpenClaw research paths are out of scope")
    filename = path.rsplit("/", 1)[-1]
    if "observer" in filename or "oracle" in filename:
        return "observer_or_oracle"
    if "audit" in filename:
        return "audit"
    if "evidence" in filename or "schema" in filename or "hash" in filename:
        return "evidence_schema"
    if "compose" in filename or "composition" in filename:
        return "production_composition"
    return "supporting_source"


def build_source_hash_manifest(
    source_sha: str,
    source_files: Mapping[str, str],
) -> SourceHashManifest:
    """Build a deterministic source-hash manifest from UTF-8 source text."""
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise ValueError("source_sha must be a lowercase 40-character hex SHA")
    artifacts = tuple(
        SourceArtifactHash(
            path=path,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            role=classify_source_role(path),
        )
        for path, content in sorted(source_files.items())
    )
    if not artifacts:
        raise ValueError("at least one source file is required")
    return SourceHashManifest(source_sha=source_sha, artifacts=artifacts)
