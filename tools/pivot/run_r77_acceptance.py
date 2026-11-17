"""Run the spec R7.7 acceptance tests on a regenerated baseline and record the results.

The tests name drawings by their v10 blind codes (B01-B15); the v10 blind key maps each
code to its design, and the design's drawing in the new baseline is measured. The R7.3
measures are recomputed on the v10 drawings too, since they predate it. Report-only: it
records what each test finds and never edits a drawing.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from ai_kicad.pivot.net_detours import pin_pair_detours
from ai_kicad.pivot.schematic_description import _instances
from ai_kicad.pivot.supply_blocks import capacitor_distances
from ai_kicad.sexpr import parse

ROOT = Path(__file__).resolve().parents[2]
V10 = ROOT / "fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1"
# R2 measures where a larger value is worse, and the one where smaller is worse.
LARGER_IS_WORSE = ("wire_length_mm", "bends", "rail_detour_mm", "perimeter_length_mm")
SMALLER_IS_WORSE = ("text_clearance_mm",)


def _sheet(directory: Path) -> list:
    return parse(Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text())


def _detours(directory: Path) -> list[dict]:
    report = json.loads((directory / "assessment.json").read_text())
    return pin_pair_detours(_sheet(directory), report["terminal_inventory"])


def _r73(rows: list[dict]) -> dict:
    return {
        "excess_mm": round(sum(r["excess_mm"] for r in rows), 3),
        "leaves_part_box": sorted("–".join(r["pins"]) for r in rows if r["leaves_part_box"]),
        "u_turns": sorted("–".join(r["pins"]) for r in rows if r["u_turn_at"]),
    }


def _centre(tree: list, reference: str) -> tuple[float, float]:
    bodies = [i["body"] for i in _instances(tree) if i["reference"] == reference]
    return (
        sum((b[0] + b[2]) / 2 for b in bodies) / len(bodies) / 1e6,
        sum((b[1] + b[3]) / 2 for b in bodies) / len(bodies) / 1e6,
    )


def u_turns(directory: Path) -> dict:
    """No connector U-turn longer than 2.54 mm without a recorded constraint."""
    presentation = json.loads((directory / "presentation.json").read_text())
    constrained = {
        m["connector"]
        for m in presentation.get("connector_flow", [])
        if m.get("change") is None and m.get("kept_because")
    }
    found = []
    for row in _detours(directory):
        for pin in row["u_turn_at"]:
            if not pin.startswith("J"):
                continue
            path = row["path"] if pin == row["pins"][0] else row["path"][::-1]
            leg = abs(path[1][0] - path[0][0]) + abs(path[1][1] - path[0][1])
            if leg > 2.54:
                found.append({"pin": pin, "pins": row["pins"], "leg_mm": round(leg, 3)})
    unexplained = [f for f in found if f["pin"].split(".")[0] not in constrained]
    return {"pass": not unexplained, "u_turns": found, "unexplained": unexplained}


def regulator_flow(directory: Path, design: dict) -> dict:
    """VIN and its connector left of U1, VOUT and J2 right of U1, capacitors by their pins."""
    tree = _sheet(directory)
    u1 = _centre(tree, "U1")
    j1, j2 = _centre(tree, "J1"), _centre(tree, "J2")
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    caps = capacitor_distances(design, text)
    local = all(c["direct"] and c["distance_mm"] <= 25.4 for c in caps)
    return {
        "pass": j1[0] < u1[0] < j2[0] and local,
        "J1_left_of_U1": j1[0] < u1[0],
        "J2_right_of_U1": j2[0] > u1[0],
        "capacitors": [(c["capacitor"], c["serves"], c["distance_mm"], c["direct"]) for c in caps],
    }


def timer_output(directory: Path) -> dict:
    """The output net reaches its connector without routing around the timer."""
    rows = [
        r
        for r in _detours(directory)
        if r["net"] in ("OUT",) and any(p.startswith("U1.") for p in r["pins"])
    ]
    to_connector = [r for r in rows if any(p.startswith("J") for p in r["pins"])]
    ok = bool(to_connector) and all(
        not r["leaves_part_box"] and not r["u_turn_at"] for r in to_connector
    )
    return {
        "pass": ok,
        "paths": [
            {k: r[k] for k in ("pins", "excess_mm", "leaves_part_box", "u_turn_at")}
            for r in to_connector
        ],
    }


def power_block(directory: Path, design: dict) -> dict:
    """The power unit and decoupling form one block, separate from the signal lines,
    with exact connectivity."""
    report = json.loads((directory / "assessment.json").read_text())
    text = Path(glob.glob(str(directory / "project/*.kicad_sch"))[0]).read_text()
    caps = capacitor_distances(design, text)
    checks_pass = all(v == "PASS" for v in report["checks"].values())
    intrusions = report.get("block_layout", {}).get("intrusions", [])
    local = all(c["direct"] and c["distance_mm"] <= 25.4 for c in caps)
    return {
        "pass": checks_pass and not intrusions and local,
        "every_check_passes": checks_pass,
        "intrusions": intrusions,
        "capacitors": [(c["capacitor"], c["serves"], c["distance_mm"], c["direct"]) for c in caps],
    }


def no_regression(directory: Path, old: Path) -> dict:
    """Not worse than v10 on the R2 measures and on R7.3."""
    new_q = json.loads((directory / "assessment.json").read_text())["quality"]
    old_q = json.loads((old / "assessment.json").read_text())["quality"]
    worse = {}
    for key in LARGER_IS_WORSE:
        if new_q.get(key) is not None and old_q.get(key) is not None and new_q[key] > old_q[key]:
            worse[key] = {"v10": old_q[key], "v11": new_q[key]}
    for key in SMALLER_IS_WORSE:
        if new_q.get(key) is not None and old_q.get(key) is not None and new_q[key] < old_q[key]:
            worse[key] = {"v10": old_q[key], "v11": new_q[key]}
    r73_old, r73_new = _r73(_detours(old)), _r73(_detours(directory))
    r73_worse = {}
    if r73_new["excess_mm"] > r73_old["excess_mm"]:
        r73_worse["excess_mm"] = {"v10": r73_old["excess_mm"], "v11": r73_new["excess_mm"]}
    for key in ("leaves_part_box", "u_turns"):
        added = sorted(set(r73_new[key]) - set(r73_old[key]))
        if added:
            r73_worse[key] = added
    return {
        "pass": not worse and not r73_worse,
        "r2_worse": worse,
        "r73_worse": r73_worse,
        "r73": {"v10": r73_old, "v11": r73_new},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args(argv)
    from tools.pivot.run_review_loop_corpus import CORPUS

    files = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}
    key = json.loads((V10 / "blind_key.json").read_text())
    design_of = {code: item["design"] for code, item in key.items()}

    def drawing(code: str) -> Path:
        return args.baseline / "drawings" / design_of[code]

    def design(code: str) -> dict:
        return json.loads(files[design_of[code]].read_text())

    results = {
        "u_turns": {c: u_turns(drawing(c)) for c in ("B04", "B08", "B11")},
        "regulator_flow": {"B03": regulator_flow(drawing("B03"), design("B03"))},
        "timer_output": {c: timer_output(drawing(c)) for c in ("B05", "B10", "B15")},
        "power_blocks": {
            c: power_block(drawing(c), design(c)) for c in ("B07", "B09", "B12", "B14")
        },
        "no_regressions": {
            c: no_regression(drawing(c), V10 / "drawings" / design_of[c])
            for c in ("B06", "B13", "B01", "B02", "B07")
        },
    }
    summary = {
        test: {code: row["pass"] for code, row in rows.items()} for test, rows in results.items()
    }
    out = {
        "schema_version": "r77-acceptance.v1",
        "baseline": os.path.relpath(args.baseline, ROOT),
        "v10_blind_key": str((V10 / "blind_key.json").relative_to(ROOT)),
        "summary": summary,
        "results": results,
    }
    (args.baseline / "r77_acceptance.json").write_text(json.dumps(out, indent=2) + "\n")
    json.dump(summary, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
