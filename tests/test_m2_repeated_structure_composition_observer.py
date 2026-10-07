from ai_kicad import m2_repeated_structure_composition_observer as obs

def test_repeated_structure_metrics():
    members = (
        obs.RepeatedMember("a1", "a", "input", (10, 10)),
        obs.RepeatedMember("a2", "a", "stage", (30, 10)),
        obs.RepeatedMember("b1", "b", "input", (10, 30)),
        obs.RepeatedMember("b2", "b", "stage", (30, 30)),
    )
    metrics = obs.measure_repeated_structure(members)
    assert metrics.column_alignment_variance == 0
    assert metrics.corresponding_displacement_variance == 0
    assert metrics.pitch_variance == 0

def test_repeated_structure_detects_orientation_and_pitch_variance():
    members = (
        obs.RepeatedMember("a1", "a", "input", (10, 10), 0),
        obs.RepeatedMember("a2", "a", "stage", (30, 10), 0),
        obs.RepeatedMember("b1", "b", "input", (10, 30), 90),
        obs.RepeatedMember("b2", "b", "stage", (50, 30), 0),
    )
    metrics = obs.measure_repeated_structure(members)
    assert metrics.orientation_variance == 90
    assert metrics.pitch_variance == 20
