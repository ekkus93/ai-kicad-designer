"""Generate a native schematic, review its images with Ollama, and iterate bounded edits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess

from ai_kicad.pivot.schematic_review import (
    OllamaSchematicReviewer,
    file_hash,
    run_schematic_review,
    write_json,
)
from ai_kicad.pivot.schematic_review_brief import resolve_review_brief
from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True, help="intended M2b circuit JSON")
    parser.add_argument(
        "--source", type=Path, help="existing schematic to review; otherwise generate"
    )
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--max-reviews", type=int, default=6)
    parser.add_argument("--max-seconds", type=float, default=600)
    parser.add_argument("--max-model-tokens", type=int, default=60000)
    parser.add_argument("--think", action="store_true")
    parser.add_argument(
        "--review-brief",
        type=Path,
        help="text criteria file or a versioned schematic-review-brief JSON",
    )
    parser.add_argument("--max-field-distance-mm", type=float)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        max_field_distance_mm, review_brief_text = resolve_review_brief(
            args.review_brief, args.max_field_distance_mm
        )
    except ValueError as error:
        parser.error(str(error))
    implementation_paths = (
        Path(__file__).resolve(),
        root / "src/ai_kicad/m2b_observation.py",
        root / "src/ai_kicad/m2_geometry.py",
        root / "src/ai_kicad/m2a_core.py",
        root / "src/ai_kicad/m2a_constants.py",
        root / "src/ai_kicad/m2_transform.py",
        root / "src/ai_kicad/m2_route_core.py",
        root / "src/ai_kicad/pivot/schematic_review_brief.py",
        root / "src/ai_kicad/pivot/schematic_review.py",
        root / "src/ai_kicad/pivot/schematic_review_native.py",
        root / "src/ai_kicad/pivot/schematic_fields.py",
    )
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
    ).strip()
    implementation_hashes = {str(p.relative_to(root)): file_hash(p) for p in implementation_paths}
    design = json.loads(args.design.read_text())
    engine = NativeSchematicEngine(
        design,
        args.kicad_apprun,
        source=args.source,
        maximum_field_distance_mm=max_field_distance_mm,
    )
    reviewer = OllamaSchematicReviewer(
        args.model,
        endpoint=args.ollama_url,
        think=args.think,
        output_tokens=4096 if args.think else 2048,
        **({"review_brief": review_brief_text} if review_brief_text else {}),
    )
    output = args.output.resolve()
    result = run_schematic_review(
        engine,
        reviewer,
        output,
        max_reviews=args.max_reviews,
        max_seconds=args.max_seconds,
        max_model_tokens=args.max_model_tokens,
    )
    write_json(
        output / "manifest.json",
        {
            "schema_version": "schematic-review-experiment.v1",
            "source_commit": source_commit,
            "implementation_sha256": implementation_hashes,
            "implementation_unchanged_during_run": all(
                file_hash(p) == implementation_hashes[str(p.relative_to(root))]
                for p in implementation_paths
            ),
            "design_sha256": file_hash(args.design),
            "initial_schematic_sha256": file_hash(args.source) if args.source else None,
            "host": platform.platform(),
            "toolchain": engine.toolchain,
            "artifacts": {
                str(p.relative_to(output)): file_hash(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
        },
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "reason": result["reason"],
                "accepted_schematic": result["accepted_schematic"],
                "reviews": len(result["iterations"]),
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "ACCEPTED_FOR_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
