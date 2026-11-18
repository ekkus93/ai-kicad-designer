"""Build the brief v12 edit menu for every corpus design and record its generator entries.

For P6-011v (spec R8.3): on the v11 corpus, generator entries should appear on the
drawings rated defective, and none may make a passing check fail. Each design is compiled
under v12 (the v11 drawing plus its runner-up variants), assessed, and its edit menu
built; the entries, what each improves, its predicted deltas and the menu record are
written to the experiment directory. No reviewer model runs.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from tools.pivot.experiment_paths import create_experiment_dir

ROOT = Path(__file__).resolve().parents[2]
V11_BASELINE = ROOT / "fixtures/pivot/experiments/review_baseline_v11_2026-11-17_run1"


def main() -> None:
    from ai_kicad.pivot.edit_menu import MenuPolicy, ValidationCache, menu_for_reviewer
    from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
    from tools.pivot.run_review_loop_corpus import CORPUS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", required=True, type=Path)
    parser.add_argument("--review-brief", required=True, type=Path)
    parser.add_argument("--designs", nargs="*")
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    service = NativeSchematicReviewService(
        args.kicad_apprun, "m", review_brief=args.review_brief.resolve()
    )
    key = json.loads((V11_BASELINE / "blind_key.json").read_text())
    ratings = {
        r["code"]: r
        for r in json.loads((V11_BASELINE / "ratings/chatgpt.json").read_text())["ratings"]
    }
    rated = {item["design"]: ratings[code]["verdict"] for code, item in key.items()}
    results = {}
    for path in CORPUS:
        name = path.parent.name if path.name == "design.json" else path.stem
        if args.designs and name not in args.designs:
            continue
        started = time.monotonic()
        directory = root / name
        engine = service.engine(path)
        source = engine.initial(directory / "initial")
        assessment = engine.assess(source, directory / "initial")
        menu = engine.edit_menu(
            assessment,
            directory / "menu",
            MenuPolicy.from_profile(service.profile.menu),
            ValidationCache(),
            service.quality_thresholds,
        )
        (directory / "menu.json").write_text(json.dumps(menu, indent=2) + "\n")
        generated = [e for e in menu["entries"] if e["action"]["operation"] == "use_variant"]
        results[name] = {
            "v11_rating": rated.get(name),
            "every_check_passes": all(v == "PASS" for v in assessment.report["checks"].values()),
            "generator_entries": [
                {k: e.get(k) for k in ("id", "class", "improves", "predicted_r73_delta")}
                for e in generated
            ],
            "shown_to_reviewer": [e["id"] for e in menu_for_reviewer(menu) if e["class"] != "keep"],
            "generator_record": {
                k: v for k, v in menu["record"].get("generator", {}).items() if k != "offered"
            },
            "seconds": round(time.monotonic() - started, 1),
        }
        print(name, rated.get(name), [e["id"] for e in generated], flush=True)
    defective = [n for n, r in results.items() if r["v11_rating"] == "defects"]
    summary = {
        "defective_with_entries": sorted(n for n in defective if results[n]["generator_entries"]),
        "defective_without_entries": sorted(
            n for n in defective if not results[n]["generator_entries"]
        ),
        "good_with_entries": sorted(
            n for n, r in results.items() if r["v11_rating"] == "good" and r["generator_entries"]
        ),
    }
    (root / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": "generator-menu-check.v1",
                "review_brief": str(args.review_brief),
                "ratings": str((V11_BASELINE / "ratings/chatgpt.json").relative_to(ROOT)),
                "summary": summary,
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
