"""Lexicographic objective hierarchy for composition candidate evidence."""

from __future__ import annotations

from dataclasses import dataclass

MetricVector = tuple[int, int, int, int, int, int, int]


@dataclass(frozen=True)
class CandidateMetrics:
    candidate_id: str
    electrical_correct: bool
    hard_invariants_ok: bool
    semantic_readability_penalty: int = 0
    routing_clarity_penalty: int = 0
    compactness_whitespace_penalty: int = 0
    aesthetic_tiebreaker_penalty: int = 0
    attempt_index: int = 0
    state_fingerprint: str | None = None


@dataclass(frozen=True)
class RejectedCandidate:
    candidate_id: str
    reason: str
    metric_vector: MetricVector


@dataclass(frozen=True)
class CandidateSelectionEvidence:
    winner_id: str
    winner_metric_vector: MetricVector
    rejected_candidates: tuple[RejectedCandidate, ...]
    best_rejected_candidate_id: str | None
    deduplicated_state_count: int
    inspected_attempt_count: int


def select_best_candidate(candidates: tuple[CandidateMetrics, ...]) -> CandidateSelectionEvidence:
    """Select a candidate without allowing lower tiers to trade away higher tiers."""
    if not candidates:
        raise ValueError("at least one candidate is required")

    unique = _deduplicate_repeated_states(candidates)
    ranked = sorted(unique, key=lambda candidate: (_metric_vector(candidate), candidate.candidate_id))
    winner = ranked[0]
    winner_vector = _metric_vector(winner)
    rejected = tuple(
        RejectedCandidate(candidate.candidate_id, _rejection_reason(winner, candidate), _metric_vector(candidate))
        for candidate in ranked[1:]
    )
    best_rejected = rejected[0].candidate_id if rejected else None
    return CandidateSelectionEvidence(
        winner.candidate_id,
        winner_vector,
        rejected,
        best_rejected,
        len(candidates) - len(unique),
        len(candidates),
    )


def _deduplicate_repeated_states(
    candidates: tuple[CandidateMetrics, ...]
) -> tuple[CandidateMetrics, ...]:
    best_by_state: dict[str, CandidateMetrics] = {}
    for candidate in candidates:
        key = candidate.state_fingerprint or candidate.candidate_id
        current = best_by_state.get(key)
        if current is None or (_metric_vector(candidate), candidate.candidate_id) < (
            _metric_vector(current),
            current.candidate_id,
        ):
            best_by_state[key] = candidate
    return tuple(sorted(best_by_state.values(), key=lambda candidate: candidate.candidate_id))


def _metric_vector(candidate: CandidateMetrics) -> MetricVector:
    return (
        0 if candidate.electrical_correct else 1,
        0 if candidate.hard_invariants_ok else 1,
        max(0, candidate.semantic_readability_penalty),
        max(0, candidate.routing_clarity_penalty),
        max(0, candidate.compactness_whitespace_penalty),
        max(0, candidate.aesthetic_tiebreaker_penalty),
        max(0, candidate.attempt_index),
    )


def _rejection_reason(winner: CandidateMetrics, rejected: CandidateMetrics) -> str:
    labels = (
        "electrical_correctness",
        "hard_m2h2_invariants",
        "semantic_readability",
        "routing_clarity",
        "compactness_whitespace",
        "aesthetic_tiebreaker",
        "deterministic_attempt_order",
    )
    winner_vector = _metric_vector(winner)
    rejected_vector = _metric_vector(rejected)
    for label, winner_value, rejected_value in zip(labels, winner_vector, rejected_vector, strict=True):
        if winner_value != rejected_value:
            return label
    return "deterministic_candidate_id"
