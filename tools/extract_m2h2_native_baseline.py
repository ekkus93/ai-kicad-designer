"""Extract a selected, fully verified M2h2 historical native SVG render set."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_kicad.m2_native_render_archive_materialize import materialize_native_baseline
from ai_kicad.m2a import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "fixtures/m2h2/human_composition_baseline_2026-10-08/"
        "native_render_archive_manifest_42ab8452.json",
    )
    parser.add_argument("--case", action="append", dest="cases", default=None)
    args = parser.parse_args()
    inventory = materialize_native_baseline(
        ROOT,
        args.manifest,
        args.out,
        cases=None if args.cases is None else tuple(args.cases),
    )
    print(
        "Verified historical qualification"
        f" {inventory.qualification_head}: {inventory.render_count} archived native SVGs."
    )
    print("Extraction does not establish current-source qualification or visual PASS.")


if __name__ == "__main__":
    main()
