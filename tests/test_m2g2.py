"""Generic M2g2 contracts; fixtures here are intentionally hand-authored geometry."""

from __future__ import annotations

from dataclasses import replace
import json
from types import MappingProxyType

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2_geometry import (
    AccessWindow,
    ConductorSegment,
    Gateway,
    GeometryItem,
    ProtectedPath,
    Reservation,
    canonical_conductor_tree,
    conductor_reachable,
    content_envelope,
    envelope_contains,
    segment_is_admissible,
)
from ai_kicad.m2_compose import LayoutBudgetError, compose_with_evidence
from ai_kicad.m2_fragments import FragmentVariant, PortAnchor, fragment_variants
from ai_kicad.m2_pack import (
    CANDIDATE_BUDGET,
    ENVELOPE_OUTER_PADDING,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    pack_fragment_candidates,
    pack_fragments,
)
from ai_kicad.m2_route import (
    MAX_ROUTE_STATES_PER_TAP,
    MAX_TAPS_PER_ATTACHMENT,
    MAX_TRACKS_PER_SIDE,
)
from ai_kicad.m2_semantics import (
    BlockPlan,
    SemanticEdge,
    SemanticPlan,
    SemanticPort,
    semantic_plan,
)
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate


P = 1_270_000
PROBES = ROOT / "fixtures/m2g2/probes"


def _segment(a, b, *, net="N", owner="tree.N", provenance=("manual",)):
    return ConductorSegment(a, b, net, owner, provenance)


def _block(block_id, kind="rc", *, role="signal_out"):
    port = SemanticPort(f"{block_id}.port", block_id, "N", role, ((block_id, "1"),))
    return BlockPlan(block_id, kind, (), frozenset(), (port,))


