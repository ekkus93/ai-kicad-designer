"""Implementation details for m2 pack beam."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_fragments_base import FragmentVariant
from .m2_fragments_types import Point
from .m2_pack_constants import (
    BOTTOM,
    CANDIDATE_BUDGET,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    RIGHT,
    TOP,
)
from .m2_pack_core import Packing, PlacedFragment, _place
from .m2_pack_distribution import _measured_repack
from .m2a_constants import PITCH
from .m2_transform import transform_library_point

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def _band_count(packing: Packing) -> int:
    tops = sorted(
        {item.envelope[1] for item in packing.fragments if item.fragment.block.kind != "interface"}
    )
    bands = []
    for top in tops:
        if not bands or top - bands[-1] > PITCH:
            bands.append(top)
    return len(bands)


def _partial_beam_candidates(
    plan: SemanticPlan,
    variants: dict[str, tuple[FragmentVariant, ...]],
) -> tuple[Packing, ...]:
    """Grow measured fragments through four bounded placement classes.

    This fallback keeps independent tall cores separable, so a successor and
    package cell may backfill beside either core instead of inheriting a rigid
    full-chain shelf rectangle.  Every retained partial state satisfies all
    obligations whose terminals have already been placed.
    """
    blocks = {block.id: block for block in plan.blocks}
    predecessors: dict[str, set[str]] = {key: set() for key in variants}
    for obligation in plan.precedence:
        # External interfaces use the reserved boundary column after core
        # placement. Their exact inequalities are checked when both endpoints
        # are assigned; they do not force a different core expansion schedule.
        if (
            obligation.source_fragment != obligation.target_fragment
            and blocks[obligation.source_fragment].kind != "interface"
        ):
            predecessors[obligation.target_fragment].add(obligation.source_fragment)
    priority = {
        "timer": 0,
        "power_stage": 0,
        "rc": 1,
        "series": 1,
        "led_branch": 1,
        "buffer": 2,
        "noninverting_amplifier": 2,
        "inverting_amplifier": 2,
        "sallen_key": 2,
        "package_power": 3,
        "reference_divider": 3,
        "unused_amplifier": 4,
        "interface": 5,
    }
    pending = set(variants)
    order = []
    while pending:
        ready = [key for key in pending if predecessors[key] <= set(order)]
        if not ready:
            return ()
        key = min(
            ready,
            key=lambda candidate: (
                priority.get(blocks[candidate].kind, 4),
                -max(
                    (choice.envelope[2] - choice.envelope[0])
                    * (choice.envelope[3] - choice.envelope[1])
                    for choice in variants[candidate]
                ),
                candidate,
            ),
        )
        order.append(key)
        pending.remove(key)

    terminal = {item.terminal: item for item in plan.terminals}

    def point(state: dict[str, PlacedFragment], key: tuple[str, str]) -> Point:
        item = terminal[key]
        placed = state[item.owner]
        origin = placed.fragment.positions[item.occurrence]
        angle = placed.fragment.angles.get(item.occurrence, 0)
        dx, dy = transform_library_point(
            item.pin_x,
            item.pin_y,
            angle,
            placed.fragment.mirrors.get(item.occurrence),
        )
        return origin[0] + placed.delta[0] + dx, origin[1] + placed.delta[1] + dy

    def partial_legal(state: dict[str, PlacedFragment]) -> bool:
        for obligation in plan.precedence:
            if {obligation.source_fragment, obligation.target_fragment} <= state.keys():
                first = point(state, obligation.source_terminal)
                second = point(state, obligation.target_terminal)
                if second[0] - first[0] < obligation.minimum_x_separation:
                    return False
        for obligation in plan.local_spans:
            owners = {terminal[obligation.first].owner, terminal[obligation.second].owner}
            if owners <= state.keys():
                first, second = point(state, obligation.first), point(state, obligation.second)
                span = abs(first[0] - second[0]) + (
                    abs(first[1] - second[1]) if obligation.metric == "manhattan" else 0
                )
                if span > obligation.maximum:
                    return False
        return True

    def fits(state: dict[str, PlacedFragment], item: PlacedFragment) -> bool:
        if (
            item.envelope[0] < LEFT
            or item.envelope[1] < TOP
            or item.envelope[2] > RIGHT
            or item.envelope[3] > BOTTOM
        ):
            return False
        if any(
            max(item.envelope[0], other.envelope[0]) < min(item.envelope[2], other.envelope[2])
            and max(item.envelope[1], other.envelope[1]) < min(item.envelope[3], other.envelope[3])
            for other in state.values()
        ):
            return False
        all_items = (*state.values(), item)
        if (
            max(value.content_envelope[2] for value in all_items)
            - min(value.content_envelope[0] for value in all_items)
            > MAX_CONTENT_WIDTH
            or max(value.content_envelope[3] for value in all_items)
            - min(value.content_envelope[1] for value in all_items)
            > MAX_CONTENT_HEIGHT
        ):
            return False
        return partial_legal({**state, item.fragment.block.id: item})

    def access_penalty(state: dict[str, PlacedFragment]) -> int:
        penalty = 0
        for obligation in plan.precedence:
            if not {obligation.source_fragment, obligation.target_fragment} <= state.keys():
                continue
            source = state[obligation.source_fragment]
            target = state[obligation.target_fragment]
            source_roles = {port.port.id: port.port.role for port in source.ports}
            target_roles = {port.port.id: port.port.role for port in target.ports}
            source_gateways = [
                gateway
                for gateway in source.gateways
                if gateway.net == obligation.net
                and source_roles[gateway.id] in {"signal_out", "power_out"}
            ]
            target_gateways = [
                gateway
                for gateway in target.gateways
                if gateway.net == obligation.net
                and target_roles[gateway.id] in {"signal_in", "power_in"}
            ]
            if not source_gateways or not target_gateways:
                continue
            first, second = source_gateways[0], target_gateways[0]
            if first.point[0] < second.point[0]:
                penalty += first.escape_direction == "left"
                penalty += second.escape_direction == "right"
            elif first.point[0] > second.point[0]:
                penalty += first.escape_direction == "right"
                penalty += second.escape_direction == "left"
        return penalty

    interface_width = max(
        (
            min(choice.envelope[2] - choice.envelope[0] for choice in variants[key])
            for key in variants
            if blocks[key].kind == "interface"
        ),
        default=0,
    )
    core_left = LEFT + interface_width + 2 * PITCH
    beam: list[tuple[dict[str, PlacedFragment], tuple[str, ...]]] = [({}, ())]
    for key in order:
        extensions = []
        choices = sorted(
            variants[key],
            key=lambda choice: (
                choice.envelope[3] - choice.envelope[1],
                (choice.envelope[2] - choice.envelope[0])
                * (choice.envelope[3] - choice.envelope[1]),
                choice.id,
            ),
        )[:8]
        for state, decisions in beam:
            related = [
                item
                for item in state.values()
                if {occurrence[0] for occurrence in item.fragment.block.occurrences}
                & {occurrence[0] for occurrence in blocks[key].occurrences}
            ]
            parents = [state[parent] for parent in sorted(predecessors[key]) if parent in state]
            for choice in choices:
                width = choice.envelope[2] - choice.envelope[0]
                height = choice.envelope[3] - choice.envelope[1]
                proposals: list[tuple[str, list[Point]]] = []
                proposals.append(
                    (
                        "aligned",
                        [(parent.envelope[2] + PITCH, parent.envelope[1]) for parent in parents],
                    )
                )
                noninterfaces = [
                    item for item in state.values() if item.fragment.block.kind != "interface"
                ]
                proposals.append(
                    (
                        "lower_band",
                        [
                            (
                                core_left if blocks[key].kind != "interface" else LEFT + PITCH,
                                max((item.envelope[3] for item in noninterfaces), default=TOP)
                                + PITCH,
                            ),
                            (core_left, TOP + 2 * PITCH),
                        ],
                    )
                )
                proposals.append(
                    (
                        "affinity",
                        [(item.envelope[0], item.envelope[3] + PITCH) for item in related]
                        + [
                            (item.envelope[0], item.envelope[1] - height - PITCH)
                            for item in related
                        ],
                    )
                )
                xs = {core_left, LEFT + PITCH} | {
                    coordinate
                    for item in state.values()
                    for coordinate in (item.envelope[0], item.envelope[2] + PITCH)
                }
                ys = {TOP + 2 * PITCH} | {
                    coordinate
                    for item in state.values()
                    for coordinate in (item.envelope[1], item.envelope[3] + PITCH)
                }
                proposals.append(
                    (
                        "backfill",
                        sorted(
                            ((x, y) for x in xs for y in ys),
                            key=lambda value: (
                                max(value[0] + width, value[1] + height),
                                value[1],
                                value[0],
                            ),
                        ),
                    )
                )
                for class_name, origins in proposals:
                    for left, top in origins:
                        item = _place(choice, left, top)
                        if fits(state, item):
                            extended = {**state, key: item}
                            new_decisions = (*decisions, f"{key}:{class_name}:{choice.id}")
                            box = (
                                max(part.content_envelope[2] for part in extended.values())
                                - min(part.content_envelope[0] for part in extended.values()),
                                max(part.content_envelope[3] for part in extended.values())
                                - min(part.content_envelope[1] for part in extended.values()),
                            )
                            score = (
                                access_penalty(extended),
                                max(box[0] / MAX_CONTENT_WIDTH, box[1] / MAX_CONTENT_HEIGHT),
                                box[0] * box[1],
                                box[0],
                                tuple(new_decisions),
                            )
                            extensions.append((score, extended, new_decisions))
                            break
        if not extensions:
            return ()
        deduplicated = {}
        for score, state, decisions in sorted(extensions, key=lambda item: item[0]):
            signature = tuple(
                (block_id, placed.fragment.id, placed.delta)
                for block_id, placed in sorted(state.items())
            )
            deduplicated.setdefault(signature, (score, state, decisions))
        ranked = list(deduplicated.values())
        diverse = []
        covered_structures = set()
        for candidate in ranked:
            _, state, _ = candidate
            cells = tuple(
                (key, item)
                for key, item in sorted(state.items())
                if item.fragment.block.kind != "interface"
            )
            structure = tuple(
                (
                    first_key,
                    second_key,
                    "same_band"
                    if max(first.envelope[1], second.envelope[1])
                    < min(first.envelope[3], second.envelope[3])
                    else (
                        "first_above" if first.envelope[3] <= second.envelope[1] else "second_above"
                    ),
                    "first_left"
                    if first.envelope[2] <= second.envelope[0]
                    else (
                        "second_left" if second.envelope[2] <= first.envelope[0] else "x_overlap"
                    ),
                )
                for index, (first_key, first) in enumerate(cells)
                for second_key, second in cells[index + 1 :]
            )
            if structure in covered_structures:
                continue
            covered_structures.add(structure)
            diverse.append(candidate)
            if len(diverse) == CANDIDATE_BUDGET:
                break
        if len(diverse) < CANDIDATE_BUDGET:
            diverse_ids = {id(item) for item in diverse}
            diverse.extend(item for item in ranked if id(item) not in diverse_ids)
        beam = [(state, decisions) for _, state, decisions in diverse[:CANDIDATE_BUDGET]]
    complete = []
    for state, decisions in beam:
        items = tuple(sorted(state.values(), key=lambda item: item.fragment.block.id))
        width = max(item.content_envelope[2] for item in items) - min(
            item.content_envelope[0] for item in items
        )
        height = max(item.content_envelope[3] for item in items) - min(
            item.content_envelope[1] for item in items
        )
        complete.append(
            Packing(
                items,
                ("partial-beam", *decisions, f"partial-beam:pass:measured={width}x{height}"),
            )
        )
    return tuple(complete)


def _branch_fanout_repack_candidates(plan: SemanticPlan, baseline: Packing) -> tuple[Packing, ...]:
    """Search two bounded, proved alternatives for a directed signal fanout.

    One alternative centers the source between its consumers; the other
    equalizes the sibling target depths. Every proposed move passes the same
    measured envelope, spread, collision, and exact-terminal hard constraints
    as other composition repairs. No route is assumed to be legal here.
    """
    by_id = {item.fragment.block.id: item for item in baseline.fragments}
    fanouts: dict[tuple[str, str], set[str]] = {}
    for edge in plan.edges:
        if edge.kind not in {"signal", "branch"} or edge.source == edge.target:
            continue
        if edge.source in by_id and edge.target in by_id:
            fanouts.setdefault((edge.source, edge.net), set()).add(edge.target)

    candidates: dict[str, list[tuple[tuple[int, int, str, str], Packing]]] = {
        "branch-fanout-origin-centered": [],
        "branch-fanout-sibling-depth": [],
    }
    trials = 0
    limit = CANDIDATE_BUDGET * 4
    for (source_id, _net), target_ids in sorted(fanouts.items()):
        if trials >= limit:
            break
        source = by_id[source_id]
        if source.fragment.block.kind == "interface":
            continue
        targets = tuple(
            by_id[target_id]
            for target_id in sorted(target_ids)
            if by_id[target_id].fragment.block.kind != "interface"
        )
        if len(targets) < 2:
            continue

        def center(item: PlacedFragment) -> Point:
            return (
                (item.envelope[0] + item.envelope[2]) // 2,
                (item.envelope[1] + item.envelope[3]) // 2,
            )

        target_rows = [center(target)[1] for target in targets]
        midpoint = (min(target_rows) + max(target_rows)) // 2
        source_y = center(source)[1]
        if source_y != midpoint:
            height = source.envelope[3] - source.envelope[1]
            new_top = ((midpoint - height // 2) // PITCH) * PITCH
            trials += 1
            proposal = _measured_repack(
                plan,
                baseline,
                source,
                source.envelope[0],
                new_top,
                "branch-fanout-origin-centered",
            )
            if proposal is not None:
                moved = next(
                    item for item in proposal.fragments if item.fragment.block.id == source_id
                )
                improvement = abs(source_y - midpoint) - abs(center(moved)[1] - midpoint)
                if improvement > 0:
                    candidates["branch-fanout-origin-centered"].append(
                        ((-improvement, abs(new_top - source.envelope[1]), source_id, ""), proposal)
                    )

        sibling_xs = sorted(center(target)[0] for target in targets)
        median_x = sibling_xs[(len(sibling_xs) - 1) // 2]
        for target in targets:
            if trials >= limit:
                break
            old_x = center(target)[0]
            if old_x == median_x:
                continue
            width = target.envelope[2] - target.envelope[0]
            new_left = ((median_x - width // 2) // PITCH) * PITCH
            trials += 1
            proposal = _measured_repack(
                plan,
                baseline,
                target,
                new_left,
                target.envelope[1],
                "branch-fanout-sibling-depth",
            )
            if proposal is None:
                continue
            moved = next(
                item
                for item in proposal.fragments
                if item.fragment.block.id == target.fragment.block.id
            )
            improvement = abs(old_x - median_x) - abs(center(moved)[0] - median_x)
            if improvement > 0:
                candidates["branch-fanout-sibling-depth"].append(
                    (
                        (
                            -improvement,
                            abs(new_left - target.envelope[0]),
                            source_id,
                            target.fragment.block.id,
                        ),
                        proposal,
                    )
                )
    return tuple(
        min(options, key=lambda item: item[0])[1]
        for label in (
            "branch-fanout-origin-centered",
            "branch-fanout-sibling-depth",
        )
        if (options := candidates[label])
    )


def _retain_composition_seed_diversity(
    successful: tuple[Packing, ...], extras: tuple[Packing, ...]
) -> tuple[Packing, ...]:
    """Retain bounded variant diversity and both legal repeated-peer grammars.

    Later generic search alternatives must not silently crowd out row or
    column candidates before the route-aware selector gets to evaluate them.
    """
    if not successful:
        return ()
    repeated = tuple(
        next(
            (candidate for candidate in extras if candidate.attempts[-1] == label),
            None,
        )
        for label in ("repeated-peer-row", "repeated-peer-column")
    )
    # Field-slot variants are independently constructed measured alternatives,
    # not mere shelf shifts. Preserve one legal distinct choice when the
    # eight-seed cap would otherwise discard it after repeated-peer repairs.
    frontier = tuple(
        next((item for item in extras if item.attempts[-1] == label), None)
        for label in (
            "interface-frontier-combined",
            "interface-frontier-output",
            "interface-frontier-output-staggered",
            "interface-frontier-input",
        )
    )
    fanout_output = next(
        (item for item in extras if item.attempts[-1] == "fanout-output-corridor"),
        None,
    )
    partial_frontier = next(
        (
            item
            for item in extras
            if item.attempts[0] == "partial-beam"
            and item.attempts[-1]
            in {
                "interface-frontier-combined",
                "interface-frontier-output",
                "interface-frontier-output-staggered",
                "interface-frontier-input",
            }
        ),
        None,
    )
    branch = tuple(
        next(
            (candidate for candidate in extras if candidate.attempts[-1] == label),
            None,
        )
        for label in ("branch-fanout-origin-centered", "branch-fanout-sibling-depth")
    )
    # Measured structural classes are contracted alternatives in their own
    # right; the growing set of interface and fanout variants must not push
    # them past the eight-seed cap.
    structural = tuple(
        next(
            (candidate for candidate in extras if candidate.attempts[-1] == label),
            None,
        )
        for label in ("functional-row-compaction", "precedence-staggered-band")
    )
    field_slot = next(
        (
            candidate
            for candidate in successful
            if any(".local-text-slot." in placed.fragment.rule_id for placed in candidate.fragments)
        ),
        None,
    )
    local_signal = next(
        (
            candidate
            for candidate in extras
            if candidate.attempts[-1] == "local-signal-direct-proximity"
        ),
        None,
    )
    centered = next(
        (candidate for candidate in extras if candidate.attempts[-1] == "centroid-balanced-page"),
        None,
    )
    # Distribution and partial-beam seeds are independent measured geometry
    # classes. Keep one of each when available: new aesthetic variants must not
    # displace the only candidate able to satisfy a global conductor bound.
    distribution = next(
        (
            candidate
            for candidate in extras
            if candidate.attempts[-1].startswith("distribution-column:")
        ),
        None,
    )
    observed_output = next(
        (candidate for candidate in extras if candidate.attempts[-1] == "observed-output-corridor"),
        None,
    )
    partial = next(
        (candidate for candidate in extras if candidate.attempts[0] == "partial-beam"),
        None,
    )
    protected = tuple(
        candidate
        for candidate in (
            distribution,
            partial,
            partial_frontier,
            *repeated,
            *frontier,
            fanout_output,
            observed_output,
            *branch,
            *structural,
            # Keep a legal rigid centering alternative in the bounded beam
            # even when optional field-slot and local-proximity variants are
            # present; routing/electrical proof still decides acceptance.
            centered,
            field_slot,
            local_signal,
        )
        if candidate is not None
    )
    ordered = successful[:1] + protected + successful[1:3] + extras + successful[3:]
    seen: set[tuple[tuple[str, Point], ...]] = set()
    retained: list[Packing] = []
    for candidate in ordered:
        identity = tuple(
            sorted((placed.fragment.id, placed.delta) for placed in candidate.fragments)
        )
        if identity in seen:
            continue
        seen.add(identity)
        retained.append(candidate)
        if len(retained) == CANDIDATE_BUDGET:
            break
    return tuple(retained)
