"""Status levels and edit outcomes for review-loop results (reviewer loop spec R1).

`ACCEPTED_FOR_REVIEW` implies only ELECTRICALLY_EQUIVALENT, PRESENTATION_PASS and
MODEL_ACCEPTED. It does not imply design suitability, PCB readiness, human review or
measured improvement. Missing evidence is PENDING, never PASS.
"""

from __future__ import annotations

PASS, FAIL, PENDING = "PASS", "FAIL", "PENDING"

# Checks that establish connectivity; an edit that makes one of them fail is rolled back.
CONNECTIVITY_CHECKS = ("native_tools", "erc", "electrical_equivalence")
LEVELS = (
    "NATIVE_VALID",
    "ELECTRICALLY_EQUIVALENT",
    "PRESENTATION_PASS",
    "QUALITY_NOT_WORSE",
    "MODEL_ACCEPTED",
    "DESIGN_REQUIREMENTS_CHECKED",
    "HUMAN_REVIEWED",
)
PRIMARY_EFFECTS = ("FUNCTIONAL_REPAIR", "PRESENTATION_FIX", "LAYOUT_CHANGE")


def _level(status: str, basis: dict | str) -> dict:
    return {"status": status, "basis": basis}


def _from_checks(checks: dict, names: list[str] | tuple[str, ...]) -> dict:
    basis = {name: checks.get(name, "MISSING") for name in names}
    if not names or any(value == "MISSING" for value in basis.values()):
        return _level(PENDING, basis or "no checks configured")
    return _level(PASS if all(value == PASS for value in basis.values()) else FAIL, basis)


def presentation_checks(checks: dict) -> list[str]:
    """Every enabled check that is not a connectivity check."""
    return sorted(name for name in checks if name not in CONNECTIVITY_CHECKS)


def ignored_erc_checks(report: dict) -> list[str] | None:
    """The ERC categories KiCad ignored, or None when the ERC report is missing."""
    erc = report.get("erc")
    if not isinstance(erc, dict) or "ignored_checks" not in erc:
        return None
    return sorted(item["key"] for item in erc["ignored_checks"])


def status_levels(
    report: dict,
    *,
    model_verdict: str | None,
    model_accepted: bool,
    quality: dict | None = None,
) -> dict:
    """R1 levels for one candidate.

    `model_verdict` is the reviewer's last decision on this revision (None when it was
    never reviewed); `model_accepted` is whether the loop accepted it. `quality` is the R2
    comparison with candidate 000, as {"not_worse": bool, ...}; None leaves it PENDING.
    """
    checks = report.get("checks", {})
    if model_accepted:
        model = _level(PASS, {"decision": "accept"})
    elif model_verdict is None:
        model = _level(PENDING, "not reviewed")
    else:
        model = _level(FAIL, {"decision": model_verdict})
    if quality is None:
        not_worse = _level(PENDING, "R2 quality measures not computed")
    else:
        not_worse = _level(PASS if quality["not_worse"] else FAIL, quality)
    return {
        "NATIVE_VALID": _from_checks(checks, ["native_tools"]),
        "ELECTRICALLY_EQUIVALENT": _from_checks(checks, ["electrical_equivalence", "erc"]),
        "PRESENTATION_PASS": _from_checks(checks, presentation_checks(checks)),
        "QUALITY_NOT_WORSE": not_worse,
        "MODEL_ACCEPTED": model,
        "DESIGN_REQUIREMENTS_CHECKED": _level(PENDING, "out of scope for the review loop"),
        "HUMAN_REVIEWED": _level(PENDING, "no human review recorded"),
    }


def broken_connectivity(before: dict, after: dict) -> list[str]:
    """Connectivity checks that passed before and do not pass after."""
    before_checks, after_checks = before.get("checks", {}), after.get("checks", {})
    return sorted(
        name
        for name in CONNECTIVITY_CHECKS
        if before_checks.get(name) == PASS and after_checks.get(name) != PASS
    )


def primary_effect(before: dict, after: dict) -> str:
    """FUNCTIONAL_REPAIR > PRESENTATION_FIX > LAYOUT_CHANGE, from which checks it fixed."""
    before_checks, after_checks = before.get("checks", {}), after.get("checks", {})
    fixed = {
        name
        for name, value in after_checks.items()
        if value == PASS and before_checks.get(name) not in (None, PASS)
    }
    if fixed & set(CONNECTIVITY_CHECKS):
        return "FUNCTIONAL_REPAIR"
    if fixed:
        return "PRESENTATION_FIX"
    return "LAYOUT_CHANGE"


def edit_outcome(
    before: dict,
    after: dict | None,
    *,
    disposition: str,
    reason_class: str | None = None,
    overlay: str | None = None,
) -> dict:
    """The three separate R1 fields of one edit. A rolled-back edit has no primary effect."""
    if disposition not in ("KEPT", "ROLLED_BACK"):
        raise ValueError(f"unknown disposition {disposition!r}")
    kept = disposition == "KEPT"
    return {
        "primary_effect": primary_effect(before, after) if kept and after is not None else None,
        "quality_overlay": overlay if kept else None,
        "disposition": disposition,
        "reason_class": None if kept else reason_class,
    }


def run_primary_effect(outcomes: list[dict]) -> str | None:
    """The highest primary effect among a run's kept edits."""
    effects = [item["primary_effect"] for item in outcomes if item["disposition"] == "KEPT"]
    for effect in PRIMARY_EFFECTS:
        if effect in effects:
            return effect
    return None


def candidate_summary(
    assessment, output, *, verdicts: dict, accepted_revision: str | None, quality: dict | None
) -> dict:
    """Levels, path and hash of one candidate, for the run result."""
    return {
        "schematic": str(assessment.schematic.relative_to(output)),
        "revision": assessment.revision,
        "levels": status_levels(
            assessment.report,
            model_verdict=verdicts.get(assessment.revision),
            model_accepted=assessment.revision == accepted_revision,
            quality=quality,
        ),
    }


def iteration_outcomes(result: dict) -> list[dict]:
    """Every edit outcome recorded in a loop result, in order."""
    found = []
    for entry in result.get("iterations", []):
        if "edit_outcome" in entry:
            found.append(entry["edit_outcome"])
        found.extend(entry.get("edit_outcomes", []))
    return found


def corpus_status_fields(result: dict) -> dict:
    """The R1 fields a corpus summary keeps for one design."""
    levels = result.get("status_levels")
    counts: dict[str, int] = {}
    overlays: dict[str, int] = {}
    for outcome in iteration_outcomes(result):
        key = outcome["disposition"]
        if outcome["reason_class"]:
            key += ":" + outcome["reason_class"]
        counts[key] = counts.get(key, 0) + 1
        if outcome.get("quality_overlay"):
            name = outcome["quality_overlay"]
            overlays[name] = overlays.get(name, 0) + 1
    quality = result.get("quality_vs_initial")
    return {
        "status_levels": {name: level["status"] for name, level in levels.items()}
        if levels
        else None,
        "run_primary_effect": result.get("run_primary_effect"),
        "edit_dispositions": dict(sorted(counts.items())),
        "edit_overlays": dict(sorted(overlays.items())),
        "quality_delta": quality["deltas"] if quality else None,
        "quality_worse": sorted(quality["worse"]) if quality else None,
        "erc_ignored_checks": result.get("erc_ignored_checks"),
    }
