"""Correct the informational-count harness classification and finish accepted reruns."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("m2f1_evaluate", HERE / "evaluate.py")
evaluate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate)


def main() -> None:
    evaluate.assert_frozen()
    results_path = HERE / "automated_results.json"
    original_path = HERE / "initial_harness_results.json"
    if original_path.exists():
        raise RuntimeError("completion already performed")
    results = json.loads(results_path.read_text())
    original_path.write_text(json.dumps(copy.deepcopy(results), indent=2) + "\n")
    reproducibility = json.loads((HERE / "reproducibility.json").read_text())
    correction = {
        "classification": "evaluation_harness_field_classification_correction",
        "changed_fields": ["semantic_block_count", "semantic_edge_count"],
        "reason": "informational semantic inventory counts are not layout violation counts",
        "threshold_changes": [],
        "implementation_changes": [],
        "ir_changes": [],
        "preserved_initial_results": "initial_harness_results.json",
    }
    for case_id in evaluate.CASE_IDS:
        case = results["cases"][case_id]
        first = case["runs"][0]
        if first.get("generation_result") != "pass":
            continue
        layout = first["layout_metrics"]
        corrected_pass = evaluate.hard_layout_pass(layout)
        manifest_pass = all(value == "pass" for value in first["manifest"]["checks"].values())
        if not corrected_pass or not manifest_pass:
            continue
        first["layout_legality"] = "pass"
        first["automated_run_pass"] = True
        first.pop("failure_class", None)
        for ordinal in range(2, 6):
            case["runs"].append(evaluate.run_build(case_id, ordinal))
        repro = evaluate.compare_runs(case_id, case["runs"])
        reproducibility["cases"][case_id] = repro
        passed = all(run.get("automated_run_pass") for run in case["runs"]) and repro["pass"]
        case["automated_status"] = "pass" if passed else "fail"
        case["failure_class"] = None if passed else "reproducibility"
        case["reproducibility_status"] = "pass" if repro["pass"] else "fail"
        results_path.write_text(json.dumps(results, indent=2) + "\n")
        (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
        print(case_id, case["automated_status"], flush=True)
    results["accepted_count"] = sum(
        case["automated_status"] == "pass" for case in results["cases"].values()
    )
    results["required_accepted_count"] = 8
    results["automated_gate"] = "pass" if results["accepted_count"] == 8 else "fail"
    results["evaluation_harness_correction"] = correction
    results["final_freeze_audit"] = evaluate.assert_frozen()
    results["runtime_seconds_total"] = round(
        sum(run["runtime_seconds"] for case in results["cases"].values() for run in case["runs"]), 3
    )
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
    print(f"automated gate: {results['accepted_count']}/8")


if __name__ == "__main__":
    main()
