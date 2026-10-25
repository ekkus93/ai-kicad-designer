"""Verify recorded native/model artifacts and regenerate the compact demo summary."""

import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
SOURCE = "df0f263604053ecbb1d6b915f1835bf412a5b819"
FINAL = ("rc_wiring_locked", "rc_labels_locked", "led_locked", "timer_locked_libraries")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    suites = ET.parse(ROOT / "validation/pivot-tests.xml").getroot()
    assert sum(int(s.get("tests", "0")) for s in suites.iter("testsuite")) == 129
    assert all(
        s.get("failures", "0") == "0" and s.get("errors", "0") == "0"
        for s in suites.iter("testsuite")
    )
    summary = {
        "schema_version": "schematic-review-demo.v1",
        "qualified_source_commit": SOURCE,
        "scope": "bounded native schematic review execution and supported edits; intended electrical design remains authoritative",
        "final_runs": {},
        "earlier_runs": {},
        "human_electrical_review": "PENDING",
        "locked_host_qualification": False,
        "limitations": [
            "Before the locality gate, Qwen accepted the deliberately detached C1 value label; model visual judgment alone is insufficient.",
            "The generated 555 still uses multiple REF and VCC labels. Model acceptance does not establish satisfaction of all earlier owner wiring-style preferences.",
            "Supported edits are field placement, whole-sheet translation and regeneration from the intended circuit. Arbitrary symbol movement, custom routing and topology changes are not implemented.",
        ],
    }
    for run in sorted(ROOT.iterdir()):
        if not run.is_dir() or not (run / "manifest.json").is_file():
            continue
        manifest = json.loads((run / "manifest.json").read_text())
        for relative, wanted in manifest["artifacts"].items():
            assert digest(run / relative) == wanted, (run.name, relative)
        for path in (run / "reviews").glob("*.json"):
            review = json.loads(path.read_text())
            for image in review["images"]:
                parts = Path(image["path"]).parts
                relative = Path(*parts[parts.index(ROOT.name) + 1 :])
                assert digest(ROOT / relative) == image["sha256"]
        result = json.loads((run / "result.json").read_text())
        if run.name not in FINAL:
            summary["earlier_runs"][run.name] = {
                "reported_status": result["status"],
                "reviews": len(result["iterations"]),
                "reason": result["reason"],
            }
            continue
        assert manifest["source_commit"] == SOURCE
        assert manifest["implementation_unchanged_during_run"]
        for relative, wanted in manifest["implementation_sha256"].items():
            blob = subprocess.check_output(["git", "show", f"{SOURCE}:{relative}"], cwd=REPO)
            assert hashlib.sha256(blob).hexdigest() == wanted
        assert result["status"] == "ACCEPTED_FOR_REVIEW"
        accepted = run / result["accepted_schematic"]
        last = result["iterations"][-1]["review"]
        assert last["base_revision"] == "sha256:" + digest(accepted)
        assert not last["issues"] and not last["actions"]
        assessment = json.loads((accepted.parent.parent / "assessment.json").read_text())
        assert all(v == "PASS" for v in assessment["checks"].values())
        summary["final_runs"][run.name] = {
            "status": result["status"],
            "reviews": len(result["iterations"]),
            "model_tokens": result["model_tokens"],
            "elapsed_seconds": result["elapsed_seconds"],
            "accepted_schematic": str(accepted.relative_to(ROOT)),
            "schematic_sha256": digest(accepted),
            "checks": assessment["checks"],
            "drawing": str(
                (accepted.parent.parent / "review-images/drawing.png").relative_to(ROOT)
            ),
        }
    assert set(summary["final_runs"]) == set(FINAL)
    summary["earlier_runs"]["rc_visual_only"]["independent_visual_audit"] = (
        "FAIL: the model accepted the deliberately detached C1 value. This motivated the generalized locality gate."
    )
    summary["earlier_runs"]["rc_visual_thinking"]["independent_visual_audit"] = (
        "NO ACCEPTANCE: six truncated 4096-token responses exhausted the review budget; repeated invalid replies now stop earlier."
    )
    summary["earlier_runs"]["timer_generated"]["independent_visual_audit"] = (
        "NO ACCEPTANCE: missing Timer/power registrations caused ERC warnings and a repeated candidate. Isolated locked library registration resolves the backend issue."
    )
    summary["earlier_runs"]["rc_corrupted"]["independent_visual_audit"] = (
        "Prototype: repair converged, but the close-up retained the page background. Subsequent runs correct the renderer."
    )
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    index = ROOT / "artifact-index.json"
    if index.is_file():
        for relative, wanted in json.loads(index.read_text())["artifacts"].items():
            assert digest(ROOT / relative) == wanted, relative
    print(
        "Verified all run manifests, images, exact source implementations and final acceptance revisions; 129 tests passed."
    )


if __name__ == "__main__":
    main()
