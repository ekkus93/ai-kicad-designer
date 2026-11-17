"""The generator's runner-up drawings as menu entries (brief v12, spec R8.2, R8.6).

When the design is compiled, each move a layout step chose is excluded in turn and the
design compiled again, so that step takes its next-best candidate (option (a), owner
decision 2026-11-17). The variants that pass every check are stored on the engine. This
module turns them into menu entries: each is applied in scratch exactly as `choose_edit`
would apply it (`use_variant`), validated like any other entry, and offered with its
scratch revision and predicted R2 delta. A "keep the current drawing" entry is always
offered beside them.

A variant replaces the whole drawing, so variants are offered only on the drawing the
generator produced; after another edit they would undo it.
"""

from __future__ import annotations

import time
from typing import Callable

from .edit_menu import ValidationCache
from .quality_measures import compare_quality
from .review_status import broken_connectivity

KEEP_ENTRY = {
    "id": "keep-1",
    "class": "keep",
    "target": {},
    "description": "keep the current drawing as it is",
    "optional": True,
    "fixes": [],
    "gains": [],
    "predicted_delta": None,
    "action": {"operation": "keep_drawing"},
    "scratch_revision": None,
}


def layout_measures(report: dict, design: dict | None, text: str) -> dict:
    """The report-only measures that trigger generator entries (spec R8.3), each with
    whether it flags something on this drawing."""
    from .block_moves import GROUPED_MM
    from .supply_blocks import BESIDE_MM, capacitor_distances, power_block_directions

    detours = report.get("net_detours")
    detours = detours if isinstance(detours, list) else []
    returns = report.get("return_connector_distances")
    returns = returns if isinstance(returns, list) else []
    caps = capacitor_distances(design, text) if design else []
    sideways = (
        [r for r in power_block_directions(design, text) if not r["consistent"]] if design else []
    )
    measures = {
        "r73_detours": {
            "excess_mm": round(sum(r["excess_mm"] for r in detours), 3),
            "u_turns": sum(1 for r in detours if r["u_turn_at"]),
            "leaves_part_box": sum(1 for r in detours if r["leaves_part_box"]),
        },
        "return_connector_distance": {
            "far_mm": round(
                sum(r["distance_mm"] for r in returns if r["distance_mm"] > GROUPED_MM), 3
            )
        },
        "capacitor_distance": {
            "far_mm": round(
                sum(
                    c["distance_mm"]
                    for c in caps
                    if c["distance_mm"] > BESIDE_MM or not c["direct"]
                ),
                3,
            ),
            "not_direct": sum(1 for c in caps if not c["direct"]),
        },
        "sideways_power_symbols": {"count": len(sideways)},
    }
    flagged = {
        "r73_detours": bool(
            measures["r73_detours"]["u_turns"] or measures["r73_detours"]["leaves_part_box"]
        ),
        "return_connector_distance": measures["return_connector_distance"]["far_mm"] > 0,
        "capacitor_distance": measures["capacitor_distance"]["far_mm"] > 0
        or measures["capacitor_distance"]["not_direct"] > 0,
        "sideways_power_symbols": measures["sideways_power_symbols"]["count"] > 0,
    }
    return {"measures": measures, "flagged": [name for name, on in flagged.items() if on]}


def _improves(before: dict, after: dict, flagged: list[str]) -> tuple[list[str], dict]:
    """Flagged measures the variant lowers (no component rises), and every delta."""
    deltas, improved = {}, []
    for name, values in before.items():
        deltas[name] = {key: round(after[name][key] - value, 3) for key, value in values.items()}
    for name in flagged:
        changes = deltas[name].values()
        if any(change < 0 for change in changes) and not any(change > 0 for change in changes):
            improved.append(name)
    return improved, deltas


