from ai_kicad import m2_graph_order_composition_oracle as oracle


def test_signal_precedence_reports_ordered_pairs_and_reversal_distance() -> None:
    nodes = (
        oracle.OrderNode("input", "signal", (0, 0)),
        oracle.OrderNode("gain", "signal", (40, 0)),
        oracle.OrderNode("out", "signal", (20, 0)),
    )
    edges = (
        oracle.OrderEdge("input", "gain", "signal"),
        oracle.OrderEdge("gain", "out", "signal"),
    )

    metrics = oracle.evaluate_graph_order(nodes, edges)

    assert metrics.ordered_pairs == (("gain", "out"), ("input", "gain"), ("input", "out"))
    assert metrics.violations == (oracle.StageOrderViolation("gain", "out", "signal", 20),)
    assert metrics.cumulative_reversal_distance == 20


def test_power_and_reference_edges_do_not_create_forward_stage_order() -> None:
    nodes = (
        oracle.OrderNode("reg", "signal", (80, 80)),
        oracle.OrderNode("amp", "signal", (20, 0)),
        oracle.OrderNode("ref", "signal", (40, 70)),
    )
    edges = (
        oracle.OrderEdge("reg", "amp", "power"),
        oracle.OrderEdge("ref", "amp", "reference"),
    )

    metrics = oracle.evaluate_graph_order(nodes, edges)

    assert metrics.ordered_pairs == ()
    assert metrics.incomparable_pairs == (("amp", "ref"), ("amp", "reg"), ("ref", "reg"))
    assert metrics.ignored_non_forward_edges == edges


def test_feedback_cycles_are_ignored_as_forward_precedence() -> None:
    nodes = (
        oracle.OrderNode("amp", "signal", (50, 0)),
        oracle.OrderNode("fb", "signal", (30, 20)),
        oracle.OrderNode("out", "signal", (90, 0)),
    )
    edges = (
        oracle.OrderEdge("amp", "out", "signal"),
        oracle.OrderEdge("out", "fb", "feedback"),
        oracle.OrderEdge("fb", "amp", "feedback"),
    )

    metrics = oracle.evaluate_graph_order(nodes, edges)

    assert metrics.ordered_pairs == (("amp", "out"),)
    assert metrics.violations == ()
    assert [edge.role for edge in metrics.ignored_non_forward_edges] == ["feedback", "feedback"]


def test_incomparable_siblings_keep_ordering_freedom() -> None:
    nodes = (
        oracle.OrderNode("source", "signal", (0, 0)),
        oracle.OrderNode("branch_a", "signal", (40, -20)),
        oracle.OrderNode("branch_b", "signal", (40, 20)),
    )
    edges = (
        oracle.OrderEdge("source", "branch_a", "signal"),
        oracle.OrderEdge("source", "branch_b", "signal"),
    )

    metrics = oracle.evaluate_graph_order(nodes, edges)

    assert ("branch_a", "branch_b") in metrics.incomparable_pairs
    assert ("source", "branch_a") in metrics.ordered_pairs
    assert ("source", "branch_b") in metrics.ordered_pairs


def test_exact_reversal_tolerance_boundary_and_off_by_one() -> None:
    nodes_at_boundary = (
        oracle.OrderNode("a", "signal", (10, 0)),
        oracle.OrderNode("b", "signal", (5, 0)),
    )
    nodes_off_by_one = (
        oracle.OrderNode("a", "signal", (11, 0)),
        oracle.OrderNode("b", "signal", (5, 0)),
    )
    edge = (oracle.OrderEdge("a", "b", "signal"),)

    boundary = oracle.evaluate_graph_order(nodes_at_boundary, edge, reversal_tolerance=5)
    off_by_one = oracle.evaluate_graph_order(nodes_off_by_one, edge, reversal_tolerance=5)

    assert boundary.violations == ()
    assert off_by_one.violations == (oracle.StageOrderViolation("a", "b", "signal", 6),)


def test_refdes_rename_and_input_order_do_not_change_distances() -> None:
    first = (
        oracle.OrderNode("u1", "signal", (30, 0)),
        oracle.OrderNode("u2", "signal", (10, 0)),
    )
    renamed = (
        oracle.OrderNode("z_target", "signal", (10, 0)),
        oracle.OrderNode("z_source", "signal", (30, 0)),
    )

    first_metrics = oracle.evaluate_graph_order(first, (oracle.OrderEdge("u1", "u2", "signal"),))
    renamed_metrics = oracle.evaluate_graph_order(
        renamed, (oracle.OrderEdge("z_source", "z_target", "signal"),)
    )

    assert first_metrics.cumulative_reversal_distance == 20
    assert renamed_metrics.cumulative_reversal_distance == 20
