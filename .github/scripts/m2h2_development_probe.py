"""Expose bounded current-source composition witnesses without claiming qualification."""
from __future__ import annotations

import json
from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2_composition_tradeoff_report import summarize_comparable_candidates

CASES = {
    "v4-3": "fixtures/m2blind_v4/ir/V4-3.json",
    "v4-7": "fixtures/m2blind_v4/ir/V4-7.json",
    "v5-3": "fixtures/m2blind_v5/ir/V5-3.json",
    "v6-3": "fixtures/m2blind_v6/ir/V6-3.json",
    "v6-5": "fixtures/m2blind_v6/ir/V6-5.json",
    "v6-6": "fixtures/m2blind_v6/ir/V6-6.json",
    "v6-8": "fixtures/m2blind_v6/ir/V6-8.json",
    "dp4": "fixtures/m2h2/development/dp4.json",
    "i4__b2_mixed": "fixtures/m2h2/interaction/i4/b2_mixed.json",
    "shared_rail": "fixtures/m2f2/ir/two_signal_chains_shared_rail.json",
    "passive_fanout": "fixtures/m2g2/probes/passive_two_level_fanout.json",
}
resolved = assets()
for case, relative in CASES.items():
    design = validate(json.loads((ROOT / relative).read_text()), resolved)
    try:
        scene, evidence = compose_with_evidence(design, resolved)
    except InputError as error:
        evidence = getattr(error, "evidence", {})
        print(json.dumps({"kind": "m2h2.development-failure.1", "case": case,
                          "message": str(error), "budgets": evidence.get("budgets")}), flush=True)
        for name in ("layout_attempts", "candidate_decisions", "variants"):
            for item in evidence.get(name, []):
                print(json.dumps({"kind": "m2h2.development-witness.1", "case": case,
                                  "category": name, "item": item}, separators=(",", ":")), flush=True)
    else:
        print(json.dumps({"kind": "m2h2.development-composition.1", "case": case,
                          "result": "composition_only_not_qualification",
                          "labels": scene.labels, "layout": scene.metrics,
                          "selection": evidence["candidate_selection"],
                          "budgets": evidence["budgets"]}, separators=(",", ":")), flush=True)
        print(json.dumps({"kind": "m2h2.development-candidate-tradeoff.1", "case": case,
                          **summarize_comparable_candidates(evidence["candidate_selection"])},
                         separators=(",", ":")), flush=True)
        # Expose which bounded routing strategies actually survive selection.
        # This is observational evidence only, never an acceptance shortcut.
        print(
            json.dumps(
                {
                    "kind": "m2h2.development-route-strategies.1",
                    "case": case,
                    "routes": [
                        {
                            "net": route["net"],
                            "strategy": route["strategy"],
                            "plan_tests": route["plan_tests"],
                            "tap_tests": route["tap_tests"],
                            "state_expansions": route["state_expansions"],
                            "segment_count": len(route["segments"]),
                        }
                        for route in evidence["routes"]
                    ],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        # A single proved candidate cannot be repaired by ranking. Preserve
        # the bounded search/route rejection ledger for generic seed diagnosis.
        selection = evidence["candidate_selection"]
        penalties = selection["selected_semantic_penalty_breakdown"]
        if selection["proved_candidate_count"] <= 1 or any(
            penalties.get(name, 0) for name in
            ("stage_order_violations", "interface_side_violations")
        ):
            print(json.dumps({
                "kind": "m2h2.development-search-witness.1",
                "case": case,
                "proved_candidate_count": selection["proved_candidate_count"],
                "seeds": [
                    {"seed": item["seed"], "placement_class": item["placement_class"]}
                    for item in evidence["structural_search"]["seeds"]
                ],
                "attempts": [
                    {key: item.get(key) for key in
                     ("seed", "round", "operation", "result", "failure_class",
                      "conflict", "net", "actual", "limit")}
                    for item in evidence["layout_attempts"]
                    if item["result"] != "pass"
                ],
            }, separators=(",", ":")), flush=True)
