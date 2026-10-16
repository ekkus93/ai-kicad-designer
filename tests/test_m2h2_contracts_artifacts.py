"""Independent small falsifications for candidate terminal and graph contracts."""

import copy
import json
from types import MappingProxyType

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2_compose import (
    ConductorLengthConflict,
    _assemble_candidate,
    _reservation_growth_repack,
    _structural_repack,
    _substitution_repack,
    compose_with_evidence,
)
from ai_kicad.m2_fragments import FragmentVariant, fragment_variants
from ai_kicad.m2_geometry import (
    GeometryItem,
    Reservation,
)
from ai_kicad.m2_pack import (
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    Packing,
    _place,
    pack_fragment_candidates,
)
from ai_kicad.m2_route import (
    RouteBlockedConflict,
)
from ai_kicad.m2_semantics import (
    BlockPlan,
    PlacementConflict,
    PresentationNet,
    SemanticPlan,
    semantic_plan,
)
from ai_kicad.m2a import PITCH, ROOT, emit
from ai_kicad.m2b import assets, validate


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
