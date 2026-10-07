from ai_kicad import m2_branch_feedback_composition_observer as obs


def test_branch_origin_and_sibling_geometry_are_reported() -> None:
    nodes = (
        obs.FlowNode("src", "gain", (0, 20)),
        obs.FlowNode("out_a", "branch_a", (60, 0)),
        obs.FlowNode("out_b", "branch_b", (60, 40)),
    )
    relation = obs.BranchRelation("fanout", "src", ("out_a", "out_b"), (10, 20))
    witness = obs.measure_branch_feedback_composition(nodes, (relation,)).branch_witnesses[0]
    assert witness.source_distance == 10
    assert witness.sibling_geometry_variance == 0


def test_branch_detours_and_crossings_are_measured() -> None:
    nodes = (
        obs.FlowNode("src", "gain", (0, 0)),
        obs.FlowNode("out_a", "branch_a", (40, 0)),
        obs.FlowNode("out_b", "branch_b", (0, 40)),
    )
    relation = obs.BranchRelation(
        "crossed",
        "src",
        ("out_a", "out_b"),
        (0, 0),
        (((0, 0), (40, 40)), ((0, 40), (40, 0))),
    )
    witness = obs.measure_branch_feedback_composition(nodes, (relation,)).branch_witnesses[0]
    assert witness.crossing_count == 1
    assert witness.detour_distance == 80


def test_feedback_span_owner_distance_and_intrusion_are_exact_witnesses() -> None:
    nodes = (
        obs.FlowNode("amp", "gain", (0, 0)),
        obs.FlowNode("fb", "gain", (80, 40)),
        obs.FlowNode("intruder", "filter", (40, 20)),
        obs.FlowNode("outside", "filter", (100, 100)),
    )
    relation = obs.FeedbackRelation("loop", "amp", ("fb",))
    metrics = obs.measure_branch_feedback_composition(nodes, feedback=(relation,))
    witness = metrics.feedback_witnesses[0]
    assert witness.owner_distance == 120
    assert witness.span == 120
    assert witness.unrelated_block_intrusions == ("intruder",)


def test_feedback_crossings_are_separate_from_forward_branch_metrics() -> None:
    nodes = (
        obs.FlowNode("amp", "gain", (0, 0)),
        obs.FlowNode("fb", "gain", (40, 40)),
    )
    relation = obs.FeedbackRelation(
        "feedback",
        "amp",
        ("fb",),
        (((0, 0), (40, 40)), ((0, 40), (40, 0))),
    )
    metrics = obs.measure_branch_feedback_composition(nodes, feedback=(relation,))
    assert metrics.branch_witnesses == ()
    assert metrics.feedback_witnesses[0].crossing_count == 1
