"""Precedence-inferred signal fanout has the same branch grammar as explicit flow."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown


def _block(name, kind):
    return SimpleNamespace(id=name, kind=kind, ports=())


def _placed(block, x, y):
    rect = (x, y, x + PITCH, y + PITCH)
    return SimpleNamespace(
        fragment=SimpleNamespace(block=block, positions={}),
        content_envelope=rect,
        envelope=rect,
        delta=(x, y),
    )


def _score(plan, source_y):
    source, upper, lower = plan.blocks
    packing = SimpleNamespace(
        fragments=(
            _placed(source, 0, source_y),
            _placed(upper, 10 * PITCH, 0),
            _placed(lower, 10 * PITCH, 10 * PITCH),
        )
    )
    return semantic_composition_penalty_breakdown(plan, packing).branch_alignment


def test_inferred_fanout_matches_explicit_and_mixed_annotations():
    blocks = (_block("input", "interface"), _block("upper", "filter"), _block("lower", "filter"))
    precedence = (
        SimpleNamespace(source_fragment="input", target_fragment="upper", net="split"),
        SimpleNamespace(source_fragment="input", target_fragment="lower", net="split"),
    )
    edges = (
        SimpleNamespace(kind="signal", source="input", target="upper", net="split"),
        SimpleNamespace(kind="signal", source="input", target="lower", net="split"),
    )

    def plan(*, inferred=(), explicit=()):
        return SimpleNamespace(blocks=blocks, edges=explicit, precedence=inferred)

    inferred = plan(inferred=precedence)
    explicit = plan(explicit=edges)
    mixed = plan(inferred=tuple(reversed(precedence)), explicit=tuple(reversed(edges)))
    assert _score(inferred, 5 * PITCH) == 0
    displaced = _score(inferred, 0)
    assert displaced > 0
    assert displaced == _score(explicit, 0) == _score(mixed, 0)


def test_unrelated_precedence_nets_are_not_a_single_fanout():
    blocks = (_block("input", "interface"), _block("upper", "filter"), _block("lower", "filter"))
    precedence = (
        SimpleNamespace(source_fragment="input", target_fragment="upper", net="a"),
        SimpleNamespace(source_fragment="input", target_fragment="lower", net="b"),
    )
    plan = SimpleNamespace(blocks=blocks, edges=(), precedence=precedence)
    assert _score(plan, 0) == 0
