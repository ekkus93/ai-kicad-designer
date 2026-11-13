"""Qualify the brief-v3 schematic reviewer on known-good and known-bad native drawings.

Three case groups, all re-assessed with the current independent checks:

* ``known_good``: drawings accepted by a full review-loop corpus run whose layout no one
  has since faulted. The expected decision is accept.
* ``historical``: drawings that an earlier corpus run accepted (or an evidence folder
  produced) and that the owner or an outside review later found defective. Each
  entry names the defect and the follow-up evidence folder that fixed it.
* ``injected``: known-good drawings with one visible readability defect injected by
  the loop's own native edits (detached value, overlapping fields, distant reference,
  off-balance page).

Every case is reviewed with the loop's real reviewer (same system prompt, brief and
model options) in ``full`` mode and, optionally, ``image_only`` mode, where every machine
check outcome is withheld. Each image, prompt, response and score is kept.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from dataclasses import replace

from ai_kicad.pivot.schematic_review import (
    OllamaSchematicReviewer,
    SchematicAssessment,
    SchematicReview,
    file_hash,
    write_json,
)
from ai_kicad.pivot.schematic_review_brief import (
    brief_allows_power_symbol_rails,
    brief_requires_field_ownership,
    brief_requires_page_balance,
    brief_requires_text_and_ground_checks,
    brief_requires_readability_checks,
    resolve_review_brief,
)
from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine, edit_schematic_text
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.qualify_visual_review import defect_actions

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "fixtures/pivot/experiments"
KNOWN_GOOD_RUN = "review_loop_corpus_v3_2026-11-12_qwen35_256k_run1"
INJECT_DESIGNS = (
    "rc_lowpass",
    "led_series",
    "linear_regulator",
    "inverting_gain",
    "sallen_key",
    "dual_rail_reference",
    "timer_astable",
    "reference_555_led_flasher_v8",
)

# Text cues that a rejection names the actual defect (case-insensitive regex over issues).
WIRE_ACROSS_U1C = r"u1c|power unit|pin name|v\+|v-|v−|cross|overlap|over the"
HISTORICAL = [
    *[
        {
            "case": f"{design}__wire_across_power_unit",
            "design": design,
            "source": f"review_loop_corpus_v3_2026-11-05_qwen35_256k_run1/{design}",
            "fixed_by": "power_unit_column_2026-11-09_run1",
            "defect": "a ground wire runs across U1C between V+ and V-, over its pin names",
            "cue": WIRE_ACROSS_U1C,
        }
        for design in (
            "dual_buffer",
            "inverting_gain",
            "noninverting_gain",
            "rc_to_buffer",
            "sallen_key",
        )
    ],
    {
        "case": "inverting_gain__r1_r2_text_misplaced",
        "design": "inverting_gain",
        "source": "review_loop_corpus_v3_2026-11-09_qwen35_256k_run1/inverting_gain",
        "fixed_by": "horizontal_field_text_2026-11-10_run1; connector_rail_symbol_2026-11-10_run1",
        "defect": "R2 10k sits above U1A's input wire and R1 100k sits under U1A's output, "
        "nearer the op-amp than their resistors; C1's REF ground symbol sits sideways",
        "cue": r"\br1\b|\br2\b|100k|10k|associat|closer|sideways|ref",
    },
    {
        "case": "inverting_gain__sideways_ground",
        "design": "inverting_gain",
        "source": "review_loop_corpus_v3_2026-11-10_qwen35_256k_run1/inverting_gain",
        "fixed_by": "upright_ground_symbol_2026-11-10_run1",
        "defect": "C2's REF ground symbol points sideways (left) instead of down",
        "cue": r"sideways|orient|rotat|point|ground symbol|\bref\b.*(symbol|glyph)",
    },
    {
        "case": "inverting_gain__long_supply_loops",
        "design": "inverting_gain",
        "source": "review_loop_corpus_v3_2026-11-11_qwen35_256k_run3/inverting_gain",
        "fixed_by": "supply_rail_symbols_2026-11-11_run1",
        "defect": "VPLUS and VMINUS run from J1 down the left edge and along the bottom to U1C",
        "cue": r"long|loop|around|perimeter|edge|detour|length|hard to follow",
    },
    {
        "case": "inverting_gain__long_ref_wire_and_loop",
        "design": "inverting_gain",
        "source": "supply_rail_symbols_2026-11-11_run1/inverting_gain",
        "fixed_by": "return_rail_symbols_2026-11-11_run1",
        "defect": "a long REF wire from J1 to U1A's + input, and C2's ground wired by a loop "
        "over U1C close under its NE5532 text",
        "cue": r"long|loop|detour|over u1c|clearance|close to|crowd",
    },
    {
        "case": "inverting_gain__decoupling_detour",
        "design": "inverting_gain",
        "source": "return_rail_symbols_2026-11-11_run1/inverting_gain",
        "fixed_by": "decoupling_placement_2026-11-11_run1",
        "defect": "C2's VMINUS wire leaves U1C pin 4, runs right under C2 and back up to C2's "
        "top pin (40.64 mm); C2's REF symbol sits 1.27 mm above that wire",
        "cue": r"c2|detour|loop|long|decoupl|crowd|close",
    },
    {
        "case": "inverting_gain__vminus_by_pin_name",
        "design": "inverting_gain",
        "source": "review_loop_corpus_v3_2026-11-11_qwen35_256k_run4/inverting_gain",
        "fixed_by": "rail_name_pin_clearance_2026-11-11_run1",
        "defect": "the VMINUS rail name sits about 1 mm right of U1C's V- pin name",
        "cue": r"vminus.*(close|crowd|near|overlap|clearance|adjacent)|"
        r"(close|crowd|near|overlap|clearance|adjacent).*vminus|pin name",
    },
    {
        "case": "inverting_gain__vminus_above_c2_text",
        "design": "inverting_gain",
        "source": "review_loop_corpus_v3_2026-11-11_qwen35_256k_run5/inverting_gain",
        "fixed_by": "rail_name_part_text_clearance_2026-11-12_run1",
        "defect": "the VMINUS rail name sits about 1 mm above C2's C2 / 100n text",
        "cue": r"(vminus|c2|100n).*(close|crowd|near|overlap|clearance|adjacent)|"
        r"(close|crowd|near|overlap|clearance|adjacent).*(vminus|c2|100n)",
    },
    {
        "case": "timer_astable__vcc_arrows_into_text",
        "design": "timer_astable",
        "source": "review_loop_corpus_v3_2026-11-11_qwen35_256k_run5/timer_astable",
        "fixed_by": "rail_name_part_text_clearance_2026-11-12_run1",
        "defect": "R1's VCC arrow points down into R1's 10k; the RST VCC arrow points sideways",
        "cue": r"vcc.*(close|crowd|near|overlap|clearance|into|point)|"
        r"(close|crowd|near|overlap|clearance).*vcc|10k",
    },
    {
        "case": "reference_555_led_flasher_v8__vcc_arrow_at_ref_text",
        "design": "reference_555_led_flasher_v8",
        "source": "review_loop_corpus_v3_2026-11-11_qwen35_256k_run5/reference_555_led_flasher_v8",
        "fixed_by": "rail_name_part_text_clearance_2026-11-12_run1",
        "defect": "the RST VCC arrow points at C2's REF text; C1's REF crowds J1's Supply text",
        "cue": r"vcc.*(close|crowd|near|overlap|clearance|point)|"
        r"(close|crowd|near|overlap|clearance).*(vcc|ref)|supply",
    },
]
INJECTED_CUES = {
    "detached_value": r"(value|label).*(detach|far|distant|associat|closer|near|belong|misplac)"
    r"|(detach|associat|misplac).*(value|label)",
    "overlapping_fields": r"overlap|collid|collision|obscur|superimpos",
    "distant_reference": r"(reference|ref|designator|label).*(detach|far|distant|associat|away)"
    r"|(detach|distant|far).*(reference|designator)",
    "off_balance_page": r"composition|balance|corner|unused|empty|whitespace|white space|"
    r"off-cent|centr|cluster",
}
# The recurring false claim on good drawings: rails drawn with power symbols read as labels.
FALSE_RAIL_CLAIM = (
    r"text label|net label|labels only|rely on (text )?label|only by (text )?label|"
    r"not (visibly|visually) (connected|continuous)|disjoint|no (continuous|explicit) wire"
)


def image_only(assessment: SchematicAssessment) -> SchematicAssessment:
    """Withhold every check outcome and diagnostic but keep the check names.

    The reviewer chooses its rail guidance from the reported check names, so dropping
    them (as the brief-v2 harness did) would switch it to wire-only rail guidance.
    """
    report = {
        key: assessment.report[key]
        for key in ("intended_circuit", "field_inventory", "terminal_inventory", "schematic_sha256")
        if key in assessment.report
    }
    report["checks"] = {name: "WITHHELD" for name in assessment.report["checks"]}
    report["independent_checks"] = "WITHHELD_FOR_IMAGE_QUALIFICATION"
    return replace(assessment, report=report)


def design_path(name: str) -> Path:
    m2b = ROOT / "fixtures/m2b" / f"{name}.json"
    return m2b if m2b.is_file() else ROOT / "fixtures/pivot" / name / "design.json"


def accepted_schematic(folder: Path) -> Path:
    result = folder / "result.json"
    if result.is_file():
        return folder / json.loads(result.read_text())["accepted_schematic"]
    (schematic,) = (folder / "project").glob("*.kicad_sch")
    return schematic


def prepare_cases(
    args,
    max_field_distance: float,
    power_rails: bool,
    readability: bool,
    page_balance: bool,
    root: Path,
    field_ownership: bool = False,
    text_and_ground_checks: bool = False,
) -> list[dict]:
    cases = []

    def add(name, design_name, group, source, expected, **extra) -> None:
        if args.cases and name not in args.cases:
            return
        directory = root / "cases" / name
        directory.mkdir(parents=True)
        engine = NativeSchematicEngine(
            json.loads(design_path(design_name).read_text()),
            args.kicad_apprun,
            source=source,
            maximum_field_distance_mm=max_field_distance,
            power_symbol_rails=power_rails,
            readability_checks=readability,
            page_balance=page_balance,
            field_ownership=field_ownership,
            text_and_ground_checks=text_and_ground_checks,
        )
        schematic = engine.initial(directory)
        assessment = engine.assess(schematic, directory)
        cases.append(
            {
                "case": name,
                "design": design_name,
                "group": group,
                "expected": expected,
                "source": str(
                    source.relative_to(ROOT)
                    if source.is_relative_to(ROOT)
                    else source.relative_to(root)
                ),
                "assessment": assessment,
                **extra,
            }
        )
        print("prepared", name, assessment.report["checks"], flush=True)

    good = EXPERIMENTS / KNOWN_GOOD_RUN
    designs = sorted(path.parent.name for path in good.glob("*/result.json"))
    for design_name in designs:
        add(
            f"{design_name}__known_good",
            design_name,
            "known_good",
            accepted_schematic(good / design_name),
            "accept",
        )
    for item in HISTORICAL:
        add(
            item["case"],
            item["design"],
            "historical",
            accepted_schematic(EXPERIMENTS / item["source"]),
            "reject",
            defect=item["defect"],
            fixed_by=item["fixed_by"],
            cue=item["cue"],
        )
    for design_name in INJECT_DESIGNS:
        source = accepted_schematic(good / design_name)
        for kind, action in defect_actions(source.read_text()).items():
            name = f"{design_name}__{kind}"
            if args.cases and name not in args.cases:
                continue
            injected = root / "injected" / name / source.name
            injected.parent.mkdir(parents=True)
            injected.write_text(edit_schematic_text(source.read_text(), [action]))
            add(
                name,
                design_name,
                "injected",
                injected,
                "reject",
                defect=kind,
                action=action.model_dump(mode="json"),
                cue=INJECTED_CUES[kind],
            )
    return cases


def score(row: dict, case: dict) -> None:
    issues = " ".join(row.get("issues", [])).lower()
    rejected = row["decision"] in {"revise", "needs_help"}
    row["model_rejects"] = rejected
    row["loop_would_accept"] = (
        row["decision"] == "accept"
        and case["assessment"].passed
        and not row.get("issues")
        and not row.get("actions")
    )
    row["names_defect"] = bool(
        rejected and case.get("cue") and re.search(case["cue"], issues) is not None
    )
    row["false_rail_claim"] = bool(rejected and re.search(FALSE_RAIL_CLAIM, issues))


def metrics(rows: list[dict]) -> dict:
    out = {}
    for mode in sorted({row["mode"] for row in rows}):
        for seed in sorted({row["seed"] for row in rows}):
            selected = [r for r in rows if r["mode"] == mode and r["seed"] == seed]
            group = {}
            for name in ("known_good", "historical", "injected"):
                part = [r for r in selected if r["group"] == name]
                silent = [r for r in part if r["machine_pass"]]
                group[name] = {
                    "cases": len(part),
                    "machine_silent": len(silent),
                    "invalid": sum(r["decision"] == "INVALID" for r in part),
                    "model_rejects": sum(r["model_rejects"] for r in part),
                    "names_defect": sum(r["names_defect"] for r in part),
                    "false_rail_claim": sum(r["false_rail_claim"] for r in part),
                    "loop_would_accept": sum(r["loop_would_accept"] for r in part),
                    "machine_silent_model_rejects": sum(r["model_rejects"] for r in silent),
                    "machine_silent_names_defect": sum(r["names_defect"] for r in silent),
                }
            out[f"{mode}/seed{seed}"] = group
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--model", default="qwen35-256k:latest")
    parser.add_argument(
        "--review-brief", type=Path, default=ROOT / "fixtures/pivot/schematic_review_brief_v3.json"
    )
    parser.add_argument("--context-tokens", type=int, default=262144)
    parser.add_argument("--output-tokens", type=int, default=2048)
    parser.add_argument("--model-timeout", type=float, default=600)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261025])
    parser.add_argument("--modes", nargs="+", choices=["full", "image_only"], default=["full"])
    parser.add_argument("--cases", nargs="*", help="run only these case names (default: all)")
    parser.add_argument("--think", action="store_true", help="let the reviewer reason first")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--svg", action="store_true", help="review the SVG source as text")
    source.add_argument(
        "--description", action="store_true", help="review a plain-text drawing description"
    )
    parser.add_argument(
        "--with-images", action="store_true", help="with --svg/--description, also send PNGs"
    )
    parser.add_argument(
        "--prepare-only", action="store_true", help="build and assess cases without the model"
    )
    parser.add_argument(
        "--scratch-dir", type=Path, help="write to this new directory instead (smoke tests only)"
    )
    args = parser.parse_args()
    args.review_brief = args.review_brief.resolve()
    max_field_distance, brief_text = resolve_review_brief(args.review_brief, None)
    power_rails = brief_allows_power_symbol_rails(args.review_brief)
    readability = brief_requires_readability_checks(args.review_brief)
    page_balance = brief_requires_page_balance(args.review_brief)
    field_ownership = brief_requires_field_ownership(args.review_brief)
    text_and_ground = brief_requires_text_and_ground_checks(args.review_brief)
    if args.scratch_dir:
        args.scratch_dir.mkdir(parents=True, exist_ok=False)
        root = args.scratch_dir.resolve()
    else:
        root = create_experiment_dir(ROOT, args.experiment_id)
    cases = prepare_cases(
        args,
        max_field_distance,
        power_rails,
        readability,
        page_balance,
        root,
        field_ownership,
        text_and_ground,
    )
    # A prepare-only run records the independent check results without any model review.
    reviewer = None
    if not args.prepare_only:
        reviewer = OllamaSchematicReviewer(
            args.model,
            context_tokens=args.context_tokens,
            output_tokens=args.output_tokens,
            timeout_seconds=args.model_timeout,
            think=args.think,
            svg_source=args.svg,
            description_source=args.description,
            with_images=args.with_images,
            review_brief=brief_text,
        )
    rows = []
    for seed in [] if args.prepare_only else args.seeds:
        reviewer.options["seed"] = seed
        for mode in args.modes:
            for case in cases:
                assessment = case["assessment"]
                sent = image_only(assessment) if mode == "image_only" else assessment
                # Blind mode: the prompt also says the verdicts are withheld.
                reviewer.withhold_checks = mode == "image_only"
                record = root / "reviews" / f"seed{seed}" / mode / f"{case['case']}.json"
                row = {
                    "seed": seed,
                    "mode": mode,
                    "case": case["case"],
                    "design": case["design"],
                    "group": case["group"],
                    "expected": case["expected"],
                    "machine_pass": assessment.passed,
                    "record": str(record.relative_to(root)),
                }
                try:
                    review = SchematicReview.model_validate_json(reviewer.review(sent, "", record))
                    row.update(
                        decision=review.decision,
                        issues=review.issues,
                        actions=[action.model_dump(mode="json") for action in review.actions],
                    )
                except (ValueError, OSError) as error:
                    row.update(decision="INVALID", error=str(error))
                score(row, case)
                rows.append(row)
                print(seed, mode, case["case"], row["decision"], flush=True)
    summary = {
        "schema_version": "review-qualification-v3.v1",
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "harness_sha256": file_hash(Path(__file__)),
        "reviewer": reviewer.identity if reviewer else "NOT_RUN",
        "reviewer_options": reviewer.options if reviewer else None,
        "review_brief": str(args.review_brief.relative_to(ROOT)),
        "review_brief_sha256": file_hash(args.review_brief),
        "known_good_run": KNOWN_GOOD_RUN,
        "scoring": {
            "names_defect": "a rejection whose issues match the case's cue regex",
            "false_rail_claim": FALSE_RAIL_CLAIM,
            "loop_would_accept": "accept with no issues/actions while every check passes",
        },
        "cases": [
            {
                key: case[key]
                for key in (
                    "case",
                    "design",
                    "group",
                    "expected",
                    "source",
                    "defect",
                    "fixed_by",
                    "action",
                    "cue",
                )
                if key in case
            }
            | {
                "machine_checks": case["assessment"].report["checks"],
                "machine_pass": case["assessment"].passed,
                "schematic_sha256": file_hash(case["assessment"].schematic),
                "images": {
                    str(path.relative_to(root)): file_hash(path)
                    for path in case["assessment"].images
                },
            }
            for case in cases
        ],
        "metrics": metrics(rows),
        "reviews": rows,
        "locked_host_qualification": False,
        "human_readability_review": "PENDING",
    }
    write_json(root / "summary.json", summary)
    print(json.dumps(summary["metrics"], indent=1))


if __name__ == "__main__":
    main()
