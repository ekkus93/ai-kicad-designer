"""Run the complete automatic schematic improvement loop across the vetted corpus.

Each design is generated natively, independently checked, rendered, reviewed by a local
vision model against the versioned owner brief, edited and re-reviewed until joint
acceptance or a budget/capability stop. Every image, request, response, candidate and
check report is retained by the loop under one write-once experiment directory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from ai_kicad.pivot.schematic_review import file_hash, write_json
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
from tools.pivot.experiment_paths import create_experiment_dir

ROOT = Path(__file__).resolve().parents[2]
CORPUS = [
    *(
        ROOT / "fixtures/m2b" / f"{name}.json"
        for name in (
            "rc_lowpass",
            "rc_highpass",
            "led_series",
            "led_long_text",
            "led_reverse_supply",
            "dual_buffer",
            "dual_rail_reference",
            "inverting_gain",
            "noninverting_gain",
            "rc_to_buffer",
            "sallen_key",
            "linear_regulator",
            "timer_astable",
        )
    ),
    ROOT / "fixtures/pivot/reference_555_led_flasher_v8/design.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument(
        "--review-brief", type=Path, default=ROOT / "fixtures/pivot/schematic_review_brief_v2.json"
    )
    parser.add_argument("--max-reviews", type=int, default=8)
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    service = NativeSchematicReviewService(
        args.kicad_apprun, args.model, review_brief=args.review_brief, max_reviews=args.max_reviews
    )
    results = {}
    for design in CORPUS:
        name = design.parent.name if design.name == "design.json" else design.stem
        try:
            result = service.review(design, root / name)
        except (OSError, RuntimeError, ValueError) as error:
            result = {"status": "TOOL_ERROR", "reason": str(error), "iterations": []}
        edits = [
            action["operation"]
            for entry in result.get("iterations", [])
            for action in (entry.get("review") or {}).get("actions", [])
        ]
        results[name] = {
            "design": str(design.relative_to(ROOT)),
            "status": result["status"],
            "reason": result.get("reason"),
            "reviews": len(result.get("iterations", [])),
            "model_tokens": result.get("model_tokens"),
            "requested_edits": edits,
            "rejected_replies": sum(
                1 for entry in result.get("iterations", []) if "rejected_response" in entry
            ),
            "accepted_schematic": result.get("accepted_schematic"),
            "best_passing_schematic": result.get("best_passing_schematic"),
        }
        print(name, result["status"], edits, flush=True)
    summary = {
        "schema_version": "review-loop-corpus.v1",
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "implementation_sha256": {
            path: file_hash(ROOT / path)
            for path in (
                "src/ai_kicad/pivot/schematic_review.py",
                "src/ai_kicad/pivot/schematic_review_native.py",
                "src/ai_kicad/pivot/schematic_review_service.py",
            )
        },
        "model": args.model,
        "review_brief": str(args.review_brief.relative_to(ROOT)),
        "budgets": service.budgets,
        "results": results,
        "accepted": sorted(name for name, item in results.items() if item["accepted_schematic"]),
        "locked_host_qualification": False,
        "independent_readability_assessment": "PENDING",
        "human_electrical_review": "PENDING",
    }
    write_json(root / "summary.json", summary)
    print(json.dumps({"accepted": summary["accepted"]}))


if __name__ == "__main__":
    main()
