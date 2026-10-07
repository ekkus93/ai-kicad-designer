from ai_kicad import m2_functional_block_composition_observer as obs


def test_dispersion_fragmentation_and_shared_ownership_are_reported() -> None:
    members = (
        obs.VisualMember("a", "gain", (0, 0)),
        obs.VisualMember("b", "gain", (60, 0)),
        obs.VisualMember("rail", "supply", (20, 20), ownership="shared"),
    )
    metrics = obs.measure_functional_block_composition(members, fragmentation_gap=40)
    assert metrics.fragmented_blocks == ("gain",)
    assert metrics.shared_members == ("rail",)
    gain = metrics.block_dispersion[0]
    assert (gain.block_id, gain.span_x, gain.manhattan_diameter) == ("gain", 60, 60)


def test_support_and_interface_owner_distances_detect_detachment() -> None:
    members = (
        obs.VisualMember("stage", "amp", (20, 20)),
        obs.VisualMember("decouple", "amp", (80, 20), "stage", "support"),
        obs.VisualMember("output", "amp", (20, 90), "stage", "interface"),
    )
    metrics = obs.measure_functional_block_composition(members)
    assert [(w.member_id, w.owner_id, w.distance) for w in metrics.support_to_owner] == [
        ("decouple", "stage", 60)
    ]
    assert [(w.member_id, w.owner_id, w.distance) for w in metrics.interface_to_owner] == [
        ("output", "stage", 70)
    ]


def test_feedback_span_and_unrelated_block_intrusion_are_exact_witnesses() -> None:
    members = (
        obs.VisualMember("amp", "gain", (10, 10)),
        obs.VisualMember("fb", "gain", (70, 50), "amp", "support"),
        obs.VisualMember("intruder", "filter", (40, 30)),
        obs.VisualMember("outside", "filter", (90, 90)),
    )
    relation = obs.VisualRelation("loop", "feedback", ("amp", "fb"), "gain")
    metrics = obs.measure_functional_block_composition(members, (relation,))
    witness = metrics.feedback[0]
    assert witness.span == 100
    assert witness.unrelated_block_intrusions == ("intruder",)


def test_negative_mutations_increase_independent_observer_witnesses() -> None:
    compact = (
        obs.VisualMember("stage", "amp", (20, 20)),
        obs.VisualMember("support", "amp", (25, 20), "stage", "support"),
        obs.VisualMember("output", "amp", (30, 20), "stage", "interface"),
    )
    detached = (
        compact[0],
        obs.VisualMember("support", "amp", (100, 20), "stage", "support"),
        obs.VisualMember("output", "amp", (20, 110), "stage", "interface"),
    )
    before = obs.measure_functional_block_composition(compact)
    after = obs.measure_functional_block_composition(detached)
    assert before.support_to_owner[0].distance == 5
    assert after.support_to_owner[0].distance == 80
    assert before.interface_to_owner[0].distance == 10
    assert after.interface_to_owner[0].distance == 90


def test_renaming_and_input_order_do_not_change_metric_values() -> None:
    original = (
        obs.VisualMember("u1", "stage", (0, 0)),
        obs.VisualMember("c1", "stage", (15, 5), "u1", "support"),
    )
    renamed = (
        obs.VisualMember("z", "omega", (15, 5), "q", "support"),
        obs.VisualMember("q", "omega", (0, 0)),
    )
    first = obs.measure_functional_block_composition(original)
    second = obs.measure_functional_block_composition(renamed)
    assert first.block_dispersion[0].manhattan_diameter == second.block_dispersion[0].manhattan_diameter
    assert first.support_to_owner[0].distance == second.support_to_owner[0].distance
