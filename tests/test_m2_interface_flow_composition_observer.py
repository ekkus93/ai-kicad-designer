from ai_kicad.m2_interface_flow_composition_observer import (
    BIDIRECTIONAL_ROLE,
    POWER_INPUT_ROLE,
    PRIMARY_FLOW_ROLE,
    SIGNAL_FLOW_ROLE,
    SIGNAL_INPUT_ROLE,
    SIGNAL_OUTPUT_ROLE,
    UNDIRECTED_ROLE,
    ExternalInterface,
    FlowPrecedence,
    FlowStage,
    measure_interface_flow_composition,
)


def test_directed_input_and_output_frontier_violations_are_reported() -> None:
    interfaces = (
        ExternalInterface("input", SIGNAL_INPUT_ROLE, (50, 0), "first"),
        ExternalInterface("output", SIGNAL_OUTPUT_ROLE, (80, 0), "final"),
    )
    stages = (
        FlowStage("first", (20, 0)),
        FlowStage("final", (120, 0)),
    )

    metrics = measure_interface_flow_composition(interfaces, stages, ())

    violations = tuple(
        (w.interface_id, w.expected_side, w.owner_stage_id, w.distance)
        for w in metrics.interface_side_violations
    )
    assert violations == (
        ("input", "left", "first", 30),
        ("output", "right", "final", 40),
    )


def test_bidirectional_undirected_and_justified_interfaces_are_exempt() -> None:
    interfaces = (
        ExternalInterface("bidirectional", BIDIRECTIONAL_ROLE, (100, 0), "stage"),
        ExternalInterface("undirected", UNDIRECTED_ROLE, (100, 10), "stage"),
        ExternalInterface(
            "documented_output",
            SIGNAL_OUTPUT_ROLE,
            (0, 0),
            "stage",
            side_justification="external constraint",
        ),
    )
    stages = (FlowStage("stage", (50, 0)),)

    metrics = measure_interface_flow_composition(interfaces, stages, ())

    assert metrics.interface_side_violations == ()
    assert metrics.justified_side_exemptions == ("documented_output",)


def test_power_input_reports_grouping_distance_not_signal_side_violation() -> None:
    interfaces = (ExternalInterface("power", POWER_INPUT_ROLE, (0, 30), "supply"),)
    stages = (FlowStage("supply", (10, 10)),)

    metrics = measure_interface_flow_composition(interfaces, stages, ())

    distances = tuple(
        (w.interface_id, w.owner_stage_id, w.distance)
        for w in metrics.power_interface_distances
    )
    assert metrics.interface_side_violations == ()
    assert distances == (("power", "supply", 30),)


def test_stage_order_inversions_and_primary_backtracking_are_reported() -> None:
    stages = (
        FlowStage("early", (100, 0)),
        FlowStage("late", (40, 0)),
    )
    precedence = (FlowPrecedence("early", "late", PRIMARY_FLOW_ROLE),)

    metrics = measure_interface_flow_composition((), stages, precedence)

    reversals = tuple(
        (w.before_stage_id, w.after_stage_id, w.reversal_distance)
        for w in metrics.stage_order_violations
    )
    assert reversals == (("early", "late", 60),)
    assert metrics.primary_flow_backtracking_distance == 60
    assert metrics.checked_precedence_count == 1


def test_incomparable_sibling_order_is_not_reported_without_precedence() -> None:
    stages = (
        FlowStage("source", (0, 0)),
        FlowStage("upper_branch", (80, -20)),
        FlowStage("lower_branch", (40, 20)),
    )
    precedence = (
        FlowPrecedence("source", "upper_branch", SIGNAL_FLOW_ROLE),
        FlowPrecedence("source", "lower_branch", SIGNAL_FLOW_ROLE),
    )

    metrics = measure_interface_flow_composition((), stages, precedence)

    assert metrics.stage_order_violations == ()
    assert metrics.checked_precedence_count == 2


def test_renamed_permuted_equivalent_keeps_same_generic_violation_distances() -> None:
    original_interfaces = (
        ExternalInterface("left_result", SIGNAL_OUTPUT_ROLE, (10, 0), "producer"),
    )
    original_stages = (FlowStage("producer", (70, 0)),)
    renamed_interfaces = (ExternalInterface("zeta", SIGNAL_OUTPUT_ROLE, (10, 0), "omega"),)
    renamed_stages = (FlowStage("omega", (70, 0)),)

    original = measure_interface_flow_composition(original_interfaces, original_stages, ())
    renamed = measure_interface_flow_composition(renamed_interfaces, renamed_stages, ())

    original_distances = tuple(w.distance for w in original.interface_side_violations)
    renamed_distances = tuple(w.distance for w in renamed.interface_side_violations)
    assert original_distances == (60,)
    assert renamed_distances == (60,)
