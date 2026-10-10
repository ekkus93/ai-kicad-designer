"""Source-level controls for label-eligible local signal placement."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import (
    _local_signal_neighbor_gap,
    semantic_composition_penalty_breakdown,
)
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    CANDIDATE_BUDGET,
    LEFT,
    Packing,
    _local_signal_proximity_candidates,
    _place,
    _retain_composition_seed_diversity,
)
from ai_kicad.m2_semantics import BlockPlan, PresentationNet, SemanticEdge, SemanticPlan


def test_local_signal_pair_gap_prefers_proximity() -> None:
    blocks = tuple(SimpleNamespace(id=name, kind="stage", ports=()) for name in ("a", "b"))
    net = SimpleNamespace(
        id="net", role="signal", fragments=("a", "b"), explicit_geometry_required=False
    )
    plan = SimpleNamespace(blocks=blocks, edges=(), precedence=(), presentation_nets=(net,))

    def packing(distance: int):
        items = []
        for block, x in zip(blocks, (0, distance), strict=True):
            rect = (x, 0, x + PITCH, PITCH)
            fragment = SimpleNamespace(block=block, positions={})
            items.append(SimpleNamespace(fragment=fragment, content_envelope=rect, envelope=rect))
        return SimpleNamespace(fragments=tuple(items))

    assert (
        semantic_composition_penalty_breakdown(plan, packing(3 * PITCH)).local_signal_neighbor_gap
        == 0
    )
    assert (
        semantic_composition_penalty_breakdown(plan, packing(18 * PITCH)).local_signal_neighbor_gap
        == 15
    )


def test_local_signal_gap_exempts_shared_explicit_and_interface_nets() -> None:
    blocks = tuple(
        SimpleNamespace(id=name, kind="interface" if name == "port" else "stage")
        for name in ("a", "b", "c", "port")
    )
    rects = {
        name: (index * 18 * PITCH, 0, (index * 18 + 1) * PITCH, PITCH)
        for index, name in enumerate(("a", "b", "c", "port"))
    }
    for role, fragments, explicit in (
        ("distributive", ("a", "b"), False),
        ("signal", ("a", "b"), True),
        ("signal", ("a", "b", "c"), False),
        ("signal", ("a", "port"), False),
    ):
        net = SimpleNamespace(
            id="net", role=role, fragments=fragments, explicit_geometry_required=explicit
        )
        plan = SimpleNamespace(blocks=blocks, presentation_nets=(net,))
        assert _local_signal_neighbor_gap(plan, rects) == 0


def test_local_signal_gap_deduplicates_renamed_nets() -> None:
    blocks = tuple(SimpleNamespace(id=name, kind="stage") for name in ("a", "b"))
    rects = {"a": (0, 0, PITCH, PITCH), "b": (18 * PITCH, 0, 19 * PITCH, PITCH)}
    net = SimpleNamespace(
        id="old", role="signal", fragments=("a", "b"), explicit_geometry_required=False
    )
    renamed = SimpleNamespace(
        id="new", role="signal", fragments=("b", "a"), explicit_geometry_required=False
    )
    plan = SimpleNamespace(blocks=blocks, presentation_nets=(net, renamed))
    assert _local_signal_neighbor_gap(plan, rects) == 15


# Measured alternatives retain the ordinary placement and routing proofs.


def _local_fragment(name: str, kind: str = "filter") -> FragmentVariant:
    block = BlockPlan(name, kind, (), frozenset(), ())
    return FragmentVariant(
        f"{name}.variant",
        block,
        {},
        {},
        {},
        (),
        (),
        (),
        (),
        (),
        (0, 0, 8 * PITCH, 4 * PITCH),
        frozenset(),
    )


def _local_layout(*, explicit: bool = False, shared: bool = False, interface: bool = False):
    source = _local_fragment("source")
    target = _local_fragment("target", "interface" if interface else "filter")
    extra = _local_fragment("extra")
    fragments = ("source", "target", "extra") if shared else ("source", "target")
    net = PresentationNet("wire", (), fragments, "signal", False, explicit, ("source",))
    blocks = (source.block, target.block, extra.block)
    plan = SemanticPlan(
        blocks,
        (SemanticEdge("signal", "source", "target", "wire", ()),),
        {},
        (),
        presentation_nets=(net,),
    )
    baseline = Packing(
        (
            _place(source, LEFT + 25 * PITCH, 48 * PITCH),
            _place(target, LEFT + 95 * PITCH, 66 * PITCH),
            _place(extra, LEFT + 60 * PITCH, 85 * PITCH),
        ),
        (),
    )
    return plan, baseline


def test_local_signal_search_moves_downstream_stage_next_to_producer() -> None:
    plan, baseline = _local_layout()
    proposals = _local_signal_proximity_candidates(plan, baseline)
    assert len(proposals) == 1
    assert proposals[0].attempts[-1] == "local-signal-direct-proximity"
    before = {item.fragment.block.id: item.envelope for item in baseline.fragments}
    after = {item.fragment.block.id: item.envelope for item in proposals[0].fragments}
    assert before["source"] == after["source"]
    assert before["extra"] == after["extra"]
    assert after["target"][0] > after["source"][2]
    assert after["target"][0] - after["source"][2] <= 2 * PITCH
    assert after["target"][0] < before["target"][0]
    assert (
        _local_signal_proximity_candidates(
            SemanticPlan(
                tuple(reversed(plan.blocks)),
                plan.edges,
                {},
                (),
                presentation_nets=plan.presentation_nets,
            ),
            baseline,
        )
        == proposals
    )


def test_local_signal_search_exempts_shared_explicit_and_interface_cases() -> None:
    for options in ({"explicit": True}, {"shared": True}, {"interface": True}):
        plan, baseline = _local_layout(**options)
        assert _local_signal_proximity_candidates(plan, baseline) == ()


def test_local_signal_search_skips_already_local_pair() -> None:
    plan, baseline = _local_layout()
    source = baseline.fragments[0]
    target = baseline.fragments[1]
    nearby = _place(target.fragment, source.envelope[2] + PITCH, source.envelope[1])
    nearby_layout = Packing((source, nearby, baseline.fragments[2]), ())
    assert _local_signal_proximity_candidates(plan, nearby_layout) == ()


def test_local_signal_search_avoids_blocked_aligned_corridor() -> None:
    plan, baseline = _local_layout()
    source, target, extra = baseline.fragments
    # A safe nearby lane should be preferred to a distant label-only island
    # when unrelated geometry obstructs the aligned corridor.
    obstructing = _place(extra.fragment, source.envelope[2] + PITCH, source.envelope[1])
    layout = Packing((source, target, obstructing), ())
    options = _local_signal_proximity_candidates(plan, layout)
    assert len(options) == 1
    placed = {item.fragment.block.id: item.envelope for item in options[0].fragments}
    assert placed["source"] == source.envelope
    assert placed["extra"] == obstructing.envelope
    assert placed["target"][0] > placed["source"][2]
    assert placed["target"][0] < target.envelope[0]
    assert placed["target"][3] <= placed["extra"][1] or placed["target"][1] >= placed["extra"][3]


def test_vertical_local_signal_alternative_is_semantically_order_invariant() -> None:
    plan, baseline = _local_layout()
    source, target, extra = baseline.fragments
    obstructing = _place(extra.fragment, source.envelope[2] + PITCH, source.envelope[1])
    layout = Packing((source, target, obstructing), ())
    reordered = SemanticPlan(
        tuple(reversed(plan.blocks)),
        plan.edges,
        {},
        (),
        presentation_nets=plan.presentation_nets,
    )
    assert _local_signal_proximity_candidates(reordered, layout) == (
        _local_signal_proximity_candidates(plan, layout)
    )


def test_local_signal_candidate_survives_eight_seed_retention_cap() -> None:
    plan, baseline = _local_layout()
    candidate = _local_signal_proximity_candidates(plan, baseline)[0]
    # Distinct successful seeds fill the cap; preserve the measured local
    # signal alternative rather than letting shelf variants crowd it out.
    source, target, extra = baseline.fragments
    successful = tuple(
        Packing(
            (
                source,
                _place(target.fragment, target.envelope[0], target.envelope[1] + index * PITCH),
                extra,
            ),
            (f"shelf-{index}",),
        )
        for index in range(CANDIDATE_BUDGET)
    )
    retained = _retain_composition_seed_diversity(successful, (candidate,))
    assert len(retained) <= CANDIDATE_BUDGET
    assert candidate in retained
