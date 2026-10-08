from ai_kicad import m2_grouping_locality_oracle as oracle


def test_intra_block_cohesion_penalizes_scattered_stage_members() -> None:
    compact = (
        oracle.GroupMember("amp", "gain", (20, 20)),
        oracle.GroupMember("bias", "gain", (35, 20)),
    )
    scattered = (
        compact[0],
        oracle.GroupMember("bias", "gain", (100, 20)),
    )
    assert oracle.evaluate_grouping_candidate("compact", compact).intra_block_penalty == 0
    score = oracle.evaluate_grouping_candidate("scattered", scattered, cohesion_limit=40)
    assert score.intra_block_penalty == 40
    assert score.witnesses[0].kind == "intra_block_dispersion"


def test_inter_block_separation_penalizes_unrelated_intrusion() -> None:
    members = (
        oracle.GroupMember("a1", "left", (10, 10)),
        oracle.GroupMember("a2", "left", (20, 10)),
        oracle.GroupMember("b1", "right", (22, 10)),
        oracle.GroupMember("b2", "right", (40, 10)),
    )
    score = oracle.evaluate_grouping_candidate("crowded", members, separation_limit=10)
    assert score.inter_block_penalty == 8
    assert any(witness.kind == "inter_block_separation" for witness in score.witnesses)


def test_support_feedback_and_label_disconnects_stay_with_owners() -> None:
    members = (
        oracle.GroupMember("opamp", "gain", (0, 0)),
        oracle.GroupMember("decouple", "gain", (80, 0), "opamp", "support"),
        oracle.GroupMember("feedback", "gain", (0, 90), "opamp", "feedback"),
        oracle.GroupMember("labelled", "gain", (100, 0), "opamp", label_mediated=True),
    )
    score = oracle.evaluate_grouping_candidate("detached", members, ownership_limit=60)
    kinds = [witness.kind for witness in score.witnesses]
    assert score.ownership_penalty == 50
    assert score.label_disconnect_penalty == 40
    assert "support_owner_distance" in kinds
    assert "feedback_owner_distance" in kinds
    assert "label_mediated_local_disconnect" in kinds


def test_shared_infrastructure_is_not_forced_into_one_block() -> None:
    members = (
        oracle.GroupMember("left_stage", "left", (0, 0)),
        oracle.GroupMember("right_stage", "right", (80, 0)),
        oracle.GroupMember("rail", "supply", (40, 20), ownership="shared"),
    )
    score = oracle.evaluate_grouping_candidate("shared", members)
    assert score.intra_block_penalty == 0
    assert not any("rail" in witness.member_ids for witness in score.witnesses)


def test_passive_series_chain_prefers_natural_left_to_right_order() -> None:
    ordered = (
        oracle.GroupMember("r1", "filter", (10, 0), chain_rank=0),
        oracle.GroupMember("r2", "filter", (30, 0), chain_rank=1),
    )
    reversed_chain = (
        oracle.GroupMember("r1", "filter", (30, 0), chain_rank=0),
        oracle.GroupMember("r2", "filter", (10, 0), chain_rank=1),
    )
    assert oracle.evaluate_grouping_candidate("ordered", ordered).series_order_penalty == 0
    score = oracle.evaluate_grouping_candidate("reversed", reversed_chain)
    assert score.series_order_penalty == 20
    assert score.witnesses[-1].kind == "passive_series_reversal"


def test_dominated_candidate_oracle_preserves_only_non_dominated_layouts() -> None:
    compact = oracle.evaluate_grouping_candidate(
        "compact",
        (
            oracle.GroupMember("a", "stage", (0, 0)),
            oracle.GroupMember("b", "stage", (10, 0)),
        ),
    )
    scattered = oracle.evaluate_grouping_candidate(
        "scattered",
        (
            oracle.GroupMember("a", "stage", (0, 0)),
            oracle.GroupMember("b", "stage", (90, 0)),
        ),
    )
    survivors = oracle.non_dominated_grouping_candidates((scattered, compact))
    assert [candidate.candidate_id for candidate in survivors] == ["compact"]

def test_feedback_owner_distance_has_positive_and_negative_controls() -> None:
    owner = oracle.GroupMember("stage", "gain", (0, 0))
    near_feedback = oracle.GroupMember(
        "feedback", "gain", (30, 0), "stage", "feedback"
    )
    far_feedback = oracle.GroupMember(
        "feedback", "gain", (100, 0), "stage", "feedback"
    )

    near = oracle.evaluate_grouping_candidate(
        "near", (owner, near_feedback), ownership_limit=60
    )
    far = oracle.evaluate_grouping_candidate(
        "far", (owner, far_feedback), ownership_limit=60
    )

    assert near.ownership_penalty == 0
    assert not any(witness.kind == "feedback_owner_distance" for witness in near.witnesses)
    assert far.ownership_penalty == 40
    assert any(witness.kind == "feedback_owner_distance" for witness in far.witnesses)