def _variant(block, variant_id, envelope, gateway, reservations=()):
    return FragmentVariant(
        variant_id,
        block,
        MappingProxyType({}),
        MappingProxyType({}),
        MappingProxyType({}),
        (),
        (),
        (),
        (),
        (PortAnchor(block.ports[0], gateway.point, gateway.escape_direction),),
        envelope,
        frozenset(),
        reservations=reservations,
        gateways=(gateway,),
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("split", [False, True])
def test_unsplit_t_graph_is_subdivision_order_and_direction_invariant(reverse, split):
    trunk = [_segment((0, 0), (40, 0))]
    if split:
        trunk = [_segment((0, 0), (10, 0)), _segment((10, 0), (40, 0))]
    branches = [_segment((10, 0), (10, 10)), _segment((30, 0), (30, -10))]
    wires = trunk + branches
    if reverse:
        wires = [replace(wire, start=wire.end, end=wire.start) for wire in reversed(wires)]
    tree = canonical_conductor_tree(wires, junctions={(10, 0), (30, 0)})
    for first in ((0, 0), (10, 10), (30, -10), (40, 0)):
        for second in ((0, 0), (10, 10), (30, -10), (40, 0)):
            assert conductor_reachable(tree, first, second)


def test_branch_at_end_and_four_way_actual_degree_junctions():
    wires = [
        _segment((-10, 0), (10, 0)),
        _segment((0, -10), (0, 10)),
        _segment((10, 0), (10, 10)),
    ]
    tree = canonical_conductor_tree(wires, junctions={(0, 0), (10, 0)})
    assert tree.degree[(0, 0)] == 4
    assert tree.degree[(10, 0)] == 2  # an endpoint bend is not a branch dot
    assert tree.junctions == ((0, 0),)


def test_observer_negative_label_only_and_missing_junction_controls():
    wires = [_segment((0, 0), (10, 0)), _segment((20, 0), (30, 0))]
    tree = canonical_conductor_tree(wires, junctions=set())
    assert not conductor_reachable(tree, (0, 0), (30, 0), labels=(("N", (10, 0)), ("N", (20, 0))))
    crossing = [_segment((0, 0), (20, 0)), _segment((10, -10), (10, 10))]
    without_dot = canonical_conductor_tree(crossing, junctions=set())
    assert not conductor_reachable(without_dot, (0, 0), (10, 10))
    with_dot = canonical_conductor_tree(crossing, junctions={(10, 0)})
    assert conductor_reachable(with_dot, (0, 0), (10, 10))


def test_canonical_tree_deduplicates_overlap_and_preserves_provenance():
    first = canonical_conductor_tree(
        [
            _segment((0, 0), (20, 0), provenance=("a",)),
            _segment((20, 0), (0, 0), provenance=("b",)),
            _segment((5, 0), (15, 0), provenance=("c",)),
            _segment((10, 0), (10, 10), provenance=("d",)),
        ],
        junctions={(10, 0)},
    )
    second = canonical_conductor_tree(
        [
            _segment((0, 0), (10, 0), provenance=("a", "b", "c")),
            _segment((10, 0), (20, 0), provenance=("a", "b", "c")),
            _segment((10, 10), (10, 0), provenance=("d",)),
        ],
        junctions={(10, 0)},
    )
    assert first.geometry_signature == second.geometry_signature
    assert first.length == second.length == 30
    assert first.junctions == ((10, 0),)
    assert {origin for segment in first.segments for origin in segment.provenance} == {
        "a",
        "b",
        "c",
        "d",
    }


def test_final_text_envelope_and_exact_accounting():
    items = (
        GeometryItem("body", "symbol", "owner", (-2, -3, 7, 5)),
        GeometryItem("value", "text", "owner", (-8, -7, 14, -4)),
        GeometryItem("feedback", "wire", "owner", (0, 0, 17, 0)),
        GeometryItem("source", "glyph", "flag", (17, -2, 20, 2)),
    )
    envelope = content_envelope(items)
    assert envelope == (-8, -7, 20, 5)
    assert envelope_contains(envelope, items)
    assert envelope_contains((0, 0, MAX_CONTENT_WIDTH, MAX_CONTENT_HEIGHT), (), exact_limit=True)
    assert not envelope_contains(
        (0, 0, MAX_CONTENT_WIDTH - 1, MAX_CONTENT_HEIGHT),
        (GeometryItem("edge", "text", "owner", (0, 0, MAX_CONTENT_WIDTH, 1)),),
    )


def test_late_outward_text_move_is_reservation_growth():
    reservation = Reservation("local", "exclusive", "owner", "text", (0, 0, 20, 20))
    final_text = GeometryItem("field", "text", "owner", (2, -1, 18, 3))
    assert not reservation.contains(final_text.rect)
    assert reservation.outward_growth(final_text.rect) == (0, 1, 0, 0)


def test_final_text_slot_alternate_fits_exact_bound():
    wire = GeometryItem("wire", "wire", "local", (0, 9, 20, 11))
    default = GeometryItem("field.default", "text", "local", (6, 8, 14, 12))
    alternate = GeometryItem("field.alternate", "text", "local", (6, 1, 14, 5))
    reservation = Reservation("local", "exclusive", "local", "content", (0, 0, 20, 11))
    assert not segment_is_admissible(
        (0, 10),
        (20, 10),
        (),
        (Reservation("default", "exclusive", "field", "text", default.rect),),
        net="N",
        owner="wire",
    )
    assert reservation.contains(alternate.rect)
    assert content_envelope((wire, alternate)) == (0, 1, 20, 11)
    assert not reservation.contains(default.rect)


def test_route_demand_turns_rectangle_fit_into_reserved_repack():
    source = _block("source")
    target = _block("target", role="signal_in")
    plan = SemanticPlan(
        (source, target),
        (SemanticEdge("signal", "source", "target", "N", ("manual",)),),
        {},
        ("source", "target"),
    )
    source_gateway = Gateway(
        source.ports[0].id,
        "N",
        (("source", "1"),),
        "source:N",
        (20 * P, 10 * P),
        "right",
        ((20 * P, 10 * P), (21 * P, 10 * P)),
        frozenset({"right"}),
        (),
    )
    target_gateway = Gateway(
        target.ports[0].id,
        "N",
        (("target", "1"),),
        "target:N",
        (0, 10 * P),
        "left",
        ((0, 10 * P), (-P, 10 * P)),
        frozenset({"left"}),
        (),
    )
    bare = _variant(source, "source.bare", (0, 0, 20 * P, 20 * P), source_gateway)
    reserved = replace(
        bare,
        id="source.reserved",
        envelope=(0, 0, 21 * P, 20 * P),
        packing_envelope=(0, 0, 21 * P, 20 * P),
        reservations=(
            Reservation(
                "trunk",
                "channel",
                "source",
                "route_demand",
                (20 * P, 9 * P, 21 * P, 11 * P),
                "N",
                1,
            ),
        ),
    )
    sink = _variant(target, "target.v0", (0, 0, 20 * P, 20 * P), target_gateway)
    initial = pack_fragment_candidates(plan, {"source": (bare,), "target": (sink,)})[0]
    repaired = pack_fragment_candidates(plan, {"source": (reserved,), "target": (sink,)})[0]
    assert (
        next(item for item in initial.fragments if item.fragment.block.id == "source").envelope[2]
        < next(item for item in repaired.fragments if item.fragment.block.id == "source").envelope[
            2
        ]
    )
    assert pack_fragments(plan, {"source": (reserved,), "target": (sink,)})


def test_universal_gateway_escape_and_protected_path_ownership():
    gateway = Gateway(
        "g",
        "N",
        (("u", "3"),),
        "island.N",
        (0, 0),
        "right",
        ((0, 0), (10, 0)),
        frozenset({"right", "up", "down"}),
        (AccessWindow((10, -2, 12, 2), frozenset({"right"}), "N"),),
    )
    body = Reservation("support", "exclusive", "owner", "body", (2, 2, 8, 8))
    path = ProtectedPath(
        "feedback",
        ("loop",),
        "fragment",
        (("u", "1"), ("u", "2")),
        "N",
        "island.N",
        (),
        (_segment((20, 0), (30, 0), owner="fragment"),),
        (Reservation("feedback.corridor", "exclusive", "fragment", "protected", (19, -1, 31, 1)),),
        (AccessWindow((24, -1, 26, 1), frozenset({"up", "down"}), "N"),),
        80_000_000,
    )
    assert gateway.escape_polyline[1] == (10, 0)
    assert segment_is_admissible((10, 0), (10, 10), (body,), (), net="N", owner="tree.N")
    assert not segment_is_admissible((0, 5), (10, 5), (body,), (), net="N", owner="tree.N")
    assert not segment_is_admissible(
        (18, 0), (32, 0), (), path.corridors, net="OTHER", owner="tree.OTHER"
    )
    assert not segment_is_admissible((18, 0), (32, 0), (), path.corridors, net="N", owner="tree.N")
    assert segment_is_admissible(
        (25, -5),
        (25, 0),
        (),
        path.corridors,
        net="N",
        owner="tree.N",
        tap=(25, 0),
        tap_windows=path.tap_windows,
    )


@pytest.mark.parametrize("support_y", [2, -8])
def test_universal_escape_single_and_multi_sink_with_blocked_entry(support_y):
    support = Reservation(
        "support", "exclusive", "support", "body", (2, support_y, 8, support_y + 6)
    )
    escape = ((0, 0), (10, 0))
    assert all(
        segment_is_admissible(a, b, (support,), (), net="N", owner="tree.N")
        for a, b in zip(escape, escape[1:])
    )
    assert segment_is_admissible((10, 0), (20, 0), (support,), (), net="N", owner="tree.N")
    assert segment_is_admissible((10, 0), (10, 10), (support,), (), net="N", owner="tree.N")
    blocked_entry = Reservation("entry", "exclusive", "other", "body", (14, 4, 18, 8))
    assert not segment_is_admissible(
        (16, 0), (16, 10), (blocked_entry,), (), net="N", owner="tree.N"
    )


def test_branch_feasibility_rejects_nearest_and_accepts_reserved_tap():
    keepout = Reservation("text", "exclusive", "label", "text", (4, -2, 8, 2))
    channel = AccessWindow((11, -1, 13, 1), frozenset({"up", "down"}), "N")
    assert not segment_is_admissible(
        (6, -5), (6, 0), (keepout,), (), net="N", owner="tree.N", tap=(6, 0)
    )
    assert segment_is_admissible(
        (12, -5),
        (12, 0),
        (),
        (Reservation("protected", "exclusive", "local", "protected", (10, -1, 14, 1)),),
        net="N",
        owner="tree.N",
        tap=(12, 0),
        tap_windows=(channel,),
    )


def test_hard_feasibility_selects_clear_larger_variant():
    source = _block("source")
    target = _block("target", role="signal_in")
    plan = SemanticPlan(
        (source, target),
        (SemanticEdge("signal", "source", "target", "N", ("manual",)),),
        {},
        ("source", "target"),
    )
    bad_gateway = Gateway(
        source.ports[0].id,
        "N",
        (("source", "1"),),
        "source:N",
        (10 * P, 15 * P),
        "down",
        ((10 * P, 15 * P), (10 * P, 16 * P)),
        frozenset({"down"}),
        (),
    )
    good_gateway = replace(
        bad_gateway,
        anchor=(20 * P, 10 * P),
        escape_direction="right",
        escape_polyline=((20 * P, 10 * P), (21 * P, 10 * P)),
        approach_directions=frozenset({"right"}),
    )
    blocker = Reservation(
        "support", "exclusive", "support", "body", (9 * P, 15 * P, 11 * P, 20 * P)
    )
    bad = _variant(source, "source.small-blocked", (0, 0, 20 * P, 20 * P), bad_gateway, (blocker,))
    good = _variant(source, "source.large-clear", (0, 0, 21 * P, 20 * P), good_gateway, (blocker,))
    target_gateway = Gateway(
        target.ports[0].id,
        "N",
        (("target", "1"),),
        "target:N",
        (0, 10 * P),
        "left",
        ((0, 10 * P), (-P, 10 * P)),
        frozenset({"left"}),
        (),
    )
    sink = _variant(target, "target.v0", (0, 0, 20 * P, 20 * P), target_gateway)
    selected = pack_fragments(plan, {"source": (bad, good), "target": (sink,)})
    assert (
        next(item.fragment.id for item in selected.fragments if item.fragment.block.id == "source")
        == "source.large-clear"
    )


def test_fanout_order_preserves_only_real_precedence():
    blocks = tuple(_block(name) for name in ("source", "a", "b", "c", "a.next", "b.next"))
    edges = (
        SemanticEdge("signal", "source", "a", "A", ()),
        SemanticEdge("signal", "source", "b", "B", ()),
        SemanticEdge("signal", "source", "c", "C", ()),
        SemanticEdge("signal", "a", "a.next", "AA", ()),
        SemanticEdge("signal", "b", "b.next", "BB", ()),
        SemanticEdge("power", "c", "a", "RAIL", ()),
        SemanticEdge("reference", "b", "c", "RETURN", ()),
    )
    plan = SemanticPlan(blocks, edges, {}, tuple(block.id for block in blocks))
    variants = {
        block.id: (
            _variant(
                block,
                block.id + ".v0",
                (0, 0, 12 * P, 8 * P),
                Gateway(
                    block.ports[0].id,
                    "N",
                    ((block.id, "1"),),
                    block.id + ":N",
                    (12 * P, 4 * P),
                    "right",
                    ((12 * P, 4 * P), (13 * P, 4 * P)),
                    frozenset({"right"}),
                    (),
                ),
            ),
        )
        for block in blocks
    }
    packing = pack_fragment_candidates(plan, variants)[0]
    positions = {item.fragment.block.id: item.envelope[:2] for item in packing.fragments}
    assert positions["a"][0] < positions["a.next"][0]
    assert positions["b"][0] < positions["b.next"][0]
    assert len({positions[name][1] for name in ("a", "b", "c")}) > 1


def test_all_m2g2_probes_and_frozen_expectations_validate():
    manifest = json.loads((PROBES / "manifest.json").read_text())
    assert [case["id"] for case in manifest["cases"]] == [
        "dual_regulator_mixed_loads",
        "passive_two_level_fanout",
        "timer_split_filtered_gain_indicator",
        "passive_two_level_fanout_long_fields",
        "timer_split_filtered_gain_indicator_unit_exchange",
    ]
    for case in manifest["cases"]:
        design = validate(json.loads((PROBES / case["file"]).read_text()), assets())
        assert design["id"] == case["design_id"]
        expected = json.loads((PROBES / case["expectations"]).read_text())
        actual = {
            net["id"]: sorted(tuple(member) for member in net["members"]) for net in design["nets"]
        }
        assert actual == {
            key: [tuple(member) for member in value]
            for key, value in expected["partitions"].items()
        }
        assert expected["path_obligations"]
        assert expected["frozen_before_layout_tuning"] is True


def test_probe_topologies_are_not_simplified_by_stress_variants():
    manifest = json.loads((PROBES / "manifest.json").read_text())
    loaded = {
        case["id"]: json.loads((PROBES / case["file"]).read_text()) for case in manifest["cases"]
    }
    long = loaded["passive_two_level_fanout_long_fields"]
    base = loaded["passive_two_level_fanout"]

    def normalize(value):
        return json.loads(json.dumps(value).replace("REQUIRED_NET_LABEL20", "BRANCH_B"))

    assert normalize(long["nets"]) == base["nets"]
    assert normalize(long["relationships"]) == base["relationships"]
    assert any(len(component["value"]) == 24 for component in long["components"])
    exchanged = loaded["timer_split_filtered_gain_indicator_unit_exchange"]
    timer = loaded["timer_split_filtered_gain_indicator"]
    assert {r["id"] for r in exchanged["relationships"]} == {
        r["id"] for r in timer["relationships"]
    }
    assert {n["id"] for n in exchanged["nets"]} == {n["id"] for n in timer["nets"]}


@pytest.mark.parametrize(
    ("fixture", "kind"),
    [
        ("dual_regulator_mixed_loads", "power_stage"),
        ("timer_split_filtered_gain_indicator", "package_power"),
        ("timer_split_filtered_gain_indicator", "timer"),
        ("passive_two_level_fanout", "rc"),
    ],
)
def test_multiple_support_types_expose_bounded_local_substitutions(fixture, kind):
    design = validate(json.loads((PROBES / f"{fixture}.json").read_text()), assets())
    plan = semantic_plan(design, assets())
    inventory = fragment_variants(design, assets(), plan)
    relevant = [inventory[block.id] for block in plan.blocks if block.kind == kind]
    assert relevant
    assert all(2 <= len(choices) <= 8 for choices in relevant)
    for choices in relevant:
        assert len({choice.block.id for choice in choices}) == 1
        assert len({tuple(sorted(choice.positions)) for choice in choices}) == 1


def test_typed_identity_ownership_and_gateway_witnesses_are_exact():
    design = validate(
        json.loads((PROBES / "timer_split_filtered_gain_indicator.json").read_text()),
        assets(),
    )
    plan = semantic_plan(design, assets())
    terminal_nets = {
        tuple(member): net["id"] for net in design["nets"] for member in net["members"]
    }
    occurrences = [occurrence for block in plan.blocks for occurrence in block.occurrences]
    assert len(occurrences) == len(set(occurrences)) == len(plan.owners)
    for block_id, choices in fragment_variants(design, assets(), plan).items():
        for gateway in choices[0].gateways:
            gateway.validate(terminal_nets)
            assert gateway.island.startswith(block_id + ":")
        assert all(obligation.owner == block_id for obligation in choices[0].obligations)


def test_bounded_failure_reports_search_and_proven_infeasibility(monkeypatch):
    block = _block("oversize")
    gateway = Gateway(
        block.ports[0].id,
        "N",
        (("oversize", "1"),),
        "oversize:N",
        (0, 0),
        "right",
        ((0, 0), (P, 0)),
        frozenset({"right"}),
        (),
    )
    too_large = _variant(
        block,
        "oversize.v0",
        (0, 0, MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING + 1, 10 * P),
        gateway,
    )
    with pytest.raises(InputError, match="PACK_SPREAD_INFEASIBLE"):
        pack_fragment_candidates(
            SemanticPlan((block,), (), {}, (block.id,)), {block.id: (too_large,)}
        )

    design = validate(json.loads((PROBES / "passive_two_level_fanout.json").read_text()), assets())
    import ai_kicad.m2_compose as compose_module

    monkeypatch.setattr(
        compose_module,
        "_assemble_candidate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(InputError("ROUTE_BLOCKED: net=N")),
    )
    with pytest.raises(LayoutBudgetError) as caught:
        compose_with_evidence(design, assets())
    assert len(caught.value.attempts) <= 32
    assert "LAYOUT_BUDGET_EXHAUSTED" in str(caught.value)
    assert any(item["result"] == "repeat_state_skipped" for item in caught.value.attempts)
    assert (
        CANDIDATE_BUDGET,
        MAX_TRACKS_PER_SIDE,
        MAX_TAPS_PER_ATTACHMENT,
        MAX_ROUTE_STATES_PER_TAP,
    ) == (8, 8, 32, 4096)


def test_metamorphic_tree_and_probe_unit_exchange_stability():
    first = canonical_conductor_tree(
        [_segment((0, 0), (20, 0)), _segment((10, 0), (10, 10))],
        junctions={(10, 0)},
    )
    second = canonical_conductor_tree(
        [_segment((10, 10), (10, 0)), _segment((20, 0), (10, 0)), _segment((10, 0), (0, 0))],
        junctions={(10, 0)},
    )
    assert (first.geometry_signature, first.length, first.bends, first.degree) == (
        second.geometry_signature,
        second.length,
        second.bends,
        second.degree,
    )
    base = validate(
        json.loads((PROBES / "timer_split_filtered_gain_indicator.json").read_text()), assets()
    )
    exchanged = validate(
        json.loads((PROBES / "timer_split_filtered_gain_indicator_unit_exchange.json").read_text()),
        assets(),
    )
    base_plan, exchanged_plan = semantic_plan(base, assets()), semantic_plan(exchanged, assets())
    assert [(edge.kind, edge.net) for edge in base_plan.edges] == [
        (edge.kind, edge.net) for edge in exchanged_plan.edges
    ]
    assert sorted(block.kind for block in base_plan.blocks) == sorted(
        block.kind for block in exchanged_plan.blocks
    )


def test_invalid_gateway_terminal_identity_is_rejected():
    with pytest.raises(InputError, match="GATEWAY_TERMINAL_IDENTITY"):
        Gateway(
            "bad",
            "N",
            (),
            "island.N",
            (0, 0),
            "right",
            ((0, 0), (1, 0)),
            frozenset({"right"}),
            (),
        ).validate({("u", "3"): "N"})
