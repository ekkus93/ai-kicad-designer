"""Keep baseline regression witnesses ranked without changing acceptance gates."""

from run_m2h2_final_artifact_audit import baseline_regression_diagnostics


def _record(case: str, unresolved: bool, detours: int, repeated_ok: bool) -> dict:
    historic_hard = {"interface_side_violations": 1}
    fresh_hard = {"interface_side_violations": 1 if unresolved else 0}
    return {
        "case": case,
        "historical_hard_defects": historic_hard,
        "fresh_hard_defects": fresh_hard,
        "historical_hard_defect_total": 1,
        "fresh_hard_defect_total": int(unresolved),
        "historical": {
            "fragmentation_total_mm": 10.0,
            "u_shaped_detours": 2,
            "branch_inconsistency_mm": 1.0,
            "interface_side_violations": 1,
            "edge_bias": False,
        },
        "fresh": {
            "fragmentation_total_mm": 12.0,
            "u_shaped_detours": 2 + detours,
            "branch_inconsistency_mm": 2.0,
            "interface_side_violations": int(unresolved),
            "repeated_within_tolerance": repeated_ok,
            "edge_bias": False,
        },
    }


def test_ranked_witnesses_and_i4_are_deterministic():
    cases = [
        _record("other", False, 0, True),
        _record("i4__b2_mixed", True, 3, False),
    ]
    report = baseline_regression_diagnostics(cases, limit=1)
    assert report["affected_count"] == 2
    assert report["omitted_count"] == 1
    assert report["ranked_cases"][0]["case"] == "i4__b2_mixed"
    assert report["ranked_cases"][0]["repeated_out_of_tolerance"]
    assert report["i4"]["case"] == "i4__b2_mixed"
    assert cases[0]["fresh_hard_defects"] == {"interface_side_violations": 0}
