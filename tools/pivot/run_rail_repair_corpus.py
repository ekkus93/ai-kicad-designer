"""Exercise generic rail-connection and symbol-move edits across the M2b corpus.

For each design with asserted power nets, the native compiler output is assessed;
each net that lacks a visible wire path receives ``connect_rail``. When no safe route
exists, single grid-aligned ``move_symbols`` edits of that net's terminal owners are
searched, each followed by a full native reassessment and another ``connect_rail``.
With ``--power-symbols`` (review brief v3), a rail that cannot be wired is next drawn
with ``use_power_symbols`` before the move search, and a final plan draws every failing
rail with power symbols.
No fixture-specific coordinates are used. Every candidate is retained.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import subprocess
import time

from ai_kicad.pivot.power_symbols import _wire_segments
from ai_kicad.pivot.power_symbols import power_symbols as placed_power_symbols
from ai_kicad.pivot.schematic_review import (
    ConnectRail,
    MoveSymbols,
    UsePowerSymbols,
    file_hash,
    write_json,
)
from ai_kicad.pivot.schematic_review_native import NativeSchematicEngine
from ai_kicad.sexpr import parse
from tools.pivot.experiment_paths import create_experiment_dir

ROOT = Path(__file__).resolve().parents[2]
HARD_CHECKS = ("native_tools", "erc", "electrical_equivalence", "observed_layout")
DESIGNS = (
    "dual_buffer",
    "dual_rail_reference",
    "inverting_gain",
    "linear_regulator",
    "noninverting_gain",
    "rc_to_buffer",
    "sallen_key",
    "timer_astable",
)
PITCHES = (4, 8, 12, 16)
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def rail_witnesses(assessment) -> list[dict]:
    layout = assessment.report.get("layout", {})
    if "rail_presentation" in assessment.report["checks"]:
        return layout.get("rail_presentation_witnesses", [])
    return layout.get("observed_power_rail_wire_path_witnesses", [])


def hard_pass(assessment) -> bool:
    checks = assessment.report["checks"]
    required = HARD_CHECKS + (("power_symbol_clearance",) if "rail_presentation" in checks else ())
    return all(checks.get(name) == "PASS" for name in required)


def presentation_cost(assessment) -> tuple[int, float]:
    """Power symbols drawn and total wire length of a candidate."""
    tree = parse(assessment.schematic.read_text())
    wire = sum(
        abs(first[0] - second[0]) + abs(first[1] - second[1])
        for first, second in _wire_segments(tree)
    )
    return len(placed_power_symbols(tree)), round(wire / 1_000_000, 2)


def design_path(name: str) -> Path:
    path = ROOT / "fixtures/m2b" / f"{name}.json"
    return path if path.is_file() else ROOT / "fixtures/pivot" / name / "design.json"


def repair_design(
    name: str, launcher: Path, output: Path, budget_seconds: float, power_symbols: bool = False
) -> dict:
    design = json.loads(design_path(name).read_text())
    engine = NativeSchematicEngine(design, launcher, power_symbol_rails=power_symbols)
    references = {component["id"]: component["refdes"] for component in design["components"]}
    owners = {
        net["id"]: sorted({references[component] for component, _pin in net["members"]})
        for net in design["nets"]
    }
    started, counter, steps = time.monotonic(), 0, []

    def next_directory() -> Path:
        nonlocal counter
        counter += 1
        return output / f"{counter:04d}"

    def attempt(assessment, action) -> object | None:
        directory = next_directory()
        record = {"candidate": directory.name, "action": action.model_dump(mode="json")}
        try:
            schematic = engine.apply(assessment.schematic, directory, [action])
        except ValueError as error:
            record["rejected"] = str(error)
            steps.append(record)
            return None
        try:
            candidate = engine.assess(schematic, directory)
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            record["assessment_error"] = str(error)
            steps.append(record)
            return None
        record["checks"] = candidate.report["checks"]
        record["schematic_sha256"] = file_hash(schematic)
        steps.append(record)
        return candidate

    directory = next_directory()
    try:
        initial = engine.assess(engine.initial(directory), directory)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        result = {
            "design": name,
            "status": "TOOL_ERROR",
            "reason": str(error),
            "applied_edits": [],
            "unresolved_nets": ["(initial assessment failed)"],
            "elapsed_seconds": round(time.monotonic() - started, 1),
        }
        write_json(output / "result.json", result)
        return result
    steps.append(
        {"candidate": directory.name, "action": "initial", "checks": initial.report["checks"]}
    )

    def plan(priority: list[str], style: str = "wire") -> tuple[object, list[dict]]:
        current, applied, blocked = initial, [], set()
        while pending := [w["net"] for w in rail_witnesses(current) if w["net"] not in blocked]:
            if time.monotonic() - started > budget_seconds:
                break
            net = min(pending, key=lambda item: (priority.index(item), item))
            edits = {
                "wire": [ConnectRail(operation="connect_rail", net=net)],
                "rewire": [ConnectRail(operation="connect_rail", net=net, replace_existing=True)],
                "power": [],
            }[style]
            if power_symbols:
                edits.append(UsePowerSymbols(operation="use_power_symbols", net=net))
            for edit in edits:
                edited = attempt(current, edit)
                if edited is not None and hard_pass(edited):
                    current = edited
                    applied.append(edit.model_dump(mode="json"))
                    break
            else:
                edited = None
            if edited is not None:
                continue
            found = False
            for reference in owners[net]:
                for pitch in PITCHES:
                    for sx, sy in DIRECTIONS:
                        if found or time.monotonic() - started > budget_seconds:
                            break
                        move = MoveSymbols(
                            operation="move_symbols",
                            references=[reference],
                            dx_mm=round(sx * pitch * 1.27, 2),
                            dy_mm=round(sy * pitch * 1.27, 2),
                        )
                        moved = attempt(current, move)
                        if moved is None or not hard_pass(moved):
                            continue
                        connected = attempt(moved, ConnectRail(operation="connect_rail", net=net))
                        if (
                            connected is not None
                            and hard_pass(connected)
                            and net not in {w["net"] for w in rail_witnesses(connected)}
                        ):
                            current, found = connected, True
                            applied += [
                                move.model_dump(mode="json"),
                                {"operation": "connect_rail", "net": net},
                            ]
            if not found:
                blocked.add(net)
        return current, applied

    # A rail routed first can enclose another rail's terminals. When a net stays blocked,
    # replan from the initial schematic with the blocked nets first; keep the best plan.
    failing = sorted({w["net"] for w in rail_witnesses(initial)})
    orderings, plans, outcomes = [(failing, "wire")], [], []
    if power_symbols:
        # Brief v3: compare every rail order, keeping or rerouting existing rail runs, and
        # prefer the drawing with the fewest power symbols (most rail drawn as wire).
        orderings = [
            (list(order), style)
            for style in ("wire", "rewire")
            for order in itertools.permutations(failing)
        ]
    while orderings and time.monotonic() - started <= budget_seconds:
        priority, style = orderings.pop(0)
        final, edits = plan(priority, style)
        unresolved = sorted({w["net"] for w in rail_witnesses(final)})
        if not hard_pass(final):
            unresolved = sorted(set(unresolved) | {"(hard checks)"})
        symbols, wire_mm = presentation_cost(final)
        plans.append(
            {
                "priority": priority,
                "style": style,
                "unresolved_nets": unresolved,
                "power_symbols": symbols,
                "wire_length_mm": wire_mm,
            }
        )
        outcomes.append((final, edits))
        if power_symbols and orderings:
            continue
        if not unresolved or any(not entry["unresolved_nets"] for entry in plans):
            break
        retry = [net for net in unresolved if net in failing]
        retry += [net for net in failing if net not in retry]
        if (retry, "wire") not in [(entry["priority"], entry["style"]) for entry in plans]:
            orderings.append((retry, "wire"))
        elif power_symbols and not any(entry["style"] == "power" for entry in plans):
            # Every wiring order left a rail unresolved: draw each failing rail with
            # power symbols, the conventional presentation brief v3 accepts.
            orderings.append((failing, "power"))
    best = min(
        range(len(plans)),
        key=lambda index: (
            len(plans[index]["unresolved_nets"]),
            plans[index]["power_symbols"],
            plans[index]["wire_length_mm"],
            index,
        ),
    )
    current, applied = outcomes[best]
    result = {
        "design": name,
        "initial_failing_nets": sorted({w["net"] for w in rail_witnesses(initial)}),
        "applied_edits": applied,
        "plans": plans,
        "unresolved_nets": sorted({w["net"] for w in rail_witnesses(current)}),
        "final_candidate": str(current.schematic.relative_to(output)),
        "final_checks": current.report["checks"],
        "final_schematic_sha256": file_hash(current.schematic),
        "final_images": [str(path.relative_to(output)) for path in current.images],
        "candidates_attempted": counter,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "budget_exhausted": time.monotonic() - started > budget_seconds,
        "steps": steps,
    }
    write_json(output / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument("--designs", nargs="*", default=list(DESIGNS))
    parser.add_argument("--budget-seconds", type=float, default=1800)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--power-symbols",
        action="store_true",
        help="apply review brief v3: rails may be drawn with matching power symbols",
    )
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "src", "tools"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            name: pool.submit(
                repair_design,
                name,
                args.kicad_apprun,
                root / name,
                args.budget_seconds,
                args.power_symbols,
            )
            for name in args.designs
        }
        results = {name: future.result() for name, future in futures.items()}
    summary = {
        "schema_version": "rail-repair-corpus.v1",
        "source_commit": commit,
        "source_tree_clean": not dirty,
        "implementation_sha256": {
            path: file_hash(ROOT / path)
            for path in (
                "src/ai_kicad/pivot/schematic_review.py",
                "src/ai_kicad/pivot/schematic_review_native.py",
                "src/ai_kicad/pivot/power_symbols.py",
                "tools/pivot/run_rail_repair_corpus.py",
            )
        },
        "rail_policy": "wire_or_power_symbols (brief v3)" if args.power_symbols else "wire_only",
        "designs": {
            name: {key: value for key, value in result.items() if key != "steps"}
            for name, result in results.items()
        },
        "locked_host_qualification": False,
        "human_readability_review": "PENDING",
    }
    write_json(root / "summary.json", summary)
    for name, result in results.items():
        print(name, result["applied_edits"], "unresolved:", result["unresolved_nets"])


if __name__ == "__main__":
    main()