def generator_entries(
    base,
    variants: dict[str, dict],
    base_text: str | None,
    validate: Callable[[dict], object],
    cache: ValidationCache,
    quality_thresholds: dict | None = None,
    budget_exhausted: str | None = None,
    design: dict | None = None,
) -> tuple[list[dict], dict]:
    """Menu entries for the stored variants, then "keep"; with a record of the work.

    Spec R8.3: entries are offered only when every check passes on the drawing and a
    report-only measure flags something there (R7.3 detours, return-connector distance,
    capacitor distance, sideways power-block symbols), and only for variants that lower a
    flagged measure without raising any of its parts. Each entry names the measures it
    improves, with its predicted R2 and R7.3 deltas."""
    started = time.monotonic()
    record = {
        "variants": len(variants),
        "offered": [],
        "rejected": [],
        "native_validations": 0,
        "cache_hits": 0,
        "budget_exhausted": budget_exhausted,
    }
    keep = dict(KEEP_ENTRY, scratch_revision=base.revision)
    if not variants:
        record["seconds"] = round(time.monotonic() - started, 3)
        return [keep], record
    if base.schematic.read_text() != base_text:
        record["not_offered"] = (
            "the drawing changed since the generator made it; a variant would replace the "
            "whole drawing and undo that change"
        )
        record["seconds"] = round(time.monotonic() - started, 3)
        return [keep], record
    checks = base.report.get("checks", {})
    if not checks or any(value != "PASS" for value in checks.values()):
        record["not_offered"] = "a check fails on this drawing; menu fixes come first (R8.3)"
        record["seconds"] = round(time.monotonic() - started, 3)
        return [keep], record
    before = layout_measures(base.report, design, base_text)
    record["measures"] = before
    if not before["flagged"]:
        record["not_offered"] = "no report-only measure flags this drawing (R8.3)"
        record["seconds"] = round(time.monotonic() - started, 3)
        return [keep], record
    entries = []
    for vid, variant in variants.items():
        action = {"operation": "use_variant", "variant": vid}
        key = cache.key(base.revision, action)
        if key in cache.results:
            record["cache_hits"] += 1
            outcome = cache.results[key]
        else:
            record["native_validations"] += 1
            try:
                trial = validate(action)
            except (ValueError, KeyError) as error:
                outcome = {"ok": False, "reason": f"editor refused: {error}"}
            else:
                trial_checks = trial.report.get("checks", {})
                broken = broken_connectivity(base.report, trial.report)
                newly_failing = sorted(
                    name
                    for name, value in checks.items()
                    if value == "PASS" and trial_checks.get(name) != "PASS"
                )
                base_q, trial_q = base.report.get("quality"), trial.report.get("quality")
                delta = (
                    compare_quality(base_q, trial_q, quality_thresholds)
                    if isinstance(base_q, dict)
                    and isinstance(trial_q, dict)
                    and "error" not in base_q
                    and "error" not in trial_q
                    else None
                )
                if trial.revision == base.revision:
                    outcome = {"ok": False, "reason": "no change"}
                elif broken:
                    outcome = {"ok": False, "reason": f"breaks {', '.join(broken)}"}
                elif newly_failing:
                    outcome = {"ok": False, "reason": f"makes {', '.join(newly_failing)} fail"}
                else:
                    after = layout_measures(trial.report, design, trial.schematic.read_text())[
                        "measures"
                    ]
                    improved, deltas = _improves(before["measures"], after, before["flagged"])
                    if not improved:
                        outcome = {
                            "ok": False,
                            "reason": "lowers no flagged measure: " + ", ".join(before["flagged"]),
                        }
                    else:
                        outcome = {
                            "ok": True,
                            "revision": trial.revision,
                            "predicted_delta": delta,
                            "improves": improved,
                            "measure_deltas": deltas,
                        }
            cache.results[key] = outcome
        if not outcome["ok"]:
            record["rejected"].append({"variant": vid, "reason": outcome["reason"]})
            continue
        entry_id = f"{variant['class']}-{len(entries) + 1}"
        record["offered"].append(entry_id)
        entries.append(
            {
                "id": entry_id,
                "class": variant["class"],
                "target": {"variant": vid, "excluded": variant["excluded"]},
                "description": variant["description"],
                "optional": True,
                "fixes": [],
                "gains": [],
                "improves": outcome["improves"],
                "predicted_r73_delta": outcome["measure_deltas"]["r73_detours"],
                "measure_deltas": outcome["measure_deltas"],
                "predicted_delta": outcome["predicted_delta"],
                "action": action,
                "scratch_revision": outcome["revision"],
            }
        )
    record["seconds"] = round(time.monotonic() - started, 3)
    return [*entries, keep], record
