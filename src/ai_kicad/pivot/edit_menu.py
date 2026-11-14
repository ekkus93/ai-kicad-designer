"""A menu of pre-checked feasible edits for the reviewer (reviewer loop spec R3).

The editor proposes candidate edits from geometry, screens the best-ranked ones with cheap
geometric checks, and validates the survivors natively: each is applied in a scratch copy
and run through KiCad ERC and netlist equivalence. Only entries that keep connectivity,
change the drawing, break no passing check and resolve something a failing check reports
are shown. A geometry-only candidate is never described as feasible.

The budget limits menu building inside one review round. It does not limit the number of
rounds; the per-design budgets do that.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import time
from typing import Callable

from ai_kicad.m2_text_layout import property_page_angle, text_extents
from ai_kicad.m2a_core import _nm
from ai_kicad.sexpr import children, one

from .field_layout import PAGE_CONTENT, TEXT_PADDING, _obstacles, _symbol
from .power_symbols import _overlaps
from .quality_measures import compare_quality
from .review_status import broken_connectivity
from .schematic_description import _instances

Box = tuple[int, int, int, int]
Target = tuple[str, int, str]
GRID = 1_270_000
# Gaps between a part's body (or anchor) and the near edge of its relocated text.
FIELD_GAPS = (GRID, 2 * GRID)
SIDE_WORDS = {"right": "right of", "left": "left of", "above": "above", "below": "below"}
# Slides along the body side, in grid steps, for each gap.
FIELD_SLIDES = (0, -1, 1, -2, 2)


def _named(witnesses: list[dict]) -> set[Target]:
    return {(item["reference"], int(item["unit"]), item["field"]) for item in witnesses}


def _collided(pairs: list) -> set[Target]:
    named = set()
    for pair in pairs:
        for item in pair:
            # Collision witnesses read "J1:1.Reference".
            owner, name = str(item).rsplit(".", 1)
            reference, unit = owner.rsplit(":", 1)
            named.add((reference, int(unit), name))
    return named


# Field checks and the (reference, unit, field) set each one reports in an assessment.
FIELD_CHECKS: dict[str, Callable[[dict], set[Target]]] = {
    "field_locality": lambda r: _named(r.get("field_locality", {}).get("witnesses", [])),
    "field_owner_association": lambda r: _named(
        r.get("field_owner_association", {}).get("witnesses", [])
    ),
    "field_nearest_owner": lambda r: _named(
        r.get("readability_witnesses", {}).get("field_nearest_owner", [])
    ),
    "field_wire_separation": lambda r: _named(
        r.get("readability_witnesses", {}).get("field_wire_separation", [])
    ),
    "field_separation": lambda r: _collided(r.get("field_collision_witnesses", [])),
}


def field_witnesses(report: dict) -> dict[str, set[Target]]:
    """Fields each failing field check reports."""
    checks = report.get("checks", {})
    return {name: read(report) for name, read in FIELD_CHECKS.items() if checks.get(name) == "FAIL"}


def canonical_action(action: dict) -> str:
    """A stable key for an action: sorted keys, coordinates rounded to 1 um."""

    def normal(value):
        if isinstance(value, float):
            return round(value, 3)
        if isinstance(value, dict):
            return {key: normal(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            return [normal(item) for item in value]
        return value

    return json.dumps(normal(action), sort_keys=True)


@dataclass
class Proposal:
    """A cheap geometric candidate edit, before native validation."""

    edit_class: str
    action: dict
    target: dict
    addresses: list[str]
    cost: float
    description: str
    # Checks the trial must pass for this entry to be shown (rail entries: clearance and
    # direction of power symbols).
    must_pass: list[str] = field(default_factory=list)

    @property
    def target_key(self) -> tuple:
        return tuple(self.target.values())


@dataclass
class MenuPolicy:
    per_class: int = 3
    total: int = 8
    optional_when_passing: int = 2
    geometric_proposals: int = 12
    native_validations: int = 8
    seconds: float = 20.0

    @classmethod
    def from_profile(cls, menu) -> MenuPolicy:
        return cls(**(menu.model_dump() if hasattr(menu, "model_dump") else dict(menu)))


@dataclass
class ValidationCache:
    """Native validations keyed by base revision, canonical action and context."""

    context: str = ""
    results: dict = field(default_factory=dict)
    hits: int = 0

    def key(self, base_revision: str, action: dict) -> tuple[str, str, str]:
        return base_revision, canonical_action(action), self.context


def resolved_items(base: dict, trial: dict, proposal: Proposal) -> list[str]:
    """Failing checks the trial passes, and the proposal's target no longer reported."""
    checks, trial_checks = base.get("checks", {}), trial.get("checks", {})
    items = [
        name
        for name, value in sorted(checks.items())
        if value != "PASS" and trial_checks.get(name) == "PASS"
    ]
    before, after = field_witnesses(base), field_witnesses(trial)
    key = proposal.target_key
    for name in proposal.addresses:
        if name in items:
            continue
        if len(key) == 3:
            if key in before.get(name, set()) and key not in after.get(name, set()):
                items.append(f"{name}: {key[0]} unit {key[1]} {key[2]}")
            continue
        old, new = unit_witnesses(base, name), unit_witnesses(trial, name)
        if len(new) < len(old):
            items.append(f"{name}: {len(old) - len(new)} fewer of {len(old)} reported")
    return items


