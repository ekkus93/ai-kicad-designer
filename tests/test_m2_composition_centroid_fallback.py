"""Generic rigid-page centering candidates must preserve worksheet clearance."""

from types import SimpleNamespace

from ai_kicad.m2_pack import (
    BOTTOM,
    LEFT,
    RIGHT,
    TOP,
    Packing,
    _best_centroid_balanced_packing,
    _centroid_balanced_packing,
    _place,
)
from ai_kicad.m2a import PITCH


def _fragment(name: str):
    box = (0, 0, 5 * PITCH, 5 * PITCH)
    return SimpleNamespace(
        id=name,
        envelope=box,
        content_envelope=box,
        ports=(),
        reservations=(),
        gateways=(),
        occupied_geometry=(SimpleNamespace(rect=box),),
    )


def _packing(first_x: int, first_y: int, second_x: int, second_y: int) -> Packing:
    return Packing(
        (
            _place(_fragment("first"), first_x * PITCH, first_y * PITCH),
            _place(_fragment("second"), second_x * PITCH, second_y * PITCH),
        ),
        (),
    )


def _balance_error(packing: Packing) -> int:
    boxes = [item.content_envelope for item in packing.fragments]
    center_x = (min(box[0] for box in boxes) + max(box[2] for box in boxes)) // 2
    center_y = (min(box[1] for box in boxes) + max(box[3] for box in boxes)) // 2
    return abs(center_x - (LEFT + RIGHT) // 2) + abs(center_y - (TOP + BOTTOM) // 2)


def test_centroid_falls_back_to_horizontal_shift_when_full_shift_hits_worksheet() -> None:
    # The lower-right occupied cell lies just above the title block.
    # Moving both axes toward the page center would overlap the title block.
    baseline = _packing(24, 30, 155, 125)
    candidate = _centroid_balanced_packing(baseline)
    assert candidate is not None
    assert _balance_error(candidate) < _balance_error(baseline)
    assert candidate.attempts[-1] == "centroid-balanced-page"
    offsets = [
        (after.delta[0] - before.delta[0], after.delta[1] - before.delta[1])
        for before, after in zip(baseline.fragments, candidate.fragments, strict=True)
    ]
    assert len(set(offsets)) == 1
    assert offsets[0][0] > 0
    assert offsets[0][1] == 0
    assert all(
        item.envelope[0] >= LEFT
        and item.envelope[2] <= RIGHT
        and item.envelope[1] >= TOP
        and item.envelope[3] <= BOTTOM
        for item in candidate.fragments
    )


def test_centroid_search_uses_later_legal_shelf_when_first_is_balanced() -> None:
    # The first candidate has exactly the physical page center and needs no
    # translation; it must not suppress a legal improvement to another seed.
    balanced = _packing(48, 50, 180, 112)
    assert _centroid_balanced_packing(balanced) is None
    off_center = _packing(24, 30, 155, 125)
    candidate = _best_centroid_balanced_packing([balanced, off_center])
    assert candidate is not None
    assert candidate.attempts[-1] == "centroid-balanced-page"
    assert _balance_error(candidate) < _balance_error(off_center)
    assert _best_centroid_balanced_packing([balanced]) is None
