"""Versioned evidence schema for M2h2 human-readable composition metrics.

The schema records observer/oracle metric definitions, behavior-affecting source
hashes, evidence roots, and qualification source binding without depending on
production layout scores as proof.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

SCHEMA_NAME = "m2h2-human-readable-composition"
SCHEMA_VERSION = "2026-10-07.1"


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    category: str
    unit: str
    description: str
    higher_is_better: bool = False


@dataclass(frozen=True)
class SourceHash:
    path: str
    sha256: str
    role: str


@dataclass(frozen=True)
class EvidenceRoot:
    root_id: str
    path: str
    purpose: str
    immutable: bool = True


@dataclass(frozen=True)
class CompositionEvidenceManifest:
    schema_name: str
    schema_version: str
    production_sha: str
    qualification_sha: str
    metrics: tuple[MetricDefinition, ...]
    source_hashes: tuple[SourceHash, ...]
    evidence_roots: tuple[EvidenceRoot, ...]
    locked_toolchain: str = "KiCad 10.0.6"

    def canonical_json(self) -> str:
        """Return deterministic JSON suitable for archival hashing."""
        return json.dumps(_manifest_dict(self), sort_keys=True, separators=(",", ":"))

    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def default_metric_definitions() -> tuple[MetricDefinition, ...]:
    """Return the frozen top-level composition metric vocabulary."""
    return (
        MetricDefinition(
            "primary_flow_reversal_distance",
            "semantic_flow",
            "grid_manhattan",
            "Cumulative reverse distance along directed primary signal flow.",
        ),
        MetricDefinition(
            "interface_side_violation_count",
            "interface_frontier",
            "count",
            "Directed external interfaces placed on a semantically wrong frontier.",
        ),
        MetricDefinition(
            "functional_block_fragmentation_count",
            "functional_grouping",
            "count",
            "Functional blocks exceeding the frozen internal dispersion tolerance.",
        ),
        MetricDefinition(
            "support_to_owner_distance",
            "visual_ownership",
            "grid_manhattan",
            "Distance from local support structures to their owning stage/package.",
        ),
        MetricDefinition(
            "feedback_intrusion_count",
            "feedback_readability",
            "count",
            "Unrelated blocks intersecting a feedback-loop visual envelope.",
        ),
        MetricDefinition(
            "shared_infrastructure_dispersion",
            "power_reference",
            "grid_manhattan",
            "Visual dispersion of supply/reference infrastructure members.",
        ),
        MetricDefinition(
            "repeated_channel_alignment_variance",
            "repeated_structure",
            "grid_squared",
            "Variance of corresponding positions in repeated semantic channels.",
        ),
        MetricDefinition(
            "occupied_area_ratio",
            "page_utilization",
            "ratio",
            "Content occupied area divided by the 210 by 140 mm composition envelope.",
            higher_is_better=True,
        ),
        MetricDefinition(
            "internal_void_area",
            "page_utilization",
            "grid_area",
            "Largest accidental empty corridor/void inside the content envelope.",
        ),
        MetricDefinition(
            "routing_bend_excess",
            "routing_clarity",
            "count",
            "Bends beyond an independent legal semantic-local routing baseline.",
        ),
        MetricDefinition(
            "label_local_disconnect_count",
            "label_discipline",
            "count",
            "Local relationships disconnected only through distant labels.",
        ),
    )


def build_manifest(
    *,
    production_sha: str,
    qualification_sha: str,
    source_texts: dict[str, str],
    evidence_roots: tuple[EvidenceRoot, ...],
) -> CompositionEvidenceManifest:
    """Build a deterministic manifest from current source and evidence roots."""
    return CompositionEvidenceManifest(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        production_sha=production_sha,
        qualification_sha=qualification_sha,
        metrics=default_metric_definitions(),
        source_hashes=_source_hashes(source_texts),
        evidence_roots=tuple(sorted(evidence_roots, key=lambda item: item.root_id)),
    )


def _source_hashes(source_texts: dict[str, str]) -> tuple[SourceHash, ...]:
    records: list[SourceHash] = []
    for path, text in sorted(source_texts.items()):
        role = "observer_or_oracle" if "observer" in path or "oracle" in path else "production"
        records.append(SourceHash(path, hashlib.sha256(text.encode("utf-8")).hexdigest(), role))
    return tuple(records)


def _manifest_dict(manifest: CompositionEvidenceManifest) -> dict[str, object]:
    return {
        "schema_name": manifest.schema_name,
        "schema_version": manifest.schema_version,
        "production_sha": manifest.production_sha,
        "qualification_sha": manifest.qualification_sha,
        "locked_toolchain": manifest.locked_toolchain,
        "metrics": [metric.__dict__ for metric in manifest.metrics],
        "source_hashes": [record.__dict__ for record in manifest.source_hashes],
        "evidence_roots": [root.__dict__ for root in manifest.evidence_roots],
    }
