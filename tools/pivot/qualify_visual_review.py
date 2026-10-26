"""Qualify local vision-model schematic review against clean and defective native images.

Clean cases are compiler outputs that pass every independent check. Defective cases
inject visible readability defects with the loop's own native edits (detached value,
overlapping fields, distant reference, off-balance page composition) or keep the
compiler's label-joined power rails; ERC and electrical equivalence still pass.
Each case is reviewed twice per model: ``image_only`` withholds every machine check
result and diagnostic, so a detection must come from the images; ``full`` sends the
normal independent assessment. Every image, prompt, response and decision is kept.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess

from ai_kicad.pivot.schematic_review import (
    MoveField,
    OllamaSchematicReviewer,
    SchematicAssessment,
    SchematicReview,
    TranslateSheet,
    file_hash,
    write_json,
)
from ai_kicad.pivot.schematic_review_brief import resolve_review_brief
from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine, edit_schematic_text
from ai_kicad.sexpr import children, one, parse
from tools.pivot.experiment_paths import create_experiment_dir

ROOT = Path(__file__).resolve().parents[2]
CLEAN_DESIGNS = ("rc_lowpass", "rc_highpass", "led_series", "led_long_text", "led_reverse_supply")
DEFECT_DESIGNS = ("rc_lowpass", "rc_highpass", "led_series")
RAIL_DESIGNS = ("linear_regulator", "dual_buffer", "timer_astable")
GRID = 1.27


def snap(value: float) -> float:
    return round(round(value / GRID) * GRID, 2)


def drawing_bounds(tree: list) -> tuple[float, float, float, float]:
    points = [
        (float(point[1]), float(point[2]))
        for wire in children(tree, "wire")
        for point in children(one(wire, "pts"), "xy")
    ] + [
        (float(one(item, "at")[1]), float(one(item, "at")[2])) for item in children(tree, "symbol")
    ]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def components(tree: list) -> list[tuple[str, float, float, dict]]:
    """Visible non-power symbols with anchors and their Reference/Value positions."""
    result = []
    for symbol in children(tree, "symbol"):
        props = {prop[1]: prop for prop in children(symbol, "property")}
        reference = props["Reference"][2]
        if reference.startswith("#"):
            continue
        at = one(symbol, "at")
        fields = {name: one(props[name], "at") for name in ("Reference", "Value") if name in props}
        result.append((reference, float(at[1]), float(at[2]), fields))
    return sorted(result)


def defect_actions(text: str) -> dict[str, object]:
    """Derive each injected defect from the observed geometry of one schematic."""
    tree = parse(text)
    parts = components(tree)
    (first, fx, fy, _), (second, sx, sy, second_fields) = parts[0], parts[-1]
    left, top, right, bottom = drawing_bounds(tree)
    far_x = snap(left - 12.7 if fx > (left + right) / 2 else right + 12.7)
    far_y = snap(top - 12.7 if fy > (top + bottom) / 2 else bottom + 12.7)
    return {
        "detached_value": MoveField(
            operation="move_field",
            reference=first,
            unit=1,
            field="Value",
            x_mm=snap(sx + 7.62),
            y_mm=snap(sy + 2.54),
            angle=0,
        ),
        "overlapping_fields": MoveField(
            operation="move_field",
            reference=first,
            unit=1,
            field="Value",
            x_mm=float(second_fields["Reference"][1]),
            y_mm=float(second_fields["Reference"][2]),
            angle=0,
        ),
        "distant_reference": MoveField(
            operation="move_field",
            reference=second,
            unit=1,
            field="Reference",
            x_mm=min(max(far_x, 30.48), 266.7),
            y_mm=min(max(far_y, 30.48), 179.07),
            angle=0,
        ),
        "off_balance_page": TranslateSheet(
            operation="translate_sheet",
            dx_mm=snap(297 - 35 - right),
            dy_mm=snap(30 - top),
        ),
    }


def image_only(assessment: SchematicAssessment) -> SchematicAssessment:
    """Withhold machine check outcomes; keep the circuit, field and terminal inventories."""
    report = {
        key: assessment.report[key]
        for key in ("intended_circuit", "field_inventory", "terminal_inventory", "schematic_sha256")
        if key in assessment.report
    }
    report["independent_checks"] = "WITHHELD_FOR_IMAGE_QUALIFICATION"
    return replace(assessment, report=report)


def prepare_cases(launcher: Path, max_field_distance: float, root: Path) -> list[dict]:
    cases = []

    def record(name: str, design_name: str, kind: str, engine, schematic, directory) -> None:
        assessment = engine.assess(schematic, directory)
        cases.append(
            {
                "case": name,
                "design": design_name,
                "kind": kind,
                "defect": kind != "clean",
                "directory": directory,
                "assessment": assessment,
                "engine": engine,
            }
        )

    for design_name in sorted(set(CLEAN_DESIGNS) | set(DEFECT_DESIGNS) | set(RAIL_DESIGNS)):
        design = json.loads((ROOT / "fixtures/m2b" / f"{design_name}.json").read_text())
        engine = NativeSchematicEngine(
            design, launcher, maximum_field_distance_mm=max_field_distance
        )
        base_dir = root / "cases" / f"{design_name}__generated"
        schematic = engine.initial(base_dir)
        kind = "label_joined_rail" if design_name in RAIL_DESIGNS else "clean"
        record(base_dir.name, design_name, kind, engine, schematic, base_dir)
        if design_name not in DEFECT_DESIGNS:
            continue
        for defect, action in defect_actions(schematic.read_text()).items():
            directory = root / "cases" / f"{design_name}__{defect}"
            project = directory / "project"
            project.mkdir(parents=True)
            target = project / schematic.name
            target.write_text(edit_schematic_text(schematic.read_text(), [action]))
            record(directory.name, design_name, defect, engine, target, directory)
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["qwen3.5:9b", "devstral-small-2:24b"])
    parser.add_argument(
        "--review-brief", type=Path, default=ROOT / "fixtures/pivot/schematic_review_brief_v2.json"
    )
    args = parser.parse_args()
    max_field_distance, brief_text = resolve_review_brief(args.review_brief, None)
    root = create_experiment_dir(ROOT, args.experiment_id)
    cases = prepare_cases(args.kicad_apprun, max_field_distance, root)
    rows = []
    for model in args.models:
        reviewer = OllamaSchematicReviewer(model, review_brief=brief_text)
        for case in cases:
            for mode in ("image_only", "full"):
                assessment = (
                    image_only(case["assessment"]) if mode == "image_only" else case["assessment"]
                )
                record = root / "reviews" / model.replace(":", "_") / mode / f"{case['case']}.json"
                row = {
                    "model": model,
                    "model_digest": reviewer.identity["digest"],
                    "mode": mode,
                    "case": case["case"],
                    "design": case["design"],
                    "kind": case["kind"],
                    "defect": case["defect"],
                    "machine_checks": case["assessment"].report["checks"],
                    "record": str(record.relative_to(root)),
                }
                try:
                    review = SchematicReview.model_validate_json(
                        reviewer.review(assessment, "", record)
                    )
                    row.update(
                        decision=review.decision,
                        issues=review.issues,
                        actions=[action.model_dump(mode="json") for action in review.actions],
                    )
                except (ValueError, OSError) as error:
                    row.update(decision="INVALID", error=str(error))
                machine_pass = case["assessment"].passed
                row["model_detects"] = row["decision"] in {"revise", "needs_help"}
                row["loop_would_accept"] = (
                    row["decision"] == "accept"
                    and machine_pass
                    and (not row.get("issues") and not row.get("actions"))
                )
                rows.append(row)
                print(model, mode, case["case"], row["decision"], flush=True)

    def rate(selected: list[dict], key: str) -> dict:
        hits = sum(1 for row in selected if row[key])
        return {"count": len(selected), "hits": hits}

    summary = {
        "schema_version": "visual-review-qualification.v1",
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "review_brief": str(args.review_brief.relative_to(ROOT)),
        "review_brief_sha256": file_hash(args.review_brief),
        "cases": [
            {
                "case": case["case"],
                "design": case["design"],
                "kind": case["kind"],
                "defect": case["defect"],
                "machine_checks": case["assessment"].report["checks"],
                "schematic_sha256": file_hash(case["assessment"].schematic),
                "images": {
                    str(path.relative_to(root)): file_hash(path)
                    for path in case["assessment"].images
                },
            }
            for case in cases
        ],
        "metrics": {
            f"{model}/{mode}": {
                "defects_detected": rate(
                    [r for r in rows if r["model"] == model and r["mode"] == mode and r["defect"]],
                    "model_detects",
                ),
                "clean_falsely_rejected": rate(
                    [
                        r
                        for r in rows
                        if r["model"] == model and r["mode"] == mode and not r["defect"]
                    ],
                    "model_detects",
                ),
                "defects_loop_would_accept": rate(
                    [r for r in rows if r["model"] == model and r["mode"] == mode and r["defect"]],
                    "loop_would_accept",
                ),
            }
            for model in args.models
            for mode in ("image_only", "full")
        },
        "reviews": rows,
        "locked_host_qualification": False,
        "human_readability_review": "PENDING",
    }
    write_json(root / "summary.json", summary)
    print(json.dumps(summary["metrics"], indent=1))


if __name__ == "__main__":
    main()
