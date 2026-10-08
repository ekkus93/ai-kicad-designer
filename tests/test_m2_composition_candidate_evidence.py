import json

import pytest

from ai_kicad.m2_composition_candidate_evidence import (
    CandidateDecision,
    select_candidate_with_evidence,
)


def test_semantic_penalty_outranks_routing_compactness() -> None:
    readable = CandidateDecision("readable", True, (0, 0, 0, 0), (900, 900, 9), 1)
    compact_wrong = CandidateDecision("compact_wrong", True, (1, 0, 0, 0), (1, 1, 0), 0)

    evidence = select_candidate_with_evidence((compact_wrong, readable))

    assert evidence.selected_candidate_id == "readable"
    assert evidence.best_rejected_candidate() == compact_wrong


def test_electrical_validity_is_a_hard_gate() -> None:
    invalid_but_pretty = CandidateDecision("invalid", False, (0, 0, 0, 0), (0, 0, 0), 0)
    valid_but_worse = CandidateDecision("valid", True, (9, 9, 9, 9), (9, 9, 9), 1)

    evidence = select_candidate_with_evidence((invalid_but_pretty, valid_but_worse))

    assert evidence.selected_candidate_id == "valid"
    assert evidence.candidates[-1].candidate_id == "invalid"


def test_routing_compactness_breaks_ties_after_semantics() -> None:
    longer = CandidateDecision("longer", True, (0, 0, 0, 0), (20, 5, 2), 0)
    shorter = CandidateDecision("shorter", True, (0, 0, 0, 0), (10, 8, 4), 1)

    evidence = select_candidate_with_evidence((longer, shorter))

    assert evidence.selected_candidate_id == "shorter"


def test_attempt_order_is_only_a_final_deterministic_tiebreaker() -> None:
    later = CandidateDecision("later", True, (0, 0), (1, 1), 3)
    earlier = CandidateDecision("earlier", True, (0, 0), (1, 1), 2)

    evidence = select_candidate_with_evidence((later, earlier))

    assert evidence.selected_candidate_id == "earlier"


def test_canonical_json_preserves_full_metric_vectors() -> None:
    first = CandidateDecision("first", True, (0, 2, 0, 1), (8, 4, 2, 16), 0)
    second = CandidateDecision("second", True, (0, 3, 0, 1), (1, 1, 1, 1), 1)

    evidence = select_candidate_with_evidence((second, first))
    decoded = json.loads(evidence.canonical_json())

    assert decoded["schema_version"] == "m2h2.composition-candidate-selection.1"
    assert decoded["selected_candidate_id"] == "first"
    assert decoded["best_rejected_candidate_id"] == "second"
    assert decoded["candidates"][0]["semantic_penalties"] == [0, 2, 0, 1]
    assert decoded["candidates"][1]["routing_compactness"] == [1, 1, 1, 1]


def test_invalid_candidate_inventory_is_rejected() -> None:
    candidate = CandidateDecision("dup", True, (), (), 0)
    with pytest.raises(ValueError, match="at least one"):
        select_candidate_with_evidence(())
    with pytest.raises(ValueError, match="duplicate"):
        select_candidate_with_evidence((candidate, candidate))
    with pytest.raises(ValueError, match="non-negative"):
        select_candidate_with_evidence(
            (CandidateDecision("bad-attempt", True, (), (), -1),)
        )
