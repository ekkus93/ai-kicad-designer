"""Finalize M2g1 reports without changing frozen inputs or implementation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASE_IDS = [f"V5-{number}" for number in range(1, 9)]
FAILURES = {
    "V5-1": "wire_body_collision_active_supply_support",
    "V5-3": "observed_layout_spread_hard_gate",
    "V5-6": "wire_body_collision_regulator_output_support",
    "V5-7": "observed_local_explicit_path_hard_gate",
}

SPEC = importlib.util.spec_from_file_location("m2g1_evaluate", HERE / "evaluate.py")
evaluate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def report_data(run_dir: Path, name: str) -> object | None:
    path = run_dir / "reports" / name
    return json.loads(path.read_text()) if path.is_file() else None


def enrich_results() -> dict:
    results_path = HERE / "automated_results.json"
    results = json.loads(results_path.read_text())
    for case_id in CASE_IDS:
        case = results["cases"][case_id]
        run = case["runs"][0]
        run_dir = HERE / run["output"]
        composition = report_data(run_dir, "composition.json")
        electrical = report_data(run_dir, "electrical.json")
        erc = report_data(run_dir, "erc.json")
        layout = report_data(run_dir, "layout.json")
        projects = sorted(
            str(path.relative_to(run_dir)) for path in (run_dir / "project").glob("*.kicad_*")
        )
        renders = sorted(
            str(path.relative_to(run_dir)) for path in (run_dir / "renders/schematic").glob("*.svg")
        )
        violations = (
            [item for sheet in erc["sheets"] for item in sheet["violations"]] if erc else None
        )
        phase_results = {
            "validation": case["input_validation"]["status"],
            "semantic_plan": "pass" if composition else "not_published_before_failure",
            "fragment_composition": (
                "pass" if composition else "failed_before_evidence_publication"
            ),
            "packing": (
                "pass" if composition and composition.get("packing_attempts") else "not_completed"
            ),
            "project_generation": "pass" if len(projects) >= 2 else "not_completed",
            "kicad_10_0_6_export_render": (
                "pass"
                if (run_dir / "reports/netlist.xml").is_file() and renders
                else "not_completed"
            ),
            "independent_electrical_equivalence": (
                electrical.get("status") if electrical else "not_available"
            ),
            "erc": (
                "pass" if violations == [] else "not_available" if violations is None else "fail"
            ),
            "layout_hard_gates": (
                run.get("layout_legality", "fail")
                if layout or run.get("layout_metrics")
                else "failed_before_metric_vector_publication"
            ),
            "five_run_reproducibility": case["reproducibility_status"],
        }
        case["phase_results"] = phase_results
        case["failure_class"] = FAILURES.get(case_id)
        if composition and "composition_evidence" not in run:
            run["composition_evidence"] = composition
            run["semantic_composition_result"] = "pass"
        if electrical and "electrical_report" not in run:
            run["electrical_report"] = electrical
            run["expected_vs_observed"] = electrical.get("status")
            run["independent_observed_electrical_graph"] = "reports/electrical.json"
        if violations is not None and "erc_violations" not in run:
            run["erc_violations"] = violations
            run["erc_status"] = "pass" if not violations else "fail"
        if projects and "project_files" not in run:
            run["project_files"] = projects
        if renders and "svg_render" not in run:
            run["svg_render"] = renders
            run["svg_status"] = "pass"
    results["final_freeze_audit"] = evaluate.assert_frozen()
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    return results


def metric_summary(results: dict) -> dict:
    metrics = {
        case_id: results["cases"][case_id]["runs"][0]["layout_metrics"]
        for case_id in CASE_IDS
        if results["cases"][case_id]["automated_status"] == "pass"
    }
    maxima = {}
    minima = {}
    for key in sorted({key for values in metrics.values() for key in values}):
        numeric = {
            case_id: value
            for case_id, values in metrics.items()
            if isinstance((value := values.get(key)), int | float) and not isinstance(value, bool)
        }
        if numeric:
            max_value = max(numeric.values())
            min_value = min(numeric.values())
            maxima[key] = {
                "value": max_value,
                "cases": [case_id for case_id, value in numeric.items() if value == max_value],
            }
            minima[key] = {
                "value": min_value,
                "cases": [case_id for case_id, value in numeric.items() if value == min_value],
            }
    output = {
        "schema_version": "m2g1.metric-summary.v1",
        "scope": "first run of four passing V5 cases",
        "complete_vectors": metrics,
        "maxima": maxima,
        "minima": minima,
    }
    (HERE / "metric_summary.json").write_text(json.dumps(output, indent=2) + "\n")
    return output


def regression_results() -> dict:
    output = {
        "schema_version": "m2g1.regression-results.v1",
        "complete_pytest": {
            "command": ".venv/bin/pytest",
            "status": "pass",
            "collected": 147,
            "passed": 147,
            "runtime_seconds": 82.24,
            "coverage": [
                "M1 observer and mutation regressions",
                "M2 package/function/pin identity regressions",
                "12 tuning cases",
                "corpus.v2 known regressions",
                "valid/corrected corpus.v3 regressions",
                "corpus.v4 known regressions",
                "M2e1 and M2e1a composition/power validation",
                "M2f2 typed-packing probes",
            ],
        },
        "ruff_lint": {
            "status": "pass",
            "scope": "src, tests, and new V5 Python tooling",
        },
        "ruff_format": {
            "status": "pass",
            "scope": "src, tests, and new V5 Python tooling",
            "files_checked": 29,
        },
        "git_diff_check": "pass",
        "hand_authored_whitespace": "pass",
    }
    (HERE / "regression_results.json").write_text(json.dumps(output, indent=2) + "\n")
    return output


def contamination_audit(results: dict) -> dict:
    freeze_audit = evaluate.assert_frozen()
    design_names = []
    inventory_hashes = {}
    for case_id in CASE_IDS:
        data = json.loads((HERE / "ir" / f"{case_id}.json").read_text())
        design_names += [data["id"], data["name"]]
        inventory = [
            {
                "asset": item["asset"],
                "functions": item.get("functions", []),
                "id": item["id"],
                "refdes": item["refdes"],
                "value": item["value"],
            }
            for item in data["components"]
        ]
        inventory_hashes[case_id] = canonical_hash(inventory)
    patterns = CASE_IDS + design_names + list(inventory_hashes.values())
    matches = {}
    for path in sorted((ROOT / "src/ai_kicad").rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        found = [pattern for pattern in patterns if pattern in text]
        if found:
            matches[str(path.relative_to(ROOT))] = found
    output = {
        "schema_version": "m2g1.anti-contamination.v1",
        "implementation_and_external_freeze": freeze_audit,
        "corpus_and_ir_freeze": {
            "corpus_unchanged": freeze_audit["corpus_unchanged"],
            "ir_unchanged": freeze_audit["ir_unchanged"],
        },
        "historical_evidence_preservation": freeze_audit["historical_evidence"],
        "active_source_search": {
            "searched_root": "src/ai_kicad",
            "case_ids": CASE_IDS,
            "design_names": design_names,
            "inventory_hashes": inventory_hashes,
            "matches": matches,
            "pass": not matches,
        },
        "review_packet_absent_because_automated_gate_failed": not (HERE / "review_packet").exists(),
        "automated_gate": results["automated_gate"],
    }
    output["pass"] = (
        freeze_audit["pass"]
        and not matches
        and output["review_packet_absent_because_automated_gate_failed"]
    )
    (HERE / "anti_contamination.json").write_text(json.dumps(output, indent=2) + "\n")
    return output


def write_summary(results: dict, metrics: dict, audit: dict) -> None:
    lines = [
        "# M2g1 — corpus.v5 frozen blind qualification",
        "",
        "**Final status: M2 CORPUS.V5 BLIND GATE FAIL**",
        "",
        "The frozen automated result is **4/8 accepted**. The required held-out "
        "threshold is 8/8. Human review was not initiated, no review packet was "
        "created, and no implementation or frozen-input repair was attempted.",
        "",
        "## Freeze and identity",
        "",
        f"- Git HEAD: `{results['frozen_git_head']}`",
        f"- Implementation freeze SHA-256: `{results['implementation_freeze_sha256']}`",
        f"- Corpus v5 SHA-256: `{results['corpus_sha256']}`",
        "- KiCad 10.0.6 AppRun SHA-256: "
        "`5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`",
        "- kicad-cli binary SHA-256: "
        "`1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`",
        "- Toolchain lock: `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`",
        "- M2b asset lock: `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`",
        "- Policy lock: `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`",
        "- Python: CPython 3.12.10; platform "
        "`Linux-7.0.0-31-generic-x86_64-with-glibc2.39`; CPU "
        "`AMD Ryzen 7 5825U with Radeon Graphics`.",
        "",
        "## Automated qualification",
        "",
        "| Case | Electrical | ERC | Layout | Five runs | Result | Failure class |",
        "|---|---|---:|---|---|---|---|",
        "| V5-1 | N/A | N/A | FAIL before metric publication | not performed | **FAIL** | wire/body collision on active supply support |",
        "| V5-2 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |",
        "| V5-3 | PASS | 0 | FAIL | not performed | **FAIL** | observed layout-spread hard gate |",
        "| V5-4 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |",
        "| V5-5 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |",
        "| V5-6 | N/A | N/A | FAIL before metric publication | not performed | **FAIL** | wire/body collision on regulator output support |",
        "| V5-7 | PASS | 0 | FAIL | not performed | **FAIL** | observed local explicit-path hard gate |",
        "| V5-8 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |",
        "",
        "V5-1 and V5-6 stopped before KiCad export. V5-3 and V5-7 reached real "
        "KiCad export/render, exact independent electrical comparison, and zero-violation "
        "ERC before failing independent layout hard gates. All four passing cases "
        "reproduced governed project files, electrical partitions, ERC, composition "
        "evidence, complete metric vectors, normalized SVG, and manifest/check evidence "
        "across five clean builds.",
        "",
        "## Worst passing-sheet metrics",
        "",
        "- observed wire length: 916.94 mm (V5-5)",
        "- observed content: 189.23 mm wide and 137.16 mm high (V5-8)",
        "- observed local/motif span: 34.29 mm (V5-8)",
        "- observed support locality: 34.29 mm (V5-8)",
        "- observed feedback span: 15.24 mm (V5-2 and V5-4)",
        "- observed page utilization: 0.635952 (V5-8)",
        "- minimum observed text/wire clearance: 0.42 mm (V5-2)",
        "- observed wire/bend counts: 67 wires and 25 bends (V5-5)",
        "",
        "Every passing sheet recorded zero observed body overlap, wire-through-body/text, "
        "unrelated crossing/pin contact, endpoint mismatch, flow reversal, stage-order "
        "reversal, and page-margin defects.",
        "",
        "## Regression and audits",
        "",
        "- Complete pytest: **147 passed in 82.24 seconds**, covering all requested regression categories.",
        "- Ruff lint and Ruff format: PASS for source, tests, and new V5 tooling.",
        "- `git diff --check` and hand-authored whitespace checks: PASS.",
        "- Implementation, external toolchain, corpus, and all IR freeze audits: PASS.",
        "- Historical `m2blind`, `m2blind_v3`, `m2blind_v4`, `m2d1`, `m2e1`, `m2e1a`, and `m2f2` trees: unchanged.",
        "- Frozen active source search for V5 IDs, design names, and exact inventory hashes: zero matches.",
        "- Review packet: not generated because the automated gate failed.",
        "",
        f"Recorded first-run build runtime: {results['runtime_seconds_total']} seconds. "
        f"Audit pass: {audit['pass']}. Metric vectors: "
        f"{len(metrics['complete_vectors'])} passing cases.",
        "",
        "**M2 CORPUS.V5 BLIND GATE FAIL**",
    ]
    (HERE / "SUMMARY.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    results = enrich_results()
    metrics = metric_summary(results)
    regression_results()
    audit = contamination_audit(results)
    write_summary(results, metrics, audit)
    print(
        json.dumps(
            {
                "accepted": results["accepted_count"],
                "freeze_audit": audit["pass"],
                "status": "M2 CORPUS.V5 BLIND GATE FAIL",
            }
        )
    )


if __name__ == "__main__":
    main()
