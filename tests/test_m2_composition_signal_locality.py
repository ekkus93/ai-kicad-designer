"""Source-level controls for label-eligible local signal placement."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown


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
