from fractions import Fraction

from ai_kicad.m2_repeated_composition_observer import RepeatedMember, measure_repeated_composition


def test_displacement_variance_detects_inconsistent_correspondence() -> None:
    metrics = measure_repeated_composition((RepeatedMember("amp", "a", (0, 0)), RepeatedMember("amp", "b", (0, 10)), RepeatedMember("amp", "c", (0, 30))))
    assert metrics.corresponding_displacement_variance == Fraction(100)
