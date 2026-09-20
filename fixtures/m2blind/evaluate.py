"""M2c2 evaluation runner; records failures and never changes compiler inputs."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checks():
    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    changed = [
        name for name, expected in freeze["files"].items() if digest(ROOT / name) != expected
    ]
    corpus_expected = (HERE / "corpus.v2.sha256").read_text().split()[0]
    corpus_ok = digest(HERE / "corpus.v2.json") == corpus_expected
    ir_expected = json.loads((HERE / "ir.sha256.json").read_text())
    ir_changed = [
        key
        for key, expected in ir_expected.items()
        if digest(HERE / "ir" / f"{key}.json") != expected
    ]
    if changed or not corpus_ok or ir_changed:
        raise RuntimeError(
            f"freeze violation: source={changed}, corpus={corpus_ok}, IR={ir_changed}"
        )


def run_build(key, ordinal):
    design = HERE / "ir" / f"{key}.json"
    out = HERE / "runs" / key / f"run{ordinal}"
    out.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ROOT / ".venv/bin/python"),
        "-m",
        "ai_kicad",
        "build",
        str(design),
        "--target",
        "schematic",
        "--assets-lock",
        str(ROOT / "fixtures/m2b/assets.lock.json"),
        "--toolchain-lock",
        str(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "--policy-lock",
        str(ROOT / "fixtures/m1a/policy.lock.json"),
        "--out",
        str(out),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    start = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
        )
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = (
            124,
            (exc.stdout or b"").decode(errors="replace"),
            (exc.stderr or b"").decode(errors="replace"),
        )
    elapsed = round(time.monotonic() - start, 3)
    actual = out if code == 0 else out.with_name(out.name + ".failed")
    record = {
        "exit_code": code,
        "runtime_seconds": elapsed,
        "output": str(actual.relative_to(HERE)),
        "stdout": stdout,
        "stderr": stderr,
    }
    if code:
        failure = actual / "reports/failure.json"
        if failure.exists():
            record["failure"] = json.loads(failure.read_text())
        record["failure_class"] = "timeout" if code == 124 else "generation_or_layout"
        return record
    reports = actual / "reports"
    electrical = json.loads((reports / "electrical.json").read_text())
    erc = json.loads((reports / "erc.json").read_text())
    layout = json.loads((reports / "layout.json").read_text())
    violations = [v for sheet in erc["sheets"] for v in sheet["violations"]]
    record.update(
        electrical_status=electrical["status"],
        erc_violations=violations,
        layout_metrics=layout,
        project_files=sorted(
            str(p.relative_to(actual)) for p in (actual / "project").glob("*.kicad_*")
        ),
        netlist=str((reports / "netlist.xml").relative_to(actual)),
        svg=sorted(str(p.relative_to(actual)) for p in (actual / "renders").rglob("*.svg")),
        manifest=json.loads((reports / "manifest.json").read_text()),
    )
    hard = (
        electrical["status"] == "pass"
        and not violations
        and all(value == "pass" for value in record["manifest"]["checks"].values())
        and all(
            value == 0
            for key2, value in layout.items()
            if key2.endswith("_count")
            and key2
            not in (
                "wire_count",
                "label_count",
                "bend_count",
                "symbol_occurrences",
                "observed_bend_count",
                "observed_wire_count",
                "observed_required_visible_fields",
            )
        )
        and layout.get("observed_page_margin_pass") is True
    )
    record["automated_pass"] = hard
    if not hard:
        record["failure_class"] = (
            "electrical"
            if electrical["status"] != "pass"
            else "erc"
            if violations
            else "layout_legality"
        )
    return record


def normalized_svg(path):
    return re.sub(r"<title>.*?</title>", "<title/>", path.read_text(), flags=re.DOTALL)


def compare_runs(key, records):
    first = HERE / records[0]["output"]
    name = json.loads((HERE / "ir" / f"{key}.json").read_text())["name"]
    comparisons = {}
    for index, record in enumerate(records[1:], 2):
        other = HERE / record["output"]
        comparisons[f"run1_vs_run{index}"] = {
            "project_bytes": all(
                (first / "project" / f"{name}{ext}").read_bytes()
                == (other / "project" / f"{name}{ext}").read_bytes()
                for ext in (".kicad_sch", ".kicad_pro")
            ),
            "electrical_report": (first / "reports/electrical.json").read_bytes()
            == (other / "reports/electrical.json").read_bytes(),
            "erc_violations": records[0]["erc_violations"] == record["erc_violations"],
            "layout_metric_vector": records[0]["layout_metrics"] == record["layout_metrics"],
            "svg_geometry_text": normalized_svg(first / "renders/schematic" / f"{name}.svg")
            == normalized_svg(other / "renders/schematic" / f"{name}.svg"),
        }
        comparisons[f"run1_vs_run{index}"]["pass"] = all(
            comparisons[f"run1_vs_run{index}"].values()
        )
    return comparisons


def main():
    checks()
    result = {
        "evaluation": "M2c2 — frozen blind M2 qualification",
        "cases": {},
        "toolchain_lock_sha256": digest(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "asset_lock_sha256": digest(ROOT / "fixtures/m2b/assets.lock.json"),
        "policy_lock_sha256": digest(ROOT / "fixtures/m1a/policy.lock.json"),
        "source_freeze_sha256": digest(HERE / "implementation_freeze.json"),
        "corpus_sha256": digest(HERE / "corpus.v2.json"),
    }
    for key in [f"H{i}" for i in range(1, 9)]:
        checks()
        runs = [run_build(key, 1)]
        if runs[0].get("automated_pass"):
            for ordinal in range(2, 6):
                checks()
                runs.append(run_build(key, ordinal))
        repro = (
            compare_runs(key, runs)
            if len(runs) == 5 and all(r.get("automated_pass") for r in runs)
            else {}
        )
        status = (
            "pass"
            if runs[0].get("automated_pass")
            and len(runs) == 5
            and all(x["pass"] for x in repro.values())
            else "fail"
        )
        result["cases"][key] = {
            "id": json.loads((HERE / "ir" / f"{key}.json").read_text())["id"],
            "automated_status": status,
            "runs": runs,
            "reproducibility": repro,
        }
        (HERE / "automated_results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            key,
            status,
            runs[0].get("failure", {}).get("message", runs[0].get("failure_class", "")),
            flush=True,
        )
    checks()
    result["freeze_unchanged"] = True
    (HERE / "automated_results.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
