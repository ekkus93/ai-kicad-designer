"""Implementation details for m2 pack search."""

from __future__ import annotations

from .ir import InputError
from .m2_fragments import FragmentVariant
from .m2_pack import (
    CANDIDATE_BUDGET,
    ENVELOPE_OUTER_PADDING,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
)
from .m2_pack_beam import (
    _band_count,
    _branch_fanout_repack_candidates,
    _partial_beam_candidates,
    _retain_composition_seed_diversity,
)
from .m2_pack_core import (
    Packing,
    _best_centroid_balanced_packing,
    _signal_chains,
)
from .m2_pack_distribution import _distribution_column_candidate
from .m2_pack_frontier import (
    _interface_frontier_candidates,
    _local_signal_proximity_candidates,
)
from .m2_pack_layout import (
    _arrangements,
    _pack_shelves,
)
from .m2_pack_semantic import (
    _repeated_peer_alignment_candidates,
    _semantic_block_order_candidates,
    _structural_repack_candidates,
    _support_affinity_candidates,
)
from .m2_semantics import SemanticPlan


def pack_fragment_candidates(
    plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]
) -> tuple[Packing, ...]:
    """Build an at-most-eight deterministic beam of complete placement seeds."""
    attempts: list[str] = []
    keys = sorted(variants)
    if set(keys) != {block.id for block in plan.blocks}:
        raise InputError("PACK_VARIANT_BLOCK_MISMATCH")
    if any(not choices or len(choices) > 8 for choices in variants.values()):
        raise InputError("PACK_VARIANT_INVENTORY: each block requires one to eight variants")

    indivisible = sorted(
        (choice.id, choice.envelope)
        for choices in variants.values()
        for choice in choices
        if choice.envelope[2] - choice.envelope[0] > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
        or choice.envelope[3] - choice.envelope[1] > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
    )
    if indivisible and any(
        all(
            choice.envelope[2] - choice.envelope[0] > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            or choice.envelope[3] - choice.envelope[1] > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
            for choice in choices
        )
        for choices in variants.values()
    ):
        raise InputError(
            "PACK_SPREAD_INFEASIBLE: indivisible measured envelope exceeds "
            f"210x140 mm bounds={indivisible}"
        )

    by_block = {block.id: block for block in plan.blocks}

    def quality(item: FragmentVariant) -> tuple[int, int, int, str]:
        width = item.envelope[2] - item.envelope[0]
        height = item.envelope[3] - item.envelope[1]
        return width * height, max(width, height), width, item.id

    ordered_choices = {key: tuple(variants[key]) for key in keys}
    baseline = {key: ordered_choices[key][0] for key in keys}
    beam: list[dict[str, FragmentVariant]] = [baseline]
    kind_priority = {
        "package_power": 0,
        "interface": 1,
        "power_stage": 2,
        "timer": 3,
        "sallen_key": 4,
        "noninverting_amplifier": 4,
        "inverting_amplifier": 4,
        "buffer": 4,
    }
    branch_targets = {edge.target for edge in plan.edges if edge.kind == "branch"}
    substitutions = sorted(
        (
            rank,
            -1 if key in branch_targets else kind_priority.get(by_block[key].kind, 5),
            key,
            choice,
        )
        for key in keys
        for rank, choice in enumerate(ordered_choices[key][1:], start=1)
    )

    def access_delta(key: str, choice: FragmentVariant) -> tuple[tuple[str, str], ...]:
        original = {
            gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction
            for gateway in baseline[key].gateways
        }
        return tuple(
            sorted(
                (gateway.id.rsplit(".", 1)[-1], gateway.escape_direction)
                for gateway in choice.gateways
                if original.get(gateway.id.rsplit(".", 1)[-1]) != gateway.escape_direction
            )
        )

    proposals: list[tuple[tuple, dict[str, FragmentVariant]]] = []
    for rank, priority, key, choice in substitutions:
        base = baseline[key]
        base_width = base.envelope[2] - base.envelope[0]
        base_height = base.envelope[3] - base.envelope[1]
        if (
            base_width > MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            or base_height > MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
        ) and (
            choice.envelope[2] - choice.envelope[0] <= MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING
            and choice.envelope[3] - choice.envelope[1]
            <= MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING
        ):
            proposals.append(((-2, rank, key), {**baseline, key: choice}))

    # A finite, measured text-slot variant for each affected block kind is
    # explored before ordinary access substitutions. This keeps at least one
    # field-only alternative visible to the bounded complete-placement beam.
    for kind in sorted({by_block[key].kind for key in keys}):
        field_candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            alternate = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if ".local-text-slot." in choice.rule_id
                ),
                None,
            )
            if alternate is not None:
                field_candidate[key] = alternate
        if any(field_candidate[key] is not baseline[key] for key in keys):
            proposals.append(((-3, "field-slot", kind), field_candidate))

    # A reusable inward-facing rail-access candidate for independent shelves:
    # upper bands expose references downward and lower bands upward.  This is
    # derived solely from the signal DAG bands and port access alternatives.
    band_facing = dict(baseline)
    chain_index_by_block = {
        fragment_id: index
        for index, chain in enumerate(_signal_chains(plan))
        for fragment_id in chain
    }
    for edge in plan.edges:
        if edge.kind == "package" and edge.source in chain_index_by_block:
            chain_index_by_block.setdefault(edge.target, chain_index_by_block[edge.source])
    for key, band_index in sorted(chain_index_by_block.items()):
        desired = "down" if band_index % 2 == 0 else "up"
        replacement = next(
            (
                choice
                for choice in ordered_choices[key]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "reference"
                    and gateway.escape_direction == desired
                    for gateway in choice.gateways
                )
            ),
            None,
        )
        if replacement is not None:
            band_facing[key] = replacement
    if any(band_facing[key] is not baseline[key] for key in keys):
        proposals.append(((-1, "band-facing-reference"), band_facing))
    output_access = dict(baseline)
    for key in keys:
        baseline_output = next(
            (
                gateway.escape_direction
                for gateway in baseline[key].gateways
                if gateway.id.rsplit(".", 1)[-1] == "output"
            ),
            None,
        )
        alternate = next(
            (
                choice
                for choice in ordered_choices[key][1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "output"
                    and gateway.escape_direction != baseline_output
                    for gateway in choice.gateways
                )
            ),
            None,
        )
        if alternate is not None:
            output_access[key] = alternate
    if any(output_access[key] is not baseline[key] for key in keys):
        proposals.append(((-1, "access-output"), output_access))
    output_band = dict(band_facing)
    for key in keys:
        if by_block[key].kind == "package_power":
            output_band[key] = baseline[key]
    for key in keys:
        selected_directions = {
            gateway.id.rsplit(".", 1)[-1]: gateway.escape_direction
            for gateway in band_facing[key].gateways
        }
        alternate = next(
            (
                choice
                for choice in ordered_choices[key][1:]
                if any(
                    gateway.id.rsplit(".", 1)[-1] == "output"
                    and gateway.escape_direction
                    != next(
                        (
                            base_gateway.escape_direction
                            for base_gateway in baseline[key].gateways
                            if base_gateway.id.rsplit(".", 1)[-1] == "output"
                        ),
                        gateway.escape_direction,
                    )
                    for gateway in choice.gateways
                )
                and all(
                    selected_directions.get(gateway.id.rsplit(".", 1)[-1])
                    == gateway.escape_direction
                    for gateway in choice.gateways
                    if gateway.id.rsplit(".", 1)[-1] == "reference"
                )
            ),
            None,
        )
        if alternate is not None:
            output_band[key] = alternate
    if any(output_band[key] is not band_facing[key] for key in keys):
        proposals.append(((-1, "access-output-band"), output_band))
    for kind in sorted({block.kind for block in plan.blocks}):
        aspect_candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            alternate = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if ".above." in choice.rule_id or ".compact." in choice.rule_id
                ),
                None,
            )
            if alternate is not None:
                aspect_candidate[key] = alternate
        if any(aspect_candidate[key] is not baseline[key] for key in keys):
            proposals.append(((-1, f"aspect-{kind}"), aspect_candidate))
    compact_candidate = {
        key: next(
            (choice for choice in ordered_choices[key] if ".compact." in choice.rule_id),
            baseline[key],
        )
        for key in keys
    }
    if any(compact_candidate[key] is not baseline[key] for key in keys):
        proposals.append(((-2, "all-compact"), compact_candidate))

    rules = sorted(
        {
            (
                -1 if key in branch_targets else kind_priority.get(by_block[key].kind, 5),
                by_block[key].kind,
                access_delta(key, choice),
            )
            for _, _, key, choice in substitutions
            if access_delta(key, choice)
        }
    )
    rule_candidates = []
    port_priority = {
        "reference": 0,
        "output": 1,
        "positive": 1,
        "supply": 1,
        "input": 2,
        "negative": 2,
        "pin1": 2,
    }
    for priority, kind, delta in rules:
        candidate = dict(baseline)
        for key in keys:
            if by_block[key].kind != kind:
                continue
            match = next(
                (
                    choice
                    for choice in ordered_choices[key][1:]
                    if access_delta(key, choice) == delta
                ),
                None,
            )
            if match is not None:
                candidate[key] = match
        changed_port = delta[0][0] if delta else ""
        rule_candidates.append(
            (port_priority.get(changed_port, 3), priority, kind, delta, candidate)
        )
    # Preserve beam diversity instead of allowing the many access choices for
    # the first typed kind to consume every complete seed.
    by_kind_rules: dict[str, list[tuple]] = {}
    for item in sorted(rule_candidates, key=lambda value: value[:4]):
        by_kind_rules.setdefault(item[2], []).append(item)
    kind_order = sorted(
        by_kind_rules,
        key=lambda kind: min((item[1], item[0], kind) for item in by_kind_rules[kind]),
    )
    for round_index in range(max(map(len, by_kind_rules.values()), default=0)):
        for kind in kind_order:
            choices = by_kind_rules[kind]
            if round_index >= len(choices):
                continue
            port_rank, priority, _, delta, candidate = choices[round_index]
            proposals.append(((0, round_index, port_rank, priority, kind, delta), candidate))
    proposals.extend(
        ((1, rank, priority, key, choice.id), {**baseline, key: choice})
        for rank, priority, key, choice in substitutions
    )
    seen = {tuple((key, baseline[key].id) for key in keys)}
    for _, candidate in sorted(proposals, key=lambda item: (item[0][0], str(item[0][1:]))):
        identity = tuple((key, candidate[key].id) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        beam.append(candidate)
        if len(beam) == CANDIDATE_BUDGET:
            break

    successful: list[Packing] = []
    arranged = [(chosen, _arrangements(plan, chosen)) for chosen in beam]
    # Reserve beam slots for different variant assignments as well as shelf
    # arrangements. A repeated baseline shelf must not hide support orientation
    # or compactness choices behind the eight complete-candidate limit.
    preferred = [(0, 0), (0, 1)] + [(index, (index - 1) % 2) for index in range(1, len(arranged))]
    remaining = [
        (chosen_index, arrangement_index)
        for arrangement_index in range(4)
        for chosen_index in range(len(arranged))
        if (chosen_index, arrangement_index) not in preferred
    ]
    for chosen_index, arrangement_index in preferred + remaining:
        chosen, choices = arranged[chosen_index]
        arrangement_name, ordered = choices[arrangement_index]
        candidate_index = len(attempts) + 1
        try:
            placed, width, height = _pack_shelves(ordered, chosen)
        except ValueError as exc:
            attempts.append(f"candidate-{candidate_index}:{arrangement_name}:{exc}")
            continue
        attempts.append(
            f"candidate-{candidate_index}:{arrangement_name}:pass:measured={width}x{height}"
        )
        successful.append(
            Packing(
                tuple(sorted(placed, key=lambda item: item.fragment.id)),
                tuple(attempts),
            )
        )
        if len(successful) == CANDIDATE_BUDGET:
            break

    if successful:
        extras = []
        # Rigid, on-grid centering is considered without displacing a complete
        # original seed. Actual native-page acceptance remains independent.
        centered = _best_centroid_balanced_packing(successful)
        if centered is not None:
            extras.append(centered)
        # Reserve candidate space for deterministic, legally measured interface
        # moves; the subsequent route proof remains authoritative.
        # A frontier move may be illegal in the first shelf arrangement but
        # legal in another bounded packing. Keep one deterministic feasible
        # alternative per directed interface role across the eight seeds.
        frontier_labels: set[str] = set()
        for baseline in successful:
            for option in _interface_frontier_candidates(plan, baseline):
                label = option.attempts[-1]
                if label not in frontier_labels and len(frontier_labels) < 4:
                    frontier_labels.add(label)
                    extras.append(option)
            if len(frontier_labels) == 4:
                break
        extras.extend(_semantic_block_order_candidates(plan, successful[0]))
        extras.extend(_support_affinity_candidates(plan, successful[0]))
        extras.extend(_local_signal_proximity_candidates(plan, successful[0]))
        extras.extend(_branch_fanout_repack_candidates(plan, successful[0]))
        extras.extend(_repeated_peer_alignment_candidates(plan, successful[0]))
        distribution = _distribution_column_candidate(plan, variants, successful)
        if distribution is not None and all(
            tuple((item.fragment.id, item.delta) for item in distribution.fragments)
            != tuple((item.fragment.id, item.delta) for item in candidate.fragments)
            for candidate in successful
        ):
            extras.append(distribution)
        structural = tuple(
            candidate
            for baseline in successful
            for candidate in _structural_repack_candidates(plan, baseline)
        )
        for label in ("functional-row-compaction", "precedence-staggered-band"):
            candidate = next((item for item in structural if item.attempts[-1] == label), None)
            if candidate is not None:
                extras.append(candidate)
        # Shelf success alone does not prove structural coverage.  A shared
        # internally generated net with several physical islands can need an
        # interleaved partial placement to meet its whole-net length bound.
        distribution_demand = any(
            net.internally_generated and net.explicit_geometry_required and len(net.fragments) >= 4
            for net in plan.presentation_nets
        )
        noninterface_count = sum(
            item.fragment.block.kind != "interface" for item in successful[0].fragments
        )
        needs_band_alternative = (
            noninterface_count >= 2
            and len({_band_count(item) for item in (*successful[:4], *extras)}) == 1
        )
        if distribution_demand or needs_band_alternative:
            partial = _partial_beam_candidates(plan, variants)
            if partial:
                baseline_bands = _band_count(successful[0])
                diverse = next(
                    (item for item in partial if _band_count(item) != baseline_bands), partial[0]
                )
                extras.append(diverse)
        return _retain_composition_seed_diversity(tuple(successful), tuple(extras))

    partial = _partial_beam_candidates(plan, variants)
    if partial:
        return partial

    raise InputError(
        f"PACK_BUDGET_EXHAUSTED: candidates={len(attempts)}/{CANDIDATE_BUDGET} "
        f"spread_limit=210x140mm attempts={attempts}"
    )


def pack_fragments(plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]) -> Packing:
    """Return the first bounded seed with a feasible route demand when observable."""
    from . import m2_pack as facade

    candidates = facade.pack_fragment_candidates(plan, variants)
    # Lazy import avoids a module cycle while retaining the route-aware packing
    # contract for callers of this compatibility entry point.
    from .m2_route import route_between_fragments

    for candidate in candidates:
        try:
            route_between_fragments(plan, candidate.fragments)
        except InputError:
            continue
        return candidate
    return candidates[0]
