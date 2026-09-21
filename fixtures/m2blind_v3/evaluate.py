"""Frozen corpus.v3 blind runner.

The runner verifies all freezes before every build, preserves failed outputs,
continues across all eight cases, and never writes outside m2blind_v3 run and
result artifacts.
"""

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
ASSET_LOCK = ROOT / "fixtures/m2b/assets.lock.json"
POLICY_LOCK = ROOT / "fixtures/m1a/policy.lock.json"
CASE_IDS = [f"V3-{number}" for number in range(1, 9)]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_map(base: Path) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): digest(path)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def file_map_digest(files: dict[str, str]) -> str:
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def freeze_checks() -> dict[str, object]:
    freeze_path = HERE / "implementation_freeze.json"
    expected_freeze_hash = (HERE / "implementation_freeze.sha256").read_text().split()[0]
    freeze = json.loads(freeze_path.read_text())
    source_changed = [
        name
        for name, expected in freeze["files"].items()
        if not (ROOT / name).is_file() or digest(ROOT / name) != expected
    ]
    external_changed = [
        item["path"]
        for item in freeze["toolchain"]["external_files"].values()
        if not Path(item["path"]).is_file() or digest(Path(item["path"])) != item["sha256"]
    ]
    corpus_expected = (HERE / "corpus.v3.sha256").read_text().split()[0]
    ir_expected = json.loads((HERE / "ir.sha256.json").read_text())
    ir_changed = [
        key
        for key, expected in ir_expected.items()
        if digest(HERE / "ir" / f"{key}.json") != expected
    ]
    historical = {}
    for relative, baseline in freeze["historical_evidence_before"].items():
        current = file_map(ROOT / relative)
        historical[relative] = {
            "file_count": len(current),
            "canonical_file_map_sha256": file_map_digest(current),
            "unchanged": current == baseline["files"],
        }
    result = {
        "implementation_freeze_sha256": digest(freeze_path),
        "implementation_freeze_self_hash_pass": digest(freeze_path) == expected_freeze_hash,
        "source_files_unchanged": not source_changed,
        "source_files_changed": source_changed,
        "external_toolchain_unchanged": not external_changed,
        "external_toolchain_changed": external_changed,
        "corpus_sha256": digest(HERE / "corpus.v3.json"),
        "corpus_unchanged": digest(HERE / "corpus.v3.json") == corpus_expected,
        "ir_unchanged": not ir_changed,
        "ir_changed": ir_changed,
        "historical_evidence": historical,
    }
    result["pass"] = (
        result["implementation_freeze_self_hash_pass"]
        and result["source_files_unchanged"]
        and result["external_toolchain_unchanged"]
        and result["corpus_unchanged"]
        and result["ir_unchanged"]
        and all(item["unchanged"] for item in historical.values())
    )
    return result


def assert_frozen() -> dict[str, object]:
    result = freeze_checks()
    if not result["pass"]:
        raise RuntimeError(f"freeze violation: {json.dumps(result, sort_keys=True)}")
    return result


def input_validation(case_id: str) -> dict[str, object]:
    try:
        raw = json.loads((HERE / "ir" / f"{case_id}.json").read_text())
        validate(raw, assets())
    except Exception as exc:  # evidence must preserve exact parser rejection
        return {"status": "fail", "exception": type(exc).__name__, "message": str(exc)}
    return {"status": "pass"}


def hard_layout_pass(layout: dict[str, object]) -> bool:
    allowed_nonzero_counts = {
        "wire_count",
        "label_count",
        "bend_count",
        "symbol_occurrences",
        "observed_bend_count",
        "observed_wire_count",
    }
    zero_illegal_counts = all(
        value == 0
        for name, value in layout.items()
        if name.endswith("_count") and name not in allowed_nonzero_counts
    )
    return (
        zero_illegal_counts
        and layout.get("page_margin_pass") is True
        and layout.get("observed_page_margin_pass") is True
    )


