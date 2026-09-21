"""Instance-based composition of qualified M2 schematic fragments."""

from __future__ import annotations

from dataclasses import dataclass

from .ir import InputError
from .m2a import PITCH, Scene
from .m2b import Draft, choose_text_slots, measure
from .m2_fragments import fragment_variants
from .m2_pack import pack_fragments
from .m2_route import route_between_fragments
from .m2_semantics import semantic_plan


@dataclass(frozen=True)
class StageGraph:
    """Compatibility view of signal-like relationship ordering."""

    ports: dict[str, tuple[str, str]]
    order: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]


def stage_graph(design: dict) -> StageGraph:
    """Return the legacy relation projection; composition uses the typed plan."""
    ports = {
        relation["id"]: (relation["input"], relation["output"])
        for relation in design["relationships"]
        if relation["kind"] in ("series", "amplifier", "power_stage") and not relation.get("unused")
    }
    ports.update(
        (relation["id"], (relation["supply"], relation["output"]))
        for relation in design["relationships"]
        if relation["kind"] == "timer"
    )
    edges = tuple(
        sorted(
            (first, second, output)
            for first, (_, output) in ports.items()
            for second, (input_net, _) in ports.items()
            if first != second and output == input_net
        )
    )
    remaining, order = set(ports), []
    while remaining:
        ready = sorted(
            stage
            for stage in remaining
            if not any(first in remaining and second == stage for first, second, _ in edges)
        )
        if not ready:
            raise InputError(f"unsupported stage graph cycle: {sorted(remaining)}")
        order.extend(ready)
        remaining.difference_update(ready)
    return StageGraph(ports, tuple(order), edges)


def _translate(point: tuple[int, int], delta: tuple[int, int]) -> tuple[int, int]:
    return point[0] + delta[0], point[1] + delta[1]


def _clear_nonpassive_text(design: dict, draft: Draft) -> None:
    """Choose a deterministic clear slot for symbols not handled by the passive chooser."""
    components = {component["id"]: component for component in design["components"]}
    for key in sorted(draft.text_positions):
        component = components.get(key[0])
        if component is None or component["asset"] in {"Device:C", "Device:R"}:
            continue
        sx, sy = draft.positions[key]
        candidates = [
            draft.text_positions[key],
            (sx, sy - 12 * PITCH),
            (sx + 12 * PITCH, sy - 8 * PITCH),
            (sx - 12 * PITCH, sy - 8 * PITCH),
            (sx + 12 * PITCH, sy + 6 * PITCH),
            (sx - 12 * PITCH, sy + 6 * PITCH),
        ]
        for x, y in candidates:
            clear = True
            for value, py in ((component["refdes"], y), (component["value"], y + 2 * PITCH)):
                half = max(635_000, len(value) * 445_000)
                for a, b in draft.wires:
                    if (
                        a[0] == b[0]
                        and x - half < a[0] < x + half
                        and max(min(a[1], b[1]), py - 850_000) < min(max(a[1], b[1]), py + 850_000)
                    ) or (
                        a[1] == b[1]
                        and py - 850_000 < a[1] < py + 850_000
                        and max(min(a[0], b[0]), x - half) < min(max(a[0], b[0]), x + half)
                    ):
                        clear = False
                        break
                if not clear:
                    break
            if clear:
                draft.text_positions[key] = (x, y)
                break
        else:
            raise InputError(f"TEXT_SLOT_INFEASIBLE: {component['id']} unit {key[1]}")


