import pytest

from ai_kicad import m2_composition_objective_hierarchy as hierarchy


def test_electrical_correctness_cannot_be_traded_for_semantic_score() -> None:
    winner = hierarchy.CandidateMetrics("safe", True, True, semantic_readability_penalty=50)
    unsafe = hierarchy.CandidateMetrics("unsafe", False, True, semantic_readability_penalty=0)
    evidence = hierarchy.select_best_candidate((unsafe, winner))
    assert evidence.winner_id == "safe"
    assert evidence.rejected_candidates[0].reason == "electrical_correctness"


def test_hard_invariants_outrank_all_human_readability_tiers() -> None:
    legal = hierarchy.CandidateMetrics("legal", True, True, semantic_readability_penalty=90)
    illegal = hierarchy.CandidateMetrics("illegal", True, False, semantic_readability_penalty=0)
    evidence = hierarchy.select_best_candidate((illegal, legal))
    assert evidence.winner_id == "legal"
    assert evidence.rejected_candidates[0].reason == "hard_m2h2_invariants"


def test_semantic_readability_outranks_routing_and_compactness() -> None:
    semantic_best = hierarchy.CandidateMetrics(
        "semantic_best",
        True,
        True,
        semantic_readability_penalty=1,
        routing_clarity_penalty=100,
        compactness_whitespace_penalty=100,
    )
    pretty_wrong = hierarchy.CandidateMetrics(
        "pretty_wrong",
        True,
        True,
        semantic_readability_penalty=2,
        routing_clarity_penalty=0,
        compactness_whitespace_penalty=0,
    )
    evidence = hierarchy.select_best_candidate((pretty_wrong, semantic_best))
    assert evidence.winner_id == "semantic_best"
    assert evidence.rejected_candidates[0].reason == "semantic_readability"


def test_routing_clarity_outranks_compactness_and_aesthetic_tiebreakers() -> None:
    clear = hierarchy.CandidateMetrics(
        "clear",
        True,
        True,
        semantic_readability_penalty=0,
        routing_clarity_penalty=1,
        compactness_whitespace_penalty=100,
    )
    compact = hierarchy.CandidateMetrics(
        "compact",
        True,
        True,
        semantic_readability_penalty=0,
        routing_clarity_penalty=2,
        compactness_whitespace_penalty=0,
    )
    evidence = hierarchy.select_best_candidate((compact, clear))
    assert evidence.winner_id == "clear"
    assert evidence.rejected_candidates[0].reason == "routing_clarity"


def test_repeated_states_are_deduplicated_and_best_rejected_is_preserved() -> None:
    duplicate_bad = hierarchy.CandidateMetrics(
        "duplicate_bad",
        True,
        True,
        semantic_readability_penalty=9,
        state_fingerprint="same",
    )
    duplicate_good = hierarchy.CandidateMetrics(
        "duplicate_good",
        True,
        True,
        semantic_readability_penalty=3,
        state_fingerprint="same",
    )
    winner = hierarchy.CandidateMetrics("winner", True, True, semantic_readability_penalty=1)
    evidence = hierarchy.select_best_candidate((duplicate_bad, duplicate_good, winner))
    assert evidence.winner_id == "winner"
    assert evidence.deduplicated_state_count == 1
    assert evidence.inspected_attempt_count == 3
    assert evidence.best_rejected_candidate_id == "duplicate_good"
    assert evidence.rejected_candidates[0].metric_vector[2] == 3


def test_attempt_order_is_deterministic_final_tiebreaker() -> None:
    first = hierarchy.CandidateMetrics("z", True, True, attempt_index=0)
    second = hierarchy.CandidateMetrics("a", True, True, attempt_index=1)
    evidence = hierarchy.select_best_candidate((second, first))
    assert evidence.winner_id == "z"
    assert evidence.rejected_candidates[0].reason == "deterministic_attempt_order"


def test_empty_candidates_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one candidate"):
        hierarchy.select_best_candidate(())