def run_build(case_id: str, ordinal: int) -> dict[str, object]:
    assert_frozen()
    design = HERE / "ir" / f"{case_id}.json"
    output = HERE / "runs" / case_id / f"run{ordinal}"
    failed_output = output.with_name(output.name + ".failed")
    if output.exists() or failed_output.exists():
        raise RuntimeError(f"refusing to overwrite existing run: {output}")
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
        str(ASSET_LOCK),
        "--toolchain-lock",
        str(TOOLCHAIN),
        "--policy-lock",
        str(POLICY_LOCK),
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
            timeout=120,
        )
        exit_code = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or b"").decode(errors="replace")
        stderr = (exc.stderr or b"").decode(errors="replace")
    elapsed = round(time.monotonic() - started, 3)
    actual = output if exit_code == 0 else failed_output
    record: dict[str, object] = {
        "ordinal": ordinal,
        "command": command,
        "exit_code": exit_code,
        "runtime_seconds": elapsed,
        "output": str(actual.relative_to(HERE)),
        "stdout": stdout,
        "stderr": stderr,
        "input_sha256": digest(design),
        "source_tool_asset_policy_hashes": {
            "implementation_freeze": digest(HERE / "implementation_freeze.json"),
            "toolchain_lock": digest(TOOLCHAIN),
            "asset_lock": digest(ASSET_LOCK),
            "policy_lock": digest(POLICY_LOCK),
        },
    }
    if exit_code != 0:
        failure = actual / "reports/failure.json"
        if failure.exists():
            record["failure"] = json.loads(failure.read_text())
        record["generation_result"] = "fail"
        record["failure_class"] = "timeout" if exit_code == 124 else "generation_or_layout"
        return record

    reports = actual / "reports"
    electrical = json.loads((reports / "electrical.json").read_text())
    erc = json.loads((reports / "erc.json").read_text())
    layout = json.loads((reports / "layout.json").read_text())
    manifest = json.loads((reports / "manifest.json").read_text())
    violations = [violation for sheet in erc["sheets"] for violation in sheet["violations"]]
    project_files = sorted((actual / "project").glob("*.kicad_*"))
    svgs = sorted((actual / "renders/schematic").glob("*.svg"))
    raw_required = [
        reports / "raw/netlist.json",
        reports / "raw/erc.json",
        reports / "raw/svg.json",
    ]
    project_ok = len(project_files) >= 2
    kicad_ok = (
        (reports / "netlist.xml").is_file()
        and (reports / "netlist.xml").stat().st_size > 0
        and all(path.is_file() and path.stat().st_size > 0 for path in raw_required)
    )
    svg_ok = bool(svgs) and all(path.stat().st_size > 0 for path in svgs)
    electrical_ok = electrical.get("status") == "pass"
    erc_ok = not violations
    layout_ok = hard_layout_pass(layout)
    manifest_ok = manifest.get("checks") and all(
        status == "pass" for status in manifest["checks"].values()
    )
    automated_pass = all(
        (project_ok, kicad_ok, svg_ok, electrical_ok, erc_ok, layout_ok, manifest_ok)
    )
    record.update(
        {
            "generation_result": "pass",
            "kicad_project_generation": "pass" if project_ok else "fail",
            "kicad_10_0_6_processing": "pass" if kicad_ok else "fail",
            "fresh_xml_export": str((reports / "netlist.xml").relative_to(actual)),
            "independent_observed_electrical_graph": str(
                (reports / "electrical.json").relative_to(actual)
            ),
            "expected_vs_observed": electrical.get("status"),
            "electrical_report": electrical,
            "erc_status": "pass" if erc_ok else "fail",
            "erc_violations": violations,
            "svg_render": [str(path.relative_to(actual)) for path in svgs],
            "svg_status": "pass" if svg_ok else "fail",
            "layout_legality": "pass" if layout_ok else "fail",
            "layout_metrics": layout,
            "manifest": manifest,
            "project_files": [str(path.relative_to(actual)) for path in project_files],
            "automated_run_pass": automated_pass,
        }
    )
    if not automated_pass:
        if not project_ok or not kicad_ok or not svg_ok:
            failure_class = "kicad_export_or_render"
        elif not electrical_ok:
            failure_class = "electrical_equivalence"
        elif not erc_ok:
            failure_class = "erc"
        elif not layout_ok or not manifest_ok:
            failure_class = "layout_legality"
        else:
            failure_class = "automated_gate"
        record["failure_class"] = failure_class
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
    paths = sorted(
        str(path.relative_to(directories[0]))
        for path in directories[0].rglob("*")
        if path.is_file() and "config" not in path.parts
    )
    files = {}
    for relative in paths:
        if relative == "reports/manifest.json":
            continue
        hashes = [
            hashlib.sha256(normalized(directory / relative, case_id)).hexdigest()
            for directory in directories
        ]
        files[relative] = {"normalized_sha256": hashes[0], "five_equal": len(set(hashes)) == 1}
    manifests = [
        json.loads((directory / "reports/manifest.json").read_text()) for directory in directories
    ]
    for manifest, directory in zip(manifests, directories, strict=True):
        manifest["artifacts"] = [
            {
                **artifact,
                "sha256": hashlib.sha256(
                    normalized(directory / artifact["path"], case_id)
                ).hexdigest(),
            }
            for artifact in manifest["artifacts"]
        ]
    manifest_equal = all(item == manifests[0] for item in manifests[1:])
    required = {
        "compiler_owned_project_files": all(
            item["five_equal"]
            for name, item in files.items()
            if name.startswith("project/") and name.endswith((".kicad_sch", ".kicad_pro"))
        ),
        "observed_electrical_partitions": files["reports/electrical.json"]["five_equal"],
        "erc_results": files["reports/erc.json"]["five_equal"],
        "complete_layout_metric_vectors": files["reports/layout.json"]["five_equal"],
        "normalized_svg_geometry_text": all(
            item["five_equal"] for name, item in files.items() if name.endswith(".svg")
        ),
        "normalized_manifests_and_evidence": manifest_equal
        and all(item["five_equal"] for item in files.values()),
    }
    return {
        "normalization_allowlist": [
            "KiCad SVG nonrendered title",
            "KiCad XML export source path and date",
            "KiCad ERC date",
            "raw CLI command staging path",
        ],
        "required_comparisons": required,
        "files": files,
        "normalized_manifest_equal": manifest_equal,
        "pass": all(required.values()),
    }


