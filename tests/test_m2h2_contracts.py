"""Independent small falsifications for candidate terminal and graph contracts."""

from collections import defaultdict, deque
import copy
import json
from itertools import product
from types import MappingProxyType

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2_fragments import FragmentVariant, PortAnchor, fragment_variants
from ai_kicad.m2a import ROOT, PITCH, Scene, certify_scene_geometry, emit, verify_serialized_scene
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import (
    ConductorLengthConflict,
    _assemble_candidate,
    _reservation_growth_repack,
    _structural_repack,
    _substitution_repack,
    compose_with_evidence,
)
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
from ai_kicad.m2_semantics import (
    BlockPlan,
    LocalSpanObligation,
    PlacementConflict,
    PresentationNet,
    SemanticPlan,
    SemanticPort,
    SignalPrecedence,
    check_placement_constraints,
    semantic_plan,
)
from ai_kicad.m2_route import (
    RouteBlockedConflict,
    RouteLengthBoundConflict,
    _distribution_initial_trees,
    route_between_fragments,
)
from ai_kicad.m2_pack import (
    CANDIDATE_BUDGET,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    Packing,
    _partial_beam_candidates,
    _place,
    pack_fragment_candidates,
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


def test_certified_scene_rejects_mutation_and_serialized_endpoint_change(tmp_path) -> None:
    design = {"id": "synthetic", "name": "Synthetic", "components": [], "power_assertions": []}
    scene = certify_scene_geometry(
        Scene({}, [((0, 0), (1_270_000, 0))], ["N"], [("N", (0, 0))], [], {})
    )
    schematic = emit(design, {}, scene, tmp_path / "good")
    verify_serialized_scene(design, scene, schematic)
    schematic.write_text(schematic.read_text().replace("(xy 1.27 0)", "(xy 2.54 0)", 1))
    with pytest.raises(InputError, match="SERIALIZED_SCENE_WIRES_CHANGED"):
        verify_serialized_scene(design, scene, schematic)

    scene.wires = (((0, 0), (2_540_000, 0)),)
    with pytest.raises(InputError, match="SCENE_CERTIFICATE_STALE"):
        emit(design, {}, scene, tmp_path / "stale")
    assert not (tmp_path / "stale").exists()


def test_certified_scene_requires_measured_text_for_every_symbol() -> None:
    with pytest.raises(InputError, match="SCENE_TEXT_POSITION_INCOMPLETE"):
        certify_scene_geometry(Scene({("unit", 1): (0, 0)}, [], [], [], [], {}))


def test_distribution_enumerates_distinct_trunk_topologies() -> None:
    gateways = tuple(
        Gateway(
            f"port.{index}",
            "N",
            ((f"unit.{index}", "1"),),
            f"island.{index}",
            (index * 10 * PITCH, (index % 2) * 3 * PITCH),
            "up",
            (
                (index * 10 * PITCH, (index % 2) * 3 * PITCH),
                (index * 10 * PITCH, ((index % 2) * 3 - 1) * PITCH),
            ),
            frozenset({"up"}),
            (),
        )
        for index in range(3)
    )
    plans = _distribution_initial_trees(
        "N",
        "tree.N",
        gateways[0],
        gateways,
        (),
        (),
        (-100 * PITCH, -100 * PITCH, 100 * PITCH, 100 * PITCH),
    )
    assert {item[0] for item in plans} == {
        "producer_centered",
        "horizontal_above",
        "horizontal_below",
        "vertical_side",
    }
    signatures = {tuple((part.start, part.end) for part in item[1]) for item in plans}
    assert len(signatures) == len(plans)


def test_fixed_partial_conductor_union_prunes_with_typed_length_bound() -> None:
    def cell(name: str, x: int, local_wire: bool):
        port = SemanticPort(f"{name}.port", name, "RAIL", "reference", ((name, "1"),))
        block = BlockPlan(name, "rc", (), frozenset(), (port,))
        gateway = Gateway(
            port.id,
            "RAIL",
            ((name, "1"),),
            f"{name}:RAIL",
            (x, 0),
            "up",
            ((x, 0), (x, -PITCH)),
            frozenset({"up"}),
            (),
        )
        fragment = FragmentVariant(
            f"{name}.v0",
            block,
            MappingProxyType({}),
            MappingProxyType({}),
            MappingProxyType({}),
            (((0, 0), (251_000_000, 0)),) if local_wire else (),
            ("RAIL",) if local_wire else (),
            (),
            (),
            (PortAnchor(port, gateway.point, "up"),),
            (0, -2 * PITCH, 10 * PITCH, 2 * PITCH),
            frozenset(),
            gateways=(gateway,),
        )
        return block, _place(fragment, x, 40 * PITCH)

    first, placed_first = cell("source", 0, True)
    second, placed_second = cell("sink", 20 * PITCH, False)
    plan = SemanticPlan(
        (first, second),
        (),
        {},
        (),
        presentation_nets=(
            PresentationNet(
                "RAIL",
                (("source", "1"), ("sink", "1")),
                ("source", "sink"),
                "distributive",
                True,
                True,
                ("source",),
            ),
        ),
    )
    with pytest.raises(RouteLengthBoundConflict) as caught:
        route_between_fragments(plan, (placed_first, placed_second))
    assert caught.value.net == "RAIL"
    assert caught.value.lower_bound > caught.value.limit == 250_000_000


@pytest.mark.parametrize("reference,count", [("internal", 2), ("distinct", 3)])
def test_standalone_generated_reference_has_owned_producer_and_complete_graph(
    reference: str, count: int
) -> None:
    path = ROOT / f"fixtures/m2h2/interaction/i2/{reference}_{count}.json"
    resolved = assets()
    design = validate(json.loads(path.read_text()), resolved)
    plan = semantic_plan(design, resolved)
    generated = [net for net in plan.presentation_nets if net.internally_generated]
    assert len(generated) == (1 if reference == "internal" else 2)
    assert all(net.producer_fragments and net.explicit_geometry_required for net in generated)
    assert all(
        plan.owners[(relation["upper"], 1)] == plan.owners[(relation["lower"], 1)]
        for relation in design["relationships"]
        if relation["kind"] == "reference_divider"
    )
    _, evidence = compose_with_evidence(design, resolved)
    proofs = {
        item["net"]: item for item in evidence["obligation_certificate"]["net_graph_witnesses"]
    }
    assert all(net.id in proofs for net in generated)
    assert all(proofs[net.id]["component_count"] == 1 for net in generated)


def test_two_shared_packages_have_complete_reference_distribution() -> None:
    path = ROOT / "fixtures/m2h2/interaction/i6/pkg2_internal.json"
    resolved = assets()
    design = validate(json.loads(path.read_text()), resolved)
    plan = semantic_plan(design, resolved)
    _, evidence = compose_with_evidence(design, resolved)
    reference = next(net for net in plan.presentation_nets if net.internally_generated)
    proof = next(
        item
        for item in evidence["obligation_certificate"]["net_graph_witnesses"]
        if item["net"] == reference.id
    )
    assert len(reference.fragments) == 4
    assert proof["component_count"] == 1
    assert proof["canonical_length_nm"] <= 250_000_000
    expected_terminals = {
        tuple(member)
        for net in design["nets"]
        if net["id"] == reference.id
        for member in net["members"]
    }
    assert {
        tuple(terminal) for terminal, _component in proof["terminal_components"]
    } == expected_terminals
    tree = next(item for item in evidence["canonical_trees"] if item["net"] == reference.id)
    # Coordinate compression preserves every orthogonal contact/crossing.
    # The cell-walk oracle uses unit cells, not millions of nanometre cells.
    xs = sorted({point[0] for segment in tree["segments"] for point in segment})
    ys = sorted({point[1] for segment in tree["segments"] for point in segment})
    segments = tuple(
        ConductorSegment(
            (xs.index(start[0]), ys.index(start[1])),
            (xs.index(end[0]), ys.index(end[1])),
            reference.id,
            "independent-oracle",
        )
        for start, end in tree["segments"]
    )
    assert reference_components(segments) == 1


def test_proved_structural_candidates_are_ranked_by_complete_tree() -> None:
    path = ROOT / "fixtures/m2h2/interaction/i3/a0_interleaved.json"
    resolved = assets()
    design = validate(json.loads(path.read_text()), resolved)
    _, evidence = compose_with_evidence(design, resolved)
    selection = evidence["candidate_selection"]
    assert selection["proved_structure_count"] >= 2
    assert selection["proved_candidate_count"] >= 2
    assert selection["selected_selection_key"] == min(
        candidate["selection_key"] for candidate in selection["proved_candidates"]
    )
    rejected = selection["best_rejected_candidate"]
    if selection["proved_candidate_count"] > 1:
        assert rejected is not None
        assert (
            rejected["selection_key"]
            == sorted(candidate["selection_key"] for candidate in selection["proved_candidates"])[1]
        )
    passes = {
        (attempt["seed"], attempt["round"])
        for attempt in evidence["layout_attempts"]
        if attempt["result"] == "pass"
    }
    assert all(
        (candidate["seed"], candidate["round"]) in passes
        for candidate in selection["proved_candidates"]
    )


def test_measured_row_compaction_and_stagger_are_legal_structural_classes() -> None:
    resolved = assets()
    for stem, label in (
        ("a1_multiple", "precedence-staggered-band"),
        ("three_amplifier_one_band", "functional-row-compaction"),
    ):
        path = ROOT / f"fixtures/m2h2/interaction/i3/{stem}.json"
        design = validate(json.loads(path.read_text()), resolved)
        plan = semantic_plan(design, resolved)
        variants = fragment_variants(design, resolved, plan)
        seeds = pack_fragment_candidates(plan, variants)
        if not any(seed.attempts[-1] == label for seed in seeds):
            print(
                json.dumps(
                    {
                        "missing_structural_class": stem,
                        "seeds": [
                            {
                                "attempt": seed.attempts[-1],
                                "placements": [
                                    {
                                        "id": p.fragment.block.id,
                                        "kind": p.fragment.block.kind,
                                        "unused": p.fragment.block.unused,
                                        "envelope": p.envelope,
                                        "delta": p.delta,
                                    }
                                    for p in seed.fragments
                                ],
                            }
                            for seed in seeds
                        ],
                    }
                )
            )
        assert any(seed.attempts[-1] == label for seed in seeds)
        alternative = next(seed for seed in seeds if seed.attempts[-1] == label)
        _, _, canonical, _, metrics = _assemble_candidate(
            design, resolved, plan, alternative, retry=0
        )
        assert canonical
        assert metrics["final_content_width_mm"] <= 210
        assert metrics["final_content_height_mm"] <= 140


def test_emission_rejects_changed_certified_design_or_assets(tmp_path) -> None:
    path = ROOT / "fixtures/m2h2/interaction/i2/internal_2.json"
    resolved = assets()
    design = validate(json.loads(path.read_text()), resolved)
    scene, evidence = compose_with_evidence(design, resolved)
    assert evidence["obligation_certificate"]["candidate_input_policy_sha256"]
    changed = copy.deepcopy(design)
    changed["components"][0]["value"] = "changed after certification"
    output = tmp_path / "changed_design"
    with pytest.raises(InputError, match="SCENE_CERTIFICATE_STALE"):
        emit(changed, resolved, scene, output)
    assert not output.exists()
    changed_assets = dict(resolved)
    changed_assets["Device:R"] = resolved["Device:R"].__class__(
        resolved["Device:R"].library_id,
        resolved["Device:R"].definition + " ",
        resolved["Device:R"].units,
        resolved["Device:R"].bodies,
    )
    output = tmp_path / "changed_assets"
    with pytest.raises(InputError, match="SCENE_CERTIFICATE_STALE"):
        emit(design, changed_assets, scene, output)
    assert not output.exists()
    scene.metrics["body_overlap_count"] = 1
    output = tmp_path / "changed_proof"
    with pytest.raises(InputError, match="SCENE_CERTIFICATE_STALE"):
        emit(design, resolved, scene, output)
    assert not output.exists()


def test_exact_content_spread_boundaries_are_hard_and_inclusive() -> None:
    block = BlockPlan("spread", "rc", (), frozenset(), ())

    def candidate(width: int, height: int) -> FragmentVariant:
        return FragmentVariant(
            f"spread.{width}.{height}",
            block,
            MappingProxyType({}),
            MappingProxyType({}),
            MappingProxyType({}),
            (),
            (),
            (),
            (),
            (),
            (0, 0, width, height),
            frozenset(),
            content_envelope=(0, 0, width, height),
        )

    plan = SemanticPlan((block,), (), {}, ())
    assert pack_fragment_candidates(
        plan,
        {block.id: (candidate(MAX_CONTENT_WIDTH, 10 * PITCH),)},
    )
    assert pack_fragment_candidates(
        plan,
        {block.id: (candidate(10 * PITCH, MAX_CONTENT_HEIGHT),)},
    )
    with pytest.raises(InputError, match="PACK_BUDGET_EXHAUSTED"):
        pack_fragment_candidates(
            plan,
            {block.id: (candidate(MAX_CONTENT_WIDTH + 1, 10 * PITCH),)},
        )
    with pytest.raises(InputError, match="PACK_BUDGET_EXHAUSTED"):
        pack_fragment_candidates(
            plan,
            {block.id: (candidate(10 * PITCH, MAX_CONTENT_HEIGHT + 1),)},
        )


def test_canonical_conductor_length_exact_boundary_passes_and_above_fails() -> None:
    block = BlockPlan("wire", "rc", (), frozenset(), ())

    def packing(total_length: int) -> tuple[SemanticPlan, Packing]:
        final_leg = total_length - 175_000_000
        wires = (
            ((0, 0), (100_000_000, 0)),
            ((100_000_000, 0), (100_000_000, 75_000_000)),
            ((100_000_000, 75_000_000), (100_000_000 - final_leg, 75_000_000)),
        )
        occupied = tuple(
            GeometryItem(
                f"wire.{index}",
                "wire",
                block.id,
                (
                    min(first[0], second[0]),
                    min(first[1], second[1]),
                    max(first[0], second[0]),
                    max(first[1], second[1]),
                ),
                ("N",),
            )
            for index, (first, second) in enumerate(wires)
        )
        reservations = tuple(
            Reservation(
                f"reservation.{item.id}",
                "exclusive",
                block.id,
                "wire",
                item.rect,
                "N",
                1,
            )
            for item in occupied
        )
        fragment = FragmentVariant(
            f"wire.{total_length}",
            block,
            MappingProxyType({}),
            MappingProxyType({}),
            MappingProxyType({}),
            wires,
            ("N",) * len(wires),
            (("N", wires[0][0]), ("N", wires[-1][1])),
            (),
            (),
            (0, 0, 100_000_000, 75_000_000),
            frozenset(),
            occupied_geometry=occupied,
            reservations=reservations,
            wire_provenance=(("first",), ("second",), ("third",)),
        )
        placed = _place(fragment, 20 * PITCH, 23 * PITCH)
        plan = SemanticPlan(
            (block,),
            (),
            {},
            (),
            presentation_nets=(
                PresentationNet("N", (), (block.id,), "presentation", False, False, ()),
            ),
        )
        return plan, Packing((placed,), ("synthetic-boundary",))

    design = {
        "id": "canonical-length-boundary",
        "name": "Canonical length boundary",
        "components": [],
        "nets": [],
        "relationships": [],
        "power_assertions": [],
    }
    exact_plan, exact_packing = packing(250_000_000)
    _, _, trees, _, _ = _assemble_candidate(design, {}, exact_plan, exact_packing, retry=0)
    assert [tree.length for tree in trees] == [250_000_000]

    above_plan, above_packing = packing(250_000_001)
    with pytest.raises(ConductorLengthConflict) as caught:
        _assemble_candidate(design, {}, above_plan, above_packing, retry=0)
    assert caught.value.actual == 250_000_001
    assert caught.value.limit == 250_000_000


def test_internal_reference_net_rename_preserves_geometry_and_search_decisions() -> None:
    path = ROOT / "fixtures/m2h2/interaction/i2/internal_2.json"
    resolved = assets()
    original = validate(json.loads(path.read_text()), resolved)

    def renamed(value):
        if isinstance(value, dict):
            return {key: renamed(item) for key, item in value.items()}
        if isinstance(value, list):
            return [renamed(item) for item in value]
        return "MIDREF" if value == "VREF" else value

    renamed_design = validate(renamed(copy.deepcopy(json.loads(path.read_text()))), resolved)
    original_scene, original_evidence = compose_with_evidence(original, resolved)
    renamed_scene, renamed_evidence = compose_with_evidence(renamed_design, resolved)

    assert original_scene.positions == renamed_scene.positions
    assert original_scene.wires == renamed_scene.wires
    assert [item["variant"] for item in original_evidence["variants"]] == [
        item["variant"] for item in renamed_evidence["variants"]
    ]
    assert original_evidence["packing_attempts"] == renamed_evidence["packing_attempts"]
    assert (
        original_evidence["candidate_selection"]["selected_seed"]
        == renamed_evidence["candidate_selection"]["selected_seed"]
    )
    assert [(item["strategy"], item["segments"]) for item in original_evidence["routes"]] == [
        (item["strategy"], item["segments"]) for item in renamed_evidence["routes"]
    ]


def test_typed_repairs_use_structured_conflict_fields_and_change_state() -> None:
    resolved = assets()

    passive_path = ROOT / "fixtures/m2h2/interaction/i1/d2_b1.json"
    passive_design = validate(json.loads(passive_path.read_text()), resolved)
    passive_plan = semantic_plan(passive_design, resolved)
    passive_variants = fragment_variants(passive_design, resolved, passive_plan)
    passive_seed = pack_fragment_candidates(passive_plan, passive_variants)[0]

    precedence = passive_plan.precedence[0]
    order_conflict = PlacementConflict(
        "precedence_violation",
        precedence.id,
        precedence.source_fragment,
        precedence.target_fragment,
        -1,
        precedence.minimum_x_separation,
    )
    order_conflict.args = ("this diagnostic is intentionally not parseable",)
    order_repaired, order_decision = _structural_repack(
        passive_design, resolved, passive_plan, passive_seed, order_conflict
    )
    assert order_decision["kind"] == "precedence_violation"
    assert tuple((item.fragment.id, item.delta) for item in order_repaired.fragments) != tuple(
        (item.fragment.id, item.delta) for item in passive_seed.fragments
    )

    span = passive_plan.local_spans[0]

    def fragment_for(terminal: tuple[str, str]) -> str:
        return next(
            block.id
            for block in passive_plan.blocks
            if any(terminal in port.terminals for port in block.ports)
        )

    span_conflict = PlacementConflict(
        "local_span_violation",
        span.id,
        fragment_for(span.first),
        fragment_for(span.second),
        span.maximum + 1,
        span.maximum,
    )
    span_conflict.args = ("also intentionally not parseable",)
    span_repaired, span_decision = _structural_repack(
        passive_design, resolved, passive_plan, passive_seed, span_conflict
    )
    assert span_decision["kind"] == "local_span_violation"
    assert tuple((item.fragment.id, item.delta) for item in span_repaired.fragments) != tuple(
        (item.fragment.id, item.delta) for item in passive_seed.fragments
    )

    reference_path = ROOT / "fixtures/m2h2/interaction/i2/internal_2.json"
    reference_design = validate(json.loads(reference_path.read_text()), resolved)
    reference_plan = semantic_plan(reference_design, resolved)
    reference_variants = fragment_variants(reference_design, resolved, reference_plan)
    reference_seed = pack_fragment_candidates(reference_plan, reference_variants)[0]
    reference_net = next(
        net.id for net in reference_plan.presentation_nets if net.internally_generated
    )
    blocked_gateway = next(
        gateway
        for item in reference_seed.fragments
        for gateway in item.gateways
        if gateway.net == reference_net
    )
    blocked = RouteBlockedConflict(reference_net, (blocked_gateway.id,), 17, 23)
    blocked.args = ("no net= token exists in this diagnostic anymore",)
    grown, growth_decision = _reservation_growth_repack(reference_plan, reference_seed, blocked, 0)
    assert growth_decision["net"] == reference_net
    assert growth_decision["growth_nm"] == PITCH
    assert tuple((item.fragment.id, item.delta) for item in grown.fragments) != tuple(
        (item.fragment.id, item.delta) for item in reference_seed.fragments
    )

    detour = ConductorLengthConflict(reference_net, 250_000_001, 100_000_000, 150_000_001)
    detour.args = ("length conflict without a parseable net token",)
    substituted, substitution = _substitution_repack(
        reference_plan, reference_variants, reference_seed, detour, 0
    )
    assert substitution["net"] == reference_net
    assert substitution["from"] != substitution["to"]
    assert tuple((item.fragment.id, item.delta) for item in substituted.fragments) != tuple(
        (item.fragment.id, item.delta) for item in reference_seed.fragments
    )
