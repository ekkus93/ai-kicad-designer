"""Final-source reproducibility evidence for M2h2 composition closure.

This module is intentionally evidence-only. It does not generate layouts and does
not weaken any existing electrical or visual qualification gate; it validates
that already collected current-source runs agree on deterministic project bytes,
semantic composition class, native-render geometry, observer metrics, and
candidate-selection decisions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

LOCKED_TOOLCHAIN = "KiCad 10.0.6"
REQUIRED_RUN_COUNT = 5


def _validate_sha(value: str, length: int, label: str) -> str:
    if len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{label} must be lowercase {length}-character hex")
    return value


@dataclass(frozen=True)
class CompositionReproducibilityRun:
    """One locked-source reproducibility observation."""

    run_id: str
    source_sha: str
    project_sha256: str
    semantic_composition_class: str
    native_render_geometry_sha256: str
    observer_metric_vector_sha256: str
    candidate_decision_sha256: str
    toolchain: str = LOCKED_TOOLCHAIN

    def __post_init__(self) -> None:
        _validate_sha(self.source_sha, 40, "source_sha")
        _validate_sha(self.project_sha256, 64, "project_sha256")
        _validate_sha(
            self.native_render_geometry_sha256,
            64,
            "native_render_geometry_sha256",
        )
        _validate_sha(
            self.observer_metric_vector_sha256,
            64,
            "observer_metric_vector_sha256",
        )
        _validate_sha(self.candidate_decision_sha256, 64, "candidate_decision_sha256")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.semantic_composition_class:
            raise ValueError("semantic_composition_class is required")
        if self.toolchain != LOCKED_TOOLCHAIN:
            raise ValueError(f"toolchain must be {LOCKED_TOOLCHAIN}")


@dataclass(frozen=True)
class CompositionReproducibilityEvidence:
    """Five-run deterministic reproducibility certificate candidate."""

    source_sha: str
    runs: tuple[CompositionReproducibilityRun, ...]
    schema_version: str = "m2h2.composition-reproducibility.1"

    def __post_init__(self) -> None:
        _validate_sha(self.source_sha, 40, "source_sha")
        run_ids = [run.run_id for run in self.runs]
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("duplicate reproducibility run_id")
        if any(run.source_sha != self.source_sha for run in self.runs):
            raise ValueError("run source_sha does not match evidence source_sha")

    def gaps(self) -> tuple[str, ...]:
        """Return exact unmet reproducibility obligations."""
        issues: list[str] = []
        if len(self.runs) != REQUIRED_RUN_COUNT:
            issues.append(f"expected {REQUIRED_RUN_COUNT} runs, observed {len(self.runs)}")
        fields = (
            "project_sha256",
            "semantic_composition_class",
            "native_render_geometry_sha256",
            "observer_metric_vector_sha256",
            "candidate_decision_sha256",
        )
        for field in fields:
            values = {getattr(run, field) for run in self.runs}
            if len(values) > 1:
                issues.append(f"non-deterministic {field}")
        return tuple(issues)

    def is_complete(self) -> bool:
        return not self.gaps()

    def canonical_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "source_sha": self.source_sha,
            "runs": [
                asdict(run)
                for run in sorted(self.runs, key=lambda item: item.run_id)
            ],
            "gaps": list(self.gaps()),
            "complete": self.is_complete(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_reproducibility_evidence(
    source_sha: str,
    runs: tuple[CompositionReproducibilityRun, ...],
) -> CompositionReproducibilityEvidence:
    """Build deterministic final reproducibility evidence from observed runs."""
    return CompositionReproducibilityEvidence(source_sha=source_sha, runs=runs)
