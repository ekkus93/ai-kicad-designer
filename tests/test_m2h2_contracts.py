"""Independent small falsifications for candidate terminal and graph contracts."""

from itertools import product

import pytest
from m2h2_contract_helpers import reference_components, segment

from ai_kicad.ir import InputError
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_geometry import (
    AccessWindow,
    ConductorSegment,
    Gateway,
    GeometryItem,
    Reservation,
    canonical_conductor_tree,
    conductor_components,
    prove_conductor_graph,
    prove_gateway_witnesses,
    prove_no_cross_net_contacts,
    prove_reservation_allocation,
)
from ai_kicad.m2_pack import (
    CANDIDATE_BUDGET,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    _partial_beam_candidates,
)
from ai_kicad.m2_semantics import (
    BlockPlan,
    LocalSpanObligation,
    SemanticPlan,
    SignalPrecedence,
    check_placement_constraints,
)
from ai_kicad.m2a import PITCH


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


def test_bypassed_internal_gateway_tip_is_a_dangling_endpoint() -> None:
    # Both real pins are connected, yet a gateway spur bypassed by the chosen
    # global branch would produce a KiCad unconnected-wire ERC warning.
    tree = canonical_conductor_tree(
        (
            segment((0, 0), (2, 0)),
            segment((2, 0), (3, 0)),
            segment((2, 0), (2, 3)),
        ),
        pins=((0, 0), (2, 3)),
    )
    with pytest.raises(InputError, match="CONDUCTOR_ENDPOINT_DANGLING"):
        prove_conductor_graph(
            tree,
            {("producer", "1"): (0, 0), ("consumer", "1"): (2, 3)},
            declared_junctions=tree.junctions,
        )


def test_tiny_exhaustive_two_band_reference_preserves_structural_classes() -> None:
    blocks = tuple(
        BlockPlan(f"cell{index}", "timer" if index < 2 else "rc", (), frozenset(), ())
        for index in range(4)
    )
    variants = {
        block.id: tuple(
            FragmentVariant(
                f"{block.id}.variant{choice}",
                block,
                {},
                {},
                {},
                (),
                (),
                (),
                (),
                (),
                (0, 0, (width + 2 * choice) * PITCH, (height - 2 * choice) * PITCH),
                frozenset(),
            )
            for choice in range(2)
        )
        for block, (width, height) in zip(
            blocks, ((40, 40), (40, 40), (20, 20), (20, 20)), strict=True
        )
    }
    exhaustive = set()
    for choices in product(range(2), repeat=4):
        widths = [
            variants[block.id][choice].envelope[2]
            for block, choice in zip(blocks, choices, strict=True)
        ]
        heights = [
            variants[block.id][choice].envelope[3]
            for block, choice in zip(blocks, choices, strict=True)
        ]
        for band in ("side", "stack"):
            # Independent finite rectangle enumeration: two tall cores, two
            # variant choices each, two legal bands and two short backfills.
            if band == "side":
                boxes = (
                    (0, 0, widths[0], heights[0]),
                    (widths[0] + PITCH, 0, widths[0] + PITCH + widths[1], heights[1]),
                    (0, max(heights[:2]) + PITCH, widths[2], max(heights[:2]) + PITCH + heights[2]),
                    (
                        widths[2] + PITCH,
                        max(heights[:2]) + PITCH,
                        widths[2] + PITCH + widths[3],
                        max(heights[:2]) + PITCH + heights[3],
                    ),
                )
            else:
                boxes = (
                    (0, 0, widths[0], heights[0]),
                    (0, heights[0] + PITCH, widths[1], heights[0] + PITCH + heights[1]),
                    (max(widths[:2]) + PITCH, 0, max(widths[:2]) + PITCH + widths[2], heights[2]),
                    (
                        max(widths[:2]) + PITCH,
                        heights[2] + PITCH,
                        max(widths[:2]) + PITCH + widths[3],
                        heights[2] + PITCH + heights[3],
                    ),
                )
            if (
                max(box[2] for box in boxes) <= MAX_CONTENT_WIDTH
                and max(box[3] for box in boxes) <= MAX_CONTENT_HEIGHT
            ):
                exhaustive.add(band)
    beam = _partial_beam_candidates(SemanticPlan(blocks, (), {}, ()), variants)
    retained = set()
    for packing in beam:
        first = next(item for item in packing.fragments if item.fragment.block.id == "cell0")
        second = next(item for item in packing.fragments if item.fragment.block.id == "cell1")
        retained.add(
            "side"
            if max(first.envelope[1], second.envelope[1])
            < min(first.envelope[3], second.envelope[3])
            else "stack"
        )
    assert len(beam) <= CANDIDATE_BUDGET
    assert exhaustive == retained == {"side", "stack"}


