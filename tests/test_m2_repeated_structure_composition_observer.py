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


def test_renamed_channels_and_members_do_not_change_spatial_displacement() -> None:
    members = (
        obs.RepeatedMember("z", "z-channel", "amp", (0, 70)),
        obs.RepeatedMember("a", "a-channel", "amp", (0, 0)),
        obs.RepeatedMember("b", "b-channel", "amp", (0, 10)),
        obs.RepeatedMember("c", "c-channel", "amp", (0, 30)),
    )
    renamed = (
        obs.RepeatedMember("new-3", "aa", "amp", (0, 30)),
        obs.RepeatedMember("new-4", "bb", "amp", (0, 70)),
        obs.RepeatedMember("new-1", "yy", "amp", (0, 0)),
        obs.RepeatedMember("new-2", "zz", "amp", (0, 10)),
    )
    measured = obs.measure_repeated_structure(members)
    assert measured == obs.measure_repeated_structure(renamed)
    assert measured.corresponding_displacement_variance == 30


def test_pitch_uses_physical_slot_geometry_not_slot_names() -> None:
    canonical = (
        obs.RepeatedMember("one", "a", "input", (0, 0)),
        obs.RepeatedMember("two", "a", "output", (10, 0)),
        obs.RepeatedMember("three", "a", "support", (40, 0)),
    )
    permuted = (
        obs.RepeatedMember("renamed-three", "renamed", "alpha", (40, 0)),
        obs.RepeatedMember("renamed-two", "renamed", "zeta", (10, 0)),
        obs.RepeatedMember("renamed-one", "renamed", "middle", (0, 0)),
    )
    first = obs.measure_repeated_structure(canonical)
    assert first.pitch_variance == 20
    assert first.pitch_variance == obs.measure_repeated_structure(permuted).pitch_variance


def test_wrapped_orientations_are_equivalent() -> None:
    members = (
        obs.RepeatedMember("first", "a", "stage", (0, 0), 0),
        obs.RepeatedMember("second", "b", "stage", (0, 10), 360),
        obs.RepeatedMember("third", "c", "stage", (0, 20), -360),
    )
    assert obs.measure_repeated_structure(members).orientation_variance == 0
