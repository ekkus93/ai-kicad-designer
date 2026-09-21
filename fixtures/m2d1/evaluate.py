"""Known-corpus M2d1 regression through real KiCad; never a blind evaluation."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CORPUS = ROOT / "fixtures/m2blind/corpus.v2.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def svg_geometry(path):
    return re.sub(r"<title>.*?</title>", "<title/>", path.read_text(), flags=re.DOTALL)


def run(case, ordinal):
    key = case["review_order_key"]
    design = ROOT / "fixtures/m2blind" / case["ir"]
    out = HERE / "regression" / key / f"run{ordinal}"
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
    process = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    actual = out if process.returncode == 0 else out.with_name(out.name + ".failed")
    record = {"exit_code": process.returncode, "output": str(actual.relative_to(HERE))}
    if process.returncode:
        record["failure"] = json.loads((actual / "reports/failure.json").read_text())
        return record
    reports = actual / "reports"
    electrical = json.loads((reports / "electrical.json").read_text())
    erc = json.loads((reports / "erc.json").read_text())
    layout = json.loads((reports / "layout.json").read_text())
    manifest = json.loads((reports / "manifest.json").read_text())
    violations = [v for sheet in erc["sheets"] for v in sheet["violations"]]
    record.update(
        electrical=electrical["status"],
        erc_violations=len(violations),
        layout=layout,
        manifest_checks=manifest["checks"],
        svg_count=len(list((actual / "renders/schematic").glob("*.svg"))),
        pass_gates=(
            electrical["status"] == "pass"
            and not violations
            and set(manifest["checks"].values()) == {"pass"}
            and layout["page_margin_pass"]
            and layout["observed_page_margin_pass"]
            and all(
                value == 0
                for name, value in layout.items()
                if name.endswith("_count")
                and name
                not in {
                    "wire_count",
                    "label_count",
                    "bend_count",
                    "observed_bend_count",
                    "observed_wire_count",
                    "symbol_occurrences",
                }
            )
        ),
    )
    return record


def compare(case, records):
    name = json.loads((ROOT / "fixtures/m2blind" / case["ir"]).read_text())["name"]
    first = HERE / records[0]["output"]
    checks = []
    for record in records[1:]:
        other = HERE / record["output"]
        checks.append(
            {
                "project_bytes": all(
                    (first / "project" / f"{name}{ext}").read_bytes()
                    == (other / "project" / f"{name}{ext}").read_bytes()
                    for ext in (".kicad_sch", ".kicad_pro")
                ),
                "electrical_report": (first / "reports/electrical.json").read_bytes()
                == (other / "reports/electrical.json").read_bytes(),
                "erc_violations": records[0]["erc_violations"] == record["erc_violations"],
                "layout_vector": records[0]["layout"] == record["layout"],
                "svg_geometry_text": svg_geometry(first / "renders/schematic" / f"{name}.svg")
                == svg_geometry(other / "renders/schematic" / f"{name}.svg"),
            }
        )
    return checks


def main():
    corpus = json.loads(CORPUS.read_text())
    result = {
        "schema_version": "m2d1.1",
        "evaluation": "M2d1 known non-blind regression",
        "source_commit_base": "07efd669000bc1ab17f6d291660951e0d9012de9",
        "source_files": {
            name: digest(ROOT / name)
            for name in (
                "src/ai_kicad/m2b.py",
                "src/ai_kicad/m2_compose.py",
                "src/ai_kicad/m2b_build.py",
            )
        },
        "corpus_sha256": digest(CORPUS),
        "cases": {},
    }
    for case in corpus["cases"]:
        records = [run(case, ordinal) for ordinal in range(1, 6)]
        reproducibility = (
            compare(case, records) if all(r.get("pass_gates") for r in records) else []
        )
        passed = (
            all(r.get("pass_gates") for r in records)
            and len(reproducibility) == 4
            and all(all(check.values()) for check in reproducibility)
        )
        result["cases"][case["review_order_key"]] = {
            "design_id": case["id"],
            "pass": passed,
            "runs": records,
            "reproducibility": reproducibility,
        }
        (HERE / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
        print(case["review_order_key"], "PASS" if passed else "FAIL", flush=True)
    result["pass"] = all(case["pass"] for case in result["cases"].values())
    (HERE / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