def unit_witnesses(report: dict, check: str) -> list:
    """What a failing check reports, as a comparable list (field checks or readability)."""
    if check in FIELD_CHECKS:
        return sorted(FIELD_CHECKS[check](report))
    return list(report.get("readability_witnesses", {}).get(check, []))


def units_named_by_failing_checks(report: dict) -> dict[tuple[str, int], list[str]]:
    """Units each failing check names: field owners, nearest other parts, and readability
    witnesses that carry a reference and unit."""
    checks = report.get("checks", {})
    named: dict[tuple[str, int], set[str]] = {}
    for name, targets in field_witnesses(report).items():
        for reference, unit, _field in targets:
            named.setdefault((reference, unit), set()).add(name)
    if checks.get("field_owner_association") == "FAIL":
        for item in report.get("field_owner_association", {}).get("witnesses", []):
            if item.get("nearest_other_reference"):
                key = (item["nearest_other_reference"], int(item["nearest_other_unit"]))
                named.setdefault(key, set()).add("field_owner_association")
    for name, witnesses in report.get("readability_witnesses", {}).items():
        if checks.get(name) != "FAIL":
            continue
        for item in witnesses:
            if isinstance(item, dict) and "reference" in item and "unit" in item:
                named.setdefault((item["reference"], int(item["unit"])), set()).add(name)
    return {key: sorted(value) for key, value in sorted(named.items())}


RAIL_CHECKS = (
    "rail_presentation",
    "visible_rail_continuity",
    "power_symbol_clearance",
    "power_symbol_direction",
    "ground_symbol_direction",
    "rail_route_detour",
)
# A rail entry is shown only when the power symbols it leaves are clear and conventional.
RAIL_MUST_PASS = ["power_symbol_clearance", "power_symbol_direction", "ground_symbol_direction"]


def _nets_named(witnesses) -> set[str]:
    named = set()
    for item in witnesses or []:
        if isinstance(item, dict) and isinstance(item.get("net"), str):
            named.add(item["net"])
    return named


def rail_proposals(report: dict) -> list[Proposal]:
    """Power-symbol placement and reroutes of asserted rails.

    With a failing rail check, every rail it names (or every asserted rail, when its
    witnesses name none) is offered `use_power_symbols` (draw or re-place that rail's power
    symbols) and `connect_rail` with `replace_existing` (reroute it). With every check
    passing, the same edits are offered as optional improvements for rails whose drawn
    route detours or that have long perimeter wires; build_menu keeps them only when they
    measurably improve the drawing.
    """
    checks = report.get("checks", {})
    rails = sorted(
        {item["net"] for item in report.get("intended_circuit", {}).get("power_assertions", [])}
    )
    failing = [name for name in RAIL_CHECKS if checks.get(name) == "FAIL"]
    targets: dict[str, list[str]] = {}
    for name in failing:
        named = _nets_named(report.get("readability_witnesses", {}).get(name)) & set(rails)
        for net in named or rails:
            targets.setdefault(net, []).append(name)
    if not any(value == "FAIL" for value in checks.values()):
        quality = report.get("quality") or {}
        detoured = {
            item["net"] for item in quality.get("rail_detours", []) if item["excess_mm"] > 0
        }
        if quality.get("perimeter_paths"):
            detoured |= set(rails)
        for net in sorted(detoured & set(rails)):
            targets.setdefault(net, [])
    proposals = []
    for net, addresses in sorted(targets.items()):
        proposals.append(
            Proposal(
                edit_class="rail_symbol",
                action={"operation": "use_power_symbols", "net": net},
                target={"net": net},
                addresses=sorted(addresses),
                cost=1,
                description=f"draw rail {net} with a power symbol at each terminal group",
                must_pass=RAIL_MUST_PASS,
            )
        )
        proposals.append(
            Proposal(
                edit_class="rail_reroute",
                action={"operation": "connect_rail", "net": net, "replace_existing": True},
                target={"net": net},
                addresses=sorted(addresses),
                cost=2,
                description=f"reroute rail {net}, replacing its existing wiring",
                must_pass=RAIL_MUST_PASS,
            )
        )
    return proposals


