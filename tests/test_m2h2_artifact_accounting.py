"""Independent artifact accounting distinguishes proposals from emitted wires."""

from collections import Counter
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ai_kicad.m2_compose import compose_with_evidence  # noqa: E402
from ai_kicad.m2b import assets, validate  # noqa: E402
from run_m2h2_final_artifact_audit import conductor_accounting, verify_emitted_conductors  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


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
    emitted = [{"net": "N", "segments": [[[0, 0], [10, 0]]]}]
    verify_emitted_conductors(emitted, [[[10, 0], [0, 0]]])
    with pytest.raises(ValueError, match="schematic bytes"):
        verify_emitted_conductors(emitted, [[[0, 0], [11, 0]]])


def test_physically_connected_label_does_not_preserve_unemitted_gateway_spur():
    resolved = assets()
    design = validate(json.loads((ROOT / "fixtures/m2blind/ir/H1.json").read_text()), resolved)
    scene, evidence = compose_with_evidence(design, resolved)

    canonical = Counter(
        (
            tree["net"],
            *tuple(sorted((tuple(first), tuple(second)))),
        )
        for tree in evidence["canonical_trees"]
        for first, second in tree["segments"]
    )
    emitted = Counter(
        (net, *tuple(sorted((tuple(first), tuple(second)))))
        for (first, second), net in zip(scene.wires, scene.wire_nets, strict=True)
    )
    accounted = Counter(
        (tree["net"], *tuple(sorted((tuple(first), tuple(second)))))
        for tree in evidence["emitted_conductors"]
        for first, second in tree["segments"]
    )
    assert accounted == emitted
    assert canonical - emitted == Counter(
        {("LEDMID", (83820000, 53340000), (87630000, 53340000)): 1}
    )
    verify_emitted_conductors(evidence["emitted_conductors"], [list(wire) for wire in scene.wires])
