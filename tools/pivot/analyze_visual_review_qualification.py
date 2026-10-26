"""Score whether retained visual reviews name the defect that was actually injected.

A rejection only counts as a *specific* detection when the model's issues mention the
injected defect: the moved field's reference and kind, an overlap, page composition,
or rail/label continuity. Clean-case rejections are counted as false rejections. The
retained review records are read, never modified; scores go to a separate file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from ai_kicad.pivot.schematic_review import write_json

COMPOSITION = (
    r"composition|balance|corner|unused|empty|whitespace|white space|off-cent|centr|cluster"
)
CUES = {
    "detached_value": r"(value|label).*(detach|far|distant|associat|closer|near|belong|misplac)"
    r"|(detach|associat|misplac).*(value|label)",
    "overlapping_fields": r"overlap|collid|collision|obscur|superimpos",
    "distant_reference": r"(reference|ref|designator|label).*(detach|far|distant|associat|away)"
    r"|(detach|distant|far).*(reference|designator)",
    "off_balance_page": COMPOSITION,
    "label_joined_rail": r"rail|continu|label[- ]joined|net label|explicit wire|visible wire",
}


def specific(row: dict) -> bool:
    if row.get("decision") not in {"revise", "needs_help"}:
        return False
    text = " ".join(row.get("issues", [])).lower()
    return re.search(CUES[row["kind"]], text) is not None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    summary = json.loads((args.experiment / "summary.json").read_text())
    rows = summary["reviews"]
    groups = sorted({(row["model"], row["mode"]) for row in rows})
    scores = {}
    for model, mode in groups:
        selected = [row for row in rows if row["model"] == model and row["mode"] == mode]
        defects = [row for row in selected if row["defect"]]
        clean = [row for row in selected if not row["defect"]]
        machine_silent = [
            row
            for row in defects
            if all(value == "PASS" for value in row["machine_checks"].values())
        ]
        scores[f"{model}/{mode}"] = {
            "defects": len(defects),
            "rejected_defects": sum(row["model_detects"] for row in defects),
            "specifically_identified_defects": sum(specific(row) for row in defects),
            "machine_silent_defects": len(machine_silent),
            "machine_silent_specifically_identified": sum(specific(row) for row in machine_silent),
            "clean": len(clean),
            "clean_falsely_rejected": sum(row["model_detects"] for row in clean),
            "invalid_responses": sum(row["decision"] == "INVALID" for row in selected),
            "by_kind": {
                kind: {
                    "cases": len(items),
                    "specific": sum(specific(row) for row in items),
                }
                for kind in sorted({row["kind"] for row in defects})
                for items in [[row for row in defects if row["kind"] == kind]]
            },
            "system_false_acceptances": sum(row["loop_would_accept"] for row in defects),
        }
    write_json(
        args.experiment / "specificity_analysis.json",
        {
            "schema_version": "visual-review-specificity.v1",
            "method": "keyword cues per injected defect kind over the model's issue list",
            "cues": CUES,
            "scores": scores,
        },
    )
    print(json.dumps(scores, indent=1))


if __name__ == "__main__":
    main()
