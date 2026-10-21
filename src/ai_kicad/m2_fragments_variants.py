"""Implementation details for m2 fragments variants."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .ir import InputError
from .m2_fragments_base import FragmentVariant
from .m2_fragments_builders import (
    _amplifier_fragment,
    _interface_fragment,
    _package_fragment,
    _passive_fragment,
    _power_stage_fragment,
    _reference_divider_fragment,
    _timer_fragment,
)
from .m2_fragments_geometry import _finish
from .m2b import (
    Draft,
)

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan
    from .m2a_core import Asset


def _access_alternatives(
    design: dict,
    resolved: dict[str, Asset],
    base: FragmentVariant,
    *,
    construction_trace: list[tuple[str, ...]] | None = None,
    uncovered: list[str] | None = None,
    family_index: int = 0,
) -> tuple[FragmentVariant, ...]:
    """Derive finite gateway alternatives from the same complete local motif."""
    suffixes = {gateway.id.rsplit(".", 1)[-1]: gateway for gateway in base.gateways}
    configurable = [
        name
        for name in (
            "input",
            "supply",
            "positive",
            "reference",
            "output",
            "negative",
            "pin1",
        )
        if name in suffixes
    ]
    if not configurable:
        return (base,)
    allowed_by_kind = {
        "power_stage": ("left", "right", "up", "down"),
        "timer": ("left", "right", "up", "down"),
        "buffer": ("right", "up", "down"),
        "unused_amplifier": ("right", "up", "down"),
        "noninverting_amplifier": ("right", "up", "down"),
        "inverting_amplifier": ("right", "up", "down"),
        "sallen_key": ("right", "up", "down"),
        "series": ("right", "up", "down"),
        "rc": ("right", "up", "down"),
        "led_branch": ("up", "right", "left"),
        "package_power": ("up", "right", "left"),
        "interface": ("left", "up", "down"),
    }
    variants = [base]
    gateway_points = {gateway.point for gateway in base.gateways}
    # Every alternative re-draws its port escapes and their labels, so the
    # base's port labels are stale: those at gateway points and those at the
    # far end of a label stub hung from a gateway point.
    stale_label_points = set(gateway_points)
    for first, second in base.wires[len(base.protected_wires) :]:
        if first in gateway_points:
            stale_label_points.add(second)
        if second in gateway_points:
            stale_label_points.add(first)
    alternatives = [
        (name, direction)
        for name in configurable
        for direction in allowed_by_kind.get(base.block.kind, (suffixes[name].escape_direction,))
        if direction != suffixes[name].escape_direction
        # A timer's right-facing output must leave the local motif outward.
        # A left escape folds back into its owned pin/terminal corridor.
        and not (base.block.kind == "timer" and name == "output" and direction == "left")
    ]
    if construction_trace is None:
        construction_trace = []
    if uncovered is None:
        uncovered = []
    for name, direction in alternatives:
        descriptor = f"family={family_index}:access={name}:{direction}"
        if len(construction_trace) >= 32:
            uncovered.append(descriptor)
            continue
        trace_index = len(construction_trace)
        construction_trace.append(("access", descriptor, "attempted", ""))
        draft = Draft(
            design,
            resolved,
            dict(base.positions),
            dict(base.angles),
            list(base.wires[: len(base.protected_wires)]),
            list(base.wire_nets[: len(base.protected_wires)]),
            [item for item in base.labels if item[1] not in stale_label_points],
            list(base.junctions),
            dict(base.text_positions),
        )
        anchors = {
            suffix: (
                gateway.anchor,
                direction if name == suffix else gateway.escape_direction,
            )
            for suffix, gateway in suffixes.items()
        }
        try:
            variant = _finish(
                design,
                resolved,
                base.block,
                draft,
                anchors,
                variant_suffix=f"v{len(variants)}",
            )
        except InputError as exc:
            construction_trace[trace_index] = ("access", descriptor, "rejected", str(exc))
            continue
        construction_trace[trace_index] = ("access", descriptor, "certified", "")
        variants.append(
            FragmentVariant(
                **{
                    **variant.__dict__,
                    "rule_id": f"m2g2.local-access.{base.block.kind}.{name}.{direction}.v1",
                }
            )
        )
    # Text placement is part of measured local geometry. Generate one
    # independently remeasured alternate per local motif; never shift fields
    # after packing or bypass the existing electrical/clearance proofs.
    passive_ids = {
        component["id"]
        for component in design["components"]
        if component["asset"] in {"Device:C", "Device:R"}
    }
    if passive_ids.intersection(occurrence[0] for occurrence in base.block.occurrences):
        descriptor = f"family={family_index}:text-slot:alternate"
        if len(construction_trace) >= 32:
            uncovered.append(descriptor)
        else:
            trace_index = len(construction_trace)
            construction_trace.append(("text_slot", descriptor, "attempted", ""))
            draft = Draft(
                design,
                resolved,
                dict(base.positions),
                dict(base.angles),
                list(base.wires[: len(base.protected_wires)]),
                list(base.wire_nets[: len(base.protected_wires)]),
                [item for item in base.labels if item[1] not in stale_label_points],
                list(base.junctions),
                dict(base.text_positions),
            )
            anchors = {
                suffix: (gateway.anchor, gateway.escape_direction)
                for suffix, gateway in suffixes.items()
            }
            try:
                alternate = _finish(
                    design,
                    resolved,
                    base.block,
                    draft,
                    anchors,
                    variant_suffix=f"{base.id.rsplit('.', 1)[-1]}_text_slot",
                    alternate_text_slots=True,
                )
            except InputError as exc:
                construction_trace[trace_index] = ("text_slot", descriptor, "rejected", str(exc))
            else:
                if alternate.text_positions != base.text_positions:
                    variants.append(
                        replace(
                            alternate,
                            rule_id=(f"m2g2.local-text-slot.{base.block.kind}.alternate.v1"),
                        )
                    )
                    construction_trace[trace_index] = ("text_slot", descriptor, "certified", "")
                else:
                    construction_trace[trace_index] = (
                        "text_slot",
                        descriptor,
                        "rejected",
                        "no distinct clear slot",
                    )
    distinct = {}
    for variant in variants:
        signature = tuple(
            (gateway.id.rsplit(".", 1)[-1], gateway.escape_direction)
            for gateway in variant.gateways
        )
        width = variant.envelope[2] - variant.envelope[0]
        height = variant.envelope[3] - variant.envelope[1]
        key = (signature, width, height, tuple(sorted(variant.text_positions.items())))
        distinct.setdefault(key, variant)
    available = [variant for variant in variants if variant in distinct.values()]
    retained = [base]
    base_directions = {
        gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction for gateway in base.gateways
    }
    for name in configurable:
        representative = next(
            (
                variant
                for variant in available[1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == name
                    and gateway.escape_direction != base_directions.get(name)
                    for gateway in variant.gateways
                )
            ),
            None,
        )
        if representative is not None and representative not in retained:
            retained.append(representative)
    for variant in available[1:]:
        if variant not in retained:
            retained.append(variant)
        if len(retained) == 8:
            break
    field_variant = next(
        (item for item in available[1:] if ".local-text-slot." in item.rule_id),
        None,
    )
    if field_variant is not None and field_variant not in retained:
        if len(retained) >= 8:
            retained[-1] = field_variant
        else:
            retained.append(field_variant)
    return tuple(retained[:8])


def fragment_variants(
    design: dict, resolved: dict[str, Asset], plan: SemanticPlan
) -> dict[str, tuple[FragmentVariant, ...]]:
    """Build finite local variants without inspecting unrelated blocks."""
    from . import m2_fragments as facade

    result = {}
    for block in plan.blocks:
        construction_trace = []
        construction_uncovered = []

        def construct(
            factory,
            *args,
            _block=block,
            _construction_trace=construction_trace,
            _construction_uncovered=construction_uncovered,
            **kwargs,
        ):
            factory = getattr(facade, factory.__name__, factory)
            descriptor = (
                factory.__name__
                + ":"
                + ",".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
            )
            if len(_construction_trace) >= 32:
                _construction_uncovered.append(descriptor)
                raise InputError("LOCAL_CONSTRUCTION_BUDGET_EXHAUSTED: limit=32")
            index = len(_construction_trace)
            _construction_trace.append(("body_support", descriptor, "attempted", ""))
            try:
                candidate = factory(*args, **kwargs)
            except InputError as exc:
                _construction_trace[index] = ("body_support", descriptor, "rejected", str(exc))
                exc.local_construction_evidence = {
                    "fragment": _block.id,
                    "proposal_limit": 32,
                    "proposals_attempted": len(_construction_trace),
                    "attempts": [list(item) for item in _construction_trace],
                    "budget_uncovered": list(_construction_uncovered),
                    "completed_fragments": {
                        block_id: family[0].construction_evidence()
                        for block_id, family in result.items()
                    },
                }
                raise
            _construction_trace[index] = ("body_support", descriptor, "certified", "")
            return candidate

        if block.kind in {
            "buffer",
            "unused_amplifier",
            "noninverting_amplifier",
            "inverting_amplifier",
            "sallen_key",
        }:
            bases = [construct(_amplifier_fragment, design, resolved, block)]
            try:
                bases.append(
                    construct(
                        _amplifier_fragment,
                        design,
                        resolved,
                        block,
                        feedback_side="above",
                    )
                )
            except InputError:
                pass
        elif block.kind == "package_power":
            bases = [construct(_package_fragment, design, resolved, block)]
            try:
                bases.append(
                    construct(
                        _package_fragment,
                        design,
                        resolved,
                        block,
                        reference_side="up",
                    )
                )
            except InputError:
                pass
            for side in ("up", "down"):
                try:
                    bases.append(
                        construct(
                            _package_fragment,
                            design,
                            resolved,
                            block,
                            reference_side=side,
                            compact=True,
                        )
                    )
                except InputError:
                    pass
            try:
                bases.append(
                    construct(
                        _package_fragment,
                        design,
                        resolved,
                        block,
                        reference_side="up",
                        compact=True,
                        balanced=True,
                    )
                )
            except InputError:
                pass
        elif block.kind == "reference_divider":
            bases = [construct(_reference_divider_fragment, design, resolved, block)]
            try:
                bases.append(
                    construct(_reference_divider_fragment, design, resolved, block, compact=True)
                )
            except InputError:
                pass
        elif block.kind == "power_stage":
            bases = [construct(_power_stage_fragment, design, resolved, block)]
        elif block.kind == "timer":
            bases = [construct(_timer_fragment, design, resolved, block)]
            try:
                bases.append(construct(_timer_fragment, design, resolved, block, compact=True))
            except InputError:
                pass
            try:
                bases.append(
                    construct(_timer_fragment, design, resolved, block, compact=True, narrow=True)
                )
            except InputError:
                pass
        elif block.kind in {"series", "rc", "led_branch"}:
            bases = [construct(_passive_fragment, design, resolved, block)]
            if block.kind in {"rc", "led_branch"}:
                try:
                    bases.append(
                        construct(_passive_fragment, design, resolved, block, compact=True)
                    )
                except InputError:
                    pass
        elif block.kind == "interface":
            bases = [construct(_interface_fragment, design, resolved, block)]
            try:
                bases.append(construct(_interface_fragment, design, resolved, block, mirrored=True))
            except InputError:
                pass
        else:
            raise InputError(f"FRAGMENT_KIND_UNSUPPORTED: {block.id}:{block.kind}")
        families = [
            _access_alternatives(
                design,
                resolved,
                base,
                construction_trace=construction_trace,
                uncovered=construction_uncovered,
                family_index=index,
            )
            for index, base in enumerate(bases)
        ]
        retained = []
        access_families = families[:2] if block.kind == "timer" and len(families) == 3 else families
        for rank in range(max(map(len, access_families))):
            for family_index, family in enumerate(access_families):
                if rank >= len(family):
                    continue
                candidate = family[rank]
                signature = (
                    tuple(sorted(candidate.positions.items())),
                    tuple(sorted(candidate.text_positions.items())),
                    candidate.wires,
                    tuple(
                        (gateway.id, gateway.escape_direction, gateway.point)
                        for gateway in candidate.gateways
                    ),
                    candidate.envelope,
                )
                if any(item[0] == signature for item in retained):
                    continue
                retained.append((signature, candidate, family_index))
                if len(retained) == 8:
                    break
            if len(retained) == 8:
                break

        field_candidate = next(
            (
                (family_index, candidate)
                for family_index, family in enumerate(families)
                for candidate in family
                if ".local-text-slot." in candidate.rule_id
            ),
            None,
        )
        if field_candidate is not None and not any(
            candidate is field_candidate[1] for _, candidate, _ in retained
        ):
            family_index, candidate = field_candidate
            entry = (None, candidate, family_index)
            if len(retained) >= 8:
                retained[-1] = entry
            else:
                retained.append(entry)

        if block.kind == "timer" and len(families) == 3:
            # Preserve both legacy families' diverse accesses within the same
            # eight-variant budget; substitute one expanded access for a new
            # independently measured narrow base, keeping compact access choices.
            narrow = families[2][0]
            retained[-2] = (None, narrow, 2)

        def structural_name(index: int, block=block, bases=bases) -> str:
            if block.kind in {"timer", "rc", "led_branch"}:
                return (
                    "narrow"
                    if block.kind == "timer" and index == 2
                    else "compact"
                    if index
                    else "expanded"
                )
            if block.kind == "package_power":
                return "compact" if ".compact_" in bases[index].id else "expanded"
            if block.kind == "interface":
                return "right_escape" if index else "left_escape"
            return "above" if index else "below"

        retained_candidates = [candidate for _, candidate, _ in retained]
        retention_uncovered = tuple(
            f"family={family_index}:access_variant={index}:envelope={candidate.envelope}"
            for family_index, family in enumerate(families)
            for index, candidate in enumerate(family)
            if candidate not in retained_candidates
        )
        result[block.id] = tuple(
            replace(
                candidate,
                id=f"{block.id}.v{index}",
                construction_trace=tuple(construction_trace),
                construction_uncovered=tuple(construction_uncovered),
                retention_uncovered=retention_uncovered,
                rule_id=(
                    f"m2g2.local-aspect.{block.kind}.{structural_name(family_index)}.v1"
                    if len(families) > 1 and ".local-text-slot." not in candidate.rule_id
                    else candidate.rule_id
                ),
            )
            for index, (_, candidate, family_index) in enumerate(retained)
        )
    return result
