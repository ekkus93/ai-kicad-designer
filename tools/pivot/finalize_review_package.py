"""Attach a recorded visual review and rebuild a content-verified review ZIP."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.pivot.fabrication import (
    deterministic_zip,
    sha256,
    verify_review_package,
    write_manifest,
)
from tools.pivot.experiment_paths import create_experiment_dir


def finalize(root: Path, source_id: str, package_id: str, reviewer: str) -> Path:
    source = root / "fixtures/pivot/experiments" / source_id
    output = create_experiment_dir(root, package_id)
    for name in ("editable_project", "fabrication", "previews", "reports"):
        shutil.copytree(source / name, output / name)
    verification = json.loads((output / "reports/verification_report.json").read_text())
    manifest = json.loads((source / "fabrication_manifest.json").read_text())
    images = []
    for name, observation in (
        (
            "board-top.png",
            "Board bodies and references U1, C2, D1, R1-R3, J1-J3 are inside the outline with no obvious overlap. C1's reference label is not clearly visible in this render.",
        ),
        (
            "board-bottom.png",
            "Bottom copper and plated holes appear inside the rectangular outline; no off-board route is visually apparent.",
        ),
    ):
        path = output / "previews" / name
        images.append(
            {
                "path": f"previews/{name}",
                "sha256": sha256(path),
                "observation": observation,
            }
        )
    schematic_preview = output / "previews" / "schematic.png"
    if schematic_preview.is_file():
        images.append(
            {
                "path": "previews/schematic.png",
                "sha256": sha256(schematic_preview),
                "observation": (
                    "The external supply, return, and output connectors are drawn at their "
                    "circuit nodes with visible wires. This rendering observation is not an "
                    "independent electrical sign-off."
                ),
            }
        )
    visual_review = {
        "schema_version": "visual-inspection.v1",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "revision_id": verification["revision_id"],
        "images": images,
        "decision": "REVIEW_NOTE",
        "review_note": "C1 reference readability should be checked in KiCad before any physical order. This review does not authorize fabrication or order placement.",
    }
    (output / "visual_inspection.json").write_text(json.dumps(visual_review, indent=2) + "\n")
    write_manifest(
        output,
        verification["revision_id"],
        manifest["checks"],
        manifest["limitations"],
        manifest["provenance"],
    )
    digest = deterministic_zip(output, output / "review-package.zip")
    (output / "package.sha256").write_text(digest + "  review-package.zip\n")
    verify_review_package(output / "review-package.zip", output / "clean-extracted")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-experiment", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--reviewer", default="Codex visual inspection")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(finalize(root, args.source_experiment, args.experiment_id, args.reviewer))


if __name__ == "__main__":
    main()
