"""Generate and assess every corpus design under a brief, without a model (spec R7).

Records each drawing's checks, the generator's layout steps and the R7.3 connector detours,
so a generator change can be shown to keep the exact netlist, ERC and every check passing
across the corpus.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from ai_kicad.pivot.schematic_review import file_hash, write_json
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--review-brief", type=Path, required=True)
    parser.add_argument("--designs", nargs="*")
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    service = NativeSchematicReviewService(
        args.kicad_apprun, "unused", review_brief=args.review_brief.resolve()
    )
    results = {}
    for design in CORPUS:
        name = design.parent.name if design.name == "design.json" else design.stem
        if args.designs and name not in args.designs:
            continue
        directory = root / name
        directory.mkdir()
        try:
            engine = service.engine(design)
            source = engine.initial(directory)
            report = engine.assess(source, directory).report
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            results[name] = {"error": str(error)}
            print(name, "ERROR", error, flush=True)
            continue
        presentation = json.loads((directory / "presentation.json").read_text())
        results[name] = {
            "schematic": str(source.relative_to(root)),
            "schematic_sha256": file_hash(source),
            "checks": report["checks"],
            "all_pass": all(value == "PASS" for value in report["checks"].values()),
            "connector_flow": presentation.get("connector_flow"),
            "connector_flow_attempts": presentation.get("connector_flow_attempts"),
            "connector_detours": [
                {key: row[key] for key in ("net", "pins", "excess_mm", "u_turn_at")}
                for row in report.get("net_detours", [])
                if row["excess_mm"] > 2.54 and any(pin.startswith("J") for pin in row["pins"])
            ],
            "quality": {
                key: report["quality"].get(key)
                for key in ("wire_length_mm", "bends", "rail_detour_mm", "perimeter_length_mm")
            },
        }
        print(name, "all_pass" if results[name]["all_pass"] else report["checks"], flush=True)
    write_json(
        root / "summary.json",
        {
            "schema_version": "generator-check.v1",
            "source_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip(),
            "review_brief": str(args.review_brief.resolve().relative_to(ROOT)),
            "review_brief_sha256": file_hash(args.review_brief),
            "results": results,
            "all_pass": all(item.get("all_pass") for item in results.values()),
        },
    )


if __name__ == "__main__":
    main()
