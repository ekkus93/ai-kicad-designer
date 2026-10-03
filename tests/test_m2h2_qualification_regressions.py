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


def test_three_timer_whole_band_has_certified_geometry_and_bounded_search():
    from argparse import Namespace

    from ai_kicad.m2_fragments import fragment_variants
    from ai_kicad.m2_semantics import semantic_plan
    from run_m2h2_structural_alternative import select_scene

    resolved = assets()
    path = ROOT / "fixtures/m2h2/interaction/i3/a3_one.json"
    design = validate(json.loads(path.read_text()), resolved)
    variants = fragment_variants(design, resolved, semantic_plan(design, resolved))
    timers = [family for family in variants.values() if family[0].block.kind == "timer"]
    assert len(timers) == 3
    for family in timers:
        assert len(family) <= 8
        rules = {item.rule_id for item in family}
        assert any(".expanded." in rule for rule in rules)
        assert any(".compact." in rule for rule in rules)
        assert any(".narrow." in rule for rule in rules)
    args = Namespace(bands=1, core_bands=False, minimum_bands=False, interleaved=False)
    scene, _routes, trees, _reservations, packing, _index, _retry, ledger = select_scene(
        design, resolved, args
    )
    # Independent envelope check includes every non-interface cell, not only cores.
    cells = [item for item in packing.fragments if item.fragment.block.kind != "interface"]
    assert len(cells) == 3
    assert len({item.envelope[1] for item in cells}) == 1
    ordered = sorted(cells, key=lambda item: item.envelope[0])
    assert all(a.envelope[2] < b.envelope[0] for a, b in zip(ordered, ordered[1:]))
    assert scene.metrics["final_content_width_mm"] <= 210
    assert scene.metrics["final_content_height_mm"] <= 140
    assert all(tree.length <= 250_000_000 for tree in trees)
    assert ledger["candidate_budget"] == 8
    assert ledger["slot_ceiling"] == 32
    assert 0 < ledger["complete_attempts"] <= 32


def test_local_construction_budget_counts_rejections_and_preserves_uncovered(monkeypatch):
    import ai_kicad.m2_fragments as fragments
    from ai_kicad.m2_semantics import semantic_plan

    calls = Counter()
    original = fragments._finish

    def count_actual_construction(*args, **kwargs):
        calls[args[2].id] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(fragments, "_finish", count_actual_construction)
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2h2/development/dp2.json").read_text()), resolved
    )
    families = fragments.fragment_variants(design, resolved, semantic_plan(design, resolved))
    for block_id, family in families.items():
        evidence = family[0].construction_evidence()
        assert calls[block_id] <= evidence["proposals_attempted"] <= 32
        assert len(family) <= 8
        assert all(item.construction_trace == family[0].construction_trace for item in family)
        assert all(attempt[2] in {"certified", "rejected"} for attempt in evidence["attempts"])
    packages = [
        family[0] for family in families.values() if family[0].block.kind == "package_power"
    ]
    assert all(item.construction_uncovered for item in packages)
    assert all(len(item.construction_trace) == 32 for item in packages)
    assert any(attempt[2] == "rejected" for item in packages for attempt in item.construction_trace)
    assert all(item.retention_uncovered for item in packages)


def test_failed_local_constructor_preserves_rejected_proposal_evidence(monkeypatch):
    import ai_kicad.m2_fragments as fragments
    from ai_kicad.ir import InputError
    from ai_kicad.m2_semantics import semantic_plan

    original = fragments._interface_fragment
    calls = 0

    def reject_constructor(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise InputError("injected local geometry rejection")
        return original(*args, **kwargs)

    monkeypatch.setattr(fragments, "_interface_fragment", reject_constructor)
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2h2/interaction/i3/a3_one.json").read_text()), resolved
    )
    plan = semantic_plan(design, resolved)
    with pytest.raises(InputError, match="injected local geometry rejection") as failure:
        fragments.fragment_variants(design, resolved, plan)
    evidence = failure.value.local_construction_evidence
    assert evidence["fragment"] == plan.blocks[1].id
    assert plan.blocks[0].id in evidence["completed_fragments"]
    assert evidence["proposals_attempted"] == 1
    assert evidence["attempts"][0][2] == "rejected"
    assert evidence["attempts"][0][3] == "injected local geometry rejection"
    assert json.loads(json.dumps(evidence)) == evidence