def test_global_branch_reuses_certified_same_net_local_interval_once() -> None:
    local = ConductorSegment((0, 0), (4, 0), "N", "fragment")
    branch = ConductorSegment((2, 0), (4, 0), "N", "tree.N")
    tree = canonical_conductor_tree((local, branch))
    assert tree.length == 4
    assert all(segment.owner == "fragment" for segment in tree.segments)
    with pytest.raises(InputError, match="CONDUCTOR_OWNER_CONFLICT"):
        canonical_conductor_tree((local, ConductorSegment((2, 0), (4, 0), "N", "foreign")))


def test_local_cross_net_contact_rejected_before_variant_acceptance() -> None:
    with pytest.raises(InputError, match="FRAGMENT_NET_CROSSING"):
        prove_no_cross_net_contacts((segment((0, 1), (4, 1), "A"), segment((2, 0), (2, 2), "B")))
    with pytest.raises(InputError, match="FRAGMENT_NET_CROSSING"):
        prove_no_cross_net_contacts((segment((0, 0), (4, 0), "A"), segment((3, 0), (5, 0), "B")))
    prove_no_cross_net_contacts((segment((0, 1), (4, 1), "A"), segment((5, 0), (5, 2), "B")))


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
    translated = Gateway(
        "translated",
        "N",
        (("a", "1"), ("b", "1")),
        "island",
        (10, 10),
        "right",
        ((10, 10), (12, 10)),
        frozenset({"right"}),
        (),
    )
    translated_tree = canonical_conductor_tree(
        (segment((10, 10), (12, 10)), segment((10, 10), (10, 12))),
        pins=((10, 10), (10, 12)),
    )
    assert prove_gateway_witnesses(
        translated_tree, translated, {("a", "1"): (10, 10), ("b", "1"): (10, 12)}
    )


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


def test_explicit_net_rejects_label_join_and_unattached_leaf() -> None:
    separated = canonical_conductor_tree(
        (segment((0, 0), (2, 0)), segment((4, 0), (6, 0))),
        pins=((0, 0), (6, 0)),
    )
    with pytest.raises(InputError, match="CONDUCTOR_ISLANDS_DISCONNECTED"):
        prove_conductor_graph(
            separated,
            {("source", "1"): (0, 0), ("load", "1"): (6, 0)},
            labels=((2, 0), (4, 0)),
            allow_labeled_islands=False,
        )
    spur = canonical_conductor_tree(
        (segment((0, 0), (4, 0)), segment((2, 0), (2, 2))),
        pins=((0, 0), (4, 0)),
    )
    with pytest.raises(InputError, match="CONDUCTOR_ENDPOINT_DANGLING"):
        prove_conductor_graph(
            spur,
            {("source", "1"): (0, 0), ("load", "1"): (4, 0)},
            declared_junctions=spur.junctions,
        )


def test_reservation_allocation_rejects_wrong_owner_net_and_capacity() -> None:
    wire = GeometryItem("wire", "wire", "tree.N", (0, 0, 10, 0), ("N",))
    corridor = Reservation("corridor", "channel", "tree.N", "global_route", (0, -1, 10, 1), "N", 1)
    assert prove_reservation_allocation((wire,), (corridor,)) == (("tree.N", "wire", "corridor"),)
    wrong_owner = Reservation(
        "wrong_owner", "channel", "tree.M", "global_route", (0, -1, 10, 1), "N", 1
    )
    wrong_net = Reservation(
        "wrong_net", "channel", "tree.N", "global_route", (0, -1, 10, 1), "M", 1
    )
    for invalid in (wrong_owner, wrong_net):
        with pytest.raises(InputError, match="RESERVATION_ALLOCATION_MISSING"):
            prove_reservation_allocation((wire,), (invalid,))
    second = GeometryItem("wire.2", "wire", "tree.N", (1, 0, 9, 0), ("N",))
    with pytest.raises(InputError, match="RESERVATION_CAPACITY_EXCEEDED"):
        prove_reservation_allocation((wire, second), (corridor,))


def test_support_span_exact_boundary() -> None:
    plan = SemanticPlan(
        (),
        (),
        {},
        (),
        local_spans=(
            LocalSpanObligation(
                "support", ("a", "1"), ("b", "1"), 60_000_000, "manhattan", "support", ()
            ),
        ),
    )
    points = {("a", "1"): (0, 0), ("b", "1"): (60_000_000, 0)}
    assert check_placement_constraints(plan, lambda *key: points[key])
    points[("b", "1")] = (60_000_001, 0)
    with pytest.raises(InputError, match="LOCAL_SPAN_VIOLATION"):
        check_placement_constraints(plan, lambda *key: points[key])


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
