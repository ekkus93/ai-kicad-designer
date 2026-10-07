import inspect

from ai_kicad import m2_interface_side_composition_observer as obs


def test_directed_interfaces_use_generic_left_and_right_frontiers() -> None:
    nodes = (
        obs.CompositionNode("in", "interface", (0, 20), "input", "left"),
        obs.CompositionNode("stage", "stage", (40, 20), stage_rank=0),
        obs.CompositionNode("out", "interface", (80, 20), "output", "right"),
    )
    metrics = obs.measure_interface_side_composition(nodes)
    assert metrics.interface_side_penalties == ()
    assert metrics.primary_flow_backtracking_distance == 0


def test_bidirectional_and_undirected_interfaces_are_semantically_exempt() -> None:
    nodes = (
        obs.CompositionNode("io", "interface", (0, 10), "bidirectional", "left"),
        obs.CompositionNode("probe", "interface", (80, 10), "undirected", "right"),
    )
    metrics = obs.measure_interface_side_composition(nodes)
    assert metrics.interface_side_penalties == ()


def test_power_input_interfaces_are_checked_against_supply_infrastructure() -> None:
    local_nodes = (
        obs.CompositionNode(
            "vin", "interface", (10, 10), "power_input", "left", supply_group_id="p"
        ),
        obs.CompositionNode("rail", "supply", (25, 10), supply_group_id="p"),
        obs.CompositionNode("stage", "stage", (80, 10), stage_rank=0),
    )
    distant_nodes = (
        local_nodes[0],
        obs.CompositionNode("rail", "supply", (100, 10), supply_group_id="p"),
        local_nodes[2],
    )
    assert obs.measure_interface_side_composition(local_nodes).supply_interface_penalties == ()
    penalty = obs.measure_interface_side_composition(distant_nodes).supply_interface_penalties[0]
    assert (penalty.interface_id, penalty.nearest_supply_id, penalty.distance) == (
        "vin",
        "rail",
        90,
    )


def test_output_on_input_frontier_and_stage_backtracking_are_exact_penalties() -> None:
    nodes = (
        obs.CompositionNode("input", "interface", (0, 10), "input", "left"),
        obs.CompositionNode("filter", "stage", (70, 10), stage_rank=1),
        obs.CompositionNode("amp", "stage", (30, 10), stage_rank=0),
        obs.CompositionNode("output", "interface", (0, 10), "output", "left"),
    )
    edges = (obs.CompositionEdge("amp", "filter", "primary_signal"),)
    metrics = obs.measure_interface_side_composition(nodes, edges)
    side_witnesses = [
        (item.interface_id, item.expected_frontier, item.actual_frontier)
        for item in metrics.interface_side_penalties
    ]
    assert side_witnesses == [("output", "right", "left")]
    assert metrics.stage_order_violations == ()

    reversed_nodes = (
        obs.CompositionNode("amp", "stage", (80, 10), stage_rank=0),
        obs.CompositionNode("filter", "stage", (30, 10), stage_rank=1),
    )
    reversed_metrics = obs.measure_interface_side_composition(reversed_nodes, edges)
    assert reversed_metrics.primary_flow_backtracking_distance == 50
    assert reversed_metrics.stage_order_violations[0].reversal_distance == 50


def test_incomparable_siblings_are_not_ordered() -> None:
    nodes = (
        obs.CompositionNode("source", "stage", (50, 10), stage_rank=0),
        obs.CompositionNode("left_branch", "stage", (20, 40)),
        obs.CompositionNode("right_branch", "stage", (80, 40)),
    )
    edges = (
        obs.CompositionEdge("source", "left_branch", "primary_signal"),
        obs.CompositionEdge("source", "right_branch", "primary_signal"),
    )
    metrics = obs.measure_interface_side_composition(nodes, edges)
    assert metrics.stage_order_violations == ()


def test_i4_b2_like_mixed_archetype_is_generic_under_rename_and_permutation() -> None:
    original = (
        obs.CompositionNode("in_a", "interface", (0, 10), "input", "left"),
        obs.CompositionNode("in_b", "interface", (0, 40), "input", "left"),
        obs.CompositionNode("mix", "stage", (40, 25), stage_rank=0),
        obs.CompositionNode("driver", "stage", (80, 25), stage_rank=1),
        obs.CompositionNode("out", "interface", (110, 25), "output", "right"),
    )
    renamed = (
        obs.CompositionNode("z5", "interface", (110, 25), "output", "right"),
        obs.CompositionNode("a2", "stage", (80, 25), stage_rank=1),
        obs.CompositionNode("q1", "interface", (0, 40), "input", "left"),
        obs.CompositionNode("a1", "stage", (40, 25), stage_rank=0),
        obs.CompositionNode("q0", "interface", (0, 10), "input", "left"),
    )
    first = obs.measure_interface_side_composition(original)
    second = obs.measure_interface_side_composition(renamed)
    assert len(first.interface_side_penalties) == len(second.interface_side_penalties) == 0
    assert first.primary_flow_backtracking_distance == 0
    assert second.primary_flow_backtracking_distance == 0


def test_observer_source_has_no_literal_case_or_refdes_dispatch() -> None:
    source = inspect.getsource(obs)
    forbidden = ("i4__b2_mixed", "R1", "U1", "case_id", "fixture")
    assert not any(token in source for token in forbidden)
