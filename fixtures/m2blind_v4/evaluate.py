"""Execute the frozen corpus.v4 and preserve complete automated evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOOLCHAIN = ROOT / "fixtures/m1a/toolchain.lock.json"
ASSETS = ROOT / "fixtures/m2b/assets.lock.json"
POLICY = ROOT / "fixtures/m1a/policy.lock.json"
CASE_IDS = [f"V4-{number}" for number in range(1, 9)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_map(base: Path) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def map_digest(files: dict[str, str]) -> str:
    value = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


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
            "canonical_file_map_sha256": map_digest(current),
            "unchanged": current == baseline["files"],
        }
    result = {
        "implementation_freeze_sha256": sha256(freeze_path),
        "implementation_freeze_self_hash_pass": sha256(freeze_path) == expected_freeze,
        "tracked_frozen_files_unchanged": not source_changed,
        "tracked_frozen_files_changed": source_changed,
        "external_toolchain_unchanged": not external_changed,
        "external_toolchain_changed": external_changed,
        "corpus_sha256": sha256(HERE / "corpus.v4.json"),
        "corpus_unchanged": sha256(HERE / "corpus.v4.json")
        == (HERE / "corpus.v4.sha256").read_text().split()[0],
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


def validate_input(case_id: str) -> dict[str, object]:
    try:
        validate(json.loads((HERE / "ir" / f"{case_id}.json").read_text()), assets())
    except Exception as exc:
        return {"status": "fail", "exception": type(exc).__name__, "message": str(exc)}
    return {"status": "pass"}


def hard_layout_pass(layout: dict[str, object]) -> bool:
    allowed = {
        "wire_count",
        "label_count",
        "bend_count",
        "symbol_occurrences",
        "observed_bend_count",
        "observed_wire_count",
        "semantic_block_count",
        "semantic_edge_count",
    }
    counts_ok = all(
        value == 0
        for key, value in layout.items()
        if key.endswith("_count") and key not in allowed
    )
    return counts_ok and layout.get("page_margin_pass") is True and layout.get(
        "observed_page_margin_pass"
    ) is True


def run_build(case_id: str, ordinal: int) -> dict[str, object]:
    assert_frozen()
    design = HERE / "ir" / f"{case_id}.json"
    output = HERE / "runs" / case_id / f"run{ordinal}"
    failed = output.with_name(output.name + ".failed")
    if output.exists() or failed.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ROOT / ".venv/bin/python"),
        "-m",
        "ai_kicad",
        "build",
        str(design),
        "--target",
        "schematic",
        "--assets-lock",
        str(ASSETS),
        "--toolchain-lock",
        str(TOOLCHAIN),
        "--policy-lock",
        str(POLICY),
        "--out",
        str(output),
    ]
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(ROOT / "src"), LC_ALL="C", TZ="UTC")
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        returncode = process.returncode
        stdout, stderr = process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = (exc.stdout or b"").decode(errors="replace")
        stderr = (exc.stderr or b"").decode(errors="replace")
    elapsed = round(time.monotonic() - started, 3)
    actual = output if returncode == 0 else failed
    record: dict[str, object] = {
        "ordinal": ordinal,
        "command": command,
        "exit_code": returncode,
        "runtime_seconds": elapsed,
        "output": str(actual.relative_to(HERE)),
        "stdout": stdout,
        "stderr": stderr,
        "input_sha256": sha256(design),
        "source_tool_assets_policy_hashes": {
            "implementation_freeze": sha256(HERE / "implementation_freeze.json"),
            "toolchain_lock": sha256(TOOLCHAIN),
            "asset_lock": sha256(ASSETS),
            "policy_lock": sha256(POLICY),
        },
    }
    if returncode != 0:
        failure_path = actual / "reports/failure.json"
        record.update(
            generation_result="fail",
            failure_class="timeout" if returncode == 124 else "generation_or_layout",
            failure=json.loads(failure_path.read_text()) if failure_path.is_file() else None,
        )
        return record

    reports = actual / "reports"
    electrical = json.loads((reports / "electrical.json").read_text())
    erc = json.loads((reports / "erc.json").read_text())
    layout = json.loads((reports / "layout.json").read_text())
    composition = json.loads((reports / "composition.json").read_text())
    manifest = json.loads((reports / "manifest.json").read_text())
    violations = [item for sheet in erc["sheets"] for item in sheet["violations"]]
    project_files = sorted((actual / "project").glob("*.kicad_*"))
    svgs = sorted((actual / "renders/schematic").glob("*.svg"))
    raw = [reports / "raw/netlist.json", reports / "raw/erc.json", reports / "raw/svg.json"]
    project_ok = len(project_files) >= 2
    kicad_ok = (reports / "netlist.xml").stat().st_size > 0 and all(
        path.is_file() and path.stat().st_size > 0 for path in raw
    )
    svg_ok = bool(svgs) and all(path.stat().st_size > 0 for path in svgs)
    electrical_ok = electrical.get("status") == "pass"
    erc_ok = not violations
    layout_ok = hard_layout_pass(layout)
    composition_ok = bool(composition)
    manifest_ok = bool(manifest.get("checks")) and all(
        status == "pass" for status in manifest["checks"].values()
    )
    passed = all(
        [project_ok, kicad_ok, svg_ok, electrical_ok, erc_ok, layout_ok, composition_ok, manifest_ok]
    )
    record.update(
        generation_result="pass",
        semantic_composition_result="pass" if composition_ok else "fail",
        kicad_project_generation="pass" if project_ok else "fail",
        kicad_10_0_6_processing="pass" if kicad_ok else "fail",
        fresh_xml_export=str((reports / "netlist.xml").relative_to(actual)),
        independent_observed_electrical_graph=str((reports / "electrical.json").relative_to(actual)),
        expected_vs_observed=electrical.get("status"),
        electrical_report=electrical,
        erc_status="pass" if erc_ok else "fail",
        erc_violations=violations,
        svg_render=[str(path.relative_to(actual)) for path in svgs],
        svg_status="pass" if svg_ok else "fail",
        layout_legality="pass" if layout_ok else "fail",
        layout_metrics=layout,
        composition_evidence=composition,
        manifest=manifest,
        project_files=[str(path.relative_to(actual)) for path in project_files],
        automated_run_pass=passed,
    )
    if not passed:
        if not project_ok or not kicad_ok or not svg_ok:
            record["failure_class"] = "kicad_export_or_render"
        elif not electrical_ok:
            record["failure_class"] = "electrical_equivalence"
        elif not erc_ok:
            record["failure_class"] = "erc"
        elif not composition_ok:
            record["failure_class"] = "semantic_composition"
        else:
            record["failure_class"] = "layout_legality"
    return record


def normalized(path: Path, case_id: str) -> bytes:
    value = path.read_text()
    if path.suffix == ".svg":
        value = re.sub(r"<title>.*?</title>", "<title/>", value, flags=re.DOTALL)
    elif path.name == "netlist.xml":
        value = re.sub(r"<source>.*?</source>", "<source/>", value)
        value = re.sub(r"<date>.*?</date>", "<date/>", value)
    elif path.name == "erc.json" and path.parent.name == "reports":
        data = json.loads(value)
        data.pop("date", None)
        data.pop("source", None)
        value = json.dumps(data, sort_keys=True)
    elif path.parent.name == "raw" and path.suffix == ".json":
        value = re.sub(
            rf"/runs/{re.escape(case_id)}/run[1-5]\.staging/",
            f"/runs/{case_id}/<RUN>.staging/",
            value,
        )
    return value.encode()


def compare_runs(case_id: str, records: list[dict[str, object]]) -> dict[str, object]:
    directories = [HERE / str(record["output"]) for record in records]
    relative_paths = sorted(
        str(path.relative_to(directories[0]))
        for path in directories[0].rglob("*")
        if path.is_file() and "config" not in path.parts and path.name != "manifest.json"
    )
    files = {}
    for relative in relative_paths:
        hashes = [
            hashlib.sha256(normalized(directory / relative, case_id)).hexdigest()
            for directory in directories
        ]
        files[relative] = {"normalized_sha256": hashes[0], "five_equal": len(set(hashes)) == 1}
    manifests = [json.loads((directory / "reports/manifest.json").read_text()) for directory in directories]
    for manifest, directory in zip(manifests, directories, strict=True):
        manifest["artifacts"] = [
            {
                **artifact,
                "sha256": hashlib.sha256(normalized(directory / artifact["path"], case_id)).hexdigest(),
            }
            for artifact in manifest["artifacts"]
        ]
    manifest_equal = all(item == manifests[0] for item in manifests[1:])
    required = {
        "compiler_owned_schematic_project_bytes": all(
            item["five_equal"]
            for name, item in files.items()
            if name.startswith("project/") and name.endswith((".kicad_sch", ".kicad_pro"))
        ),
        "independently_observed_electrical_partition": files["reports/electrical.json"]["five_equal"],
        "erc_result": files["reports/erc.json"]["five_equal"],
        "semantic_composition_evidence": files["reports/composition.json"]["five_equal"],
        "complete_layout_metric_vector": files["reports/layout.json"]["five_equal"],
        "normalized_kicad_svg_geometry_text": all(
            item["five_equal"] for name, item in files.items() if name.endswith(".svg")
        ),
        "normalized_manifest_check_evidence": manifest_equal and all(
            item["five_equal"] for item in files.values()
        ),
    }
    return {
        "normalization_allowlist": [
            "KiCad SVG nonrendered title",
            "KiCad XML source path and date",
            "KiCad ERC source/date",
            "raw CLI staging path",
        ],
        "required_comparisons": required,
        "files": files,
        "normalized_manifest_equal": manifest_equal,
        "pass": all(required.values()),
    }


def main() -> None:
    initial = assert_frozen()
    corpus = json.loads((HERE / "corpus.v4.json").read_text())
    if [case["case_id"] for case in corpus["cases"]] != CASE_IDS:
        raise RuntimeError("unexpected corpus inventory/order")
    if (HERE / "runs").exists() or (HERE / "automated_results.json").exists():
        raise RuntimeError("blind execution already started")
    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    results: dict[str, object] = {
        "schema_version": "m2f1.automated-results.v1",
        "evaluation": "M2f1 — corpus.v4 frozen blind qualification",
        "frozen_git_head": freeze["git_head"],
        "implementation_freeze_sha256": sha256(HERE / "implementation_freeze.json"),
        "corpus_sha256": sha256(HERE / "corpus.v4.json"),
        "ir_sha256": json.loads((HERE / "ir.sha256.json").read_text()),
        "toolchain": freeze["toolchain"],
        "python": freeze["python"],
        "platform": freeze["platform"],
        "initial_freeze_audit": initial,
        "cases": {},
    }
    reproducibility: dict[str, object] = {"schema_version": "m2f1.reproducibility.v1", "cases": {}}
    for case_id in CASE_IDS:
        validation = validate_input(case_id)
        runs = []
        if validation["status"] == "pass":
            runs.append(run_build(case_id, 1))
            if runs[0].get("automated_run_pass"):
                for ordinal in range(2, 6):
                    runs.append(run_build(case_id, ordinal))
        repro = (
            compare_runs(case_id, runs)
            if len(runs) == 5 and all(run.get("automated_run_pass") for run in runs)
            else {"pass": False, "not_performed_reason": "case did not pass first-run automated gates"}
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
        print(case_id, results["cases"][case_id]["automated_status"], failure_class or "", flush=True)
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
