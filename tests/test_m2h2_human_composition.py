from ai_kicad.m2_composition_quality import observe_human_composition
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _port(block: str, role: str, net: str) -> SemanticPort:
    return SemanticPort(f"{block}.{role}", block, net, role, ((block, "1"),))


def _plan(net: str = "SIG") -> SemanticPlan:
    blocks = (
        BlockPlan(
            "input.j1",
            "interface",
            (),
            frozenset({("J1", 1)}),
            (_port("input.j1", "signal_in", net),),
        ),
        BlockPlan(
            "stage.filter",
            "filter",
            (),
            frozenset({("R1", 1), ("C1", 1)}),
            (
                _port("stage.filter", "signal_in", net),
                _port("stage.filter", "signal_out", "OUT"),
            ),
        ),
        BlockPlan(
            "output.j2",
            "interface",
            (),
            frozenset({("J2", 1)}),
            (_port("output.j2", "signal_out", "OUT"),),
        ),
    )
    return SemanticPlan(
        blocks,
        (
            SemanticEdge("signal", "input.j1", "stage.filter", net, ("synthetic-input",)),
            SemanticEdge("signal", "stage.filter", "output.j2", "OUT", ("synthetic-output",)),
        ),
        {},
        ("input.j1", "stage.filter", "output.j2"),
    )


def test_observer_accepts_left_to_right_interface_flow() -> None:
    report = observe_human_composition(
        _plan(),
        {
            "input.j1": (0, 0, 10, 10),
            "stage.filter": (30, 0, 50, 10),
            "output.j2": (80, 0, 90, 10),
        },
    )

    assert report.passed
    assert report.metrics.primary_stage_order_inversions == 0
    assert report.metrics.input_side_violations == 0
    assert report.metrics.output_side_violations == 0
    assert report.as_dict()["schema_version"] == "m2h2.human-readable-composition.observer.1"


def test_observer_rejects_output_connector_on_input_side() -> None:
    report = observe_human_composition(
        _plan(),
        {
            "input.j1": (0, 0, 10, 10),
            "stage.filter": (60, 0, 80, 10),
            "output.j2": (20, 0, 30, 10),
        },
    )

    assert not report.passed
    assert report.metrics.primary_stage_order_inversions == 1
    assert report.metrics.output_side_violations == 1
    assert {item.kind for item in report.violations} == {
        "primary_stage_order_inversion",
        "output_side_violation",
    }


def test_observer_rejects_input_connector_right_of_consumer() -> None:
    report = observe_human_composition(
        _plan(),
        {
            "input.j1": (90, 0, 100, 10),
            "stage.filter": (40, 0, 60, 10),
            "output.j2": (110, 0, 120, 10),
        },
    )

    assert not report.passed
    assert report.metrics.primary_stage_order_inversions == 1
    assert report.metrics.input_side_violations == 1
    assert any(item.kind == "input_side_violation" for item in report.violations)


def test_observer_is_stable_under_literal_net_rename() -> None:
    envelopes = {
        "input.j1": (0, 0, 10, 10),
        "stage.filter": (60, 0, 80, 10),
        "output.j2": (20, 0, 30, 10),
    }

    original = observe_human_composition(_plan("SIG"), envelopes)
    renamed = observe_human_composition(_plan("RENAMED_SIGNAL"), envelopes)

    assert (
        original.metrics.primary_stage_order_inversions
        == renamed.metrics.primary_stage_order_inversions
    )
    assert original.metrics.input_side_violations == renamed.metrics.input_side_violations
    assert original.metrics.output_side_violations == renamed.metrics.output_side_violations
    assert [item.kind for item in original.violations] == [item.kind for item in renamed.violations]


def test_observer_preserves_incomparable_sibling_ordering() -> None:
    blocks = (
        BlockPlan(
            "input.j1",
            "interface",
            (),
            frozenset(),
            (_port("input.j1", "signal_in", "IN"),),
        ),
        BlockPlan("stage.a", "filter", (), frozenset(), (_port("stage.a", "signal_in", "A"),)),
        BlockPlan("stage.b", "filter", (), frozenset(), (_port("stage.b", "signal_in", "B"),)),
    )
    plan = SemanticPlan(
        blocks,
        (
            SemanticEdge("branch", "input.j1", "stage.a", "A", ("branch-a",)),
            SemanticEdge("branch", "input.j1", "stage.b", "B", ("branch-b",)),
        ),
        {},
        ("input.j1",),
    )

    report = observe_human_composition(
        plan,
        {
            "input.j1": (0, 0, 10, 10),
            "stage.b": (40, 0, 50, 10),
            "stage.a": (40, 30, 50, 40),
        },
    )

    assert report.passed
    assert report.metrics.primary_stage_order_inversions == 0
