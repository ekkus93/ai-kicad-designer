"""Implementation details for m2 pack semantic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .m2_fragments_types import Point
from .m2_pack_constants import (
    CANDIDATE_BUDGET,
    CHANNEL_GAP,
    LEFT,
)
from .m2_pack_core import Packing
from .m2_pack_distribution import _measured_repack
from .m2a_constants import PITCH

if TYPE_CHECKING:
    from .m2_semantics_core import SemanticPlan


def _semantic_block_order_candidates(plan: SemanticPlan, baseline: Packing) -> tuple[Packing, ...]:
    """Try a legal adjacent functional-stage exchange between incomparable peers.

    A branch or forward-signal dependency forbids an exchange, while unrelated
    functional stages may trade same-band positions. Final legality is checked
    against every hard placement obligation and measured reservation envelope.
    """
    placed = tuple(
        sorted(
            (
                item
                for item in baseline.fragments
                if item.fragment.block.function is not None
                and not item.fragment.block.unused
                and item.fragment.block.kind != "interface"
            ),
            key=lambda item: (
                item.envelope[1],
                item.envelope[0],
                item.fragment.block.id,
            ),
        )
    )
    forward: dict[str, set[str]] = {}
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"} and edge.source != edge.target:
            forward.setdefault(edge.source, set()).add(edge.target)
    for relation in plan.precedence:
        if relation.source_fragment != relation.target_fragment:
            forward.setdefault(relation.source_fragment, set()).add(relation.target_fragment)

    def reaches(source: str, target: str) -> bool:
        visited: set[str] = set()
        pending = [source]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            if target in forward.get(current, set()):
                return True
            pending.extend(sorted(forward.get(current, set()) - visited))
        return False

    proposals: list[tuple[tuple[int, str, str], Packing]] = []
    trial_limit = CANDIDATE_BUDGET * 4
    trials = 0
    for index, first in enumerate(placed):
        if trials >= trial_limit:
            break
        for second in placed[index + 1 :]:
            if trials >= trial_limit:
                break
            first_id = first.fragment.block.id
            second_id = second.fragment.block.id
            if first.envelope[1] != second.envelope[1]:
                continue
            if reaches(first_id, second_id) or reaches(second_id, first_id):
                continue
            if first.envelope[0] == second.envelope[0]:
                continue
            trials += 1
            exchanged = _measured_repack(
                plan,
                baseline,
                first,
                second.envelope[0],
                second.envelope[1],
                "semantic-block-order-swap",
                additional_moves=((second, first.envelope[0], first.envelope[1]),),
            )
            if exchanged is None:
                continue
            separation = abs(first.envelope[0] - second.envelope[0])
            proposals.append(((separation, first_id, second_id), exchanged))
    if not proposals:
        return ()
    return (min(proposals, key=lambda item: item[0])[1],)


def _support_affinity_candidates(plan: SemanticPlan, baseline: Packing) -> tuple[Packing, ...]:
    """Search a legal, closer slot for an explicitly owned support fragment."""
    placed = {item.fragment.block.id: item for item in baseline.fragments}
    options: list[tuple[tuple[int, str, str, int, int], Packing]] = []
    trial_limit = CANDIDATE_BUDGET * 4
    trials = 0
    for edge in sorted(
        plan.edges, key=lambda item: (item.kind, item.source, item.target, item.net)
    ):
        if trials >= trial_limit:
            break
        if edge.kind not in {"support", "feedback", "package"}:
            continue
        first, second = placed.get(edge.source), placed.get(edge.target)
        if first is None or second is None:
            continue
        if first.fragment.block.function is not None and second.fragment.block.function is None:
            owner, support = first, second
        elif second.fragment.block.function is not None and first.fragment.block.function is None:
            owner, support = second, first
        else:
            continue
        if support.fragment.block.kind == "interface" or support.fragment.block.unused:
            continue
        width = support.envelope[2] - support.envelope[0]
        height = support.envelope[3] - support.envelope[1]
        original = abs(support.envelope[0] - owner.envelope[0]) + abs(
            support.envelope[1] - owner.envelope[1]
        )
        for x, y in (
            (owner.envelope[0], owner.envelope[3] + CHANNEL_GAP),
            (owner.envelope[0], owner.envelope[1] - height - CHANNEL_GAP),
            (owner.envelope[0] - width - CHANNEL_GAP, owner.envelope[1]),
            (owner.envelope[2] + CHANNEL_GAP, owner.envelope[1]),
        ):
            if trials >= trial_limit:
                break
            trials += 1
            candidate = _measured_repack(plan, baseline, support, x, y, "semantic-support-affinity")
            if candidate is None:
                continue
            distance = abs(x - owner.envelope[0]) + abs(y - owner.envelope[1])
            if distance < original:
                options.append(
                    (
                        (distance, support.fragment.block.id, owner.fragment.block.id, x, y),
                        candidate,
                    )
                )
    return (min(options, key=lambda item: item[0])[1],) if options else ()


def _repeated_peer_alignment_candidates(
    plan: SemanticPlan, baseline: Packing
) -> tuple[Packing, ...]:
    """Search both row- and column-oriented alignments of equivalent signal peers."""
    by_block = {block.id: block for block in plan.blocks}
    active = sorted(
        (
            item
            for item in baseline.fragments
            if item.fragment.block.function is not None
            and not item.fragment.block.unused
            and item.fragment.block.kind != "interface"
        ),
        key=lambda item: item.fragment.block.id,
    )
    forward: dict[str, set[str]] = {}
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"} and edge.source != edge.target:
            forward.setdefault(edge.source, set()).add(edge.target)

    def reaches(start: str, end: str) -> bool:
        pending = [start]
        seen: set[str] = set()
        while pending:
            item = pending.pop()
            if item in seen:
                continue
            seen.add(item)
            if end in forward.get(item, set()):
                return True
            pending.extend(sorted(forward.get(item, set()) - seen))
        return False

    def signature(block_id: str) -> tuple:
        block = by_block[block_id]
        incident = []
        for edge in plan.edges:
            if edge.source == block_id and edge.target in by_block:
                incident.append(("out", edge.kind, by_block[edge.target].kind))
            elif edge.target == block_id and edge.source in by_block:
                incident.append(("in", edge.kind, by_block[edge.source].kind))
        return (
            block.kind,
            tuple(sorted(port.role for port in block.ports)),
            tuple(sorted(incident)),
        )

    options: list[tuple[tuple[int, str, str, str], Packing]] = []
    trials = 0
    limit = CANDIDATE_BUDGET * 4
    for index, first in enumerate(active):
        if trials >= limit:
            break
        for second in active[index + 1 :]:
            if trials >= limit:
                break
            first_id = first.fragment.block.id
            second_id = second.fragment.block.id
            if signature(first_id) != signature(second_id):
                continue
            if reaches(first_id, second_id) or reaches(second_id, first_id):
                continue
            first_width = first.envelope[2] - first.envelope[0]
            first_height = first.envelope[3] - first.envelope[1]
            second_width = second.envelope[2] - second.envelope[0]
            second_height = second.envelope[3] - second.envelope[1]
            for mode, x, y in (
                (
                    "column",
                    first.envelope[0] + (first_width - second_width) // 2,
                    first.envelope[3] + CHANNEL_GAP,
                ),
                (
                    "row",
                    first.envelope[2] + CHANNEL_GAP,
                    first.envelope[1] + (first_height - second_height) // 2,
                ),
            ):
                if trials >= limit:
                    break
                trials += 1
                candidate = _measured_repack(plan, baseline, second, x, y, f"repeated-peer-{mode}")
                if candidate is None:
                    continue
                movement = abs(x - second.envelope[0]) + abs(y - second.envelope[1])
                options.append(((movement, first_id, second_id, mode), candidate))
    # Expose both grammars independently. Returning only the globally nearest
    # proposal silently prevents the final route-aware selector from ever
    # evaluating the other arrangement even when it is the clearer choice.
    candidates: list[Packing] = []
    identities: set[tuple[tuple[str, str, Point], ...]] = set()
    for mode in ("row", "column"):
        eligible = (
            (key, candidate)
            for key, candidate in options
            if candidate.attempts[-1] == f"repeated-peer-{mode}"
        )
        best = min(eligible, key=lambda item: item[0], default=None)
        if best is None:
            continue
        candidate = best[1]
        identity = tuple(
            sorted(
                (
                    placed.fragment.block.id,
                    placed.fragment.id,
                    placed.delta,
                )
                for placed in candidate.fragments
            )
        )
        if identity not in identities:
            identities.add(identity)
            candidates.append(candidate)
    return tuple(candidates)


def _structural_repack_candidates(plan: SemanticPlan, baseline: Packing) -> tuple[Packing, ...]:
    """Try functional row compaction and precedence-bound band staggering."""
    items = baseline.fragments
    by_id = {item.fragment.block.id: item for item in items}
    proposals = []
    functional = [item for item in items if item.fragment.block.function is not None]
    for target in functional:
        if target.fragment.block.unused:
            continue
        for row_top in sorted({item.envelope[1] for item in functional}):
            row = [item for item in items if item is not target and item.envelope[1] == row_top]
            if row:
                # A boundary interface or support cell need not force the
                # whole functional row past its rightmost endpoint. Enumerate
                # measured gaps and keep only complete legal transactions.
                origins = (
                    {LEFT + PITCH, target.envelope[0]}
                    | {item.envelope[2] + PITCH for item in row}
                    | {item.envelope[0] for item in row if item.fragment.block.unused}
                )
                for left in sorted(origins):
                    if row_top == target.envelope[1] and left >= target.envelope[0]:
                        continue
                    candidate = _measured_repack(
                        plan, baseline, target, left, row_top, "functional-row-compaction"
                    )
                    if candidate is not None:
                        proposals.append(candidate)
                    else:
                        # A parked function can occupy the only measured row
                        # gap. Exchange it into the vacated cell as one atomic
                        # transaction, then recheck every placement obligation.
                        for parked in row:
                            if not parked.fragment.block.unused or parked.envelope[0] != left:
                                continue
                            exchanged = _measured_repack(
                                plan,
                                baseline,
                                target,
                                left,
                                row_top,
                                "functional-row-compaction",
                                displaced=parked,
                            )
                            if exchanged is not None:
                                proposals.append(exchanged)
    # A row may contain several independently constrained active functions.
    # Compact the whole row transaction so an existing reversed sibling does
    # not make every single-fragment move fail before it can be repaired.
    active = sorted(
        (item for item in functional if not item.fragment.block.unused),
        key=lambda item: item.fragment.block.id,
    )
    for row_top in sorted({item.envelope[1] for item in active}):
        outside = [item for item in active if item.envelope[1] != row_top]
        parked = sorted(
            (
                item
                for item in functional
                if item.fragment.block.unused and item.envelope[1] == row_top
            ),
            key=lambda item: item.fragment.block.id,
        )
        if not outside or len(parked) > len(outside):
            continue
        moves = []
        left = LEFT + PITCH
        for item in active:
            moves.append((item, left, row_top))
            left += item.envelope[2] - item.envelope[0] + PITCH
        moves.extend(
            (item, vacant.envelope[0], vacant.envelope[1])
            for item, vacant in zip(parked, outside, strict=False)
        )
        target, x, y = next(move for move in moves if move[0] in outside)
        grouped = _measured_repack(
            plan,
            baseline,
            target,
            x,
            y,
            "functional-row-compaction",
            additional_moves=tuple(move for move in moves if move[0] is not target),
        )
        if grouped is not None:
            proposals.append(grouped)
    for obligation in plan.precedence:
        source = by_id.get(obligation.source_fragment)
        target = by_id.get(obligation.target_fragment)
        if source is None or target is None or source is target:
            continue
        target_height = target.envelope[3] - target.envelope[1]
        for numerator in (1, 2, 3):
            candidate = _measured_repack(
                plan,
                baseline,
                target,
                target.envelope[0],
                source.envelope[3] - numerator * target_height // 4,
                "precedence-staggered-band",
            )
            if candidate is not None:
                proposals.append(candidate)
    return tuple(proposals)
