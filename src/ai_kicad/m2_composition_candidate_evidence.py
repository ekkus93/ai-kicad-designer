"""Evidence records for human-readable composition candidate selection.

This module is intentionally independent of the production composer.  It makes
candidate-ranking decisions auditable with explicit semantic and routing metric
vectors, so a compact route cannot hide a worse human-readable composition.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

type MetricValue = int | float


@dataclass(frozen=True)
class CandidateDecision:
    """One electrically proved or rejected composition candidate."""

    candidate_id: str
    electrically_valid: bool
    semantic_penalties: tuple[MetricValue, ...]
    routing_compactness: tuple[MetricValue, ...]
    attempt_index: int

    def ranking_key(self) -> tuple[MetricValue | str, ...]:
        """Return the frozen lexicographic key used for evidence ordering."""
        return (
            0 if self.electrically_valid else 1,
            *self.semantic_penalties,
            *self.routing_compactness,
            self.attempt_index,
            self.candidate_id,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""
        return {
            "candidate_id": self.candidate_id,
            "electrically_valid": self.electrically_valid,
            "semantic_penalties": list(self.semantic_penalties),
            "routing_compactness": list(self.routing_compactness),
            "attempt_index": self.attempt_index,
            "ranking_key": list(self.ranking_key()),
        }


@dataclass(frozen=True)
class CandidateSelectionEvidence:
    """Complete audit record for one candidate-selection decision."""

    selected_candidate_id: str
    rule: str
    candidates: tuple[CandidateDecision, ...]

    def rejected_candidates(self) -> tuple[CandidateDecision, ...]:
        """Return non-selected candidates in deterministic evidence order."""
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.candidate_id != self.selected_candidate_id
        )

    def best_rejected_candidate(self) -> CandidateDecision | None:
        """Return the closest rejected candidate, preserving full metrics."""
        rejected = self.rejected_candidates()
        return rejected[0] if rejected else None

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""
        best_rejected = self.best_rejected_candidate()
        return {
            "schema_version": "m2h2.composition-candidate-selection.1",
            "rule": self.rule,
            "selected_candidate_id": self.selected_candidate_id,
            "best_rejected_candidate_id": (
                best_rejected.candidate_id if best_rejected is not None else None
            ),
            "candidate_count": len(self.candidates),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }

    def canonical_json(self) -> str:
        """Serialize the evidence record with stable key ordering."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def select_candidate_with_evidence(
    candidates: tuple[CandidateDecision, ...],
) -> CandidateSelectionEvidence:
    """Select the best candidate and preserve a full decision trace.

    The ordering is deliberately lexicographic: electrical validity is a hard
    gate, semantic readability penalties outrank routing/area compactness, and
    attempt order is only a deterministic final tiebreaker.
    """
    if not candidates:
        raise ValueError("at least one candidate is required")
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.candidate_id:
            raise ValueError("candidate id is required")
        if candidate.candidate_id in seen:
            raise ValueError(f"duplicate candidate id: {candidate.candidate_id}")
        seen.add(candidate.candidate_id)
        if candidate.attempt_index < 0:
            raise ValueError("attempt index must be non-negative")
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.ranking_key()))
    selected = ordered[0]
    return CandidateSelectionEvidence(
        selected_candidate_id=selected.candidate_id,
        rule="electrical_validity_then_semantic_readability_then_routing_compactness",
        candidates=ordered,
    )
