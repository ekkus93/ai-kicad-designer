"""Preserve structural regressions found by fresh locked qualification."""

import json
from collections import Counter

import pytest

from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import compose_with_evidence


@pytest.mark.parametrize(
    "path",
    [
        "fixtures/m2blind_v5/ir/V5-3.json",
        "fixtures/m2blind_v6/ir/V6-5.json",
        "fixtures/m2blind_v6/ir/V6-6.json",
        "fixtures/m2blind_v6/ir/V6-8.json",
        "fixtures/m2h2/development/dp4.json",
        "fixtures/m2f2/ir/two_signal_chains_shared_rail.json",
        "fixtures/m2h2/interaction/i1/d2_b3.json",
        "fixtures/m2h2/interaction/i1/d3_b3.json",
        "fixtures/m2h2/interaction/i3/selected_triple.json",
    ],
)
def test_fresh_qualification_failures_have_complete_bounded_composition(path):
    resolved = assets()
    design = validate(json.loads((ROOT / path).read_text()), resolved)
    _scene, evidence = compose_with_evidence(design, resolved)
    assert evidence["budgets"]["seed_limit"] == 8
    assert evidence["budgets"]["complete_attempt_limit"] == 32
    assert evidence["budgets"]["complete_attempts_used"] <= 32
    assert any(attempt["result"] == "pass" for attempt in evidence["layout_attempts"])
    assert all(tree["length_nm"] <= 250_000_000 for tree in evidence["canonical_trees"])
    for _obligation, actual, limit in evidence["obligation_certificate"]["placement_witnesses"]:
        assert actual >= limit if limit == 1 else actual <= limit
    if path.endswith("V6-8.json"):
        supply = next(tree for tree in evidence["canonical_trees"] if tree["net"] == "VCC")
        degree = Counter(tuple(point) for segment in supply["segments"] for point in segment)
        gateways = [
            witness
            for witness in evidence["obligation_certificate"]["gateway_witnesses"]
            if witness["net"] == "VCC"
        ]
        label_contacts = {point for net, point in _scene.labels if net == "VCC"}
        assert all(
            degree[tuple(witness["point"])] >= 2 or tuple(witness["point"]) in label_contacts
            for witness in gateways
        )