def compose_with_evidence(design: dict, resolved: dict) -> tuple[Scene, dict]:
    """Compose a scene and return the derived semantic/geometry decision record."""
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    packing = pack_fragments(plan, variants)
    draft = Draft(design, resolved, {}, {}, [], [], [], [], {})
    for placed in packing.fragments:
        fragment, delta = placed.fragment, placed.delta
        for key, point in fragment.positions.items():
            if key in draft.positions:
                raise InputError(f"COMPOSE_GEOMETRY_OWNER_CONFLICT: {key}")
            draft.positions[key] = _translate(point, delta)
        draft.angles.update(fragment.angles)
        draft.text_positions.update(
            (key, _translate(point, delta)) for key, point in fragment.text_positions.items()
        )
        draft.wires.extend(
            (_translate(first, delta), _translate(second, delta))
            for first, second in fragment.wires
        )
        draft.wire_nets.extend(fragment.wire_nets)
        draft.labels.extend((net, _translate(point, delta)) for net, point in fragment.labels)
        draft.junctions.extend(_translate(point, delta) for point in fragment.junctions)

    route_trees = route_between_fragments(plan, packing.fragments)
    for tree in route_trees:
        draft.wires.extend(tree.segments)
        draft.wire_nets.extend([tree.net] * len(tree.segments))
        draft.junctions.extend(tree.junctions)

    component_ids = {component["id"] for component in design["components"]}
    expected = set(plan.owners)
    actual = {key for key in draft.positions if key[0] in component_ids}
    if actual != expected:
        raise InputError(
            f"COMPOSE_OWNER_INCOMPLETE: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}"
        )
    for assertion in design["power_assertions"]:
        candidates = sorted(point for net, point in draft.labels if net == assertion["net"])
        if not candidates:
            raise InputError(
                f"COMPOSE_ASSERTION_PORT_MISSING: {assertion['id']}:{assertion['net']}"
            )
        draft.positions[(assertion["id"], 1)] = candidates[0]

    choose_text_slots(design, draft)
    _clear_nonpassive_text(design, draft)
    metrics = measure(design, resolved, draft)
    metrics.update(
        {
            "semantic_block_count": len(plan.blocks),
            "semantic_edge_count": len(plan.edges),
            "packing_attempts": list(packing.attempts),
        }
    )
    scene = Scene(
        draft.positions,
        draft.wires,
        draft.wire_nets,
        draft.labels,
        draft.junctions,
        metrics,
        draft.angles,
        draft.text_positions,
    )
    evidence = {
        "schema_version": "m2e1.composition.1",
        "blocks": [
            {
                "id": block.id,
                "kind": block.kind,
                "relationships": list(block.relationships),
                "occurrences": [list(item) for item in sorted(block.occurrences)],
                "function": list(block.function) if block.function else None,
                "unused": block.unused,
                "ports": [
                    {
                        "id": port.id,
                        "net": port.net,
                        "role": port.role,
                        "terminals": [list(item) for item in port.terminals],
                    }
                    for port in block.ports
                ],
            }
            for block in plan.blocks
        ],
        "owners": [
            {"occurrence": list(occurrence), "fragment": owner}
            for occurrence, owner in sorted(plan.owners.items())
        ],
        "edges": [
            {
                "kind": edge.kind,
                "source": edge.source,
                "target": edge.target,
                "net": edge.net,
                "origins": list(edge.origins),
            }
            for edge in plan.edges
        ],
        "signal_order": list(plan.signal_order),
        "variants": [
            {
                "fragment": item.fragment.block.id,
                "variant": item.fragment.id,
                "rule": item.fragment.rule_id,
                "origins": list(item.fragment.origins),
                "local_envelope": list(item.fragment.envelope),
                "placed_envelope": list(item.envelope),
                "translation": list(item.delta),
                "protected_wire_count": len(item.fragment.protected_wires),
                "obstacle_count": len(item.fragment.obstacles),
            }
            for item in packing.fragments
        ],
        "packing_attempts": list(packing.attempts),
        "routes": [
            {
                "net": tree.net,
                "edge_count": len(tree.edges),
                "segments": [[list(first), list(second)] for first, second in tree.segments],
                "junctions": [list(point) for point in tree.junctions],
            }
            for tree in route_trees
        ],
    }
    return scene, evidence


def compose_layout(design: dict, resolved: dict) -> Scene:
    """Compatibility entry point returning the composed scene."""
    return compose_with_evidence(design, resolved)[0]