def main() -> None:
    initial_audit = assert_frozen()
    corpus = json.loads((HERE / "corpus.v3.json").read_text())
    corpus_ids = [case["case_id"] for case in corpus["cases"]]
    if corpus_ids != CASE_IDS:
        raise RuntimeError(f"unexpected corpus order/inventory: {corpus_ids}")
    if (HERE / "automated_results.json").exists() or (HERE / "runs").exists():
        raise RuntimeError("blind execution already started; refusing a second V3 revision/run")

    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    result: dict[str, object] = {
        "schema_version": "m2d2.automated-results.v1",
        "evaluation": "M2d2 — corpus.v3 frozen blind composition qualification",
        "frozen_git_head": freeze["git_head"],
        "implementation_freeze_sha256": digest(HERE / "implementation_freeze.json"),
        "corpus_sha256": digest(HERE / "corpus.v3.json"),
        "ir_sha256": json.loads((HERE / "ir.sha256.json").read_text()),
        "toolchain": freeze["toolchain"],
        "python": freeze["python"],
        "platform": freeze["platform"],
        "initial_freeze_audit": initial_audit,
        "cases": {},
    }
    reproducibility: dict[str, object] = {
        "schema_version": "m2d2.reproducibility.v1",
        "cases": {},
    }
    for case_id in CASE_IDS:
        validation = input_validation(case_id)
        runs: list[dict[str, object]] = []
        if validation["status"] == "pass":
            runs.append(run_build(case_id, 1))
            if runs[0].get("automated_run_pass"):
                for ordinal in range(2, 6):
                    runs.append(run_build(case_id, ordinal))
        repro = (
            compare_runs(case_id, runs)
            if len(runs) == 5 and all(run.get("automated_run_pass") for run in runs)
            else {"pass": False, "not_performed_reason": "case did not pass automated run gates"}
        )
        passed = (
            validation["status"] == "pass"
            and len(runs) == 5
            and all(run.get("automated_run_pass") for run in runs)
            and repro["pass"]
        )
        failure_class = None
        if validation["status"] != "pass":
            failure_class = "input_validation"
        elif not runs[0].get("automated_run_pass"):
            failure_class = runs[0].get("failure_class", "automated_gate")
        elif not repro["pass"]:
            failure_class = "reproducibility"
        result["cases"][case_id] = {
            "design_id": json.loads((HERE / "ir" / f"{case_id}.json").read_text())["id"],
            "input_validation": validation,
            "automated_status": "pass" if passed else "fail",
            "failure_class": failure_class,
            "runs": runs,
            "reproducibility_status": "pass" if repro["pass"] else "fail",
        }
        reproducibility["cases"][case_id] = repro
        (HERE / "automated_results.json").write_text(json.dumps(result, indent=2) + "\n")
        (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
        print(
            case_id,
            result["cases"][case_id]["automated_status"],
            failure_class or "",
            flush=True,
        )
    final_audit = assert_frozen()
    result["accepted_count"] = sum(
        case["automated_status"] == "pass" for case in result["cases"].values()
    )
    result["required_accepted_count"] = 8
    result["automated_gate"] = "pass" if result["accepted_count"] == 8 else "fail"
    result["final_freeze_audit"] = final_audit
    result["runtime_seconds_total"] = round(
        sum(run["runtime_seconds"] for case in result["cases"].values() for run in case["runs"]),
        3,
    )
    (HERE / "automated_results.json").write_text(json.dumps(result, indent=2) + "\n")
    (HERE / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
    print(f"automated gate: {result['accepted_count']}/8")


if __name__ == "__main__":
    main()