def quality_gains(delta: dict | None, thresholds: dict | None = None) -> list[str]:
    """Measures an edit clearly improves (the mirror of compare_quality's worse rule)."""
    from .quality_measures import DEFAULT_QUALITY_THRESHOLDS

    if not delta or not delta["not_worse"]:
        return []
    thresholds = thresholds or DEFAULT_QUALITY_THRESHOLDS
    deltas, gains = delta["deltas"], []
    if (deltas.get("wire_length_mm") or 0) <= -thresholds["wire_length_min_mm"]:
        gains.append("wire_length_mm")
    if (deltas.get("rail_detour_mm") or 0) <= -thresholds["rail_detour_min_mm"]:
        gains.append("rail_detour_mm")
    if (deltas.get("perimeter_length_mm") or 0) < 0:
        gains.append("perimeter_paths")
    if (deltas.get("bends") or 0) <= -thresholds["bends_added"]:
        gains.append("bends")
    return gains


# Nudge offsets in grid steps: one and two steps along each axis.
NUDGES = [(dx, 0) for dx in (1, -1, 2, -2)] + [(0, dy) for dy in (1, -1, 2, -2)]


def symbol_nudge_proposals(tree: list, report: dict) -> list[Proposal]:
    """Grid nudges of each unit a failing check names, by canonical (reference, unit)."""
    instances = {(item["reference"], item["unit"]): item for item in _instances(tree)}
    proposals = []
    for (reference, unit), checks in units_named_by_failing_checks(report).items():
        instance = instances.get((reference, unit))
        if instance is None or reference.startswith("#"):
            continue
        for dx, dy in NUDGES:
            proposals.append(
                Proposal(
                    edit_class="symbol_nudge",
                    action={
                        "operation": "move_units",
                        "units": [{"reference": reference, "unit": unit}],
                        "dx_mm": round(dx * GRID / 1e6, 2),
                        "dy_mm": round(dy * GRID / 1e6, 2),
                    },
                    target={"reference": reference, "unit": unit},
                    addresses=checks,
                    cost=abs(dx) + abs(dy),
                    description=(
                        f"nudge {instance['name']} (unit {unit}) by "
                        f"({dx * GRID / 1e6:+.2f}, {dy * GRID / 1e6:+.2f}) mm with its wiring"
                    ),
                )
            )
    return proposals


def _text_box(centre: tuple[int, int], text: str, page_angle: int) -> Box:
    width, height = text_extents(text, page_angle)
    half_width, half_height = width // 2 + TEXT_PADDING, height // 2 + TEXT_PADDING
    return (
        centre[0] - half_width,
        centre[1] - half_height,
        centre[0] + half_width,
        centre[1] + half_height,
    )


