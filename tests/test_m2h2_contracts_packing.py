"""Independent small falsifications for candidate terminal and graph contracts."""

import json
from types import MappingProxyType

import pytest
from m2h2_contract_helpers import reference_components

from ai_kicad.ir import InputError
from ai_kicad.m2_compose import (
    _assemble_candidate,
    compose_with_evidence,
)
from ai_kicad.m2_fragments import FragmentVariant, PortAnchor, fragment_variants
from ai_kicad.m2_geometry import (
    ConductorSegment,
    Gateway,
)
from ai_kicad.m2_pack import (
    _place,
    pack_fragment_candidates,
)
from ai_kicad.m2_route import (
    RouteLengthBoundConflict,
    _distribution_initial_trees,
    route_between_fragments,
)
from ai_kicad.m2_semantics import (
    BlockPlan,
    PresentationNet,
    SemanticPlan,
    SemanticPort,
    semantic_plan,
)
from ai_kicad.m2a import PITCH, ROOT, Scene, certify_scene_geometry, emit, verify_serialized_scene
from ai_kicad.m2b import assets, validate


def test_local_visible_route_conflict_reports_its_own_limit():
    conflict = RouteLengthBoundConflict("OUT", 150_000_001, limit=150_000_000)

    assert conflict.lower_bound == 150_000_001
    assert conflict.limit == 150_000_000
    assert "limit=150000000" in str(conflict)


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
        "horizontal_median",
        "horizontal_clear_lane",
        "vertical_median",
        "vertical_clear_lane",
        "vertical_side",
    }
    assert len(plans) <= 8
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
