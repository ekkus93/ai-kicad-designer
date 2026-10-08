import pytest

from ai_kicad.m2_composition_reproducibility import (
    LOCKED_TOOLCHAIN,
    CompositionReproducibilityRun,
    build_reproducibility_evidence,
)

SOURCE = "a" * 40
HASH_ONE = "1" * 64
HASH_TWO = "2" * 64
HASH_THREE = "3" * 64
HASH_FOUR = "4" * 64


def _run(index: int, **overrides: str) -> CompositionReproducibilityRun:
    values = {
        "run_id": f"run-{index}",
        "source_sha": SOURCE,
        "project_sha256": HASH_ONE,
        "semantic_composition_class": "one-band-linear-output-right",
        "native_render_geometry_sha256": HASH_TWO,
        "observer_metric_vector_sha256": HASH_THREE,
        "candidate_decision_sha256": HASH_FOUR,
        "toolchain": LOCKED_TOOLCHAIN,
    }
    values.update(overrides)
    return CompositionReproducibilityRun(**values)


def test_complete_reproducibility_requires_five_matching_runs() -> None:
    evidence = build_reproducibility_evidence(
        SOURCE,
        tuple(_run(index) for index in range(5)),
    )

    assert evidence.is_complete()
    assert evidence.gaps() == ()
    assert len(evidence.manifest_sha256()) == 64


def test_missing_run_count_is_reported_exactly() -> None:
    evidence = build_reproducibility_evidence(SOURCE, tuple(_run(index) for index in range(4)))

    assert not evidence.is_complete()
    assert evidence.gaps() == ("expected 5 runs, observed 4",)


def test_each_required_deterministic_field_is_checked() -> None:
    runs = (
        _run(0),
        _run(1, project_sha256="5" * 64),
        _run(2, semantic_composition_class="two-band-feedback"),
        _run(3, native_render_geometry_sha256="6" * 64),
        _run(4, candidate_decision_sha256="7" * 64),
    )

    gaps = build_reproducibility_evidence(SOURCE, runs).gaps()

    assert "non-deterministic project_sha256" in gaps
    assert "non-deterministic semantic_composition_class" in gaps
    assert "non-deterministic native_render_geometry_sha256" in gaps
    assert "non-deterministic candidate_decision_sha256" in gaps


def test_observer_metric_vector_mismatch_is_not_hidden_by_other_matches() -> None:
    runs = tuple(
        _run(index, observer_metric_vector_sha256=("8" * 64 if index == 4 else HASH_THREE))
        for index in range(5)
    )

    assert build_reproducibility_evidence(SOURCE, runs).gaps() == (
        "non-deterministic observer_metric_vector_sha256",
    )


def test_reproducibility_json_is_deterministic_by_run_id() -> None:
    forward = build_reproducibility_evidence(SOURCE, tuple(_run(index) for index in range(5)))
    reverse = build_reproducibility_evidence(
        SOURCE,
        tuple(_run(index) for index in reversed(range(5))),
    )

    assert forward.canonical_json() == reverse.canonical_json()
    assert forward.manifest_sha256() == reverse.manifest_sha256()


def test_rejects_wrong_source_toolchain_and_duplicate_runs() -> None:
    with pytest.raises(ValueError, match="run source_sha"):
        build_reproducibility_evidence(SOURCE, (_run(0, source_sha="b" * 40),))

    with pytest.raises(ValueError, match="toolchain"):
        _run(0, toolchain="KiCad 9.0.0")

    with pytest.raises(ValueError, match="duplicate reproducibility run_id"):
        build_reproducibility_evidence(SOURCE, (_run(0), _run(0)))


def test_rejects_malformed_hash_inputs() -> None:
    with pytest.raises(ValueError, match="project_sha256"):
        _run(0, project_sha256="not-a-sha")

    with pytest.raises(ValueError, match="source_sha"):
        build_reproducibility_evidence("A" * 40, ())