def field_relocation_proposals(text: str, tree: list, report: dict) -> list[Proposal]:
    """Clear grid spots beside the owning body or anchor for each field a check reports."""
    instances = {(item["reference"], item["unit"]): item for item in _instances(tree)}
    targets: dict[Target, list[str]] = {}
    for name, named in field_witnesses(report).items():
        for target in named:
            targets.setdefault(target, []).append(name)
    proposals = []
    for (reference, unit, name), checks in sorted(targets.items()):
        instance = instances.get((reference, unit))
        if instance is None:
            continue
        props = {prop[1]: prop for prop in children(_symbol(tree, (reference, unit)), "property")}
        prop = props.get(name)
        if prop is None:
            continue
        at = one(prop, "at")
        current = (_nm(at[1]), _nm(at[2]))
        angle = int(float(at[3]))
        page_angle = property_page_angle(instance["angle"], angle)
        label = instance["name"] if name == "Reference" else prop[2]
        obstacles = _obstacles(text, tree, (reference, unit))
        sibling = props.get("Value" if name == "Reference" else "Reference")
        if sibling is not None and not children(sibling, "hide"):
            sibling_at = one(sibling, "at")
            obstacles.append(
                _text_box(
                    (_nm(sibling_at[1]), _nm(sibling_at[2])),
                    instance["name"] if name == "Value" else sibling[2],
                    property_page_angle(instance["angle"], int(float(sibling_at[3]))),
                )
            )
        width, height = text_extents(label, page_angle)
        half_width, half_height = width // 2, height // 2
        origin = instance["origin"]
        frames = [("body", instance["body"])]
        if instance["origin"] != (
            (instance["body"][0] + instance["body"][2]) // 2,
            (instance["body"][1] + instance["body"][3]) // 2,
        ):
            # Association is measured from the symbol anchor; try spots around it too.
            frames.append(("anchor", (*origin, *origin)))
        seen = set()
        for frame, (left, top, right, bottom) in frames:
            middle = ((left + right) // 2, (top + bottom) // 2)
            for gap in FIELD_GAPS:
                sides = {
                    "right": (right + gap + half_width, middle[1], (0, 1)),
                    "left": (left - gap - half_width, middle[1], (0, 1)),
                    "above": (middle[0], top - gap - half_height, (1, 0)),
                    "below": (middle[0], bottom + gap + half_height, (1, 0)),
                }
                for side, (x, y, (sx, sy)) in sides.items():
                    for slide in FIELD_SLIDES:
                        centre = (
                            round((x + sx * slide * GRID) / GRID) * GRID,
                            round((y + sy * slide * GRID) / GRID) * GRID,
                        )
                        if centre in seen or centre == current:
                            continue
                        seen.add(centre)
                        box = _text_box(centre, label, page_angle)
                        inside = (
                            PAGE_CONTENT[0] <= box[0]
                            and PAGE_CONTENT[1] <= box[1]
                            and box[2] <= PAGE_CONTENT[2]
                            and box[3] <= PAGE_CONTENT[3]
                        )
                        if not inside or any(_overlaps(box, other) for other in obstacles):
                            continue
                        distance = abs(centre[0] - origin[0]) + abs(centre[1] - origin[1])
                        proposals.append(
                            Proposal(
                                edit_class="field_relocation",
                                action={
                                    "operation": "move_field",
                                    "reference": reference,
                                    "unit": unit,
                                    "field": name,
                                    "x_mm": centre[0] / 1e6,
                                    "y_mm": centre[1] / 1e6,
                                    "angle": angle,
                                },
                                target={"reference": reference, "unit": unit, "field": name},
                                addresses=sorted(checks),
                                cost=distance / 1e6,
                                description=(
                                    f"move {instance['name']} {name} '{label}' "
                                    f"{SIDE_WORDS[side]} its {frame} to "
                                    f"({centre[0] / 1e6:.2f}, {centre[1] / 1e6:.2f})"
                                ),
                            )
                        )
    return proposals


def _interleave(proposals: list[Proposal]) -> list[Proposal]:
    """Cheapest first within each target, alternating between targets."""
    by_target: dict[tuple, list[Proposal]] = {}
    for proposal in proposals:
        by_target.setdefault(proposal.target_key, []).append(proposal)
    queues = [sorted(items, key=lambda p: p.cost) for _key, items in sorted(by_target.items())]
    ordered = []
    while any(queues):
        for queue in queues:
            if queue:
                ordered.append(queue.pop(0))
    return ordered


def build_menu(
    base,
    proposals: list[Proposal],
    validate: Callable[[dict], object],
    policy: MenuPolicy,
    cache: ValidationCache,
    *,
    precheck: Callable[[Proposal], bool] | None = None,
    quality_thresholds: dict | None = None,
    clock: Callable[[], float] = time.monotonic,
    kicad_commands_per_validation: int = 1,
) -> dict:
    """Rank, screen and natively validate proposals; return the menu and its record.

    `precheck(proposal)` is a cheap geometric screen; at most `geometric_proposals`
    proposals are screened. `validate(action)` applies the action in scratch and returns
    its assessment, or raises ValueError when the editor refuses it.
    """
    started = clock()
    unique: dict[str, Proposal] = {}
    for proposal in sorted(proposals, key=lambda p: (p.cost, canonical_action(p.action))):
        unique.setdefault(canonical_action(proposal.action), proposal)
    considered, screened_out, passed = 0, 0, []
    checks = base.report.get("checks", {})
    all_passing = bool(checks) and all(value == "PASS" for value in checks.values())
    # Fixes for failing checks come first; optional improvements only when all pass.
    addressing = [p for p in unique.values() if p.addresses]
    optional = [p for p in unique.values() if not p.addresses] if all_passing else []
    for proposal in _interleave(addressing) + _interleave(optional):
        if considered >= policy.geometric_proposals:
            break
        considered += 1
        if precheck is None or precheck(proposal):
            passed.append(proposal)
        else:
            screened_out += 1
    entries, per_class, rejected = [], {}, []
    optional_shown = 0
    validations, exhausted = 0, None
    covered: set[tuple] = set()
    # Validate one proposal per target before a second for any target.
    passed.sort(key=lambda p: p.target_key in covered)
    for proposal in passed:
        if len(entries) >= policy.total:
            break
        if per_class.get(proposal.edit_class, 0) >= policy.per_class:
            continue
        if not proposal.addresses and optional_shown >= policy.optional_when_passing:
            continue
        key = cache.key(base.revision, proposal.action)
        if key in cache.results:
            cache.hits += 1
            outcome = cache.results[key]
        else:
            if validations >= policy.native_validations:
                exhausted = "native validation limit reached"
                break
            if clock() - started >= policy.seconds:
                exhausted = "menu time budget reached"
                break
            validations += 1
            try:
                trial = validate(proposal.action)
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
                fixes = resolved_items(base.report, trial.report, proposal)
                base_quality, trial_quality = (
                    base.report.get("quality"),
                    trial.report.get("quality"),
                )
                delta = (
                    compare_quality(base_quality, trial_quality, quality_thresholds)
                    if isinstance(base_quality, dict)
                    and isinstance(trial_quality, dict)
                    and "error" not in base_quality
                    and "error" not in trial_quality
                    else None
                )
                gains = quality_gains(delta, quality_thresholds)
                left_failing = sorted(
                    name
                    for name in proposal.must_pass
                    if name in trial_checks and trial_checks[name] != "PASS"
                )
                if trial.revision == base.revision:
                    outcome = {"ok": False, "reason": "no change"}
                elif broken:
                    outcome = {"ok": False, "reason": f"breaks {', '.join(broken)}"}
                elif newly_failing:
                    outcome = {"ok": False, "reason": f"makes {', '.join(newly_failing)} fail"}
                elif left_failing:
                    outcome = {"ok": False, "reason": f"leaves {', '.join(left_failing)} failing"}
                elif proposal.addresses and not fixes:
                    outcome = {"ok": False, "reason": "resolves nothing a failing check reports"}
                elif not proposal.addresses and not gains:
                    outcome = {
                        "ok": False,
                        "reason": "optional edit shows no measured quality gain",
                    }
                else:
                    outcome = {
                        "ok": True,
                        "fixes": fixes,
                        "gains": gains,
                        "revision": trial.revision,
                        "predicted_delta": delta,
                    }
            cache.results[key] = outcome
        if not outcome["ok"]:
            rejected.append({"action": proposal.action, "reason": outcome["reason"]})
            continue
        covered.add(proposal.target_key)
        per_class[proposal.edit_class] = per_class.get(proposal.edit_class, 0) + 1
        optional_shown += not proposal.addresses
        entries.append(
            {
                "id": f"{proposal.edit_class}-{len(entries) + 1}",
                "class": proposal.edit_class,
                "target": proposal.target,
                "description": proposal.description,
                "optional": not proposal.addresses,
                "fixes": outcome["fixes"],
                "gains": outcome.get("gains", []),
                "predicted_delta": outcome["predicted_delta"],
                "action": proposal.action,
                "scratch_revision": outcome["revision"],
            }
        )
    return {
        "entries": entries,
        "record": {
            "proposals_generated": len(unique),
            "proposals_considered": considered,
            "screened_out": screened_out,
            "native_validations": validations,
            "kicad_invocations": validations * kicad_commands_per_validation,
            "cache_hits": cache.hits,
            "seconds": round(clock() - started, 3),
            "budget_exhausted": exhausted,
            "rejected": rejected,
            "policy": asdict(policy),
        },
    }


def menu_for_reviewer(menu: dict) -> list[dict]:
    """What the reviewer sees: ID, target, what it fixes and the predicted R2 delta."""
    shown = []
    for entry in menu["entries"]:
        delta = entry["predicted_delta"]
        shown.append(
            {
                "id": entry["id"],
                "class": entry["class"],
                "target": entry["target"],
                "description": entry["description"],
                "optional": entry.get("optional", False),
                "fixes": entry["fixes"],
                "quality_gains": entry.get("gains", []),
                "predicted_quality_delta": delta["deltas"] if delta else None,
                "predicted_quality_worse": sorted(delta["worse"]) if delta else None,
            }
        )
    return shown
