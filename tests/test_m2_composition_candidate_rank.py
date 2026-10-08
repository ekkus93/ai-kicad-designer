"""Independent authored controls for semantic composition penalties."""

from types import SimpleNamespace

from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalties
from ai_kicad.m2_pack import PITCH
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _block(name: str, kind: str, net: str, role: str) -> BlockPlan:
    port = SemanticPort(name + ".p", name, net, role, ())
    return BlockPlan(name, kind, (), frozenset(), (port,))


def _packing(positions: dict[str, tuple[int, int]]):
    return SimpleNamespace(
        fragments=tuple(
            SimpleNamespace(
                fragment=SimpleNamespace(block=SimpleNamespace(id=name)),
                content_envelope=(x, y, x + PITCH, y + PITCH),
                envelope=(x, y, x + PITCH, y + PITCH),
            )
            for name, (x, y) in positions.items()
        )
    )


def test_wrong_input_and_output_frontiers_are_penalized() -> None:
    plan = SemanticPlan(
        (
            _block("in", "interface", "source", "passive"),
            _block("stage_in", "stage", "source", "signal_in"),
            _block("stage_out", "stage", "sink", "signal_out"),
            _block("out", "interface", "sink", "passive"),
        ),
        (),
        {},
        (),
    )
    correct = _packing(
        {"in": (0, 0), "stage_in": (2 * PITCH, 0),
         "stage_out": (3 * PITCH, 0), "out": (5 * PITCH, 0)}
    )
    wrong = _packing(
        {"in": (4 * PITCH, 0), "stage_in": (2 * PITCH, 0),
         "stage_out": (3 * PITCH, 0), "out": (0, 0)}
    )
    assert semantic_composition_penalties(plan, correct)[0] == 0
    assert semantic_composition_penalties(plan, wrong)[0] == 5


def test_feedback_does_not_create_forward_stage_precedence() -> None:
    blocks = (
        _block("a", "stage", "net", "signal_out"),
        _block("b", "stage", "net", "signal_in"),
    )
    packing = _packing({"a": (3 * PITCH, 0), "b": (0, 0)})
    forward = SemanticPlan(
        blocks, (SemanticEdge("signal", "a", "b", "net", ()),), {}, ()
    )
    feedback = SemanticPlan(
        blocks, (SemanticEdge("feedback", "a", "b", "net", ()),), {}, ()
    )
    assert semantic_composition_penalties(forward, packing)[1] == 3
    assert semantic_composition_penalties(feedback, packing)[1] == 0


def test_support_locality_is_distinct_from_power_distribution() -> None:
    blocks = (
        _block("stage", "stage", "net", "signal_in"),
        _block("cap", "support", "rail", "reference"),
    )
    packing = _packing({"stage": (0, 0), "cap": (0, 5 * PITCH)})
    support = SemanticPlan(
        blocks, (SemanticEdge("support", "cap", "stage", "rail", ()),), {}, ()
    )
    power = SemanticPlan(
        blocks, (SemanticEdge("power", "cap", "stage", "rail", ()),), {}, ()
    )
    assert semantic_composition_penalties(support, packing)[3] == 5
    assert semantic_composition_penalties(power, packing)[3] == 0


def test_rename_and_permutation_preserve_penalties() -> None:
    first = SemanticPlan(
        (_block("stage", "stage", "out", "signal_out"),
         _block("connector", "interface", "out", "passive")),
        (), {}, ()
    )
    second = SemanticPlan(
        (_block("z", "interface", "renamed", "passive"),
         _block("a", "stage", "renamed", "signal_out")),
        (), {}, ()
    )
    before = semantic_composition_penalties(
        first, _packing({"stage": (2 * PITCH, 0), "connector": (0, 0)})
    )
    after = semantic_composition_penalties(
        second, _packing({"z": (0, 0), "a": (2 * PITCH, 0)})
    )
    assert before == after
