"""Generic semantic-readability ranking for electrically proved M2 placements.

The caller must establish all existing hard invariants before ranking. External
signal direction comes from producer/consumer ports, never from case IDs,
reference designators, net-name literals or production layout scores.
"""

from __future__ import annotations

from .m2_pack import PITCH, Packing
from .m2_semantics import SemanticPlan


def semantic_composition_penalties(
    plan: SemanticPlan, packing: Packing
) -> tuple[int, int, int, int]:
    """Return side, forward-flow, interface-owner, support-owner penalties."""
    centers = {}
    for item in packing.fragments:
        bounds = item.content_envelope or item.envelope
        centers[item.fragment.block.id] = (
            (bounds[0] + bounds[2]) // 2,
            (bounds[1] + bounds[3]) // 2,
        )

    producers: dict[str, set[str]] = {}
    consumers: dict[str, set[str]] = {}
    for block in plan.blocks:
        if block.kind == "interface":
            continue
        for port in block.ports:
            if port.role == "signal_out":
                producers.setdefault(port.net, set()).add(block.id)
            elif port.role == "signal_in":
                consumers.setdefault(port.net, set()).add(block.id)

    side_penalty = 0
    owner_distance = 0
    for block in plan.blocks:
        if block.kind != "interface" or block.id not in centers:
            continue
        directions = set()
        relations = []
        for port in block.ports:
            sources = sorted(producers.get(port.net, set()) & centers.keys())
            targets = sorted(consumers.get(port.net, set()) & centers.keys())
            if sources:
                directions.add("output")
                relations.append(("output", sources))
            elif targets:
                directions.add("input")
                relations.append(("input", targets))
        if len(directions) != 1:
            continue  # ambiguous/bidirectional or non-signal interface
        x, y = centers[block.id]
        for direction, owners in relations:
            witnesses = [
                (
                    max(0, centers[owner][0] - x)
                    if direction == "output"
                    else max(0, x - centers[owner][0]),
                    abs(x - centers[owner][0]) + abs(y - centers[owner][1]),
                )
                for owner in owners
            ]
            side, distance = min(witnesses, key=lambda pair: (pair[1], pair[0]))
            side_penalty += (side + PITCH - 1) // PITCH
            owner_distance += (distance + PITCH - 1) // PITCH

    flow_backtracking = sum(
        (max(0, centers[edge.source][0] - centers[edge.target][0]) + PITCH - 1)
        // PITCH
        for edge in plan.edges
        if edge.kind in {"signal", "branch"}
        and edge.source in centers
        and edge.target in centers
        and edge.source != edge.target
    )
    support_distance = sum(
        (
            abs(centers[edge.source][0] - centers[edge.target][0])
            + abs(centers[edge.source][1] - centers[edge.target][1])
            + PITCH
            - 1
        )
        // PITCH
        for edge in plan.edges
        if edge.kind == "support"
        and edge.source in centers
        and edge.target in centers
    )
    return side_penalty, flow_backtracking, owner_distance, support_distance
