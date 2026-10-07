"""Deterministic composition reproducibility comparison."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunFingerprint:
    project_sha256: str
    semantic_class: str
    normalized_render_sha256: str
    metric_vector_sha256: str
    candidate_decision_sha256: str


@dataclass(frozen=True)
class ReproducibilityResult:
    run_count: int
    project_bytes_match: bool
    semantic_class_matches: bool
    normalized_render_matches: bool
    metric_vector_matches: bool
    candidate_decisions_match: bool

    @property
    def passed(self) -> bool:
        return self.run_count == 5 and all(
            (
                self.project_bytes_match,
                self.semantic_class_matches,
                self.normalized_render_matches,
                self.metric_vector_matches,
                self.candidate_decisions_match,
            )
        )


def compare_five_runs(runs: tuple[RunFingerprint, ...]) -> ReproducibilityResult:
    if len(runs) != 5:
        raise ValueError("governed reproducibility requires exactly five runs")
    return ReproducibilityResult(
        run_count=len(runs),
        project_bytes_match=_same(runs, "project_sha256"),
        semantic_class_matches=_same(runs, "semantic_class"),
        normalized_render_matches=_same(runs, "normalized_render_sha256"),
        metric_vector_matches=_same(runs, "metric_vector_sha256"),
        candidate_decisions_match=_same(runs, "candidate_decision_sha256"),
    )


def _same(runs: tuple[RunFingerprint, ...], field: str) -> bool:
    return len({getattr(run, field) for run in runs}) == 1
