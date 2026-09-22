"""Typed-projection and bounded packing regressions for M2f2."""

from __future__ import annotations

import copy
from dataclasses import replace
import json

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2_compose import compose_layout
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    ENVELOPE_OUTER_PADDING,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    pack_fragments,
)
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, semantic_plan
from ai_kicad.m2b import assets, validate


def _block(block_id: str, kind: str = "rc") -> BlockPlan:
    return BlockPlan(block_id, kind, (), frozenset(), ())


def _edge(kind: str, source: str, target: str, net: str = "N") -> SemanticEdge:
    return SemanticEdge(kind, source, target, net, ())


def _plan(blocks: list[BlockPlan], edges: list[SemanticEdge]) -> SemanticPlan:
    return SemanticPlan(tuple(blocks), tuple(edges), {}, tuple(block.id for block in blocks))


def _variant(block: BlockPlan, width_mm: int, height_mm: int) -> FragmentVariant:
    return FragmentVariant(
        f"{block.id}.v0",
        block,
        {},
        {},
        {},
        (),
        (),
        (),
        (),
        (),
        (0, 0, width_mm * 1_000_000, height_mm * 1_000_000),
        frozenset(),
    )


def _pack(blocks: list[BlockPlan], edges: list[SemanticEdge], sizes: dict[str, tuple[int, int]]):
    plan = _plan(blocks, edges)
    variants = {block.id: (_variant(block, *sizes[block.id]),) for block in blocks}
    return pack_fragments(plan, variants)


def _positions(packing) -> dict[str, tuple[int, int]]:
    return {
        item.fragment.block.id: (item.envelope[0], item.envelope[1]) for item in packing.fragments
    }


def test_signal_progression_remains_serial_left_to_right():
    blocks = [_block("stage.alpha"), _block("stage.beta")]
    packed = _pack(
        blocks,
        [_edge("signal", "stage.alpha", "stage.beta")],
        {
            "stage.alpha": (40, 30),
            "stage.beta": (40, 30),
        },
    )
    positions = _positions(packed)
    assert positions["stage.alpha"][0] < positions["stage.beta"][0]
    assert positions["stage.alpha"][1] == positions["stage.beta"][1]


def test_two_parallel_power_consumers_are_not_a_serial_stage_chain():
    blocks = [
        _block("producer", "power_stage"),
        _block("consumer.alpha", "rc"),
        _block("consumer.beta", "buffer"),
    ]
    edges = [
        _edge("power", "producer", "consumer.alpha", "RAIL"),
        _edge("power", "producer", "consumer.beta", "RAIL"),
    ]
    packed = _pack(
        blocks,
        edges,
        {
            "producer": (60, 30),
            "consumer.alpha": (80, 40),
            "consumer.beta": (80, 40),
        },
    )
    positions = _positions(packed)
    assert positions["consumer.alpha"][1] == positions["consumer.beta"][1]
    assert positions["producer"][1] < positions["consumer.alpha"][1]


def test_three_parallel_consumers_use_the_same_deterministic_fanout_shelf():
    blocks = [_block("source", "power_stage")] + [
        _block(f"load.{name}", kind)
        for name, kind in (("alpha", "rc"), ("beta", "buffer"), ("gamma", "series"))
    ]
    edges = [_edge("power", "source", block.id, "RAIL") for block in blocks[1:]]
    sizes = {"source": (60, 30), **{block.id: (60, 35) for block in blocks[1:]}}
    first = _pack(blocks, edges, sizes)
    second = _pack(blocks, list(reversed(edges)), sizes)
    assert first == second
    positions = _positions(first)
    assert len({positions[block.id][1] for block in blocks[1:]}) == 1


def test_independent_signal_chains_sharing_a_supply_keep_separate_shelves():
    blocks = [_block(name) for name in ("a.in", "a.out", "b.in", "b.out")]
    blocks.append(_block("supply", "power_stage"))
    edges = [
        _edge("signal", "a.in", "a.out", "A"),
        _edge("signal", "b.in", "b.out", "B"),
        _edge("power", "supply", "a.in", "RAIL"),
        _edge("power", "supply", "b.in", "RAIL"),
    ]
    packed = _pack(blocks, edges, {block.id: (35, 25) for block in blocks})
    positions = _positions(packed)
    assert positions["a.in"][0] < positions["a.out"][0]
    assert positions["b.in"][0] < positions["b.out"][0]
    assert positions["a.in"][1] != positions["b.in"][1]


@pytest.mark.parametrize("kind", ["reference", "support"])
def test_reference_and_support_edges_do_not_impose_stage_order(kind):
    blocks = [_block("zeta"), _block("alpha")]
    sizes = {block.id: (35, 25) for block in blocks}
    forward = _pack(blocks, [_edge(kind, "zeta", "alpha")], sizes)
    reverse = _pack(blocks, [_edge(kind, "alpha", "zeta")], sizes)
    assert _positions(forward) == _positions(reverse)


def test_branch_load_uses_source_affinity_without_extending_signal_order():
    source = _block("source", "buffer")
    load = _block("load", "led_branch")
    packed = _pack(
        [source, load],
        [_edge("branch", source.id, load.id, "OUTPUT")],
        {source.id: (70, 45), load.id: (20, 30)},
    )
    positions = _positions(packed)
    assert positions[load.id][0] - positions[source.id][0] <= 72_000_000
    assert positions[load.id][1] - positions[source.id][1] <= 45_000_000


def test_set_like_plan_permutation_preserves_compiler_owned_output():
    blocks = [_block("source", "power_stage"), _block("load.a"), _block("load.b")]
    edges = [
        _edge("power", "source", "load.a", "RAIL"),
        _edge("power", "source", "load.b", "RAIL"),
        _edge("reference", "load.a", "load.b", "RETURN"),
    ]
    sizes = {block.id: (60, 30) for block in blocks}
    assert _pack(blocks, edges, sizes) == _pack(
        list(reversed(blocks)), list(reversed(edges)), sizes
    )


def test_refdes_renaming_preserves_semantic_packing_decisions():
    path = ROOT / "fixtures/m2e1/ir/regulator_parallel_rc.json"
    original = validate(json.loads(path.read_text()), assets())
    renamed = copy.deepcopy(original)
    for component in renamed["components"]:
        prefix = component["refdes"].rstrip("0123456789")
        number = int(component["refdes"][len(prefix) :])
        component["refdes"] = f"{prefix}{number + 40}"
    renamed = validate(renamed, assets())
    original_plan = semantic_plan(original, assets())
    renamed_plan = semantic_plan(renamed, assets())
    assert original_plan.edges == renamed_plan.edges
    assert original_plan.signal_order == renamed_plan.signal_order


def test_oversized_measured_fragment_reports_prospective_spread_conflict():
    block = _block("oversized")
    variant = _variant(block, 20, 20)
    variant = replace(
        variant,
        envelope=(
            0,
            0,
            MAX_CONTENT_WIDTH + ENVELOPE_OUTER_PADDING + 1,
            MAX_CONTENT_HEIGHT + ENVELOPE_OUTER_PADDING + 1,
        ),
    )
    with pytest.raises(InputError, match="PACK_SPREAD_INFEASIBLE.*210x140"):
        pack_fragments(_plan([block], []), {block.id: (variant,)})


def test_known_v4_7_regression_fits_the_unchanged_prospective_gate():
    path = ROOT / "fixtures/m2blind_v4/ir/V4-7.json"
    design = validate(json.loads(path.read_text()), assets())
    scene = compose_layout(design, assets())
    assert scene.metrics["page_margin_pass"] is True
    assert ":pass:measured=" in scene.metrics["packing_attempts"][-1]
