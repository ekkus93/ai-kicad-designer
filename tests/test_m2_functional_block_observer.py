from math import isinf

from ai_kicad.m2_functional_block_observer import Edge, Node, Ownership, observe


def test_blocks_derive_from_connectivity_and_exclude_shared_rail() -> None:
    nodes = (
        Node("in", 10, 20),
        Node("stage", 30, 20),
        Node("out", 50, 20),
        Node("rail", 30, 5, "power"),
    )
    edges = (
        Edge("in", "stage"),
        Edge("stage", "out"),
        Edge("rail", "stage", "power"),
    )
    result = observe(nodes, edges)
    assert result.blocks == (("in", "out", "stage"),)
    assert result.block_dispersion == (40.0,)


def test_support_and_interface_detachment_are_measured() -> None:
    nodes = (
        Node("owner", 20, 20),
        Node("support", 100, 100, "support"),
        Node("output", 170, 20, "interface"),
    )
    ownership = (
        Ownership("support", ("owner",), "support"),
        Ownership("output", ("owner",), "interface"),
    )
    distances = dict(observe(nodes, (), ownership).ownership_distance)
    assert distances["support"] > 100
    assert distances["output"] == 150


def test_shared_reference_preserves_multiple_owner_semantics() -> None:
    nodes = (
        Node("a", 20, 30),
        Node("b", 80, 30),
        Node("vref", 50, 10, "reference"),
    )
    metric = dict(
        observe(nodes, (), (Ownership("vref", ("a", "b"), "shared"),)).ownership_distance
    )
    assert metric["vref"] > 0


def test_missing_owner_is_explicitly_unbounded() -> None:
    metric = dict(
        observe(
            (Node("s", 20, 20, "support"),),
            (),
            (Ownership("s", ("missing",), "support"),),
        ).ownership_distance
    )
    assert isinf(metric["s"])


def test_feedback_span_is_observed() -> None:
    nodes = (Node("amp", 20, 20), Node("fb", 60, 60))
    assert observe(nodes, (Edge("amp", "fb", "feedback"),)).feedback_span > 50


def test_rename_and_input_order_leave_metrics_unchanged() -> None:
    first = observe((Node("a", 10, 10), Node("b", 30, 10)), (Edge("a", "b"),))
    second = observe((Node("z", 30, 10), Node("y", 10, 10)), (Edge("z", "y"),))
    assert first.block_dispersion == second.block_dispersion
