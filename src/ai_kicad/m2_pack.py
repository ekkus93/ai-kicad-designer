"""Deterministic measured-envelope packing for M2 fragments."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice, product

from .ir import InputError
from .m2a import PITCH
from .m2_fragments import FragmentVariant, Point, PortAnchor, Rect
from .m2_semantics import SemanticPlan


LEFT = 18 * PITCH
TOP = 23 * PITCH
RIGHT = 215 * PITCH
BOTTOM = 144 * PITCH
GAP = 4 * PITCH


@dataclass(frozen=True)
class PlacedFragment:
    fragment: FragmentVariant
    delta: Point
    envelope: Rect
    ports: tuple[PortAnchor, ...]


@dataclass(frozen=True)
class Packing:
    fragments: tuple[PlacedFragment, ...]
    attempts: tuple[str, ...]


def _translate_point(point: Point, delta: Point) -> Point:
    return point[0] + delta[0], point[1] + delta[1]


def _place(fragment: FragmentVariant, left: int, top: int) -> PlacedFragment:
    old = fragment.envelope
    delta = (
        ((left - old[0] + PITCH - 1) // PITCH) * PITCH,
        ((top - old[1] + PITCH - 1) // PITCH) * PITCH,
    )
    envelope = tuple(value + shift for value, shift in zip(old, (*delta, *delta), strict=True))
    ports = tuple(
        PortAnchor(anchor.port, _translate_point(anchor.point, delta), anchor.direction)
        for anchor in fragment.ports
    )
    return PlacedFragment(fragment, delta, envelope, ports)


def _ordered_main(plan: SemanticPlan) -> list[str]:
    graph_edges = [edge for edge in plan.edges if edge.kind in {"signal", "power", "branch"}]
    connected = {endpoint for edge in graph_edges for endpoint in (edge.source, edge.target)}
    by_id = {block.id: block for block in plan.blocks}
    connected.update(
        block.id
        for block in plan.blocks
        if block.kind not in {"interface", "package_power", "unused_amplifier", "led_branch"}
        and not connected
    )
    remaining = set(connected)
    result = []
    while remaining:
        ready = sorted(
            node
            for node in remaining
            if not any(edge.source in remaining and edge.target == node for edge in graph_edges)
        )
        if not ready:
            raise InputError(f"PACK_ORDER_CYCLE: {sorted(remaining)}")
        selected = ready[0]
        result.append(selected)
        remaining.remove(selected)
    return [item for item in result if item in by_id]


def pack_fragments(plan: SemanticPlan, variants: dict[str, tuple[FragmentVariant, ...]]) -> Packing:
    """Pack actual envelopes in a signal/power row plus deterministic auxiliary shelves."""
    main = _ordered_main(plan)
    attempts: list[str] = []
    keys = sorted(variants)
    if any(not choices or len(choices) > 8 for choices in variants.values()):
        raise InputError("PACK_VARIANT_INVENTORY: each block requires one to eight variants")
    combinations = islice(product(*(variants[key] for key in keys)), 8)
    for candidate_index, combination in enumerate(combinations, 1):
        chosen = dict(zip(keys, combination, strict=True))
        auxiliary = sorted(set(chosen) - set(main))
        placed: list[PlacedFragment] = []
        try:
            x = LEFT
            main_bottom = TOP
            for fragment_id in main:
                fragment = chosen[fragment_id]
                width = fragment.envelope[2] - fragment.envelope[0]
                if x + width > RIGHT:
                    raise ValueError(f"primary-row-overflow:{fragment_id}")
                item = _place(fragment, x, TOP)
                placed.append(item)
                x = item.envelope[2] + GAP
                main_bottom = max(main_bottom, item.envelope[3])

            x, y, row_bottom = LEFT, main_bottom + GAP, main_bottom + GAP
            for fragment_id in auxiliary:
                fragment = chosen[fragment_id]
                width = fragment.envelope[2] - fragment.envelope[0]
                height = fragment.envelope[3] - fragment.envelope[1]
                if width > RIGHT - LEFT or height > BOTTOM - TOP:
                    raise ValueError(f"indivisible-envelope-overflow:{fragment_id}")
                if x + width > RIGHT:
                    x, y = LEFT, row_bottom + GAP
                if y + height > BOTTOM:
                    raise ValueError(f"auxiliary-shelf-overflow:{fragment_id}")
                item = _place(fragment, x, y)
                placed.append(item)
                x = item.envelope[2] + GAP
                row_bottom = max(row_bottom, item.envelope[3])
        except ValueError as exc:
            attempts.append(f"candidate-{candidate_index}:{exc}")
            continue
        attempts.append(f"candidate-{candidate_index}:pass")
        return Packing(tuple(sorted(placed, key=lambda item: item.fragment.id)), tuple(attempts))

    indivisible = [
        (fragment.id, fragment.envelope)
        for choices in variants.values()
        for fragment in choices
        if fragment.envelope[2] - fragment.envelope[0] > RIGHT - LEFT
        or fragment.envelope[3] - fragment.envelope[1] > BOTTOM - TOP
    ]
    if indivisible and all(
        all(
            choice.envelope[2] - choice.envelope[0] > RIGHT - LEFT
            or choice.envelope[3] - choice.envelope[1] > BOTTOM - TOP
            for choice in choices
        )
        for choices in variants.values()
        if any(choice.id == item[0] for item in indivisible for choice in choices)
    ):
        raise InputError(f"PACK_PAGE_INFEASIBLE: indivisible envelope bounds={indivisible}")
    raise InputError(f"PACK_BUDGET_EXHAUSTED: candidates=8 attempts={attempts}")
