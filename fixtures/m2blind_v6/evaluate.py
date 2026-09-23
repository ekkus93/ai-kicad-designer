"""Execute frozen corpus.v6 and preserve complete automated evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASE_IDS = [f"V6-{number}" for number in range(1, 9)]

SPEC = importlib.util.spec_from_file_location(
    "m2f1_evaluate_for_v6", ROOT / "fixtures/m2blind_v4/evaluate.py"
)
base = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(base)
base.HERE = HERE
base.CASE_IDS = CASE_IDS


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_map(base_path: Path) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(base_path.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def freeze_audit() -> dict[str, object]:
    freeze_path = HERE / "implementation_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    expected_freeze = (HERE / "implementation_freeze.sha256").read_text().split()[0]
    source_changed = [
        path
        for path, expected in freeze["tracked_files"].items()
        if not (ROOT / path).is_file() or sha256(ROOT / path) != expected
    ]
    external_changed = [
        item["path"]
        for item in freeze["toolchain"]["external_files"].values()
        if not Path(item["path"]).is_file() or sha256(Path(item["path"])) != item["sha256"]
    ]
    expected_irs = json.loads((HERE / "ir.sha256.json").read_text())
    ir_changed = [
        case_id
        for case_id, expected in expected_irs.items()
        if sha256(HERE / "ir" / f"{case_id}.json") != expected
    ]
    historical = {}
    for relative, baseline in freeze["historical_evidence_before"].items():
        current = file_map(ROOT / relative)
        historical[relative] = {
            "file_count": len(current),
            "canonical_file_map_sha256": base.map_digest(current),
            "unchanged": current == baseline["files"],
        }
    result = {
        "implementation_freeze_sha256": sha256(freeze_path),
        "implementation_freeze_self_hash_pass": sha256(freeze_path) == expected_freeze,
        "tracked_frozen_files_unchanged": not source_changed,
        "tracked_frozen_files_changed": source_changed,
        "external_toolchain_unchanged": not external_changed,
        "external_toolchain_changed": external_changed,
        "corpus_sha256": sha256(HERE / "corpus.v6.json"),
        "corpus_unchanged": sha256(HERE / "corpus.v6.json")
        == (HERE / "corpus.v6.sha256").read_text().split()[0],
        "ir_unchanged": not ir_changed,
        "ir_changed": ir_changed,
        "historical_evidence": historical,
    }
    result["pass"] = all(
        [
            result["implementation_freeze_self_hash_pass"],
            result["tracked_frozen_files_unchanged"],
            result["external_toolchain_unchanged"],
            result["corpus_unchanged"],
            result["ir_unchanged"],
            all(item["unchanged"] for item in historical.values()),
        ]
    )
    return result


def assert_frozen() -> dict[str, object]:
    result = freeze_audit()
    if not result["pass"]:
        raise RuntimeError(f"freeze violation: {json.dumps(result, sort_keys=True)}")
    return result


base.freeze_audit = freeze_audit
base.assert_frozen = assert_frozen


def hard_layout_pass(layout: dict[str, object]) -> bool:
    informational_counts = {
        "wire_count",
        "label_count",
        "bend_count",
        "symbol_occurrences",
        "semantic_block_count",
        "semantic_edge_count",
        "layout_attempt_count",
        "layout_repair_count",
        "observed_bend_count",
        "observed_wire_count",
        "observed_raw_wire_count",
        "observed_actual_junction_count",
    }
    counts_ok = all(
        value == 0
        for key, value in layout.items()
        if key.endswith("_count") and key not in informational_counts
    )
    return (
        counts_ok
        and layout.get("page_margin_pass") is True
        and layout.get("observed_page_margin_pass") is True
        and layout.get("reservation_containment_pass") is True
    )


base.hard_layout_pass = hard_layout_pass


def validate_input(case_id: str) -> dict[str, object]:
    try:
        validate(json.loads((HERE / "ir" / f"{case_id}.json").read_text()), assets())
    except Exception as exc:
        return {"status": "fail", "exception": type(exc).__name__, "message": str(exc)}
    return {"status": "pass"}


def main() -> None:
    initial = assert_frozen()
    corpus = json.loads((HERE / "corpus.v6.json").read_text())
    if [case["case_id"] for case in corpus["cases"]] != CASE_IDS:
        raise RuntimeError("unexpected corpus inventory/order")
    if (HERE / "runs").exists() or (HERE / "automated_results.json").exists():
        raise RuntimeError("blind execution already started")
    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    results: dict[str, object] = {
        "schema_version": "m2h1.automated-results.v1",
        "evaluation": "M2h1 — corpus.v6 frozen blind qualification",
        "frozen_git_head": freeze["git_head"],
        "implementation_freeze_sha256": sha256(HERE / "implementation_freeze.json"),
        "corpus_sha256": sha256(HERE / "corpus.v6.json"),
        "ir_sha256": json.loads((HERE / "ir.sha256.json").read_text()),
        "toolchain": freeze["toolchain"],
        "python": freeze["python"],
        "platform": freeze["platform"],
        "initial_freeze_audit": initial,
        "cases": {},
    }
    reproducibility: dict[str, object] = {"schema_version": "m2h1.reproducibility.v1", "cases": {}}
    for case_id in CASE_IDS:
        validation = validate_input(case_id)
        runs = []
        if validation["status"] == "pass":
            runs.append(base.run_build(case_id, 1))
            if runs[0].get("automated_run_pass"):
                for ordinal in range(2, 6):
                    runs.append(base.run_build(case_id, ordinal))
        repro = (
            base.compare_runs(case_id, runs)
            if len(runs) == 5 and all(run.get("automated_run_pass") for run in runs)
            else {
                "pass": False,
                "not_performed_reason": "case did not pass first-run automated gates",
            }
        )
        passed = (
            validation["status"] == "pass"
            and len(runs) == 5
            and all(run.get("automated_run_pass") for run in runs)
            and repro["pass"]
        )
        if validation["status"] != "pass":
            failure_class = "input_validation"
        elif not runs[0].get("automated_run_pass"):
            failure_class = runs[0].get("failure_class", "automated_gate")
        elif not repro["pass"]:
            failure_class = "reproducibility"
        else:
            failure_class = None
        results["cases"][case_id] = {
            "design_id": json.loads((HERE / "ir" / f"{case_id}.json").read_text())["id"],
            "input_validation": validation,
            "automated_status": "pass" if passed else "fail",
            "failure_class": failure_class,
            "runs": runs,
            "reproducibility_status": "pass" if repro["pass"] else "fail",
        }
        reproducibility["cases"][case_id] = repro
        (HERE / "automated_results.json").write_text(json.dumps(results, indent=2) + "\n")
        (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
        print(
            case_id, results["cases"][case_id]["automated_status"], failure_class or "", flush=True
        )
    results["accepted_count"] = sum(
        case["automated_status"] == "pass" for case in results["cases"].values()
    )
    results["required_accepted_count"] = 8
    results["automated_gate"] = "pass" if results["accepted_count"] == 8 else "fail"
    results["final_freeze_audit"] = assert_frozen()
    results["runtime_seconds_total"] = round(
        sum(run["runtime_seconds"] for case in results["cases"].values() for run in case["runs"]), 3
    )
    (HERE / "automated_results.json").write_text(json.dumps(results, indent=2) + "\n")
    (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
    print(f"automated gate: {results['accepted_count']}/8")


if __name__ == "__main__":
    main()
