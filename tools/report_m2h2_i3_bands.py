"""Check measured I3 band structure in qualified emitted candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def assess(record: dict) -> dict:
    expected_path = Path("fixtures/m2h2/interaction/i3") / f"{record['id']}.expected.json"
    expected = json.loads(expected_path.read_text())
    observed_run = next((run for run in record["runs"] if "signature" in run), None)
    if observed_run is None:
        return {
            "id": record["id"],
            "cell": expected["factor_cell"],
            "real_tool_accepted": False,
            "observed_band_count": "not_evaluated",
            "covered": False,
        }
    variants = observed_run["signature"]["composition"]["variants"]
    placed = [item for item in variants if not item["fragment"].startswith("interface.")]
    timers = [item for item in placed if item["fragment"].startswith("timer.")]
    groups: list[list[dict]] = []
    for item in sorted(placed, key=lambda value: (value["placed_envelope"][1], value["fragment"])):
        top = item["placed_envelope"][1]
        if not groups or top - groups[-1][0]["placed_envelope"][1] > 5_080_000:
            groups.append([])
        groups[-1].append(item)
    backfill = any(
        any(item["fragment"].startswith("timer.") for item in group)
        and any(item["fragment"].startswith("passive.") for item in group)
        for group in groups
    )
    requested = expected["requested_band_structure"]
    band_match = (
        len(groups) == 1
        if requested == "one"
        else len(groups) >= 2 and (requested != "interleaved" or backfill)
    )
    qualified = record["accepted"] and len(timers) == expected["active_core_count"] and band_match
    return {
        "id": record["id"],
        "cell": expected["factor_cell"],
        "real_tool_accepted": record["accepted"],
        "active_core_count": len(timers),
        "requested_band_structure": requested,
        "observed_band_count": len(groups),
        "backfill_with_active_core": backfill,
        "band_groups": [[item["fragment"] for item in group] for group in groups],
        "covered": qualified,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    results = json.loads(args.results.read_text())
    cases = [assess(item) for item in results["results"] if item["id"].startswith("a")]
    payload = {
        "schema_version": "m2h2.i3-band-assessment.1",
        "covered": sum(item["covered"] for item in cases),
        "required": 12,
        "cases": cases,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(payload["covered"], "/", payload["required"])


if __name__ == "__main__":
    main()
