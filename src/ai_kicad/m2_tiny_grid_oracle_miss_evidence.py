"""Independent, fail-closed evidence gate for bounded tiny-oracle misses.

The oracle recomputes the production placement score from grid geometry;
reported search scores are only used to audit what the bounded search tried.
A search that did not use its full budget cannot excuse a dominated result.
"""

from __future__ import annotations

from dataclasses import dataclass

from .m2_tiny_grid_composition_oracle import ScoreVector, TinyOracleEvidence


@dataclass(frozen=True)
class TinyBoundedSearchAudit:
    selected_score: ScoreVector
    oracle_best_score: ScoreVector
    attempted_scores: tuple[ScoreVector, ...]
    attempt_budget: int
    missed_optimum: bool
    miss_reason: str | None

    def to_dict(self) -> dict[str, object]:
        """Emit a deterministic, machine-checkable qualification witness."""
        return {
            "schema_version": "m2h2.tiny-bounded-search-audit.1",
            "selected_score": list(self.selected_score),
            "oracle_best_score": list(self.oracle_best_score),
            "attempted_scores": [list(score) for score in self.attempted_scores],
            "attempted_count": len(self.attempted_scores),
            "attempt_budget": self.attempt_budget,
            "missed_optimum": self.missed_optimum,
            "miss_reason": self.miss_reason,
        }


def require_bounded_search_miss_evidence(
    oracle: TinyOracleEvidence,
    attempted_scores: tuple[ScoreVector, ...],
    *,
    attempt_budget: int,
    miss_reason: str | None = None,
) -> TinyBoundedSearchAudit:
    """Reject unexplained oracle misses or hidden better attempted candidates.

    Only an exhausted budget smaller than the independent oracle's legal
    candidate count can justify missing the optimum. A reason alone is never
    sufficient. No ranking objective or correctness gate is relaxed here.
    """
    production = oracle.production_candidate
    if production is None or not oracle.nondominated_candidates:
        raise ValueError("production placement and independent oracle optimum required")
    if attempt_budget < 1 or not attempted_scores or len(attempted_scores) > attempt_budget:
        raise ValueError("invalid bounded search attempt accounting")
    if any(
        len(score) != len(production.score_vector)
        or any(type(value) is not int or value < 0 for value in score)
        for score in attempted_scores
    ):
        raise ValueError("invalid attempted composition score vector")
    if min(attempted_scores) != production.score_vector:
        raise ValueError("selected production score is not the best attempted score")

    best = min(candidate.score_vector for candidate in oracle.nondominated_candidates)
    missed = production.score_vector > best
    if missed != oracle.production_is_dominated:
        raise ValueError("independent oracle domination evidence is inconsistent")
    if missed:
        if (
            len(attempted_scores) != attempt_budget
            or attempt_budget >= oracle.candidate_count
            or miss_reason != "bounded_candidate_budget"
        ):
            raise ValueError("dominated production result requires exhausted-budget evidence")
    elif miss_reason is not None:
        raise ValueError("an optimal production result must not claim a search miss")

    return TinyBoundedSearchAudit(
        selected_score=production.score_vector,
        oracle_best_score=best,
        attempted_scores=attempted_scores,
        attempt_budget=attempt_budget,
        missed_optimum=missed,
        miss_reason=miss_reason,
    )
