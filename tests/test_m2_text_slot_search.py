"""Bounded, independently measured M2 text-slot search contracts."""

from dataclasses import replace

from ai_kicad.m2a import PITCH
from ai_kicad.m2b import Draft, choose_text_slots
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import pack_fragment_candidates
from ai_kicad.m2_semantics import BlockPlan, SemanticPlan


def test_alternate_passive_text_slot_is_distinct_and_deterministic() -> None:
    design = {
        "components": [
            {"id": "passive", "asset": "Device:R", "refdes": "R1", "value": "10k"}
        ]
    }

    def make_draft() -> Draft:
        return Draft(
            design,
            {},
            {("passive", 1): (30 * PITCH, 30 * PITCH)},
            {("passive", 1): 0},
            [],
            [],
            [],
            [],
            {("passive", 1): (38 * PITCH, 28 * PITCH)},
        )

    baseline = make_draft()
    alternate = make_draft()
    choose_text_slots(design, baseline)
    choose_text_slots(design, alternate, alternate=True)
    assert baseline.text_positions[("passive", 1)] == (38 * PITCH, 28 * PITCH)
    assert alternate.text_positions[("passive", 1)] == (22 * PITCH, 28 * PITCH)
    again = make_draft()
    choose_text_slots(design, again, alternate=True)
    assert again.text_positions == alternate.text_positions


def test_alternate_text_slot_falls_back_when_every_other_slot_is_blocked() -> None:
    design = {
        "components": [
            {"id": "passive", "asset": "Device:R", "refdes": "R1", "value": "10k"}
        ]
    }
    # A vertical conductor at every other candidate slot blocks all alternates.
    sx, sy = 30 * PITCH, 30 * PITCH
    xs = (sx - 8 * PITCH, sx + 12 * PITCH, sx - 12 * PITCH,
          sx + 16 * PITCH, sx - 16 * PITCH, sx + 20 * PITCH,
          sx - 20 * PITCH)
    draft = Draft(
        design,
        {},
        {("passive", 1): (sx, sy)},
        {("passive", 1): 0},
        [((x, sy - 20 * PITCH), (x, sy + 20 * PITCH)) for x in xs],
        ["other"] * len(xs),
        [],
        [],
        {("passive", 1): (sx + 8 * PITCH, sy - 2 * PITCH)},
    )
    choose_text_slots(design, draft, alternate=True)
    assert draft.text_positions[("passive", 1)] == (sx + 8 * PITCH, sy - 2 * PITCH)


def test_bounded_pack_search_retains_field_slot_variant() -> None:
    block = BlockPlan("stage", "series", (), frozenset(), ())
    base = FragmentVariant(
        "stage.base", block, {}, {}, {}, (), (), (), (), (),
        (0, 0, 8 * PITCH, 4 * PITCH), frozenset(),
    )
    alternate = replace(
        base,
        id="stage.field",
        rule_id="m2g2.local-text-slot.series.alternate.v1",
        text_positions={("passive", 1): (2 * PITCH, 2 * PITCH)},
    )
    plan = SemanticPlan((block,), (), {}, ())
    candidates = pack_fragment_candidates(plan, {"stage": (base, alternate)})
    assert any(
        any(item.fragment.id == alternate.id for item in candidate.fragments)
        for candidate in candidates
    )
    assert len(candidates) <= 8
