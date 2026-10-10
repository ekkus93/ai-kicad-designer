"""Generic bounded page-centering candidate controls.

These controls prove relative geometry and search-budget invariants only, not
native-render aesthetics or final KiCad acceptance.
"""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import compactness_whitespace_penalties
from ai_kicad.m2_fragments import FragmentVariant
from ai_kicad.m2_pack import (
    CANDIDATE_BUDGET,
    LEFT,
    TOP,
    Packing,
    _centroid_balanced_packing,
    _place,
    _retain_composition_seed_diversity,
)
from ai_kicad.m2_semantics import BlockPlan


def _fragment(block_id: str) -> FragmentVariant:
    block = BlockPlan(block_id, "filter", (), frozenset(), ())
    return FragmentVariant(
        f"{block_id}.variant",
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


def test_balanced_candidate_improves_page_center_without_changing_geometry() -> None:
    first = _fragment("first")
    second = _fragment("second")
    baseline = Packing(
        (
            _place(first, LEFT + 2 * PITCH, TOP + 2 * PITCH),
            _place(second, LEFT + 20 * PITCH, TOP + 2 * PITCH),
        ),
        ("baseline",),
    )
    moved = _centroid_balanced_packing(baseline)
    assert moved is not None
    assert moved.attempts[-1] == "centroid-balanced-page"
    assert compactness_whitespace_penalties(moved)[0] == compactness_whitespace_penalties(
        baseline
    )[0]
    assert compactness_whitespace_penalties(moved)[1] < compactness_whitespace_penalties(
        baseline
    )[1]
    original_spacing = (
        baseline.fragments[1].delta[0] - baseline.fragments[0].delta[0],
        baseline.fragments[1].delta[1] - baseline.fragments[0].delta[1],
    )
    moved_spacing = (
        moved.fragments[1].delta[0] - moved.fragments[0].delta[0],
        moved.fragments[1].delta[1] - moved.fragments[0].delta[1],
    )
    assert original_spacing == moved_spacing
    assert baseline.fragments[0].envelope != moved.fragments[0].envelope


def test_balanced_candidate_is_optional_and_does_not_evict_original_seed() -> None:
    fragment = _fragment("only")
    baseline = Packing((_place(fragment, LEFT + 2 * PITCH, TOP + 2 * PITCH),), ("base",))
    centered = _centroid_balanced_packing(baseline)
    assert centered is not None
    result = _retain_composition_seed_diversity((baseline,), (centered,))
    assert result[0] is baseline
    assert centered in result
    assert len(result) <= CANDIDATE_BUDGET


def test_balanced_candidate_is_idempotent_after_centering() -> None:
    fragment = _fragment("only")
    baseline = Packing((_place(fragment, LEFT + 2 * PITCH, TOP + 2 * PITCH),), ("base",))
    centered = _centroid_balanced_packing(baseline)
    assert centered is not None
    assert _centroid_balanced_packing(centered) is None
