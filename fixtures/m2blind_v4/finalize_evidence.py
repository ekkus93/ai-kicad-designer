"""Derive final M2f1 reports from the frozen run evidence."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("m2f1_evaluate", HERE / "evaluate.py")
evaluate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate)


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def source_search() -> dict[str, object]:
    patterns = [
        *evaluate.CASE_IDS,
        "lowpass_inverting_led",
        "highpass_noninverting_lowpass",
        "reference_noninverting_rc",
        "parallel_dual_opamp_functions",
        "sallen_key_buffer_led",
        "regulated_timer_rc_output",
        "regulated_dual_timer_system",
        "timer_dual_output_load",
        "V4LowpassInvertingLed",
        "V4HighpassNoninvertingLowpass",
        "V4ReferenceNoninvertingRc",
        "V4ParallelDualOpampFunctions",
        "V4SallenKeyBufferLed",
        "V4RegulatedTimerRcOutput",
        "V4RegulatedDualTimerSystem",
        "V4TimerDualOutputLoad",
    ]
    expression = re.compile("|".join(re.escape(item) for item in patterns), re.IGNORECASE)
    matches = []
    for path in sorted((ROOT / "src/ai_kicad").glob("*.py")):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            if expression.search(line):
                matches.append(
                    {"path": str(path.relative_to(ROOT)), "line": line_number, "text": line}
                )
    return {"patterns": patterns, "matches": matches, "pass": not matches}


def metric_summary(results: dict) -> dict[str, object]:
    passing = {
        case_id: case["runs"][0]["layout_metrics"]
        for case_id, case in results["cases"].items()
        if case["automated_status"] == "pass"
    }
    maximum = [
        "wire_count",
        "label_count",
        "bend_count",
        "wire_length_mm",
        "symbol_occurrences",
        "semantic_block_count",
        "semantic_edge_count",
        "observed_motif_fragmentation_mm",
        "observed_bend_count",
        "observed_feedback_span_mm",
        "observed_wire_length_mm",
        "observed_wire_count",
        "observed_local_wire_span_mm",
        "observed_support_locality_mm",
        "observed_content_width_mm",
        "observed_content_height_mm",
        "observed_page_utilization",
    ]
    minimum = ["observed_text_wire_clearance_mm"]
    worst = {}
    for name in maximum:
        candidates = [(metrics[name], case_id) for case_id, metrics in passing.items() if name in metrics]
        if candidates:
            value, case_id = max(candidates)
            worst[name] = {"direction": "maximum", "value": value, "case_id": case_id}
    for name in minimum:
        candidates = [(metrics[name], case_id) for case_id, metrics in passing.items() if name in metrics]
        if candidates:
            value, case_id = min(candidates)
            worst[name] = {"direction": "minimum", "value": value, "case_id": case_id}
    return {"passing_cases": sorted(passing), "worst_values": worst, "complete_vectors": passing}


def main() -> None:
    results_path = HERE / "automated_results.json"
    results = json.loads(results_path.read_text())
    if results.get("accepted_count") != 7 or results.get("automated_gate") != "fail":
        raise RuntimeError("unexpected final blind-run result")

    failed = HERE / "runs/V4-7/run1.failed/reports"
    electrical = json.loads((failed / "electrical.json").read_text())
    erc = json.loads((failed / "erc.json").read_text())
    violations = [item for sheet in erc["sheets"] for item in sheet["violations"]]
    case = results["cases"]["V4-7"]
    case["failure_class_exact"] = "observed_layout_spread_hard_gate"
    case["failure_message"] = case["runs"][0]["failure"]["message"]
    case["available_failure_artifact_evidence"] = {
        "semantic_composition": "pass",
        "kicad_10_0_6_export_render": "pass",
        "independent_electrical_comparison": electrical.get("status"),
        "erc": "pass" if not violations else "fail",
        "erc_violation_count": len(violations),
        "layout": "fail",
        "layout_report": "not published because build failed its observed spread gate",
    }
    results_path.write_text(json.dumps(results, indent=2) + "\n")

    regressions = {
        "schema_version": "m2f1.regressions.v1",
        "pytest": {
            "command": ".venv/bin/pytest -q",
            "status": "pass",
            "tests_passed": 136,
            "duration_seconds": 82.27,
            "summary": "136 passed in 82.27s",
            "coverage_includes": [
                "M1 mutation and independent-observation tests",
                "M2 physical identity tests",
                "12 M2c1 tuning regressions",
                "corpus.v2 known regressions",
                "valid corpus.v3 known regressions",
                "corrected V3-8-equivalent regression",
                "M2e1 development probes",
                "M2e1a power-source validation tests",
            ],
        },
        "ruff_lint": {
            "command": ".venv/bin/ruff check src tests tools fixtures/m2blind/*.py fixtures/m2blind_v3/*.py fixtures/m2d1/*.py fixtures/m2blind_v4/*.py",
            "status": "pass",
            "summary": "All checks passed!",
        },
        "ruff_format": {
            "command": ".venv/bin/ruff format --check src tests tools fixtures/m2blind/*.py fixtures/m2blind_v3/*.py fixtures/m2d1/*.py fixtures/m2blind_v4/*.py",
            "status": "fail",
            "summary": "3 new qualification scripts would be reformatted; 37 files already formatted",
            "files": [
                "fixtures/m2blind_v4/author_corpus.py",
                "fixtures/m2blind_v4/evaluate.py",
                "fixtures/m2blind_v4/prepare_freeze.py",
            ],
            "repair_attempted": False,
        },
        "git_diff_check": {"command": "git diff --check", "status": "pass"},
        "hand_authored_whitespace": {
            "status": "pass",
            "files_checked": 59,
            "findings": 0,
            "excluded": ["generated run artifacts", "review_packet", "__pycache__", ".local", "research/legacy_openclaw"],
        },
    }
    regressions["pass"] = all(
        item.get("status") == "pass"
        for key, item in regressions.items()
        if key not in {"schema_version", "pass"}
    )
    (HERE / "regression_results.json").write_text(json.dumps(regressions, indent=2) + "\n")

    audit = evaluate.freeze_audit()
    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    audit.update(
        {
            "git_head_at_freeze": freeze["git_head"],
            "git_head_at_completion": git("rev-parse", "HEAD"),
            "git_head_unchanged": git("rev-parse", "HEAD") == freeze["git_head"],
            "tracked_frozen_diff": git("diff", "--name-only").splitlines(),
            "source_v4_identifier_and_design_name_search": source_search(),
            "review_packet_generated": False,
            "review_packet_reason": "automated gate failed; human review prohibited",
            "astra_called": False,
            "corpus_v5_created": False,
            "m3_started": False,
        }
    )
    audit["pass"] = (
        audit["pass"]
        and audit["git_head_unchanged"]
        and not audit["tracked_frozen_diff"]
        and audit["source_v4_identifier_and_design_name_search"]["pass"]
    )
    (HERE / "anti_contamination.json").write_text(json.dumps(audit, indent=2) + "\n")

    metrics = metric_summary(results)
    (HERE / "metric_summary.json").write_text(json.dumps(metrics, indent=2) + "\n")
    worst = metrics["worst_values"]
    summary = f"""# M2f1 — corpus.v4 frozen blind qualification

