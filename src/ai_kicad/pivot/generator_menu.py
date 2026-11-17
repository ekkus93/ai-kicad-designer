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


def generator_entries(
    base,
    variants: dict[str, dict],
    base_text: str | None,
    validate: Callable[[dict], object],
    cache: ValidationCache,
    quality_thresholds: dict | None = None,
    budget_exhausted: str | None = None,
) -> tuple[list[dict], dict]:
    """Menu entries for the stored variants, then "keep"; with a record of the work."""
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
                    outcome = {"ok": True, "revision": trial.revision, "predicted_delta": delta}
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
                "predicted_delta": outcome["predicted_delta"],
                "action": action,
                "scratch_revision": outcome["revision"],
            }
        )
    record["seconds"] = round(time.monotonic() - started, 3)
    return [*entries, keep], record
