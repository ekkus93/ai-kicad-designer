"""Correct the V4-harness count classification and complete V6 reproducibility."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("m2h1_evaluate", HERE / "evaluate.py")
evaluation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluation)


def main() -> None:
    evaluation.assert_frozen()
    results_path = HERE / "automated_results.json"
    initial_path = HERE / "initial_harness_results.json"
    if initial_path.exists():
        raise SystemExit("completion already performed")
    original = results_path.read_bytes()
    initial_path.write_bytes(original)
    results = json.loads(original)
    reproducibility = json.loads((HERE / "reproducibility.json").read_text())

    for case_id in ("V6-1", "V6-5", "V6-7"):
        case = results["cases"][case_id]
        run1 = case["runs"][0]
        if not evaluation.hard_layout_pass(run1["layout_metrics"]):
            raise RuntimeError(f"{case_id} still fails corrected hard-layout classification")
        if not all(status == "pass" for status in run1["manifest"]["checks"].values()):
            raise RuntimeError(f"{case_id} manifest did not pass")
        run1["layout_legality"] = "pass"
        run1["automated_run_pass"] = True
        run1.pop("failure_class", None)
        for ordinal in range(2, 6):
            run1.setdefault(
                "harness_correction",
                {
                    "reason": "M2g2 informational attempt/repair/tree counts are not violations",
                    "original_evidence": "initial_harness_results.json",
                },
            )
            case["runs"].append(evaluation.base.run_build(case_id, ordinal))
        repro = evaluation.base.compare_runs(case_id, case["runs"])
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
    results["final_freeze_audit"] = evaluation.assert_frozen()
    results["runtime_seconds_total"] = round(
        sum(run["runtime_seconds"] for case in results["cases"].values() for run in case["runs"]),
        3,
    )
    results["harness_correction"] = {
        "scope": "V6 evaluation tooling only",
        "implementation_or_ir_changed": False,
        "original_results": "initial_harness_results.json",
        "correction": "informational M2g2 count fields excluded from zero-violation test",
    }
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
    print(f"automated gate: {results['accepted_count']}/8")


if __name__ == "__main__":
    main()