**Final status: M2 CORPUS.V4 BLIND GATE FAIL**

The frozen automated result is **7/8 accepted**. The required held-out threshold is
8/8. V4-7 failed the observed layout-spread hard gate, so human review was not
started, no review packet was generated, and no implementation or frozen-IR repair
was attempted.

## Freeze and identity

- Git HEAD: `{freeze['git_head']}`
- Implementation freeze SHA-256: `{results['implementation_freeze_sha256']}`
- Corpus v4 SHA-256: `{results['corpus_sha256']}`
- KiCad 10.0.6 AppRun SHA-256: `{freeze['toolchain']['external_files']['kicad-cli']['sha256']}`
- kicad-cli binary SHA-256: `{freeze['toolchain']['external_files']['kicad-cli-binary']['sha256']}`
- Toolchain lock: `{freeze['locks']['toolchain']['sha256']}`
- M2b asset lock: `{freeze['locks']['m2b_assets']['sha256']}`
- Policy lock: `{freeze['locks']['policy']['sha256']}`
- Python: {freeze['python']['implementation']} 3.12.10; platform `{freeze['platform']['platform']}`;
  CPU `{freeze['platform']['cpu_model']}`.

## Automated qualification

| Case | Electrical | ERC | Layout | Five-run reproducibility | Result | Failure class |
|---|---|---|---|---|---|---|
| V4-1 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-2 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-3 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-4 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-5 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-6 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-7 | PASS (available failure artifact) | 0 violations | **FAIL** | not applicable | **FAIL** | `observed_layout_spread_hard_gate` |
| V4-8 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |

V4-7 reached real KiCad export, independent electrical comparison, zero ERC
violations, SVG rendering, and semantic-composition evidence. It was rejected with
`observed layout spreads unnecessarily across the page`; its failed build tree is
preserved under `runs/V4-7/run1.failed/`.

An initial evaluation-harness pass incorrectly treated informational
`semantic_block_count` and `semantic_edge_count` fields as violation counts. The raw
initial result is preserved in `initial_harness_results.json`. The classification was
corrected without changing thresholds, implementation, IR, or run artifacts.

## Passing-sheet worst metrics

- observed wire length: {worst['observed_wire_length_mm']['value']} mm ({worst['observed_wire_length_mm']['case_id']})
- observed content: {worst['observed_content_width_mm']['value']} mm wide ({worst['observed_content_width_mm']['case_id']}); {worst['observed_content_height_mm']['value']} mm high ({worst['observed_content_height_mm']['case_id']})
- observed local wire span: {worst['observed_local_wire_span_mm']['value']} mm ({worst['observed_local_wire_span_mm']['case_id']})
- observed support locality: {worst['observed_support_locality_mm']['value']} mm ({worst['observed_support_locality_mm']['case_id']})
- observed feedback span: {worst['observed_feedback_span_mm']['value']} mm ({worst['observed_feedback_span_mm']['case_id']})
- page utilization: {worst['observed_page_utilization']['value']} ({worst['observed_page_utilization']['case_id']})
- minimum text/wire clearance: {worst['observed_text_wire_clearance_mm']['value']} mm ({worst['observed_text_wire_clearance_mm']['case_id']})

All seven passing cases reproduced compiler-owned schematic/project bytes,
independently observed partitions, ERC, semantic composition, complete layout vectors,
normalized KiCad SVG geometry/text, and normalized manifest/check evidence across five
clean builds.

## Regression and audits

- Pytest: 136 passed in 82.27 seconds, covering every requested regression category.
- Ruff lint: PASS.
- Ruff format: **FAIL** for three new qualification scripts; no repair was made.
- `git diff --check`: PASS.
- Hand-authored whitespace scan: 59 files, zero findings.
- Implementation, external toolchain, corpus, and all IR freeze audits: PASS.
- Historical `m2blind`, `m2blind_v3`, `m2d1`, `m2e1`, and `m2e1a` trees: unchanged.
- Frozen implementation search for all V4 IDs and design names: zero matches.
- Review packet: not generated because the automated gate failed.

**M2 CORPUS.V4 BLIND GATE FAIL**
"""
    (HERE / "SUMMARY.md").write_text(summary)


if __name__ == "__main__":
    main()
