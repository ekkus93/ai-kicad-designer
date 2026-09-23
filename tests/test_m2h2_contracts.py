"""Independent small falsifications for candidate terminal and graph contracts."""

from collections import defaultdict, deque

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2_geometry import (
    AccessWindow,
    ConductorSegment,
    Gateway,
    canonical_conductor_tree,
    conductor_components,
    prove_conductor_graph,
    prove_gateway_witnesses,
)
from ai_kicad.m2_semantics import (
    LocalSpanObligation,
    SemanticPlan,
    SignalPrecedence,
    check_placement_constraints,
)


def reference_components(segments: tuple[ConductorSegment, ...]) -> int:
    """Cell-walk oracle, independent of the production segment canonicalizer."""
    cells: set[tuple[int, int]] = set()
    for segment in segments:
        first, second = segment.start, segment.end
        if first[0] == second[0]:
            cells.update(
                (first[0], y) for y in range(min(first[1], second[1]), max(first[1], second[1]) + 1)
            )
        else:
            cells.update(
                (x, first[1]) for x in range(min(first[0], second[0]), max(first[0], second[0]) + 1)
            )
    adjacent = defaultdict(set)
    for x, y in cells:
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in cells:
                adjacent[(x, y)].add(neighbor)
    count = 0
    remaining = set(cells)
    while remaining:
        count += 1
        pending = deque((min(remaining),))
        remaining.remove(pending[0])
        while pending:
            for neighbor in adjacent[pending.popleft()] & remaining:
                remaining.remove(neighbor)
                pending.append(neighbor)
    return count


def segment(a: tuple[int, int], b: tuple[int, int], net: str = "N") -> ConductorSegment:
    return ConductorSegment(a, b, net, "synthetic")


def test_disconnected_internal_islands_reject_matching_net_strings() -> None:
    wires = (segment((0, 0), (2, 0)), segment((5, 0), (7, 0)))
    tree = canonical_conductor_tree(wires, pins=((0, 0), (7, 0)))
    assert len(conductor_components(tree)) == reference_components(wires) == 2
    with pytest.raises(InputError, match="CONDUCTOR_ISLANDS_DISCONNECTED"):
        prove_conductor_graph(
            tree,
            {("producer", "1"): (0, 0), ("parked", "5"): (7, 0)},
            intentional_ends=((2, 0), (5, 0)),
        )


def test_exact_pin_and_all_gateway_witnesses() -> None:
    gateway = Gateway(
        "access",
        "N",
        (("a", "1"), ("b", "1")),
        "island",
        (0, 0),
        "right",
        ((0, 0), (2, 0)),
        frozenset({"right"}),
        (AccessWindow((2, -1, 3, 1), frozenset({"right"}), "N"),),
    )
    tree = canonical_conductor_tree(
        (segment((0, 0), (2, 0)), segment((0, 0), (0, 2))), pins=((0, 0), (0, 2))
    )
    assert prove_gateway_witnesses(tree, gateway, {("a", "1"): (0, 0), ("b", "1"): (0, 2)})
    with pytest.raises(InputError, match="GATEWAY_PIN_DETACHED"):
        prove_gateway_witnesses(tree, gateway, {("a", "1"): (0, 0), ("b", "1"): (1, 2)})
    with pytest.raises(InputError, match="GATEWAY_PIN_DETACHED"):
        prove_gateway_witnesses(tree, gateway, {("a", "1"): (0, 0), ("b", "1"): (9, 9)})
    stale = Gateway(
        "stale",
        "N",
        (("a", "1"),),
        "island",
        (0, 0),
        "right",
        ((0, 0), (3, 0)),
        frozenset({"right"}),
        (),
    )
    with pytest.raises(InputError, match="GATEWAY_ESCAPE_DETACHED"):
        prove_gateway_witnesses(tree, stale, {("a", "1"): (0, 0)})


def test_junction_and_unrelated_crossing_are_not_metadata_shortcuts() -> None:
    t = canonical_conductor_tree(
        (segment((0, 0), (4, 0)), segment((2, 0), (2, 2))), pins=((0, 0), (4, 0), (2, 2))
    )
    assert reference_components((segment((0, 0), (4, 0)), segment((2, 0), (2, 2)))) == 1
    with pytest.raises(InputError, match="CONDUCTOR_JUNCTION_MISSING"):
        prove_conductor_graph(t, {("a", "1"): (0, 0), ("b", "1"): (4, 0), ("c", "1"): (2, 2)})
    assert prove_conductor_graph(
        t,
        {("a", "1"): (0, 0), ("b", "1"): (4, 0), ("c", "1"): (2, 2)},
        declared_junctions=t.junctions,
    ).components
    crossing = canonical_conductor_tree((segment((0, 1), (4, 1)), segment((2, 0), (2, 2))))
    assert len(conductor_components(crossing)) == 2


def test_exact_locality_boundary_and_precedence_inequality() -> None:
    plan = SemanticPlan(
        (),
        (),
        {},
        (),
        precedence=(SignalPrecedence("order", "left", "right", ("a", "1"), ("b", "1"), "N", ()),),
        local_spans=(
            LocalSpanObligation(
                "local", ("a", "1"), ("b", "1"), 80_000_000, "manhattan", "protected_signal", ()
            ),
        ),
    )
    positions = {("a", "1"): (0, 0), ("b", "1"): (80_000_000, 0)}
    assert check_placement_constraints(plan, lambda *key: positions[key])
    positions[("b", "1")] = (80_000_001, 0)
    with pytest.raises(InputError, match="LOCAL_SPAN_VIOLATION"):
        check_placement_constraints(plan, lambda *key: positions[key])
    positions[("b", "1")] = (-1, 0)
    with pytest.raises(InputError, match="PRECEDENCE_VIOLATION"):
        check_placement_constraints(plan, lambda *key: positions[key])
