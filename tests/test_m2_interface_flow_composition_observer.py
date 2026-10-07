from ai_kicad import m2_interface_flow_composition_observer as obs


def test_directed_input_and_output_frontier_violations_are_reported() -> None:
    input_interface = obs.ExternalInterface(
        "input",
        obs.SIGNAL_INPUT_ROLE,
        (50, 0),
        "first",
    )
    output_interface = obs.ExternalInterface(
        "output",
        obs.SIGNAL_OUTPUT_ROLE,
        (80, 0),
        "final",
    )
    first = obs.FlowStage("first", (20, 0))
    final = obs.FlowStage("final", (120, 0))

    metrics = obs.measure_interface_flow_composition(
        (input_interface, output_interface),
        (first, final),
        (),
    )

    violations = tuple(
        (w.interface_id, w.expected_side, w.owner_stage_id, w.distance)
        for w in metrics.interface_side_violations
    )
    assert violations == (
        ("input", "left", "first", 30),
        ("output", "right", "final", 40),
    )


def test_bidirectional_undirected_and_justified_interfaces_are_exempt() -> None:
    bidirectional = obs.ExternalInterface(
        "bidirectional",
        obs.BIDIRECTIONAL_ROLE,
        (100, 0),
        "stage",
    )
    undirected = obs.ExternalInterface(
        "undirected",
        obs.UNDIRECTED_ROLE,
        (100, 10),
        "stage",
    )
    documented = obs.ExternalInterface(
        "documented_output",
        obs.SIGNAL_OUTPUT_ROLE,
        (0, 0),
        "stage",
        side_justification="external constraint",
    )
    stage = obs.FlowStage("stage", (50, 0))

    metrics = obs.measure_interface_flow_composition(
        (bidirectional, undirected, documented),
        (stage,),
        (),
    )

    assert metrics.interface_side_violations == ()
    assert metrics.justified_side_exemptions == ("documented_output",)


def test_power_input_reports_grouping_distance_not_signal_side_violation() -> None:
    power = obs.ExternalInterface(
        "power",
        obs.POWER_INPUT_ROLE,
        (0, 30),
        "supply",
    )
    supply = obs.FlowStage("supply", (10, 10))

    metrics = obs.measure_interface_flow_composition((power,), (supply,), ())

    distances = tuple(
        (w.interface_id, w.owner_stage_id, w.distance)
        for w in metrics.power_interface_distances
    )
    assert metrics.interface_side_violations == ()
    assert distances == (("power", "supply", 30),)


def test_stage_order_inversions_and_primary_backtracking_are_reported() -> None:
    early = obs.FlowStage("early", (100, 0))
    late = obs.FlowStage("late", (40, 0))
    precedence = obs.FlowPrecedence("early", "late", obs.PRIMARY_FLOW_ROLE)

    metrics = obs.measure_interface_flow_composition((), (early, late), (precedence,))

    reversals = tuple(
        (w.before_stage_id, w.after_stage_id, w.reversal_distance)
        for w in metrics.stage_order_violations
    )
    assert reversals == (("early", "late", 60),)
    assert metrics.primary_flow_backtracking_distance == 60
    assert metrics.checked_precedence_count == 1


def test_incomparable_sibling_order_is_not_reported_without_precedence() -> None:
    source = obs.FlowStage("source", (0, 0))
    upper_branch = obs.FlowStage("upper_branch", (80, -20))
    lower_branch = obs.FlowStage("lower_branch", (40, 20))
    upper_flow = obs.FlowPrecedence(
        "source",
        "upper_branch",
        obs.SIGNAL_FLOW_ROLE,
    )
    lower_flow = obs.FlowPrecedence(
        "source",
        "lower_branch",
        obs.SIGNAL_FLOW_ROLE,
    )

    metrics = obs.measure_interface_flow_composition(
        (),
        (source, upper_branch, lower_branch),
        (upper_flow, lower_flow),
    )

    assert metrics.stage_order_violations == ()
    assert metrics.checked_precedence_count == 2


def test_renamed_permuted_equivalent_keeps_same_generic_violation_distances() -> None:
    original_interface = obs.ExternalInterface(
        "left_result",
        obs.SIGNAL_OUTPUT_ROLE,
        (10, 0),
        "producer",
    )
    renamed_interface = obs.ExternalInterface(
        "zeta",
        obs.SIGNAL_OUTPUT_ROLE,
        (10, 0),
        "omega",
    )
    producer = obs.FlowStage("producer", (70, 0))
    omega = obs.FlowStage("omega", (70, 0))

    original = obs.measure_interface_flow_composition(
        (original_interface,),
        (producer,),
        (),
    )
    renamed = obs.measure_interface_flow_composition(
        (renamed_interface,),
        (omega,),
        (),
    )

    original_distances = tuple(w.distance for w in original.interface_side_violations)
    renamed_distances = tuple(w.distance for w in renamed.interface_side_violations)
    assert original_distances == (60,)
    assert renamed_distances == (60,)
