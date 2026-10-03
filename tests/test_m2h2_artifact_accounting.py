"""Independent artifact accounting distinguishes proposals from emitted wires."""

import pytest

from run_m2h2_final_artifact_audit import conductor_accounting, verify_emitted_conductors


def test_pruned_router_leaf_is_not_emitted_global_conductor():
    canonical = [[[0, 0], [10, 0]], [[10, 0], [10, 5]]]
    proposal = [[[5, 0], [12, 0]], [[10, 0], [10, 3]]]
    result = conductor_accounting(canonical, proposal, 15, 1)
    assert result["canonical_union_nm"] == 15
    assert result["global_union_nm"] == 8
    assert result["local_residual_nm"] == 7
    assert result["proposed_global_union_nm"] == 10
    assert result["pruned_proposal_union_nm"] == 2


def test_unwitnessed_proposal_or_wrong_canonical_length_fails():
    canonical = [[[0, 0], [10, 0]]]
    with pytest.raises(ValueError, match="no pruning witness"):
        conductor_accounting(canonical, [[[0, 0], [11, 0]]], 10, 0)
    with pytest.raises(ValueError, match="independent interval union"):
        conductor_accounting(canonical, [], 11, 1)


def test_shared_global_local_intervals_are_charged_once():
    result = conductor_accounting(
        [[[0, 0], [10, 0]], [[5, 0], [15, 0]]],
        [[[2, 0], [8, 0]], [[4, 0], [12, 0]]],
        15,
        0,
    )
    assert result["global_union_nm"] == 10
    assert result["local_residual_nm"] == 5


def test_emitted_wire_inventory_is_independent_of_report():
    trees = [{"segments": [[[0, 0], [10, 0]]]}]
    verify_emitted_conductors(trees, [[[10, 0], [0, 0]]])
    with pytest.raises(ValueError, match="emitted schematic bytes"):
        verify_emitted_conductors(trees, [[[0, 0], [11, 0]]])
