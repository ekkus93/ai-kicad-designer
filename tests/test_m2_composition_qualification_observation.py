from ai_kicad.m2_composition_qualification_matrix import (
    LOCKED_KICAD_VERSION,
    build_required_matrix,
)
from types import SimpleNamespace

from ai_kicad.m2_composition_qualification_observation import (
    QualificationObservation,
    build_observation_report,
    observe_composition_evidence,
    observe_composition_packing,
    observe_native_pin_composition,
)
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan

SOURCE = "a" * 40
BASE_CASES = tuple(f"base-{index:02d}" for index in range(56))


def _matrix():
    return build_required_matrix(
        source_sha=SOURCE,
        base_case_ids=BASE_CASES,
        interaction_case_ids=("I1",),
        structural_case_ids=("one-band",),
        targeted_case_ids=("targeted",),
    )


def _observation(case_id: str, repetition: int, **overrides) -> QualificationObservation:
    values = {
        "case_id": case_id,
        "repetition": repetition,
        "source_sha": SOURCE,
        "toolchain": LOCKED_KICAD_VERSION,
        "status": "passed",
        "native_kicad": True,
        "composition_observer_passed": True,
        "electrical_passed": True,
        "serialized_scene_verified": True,
    }
    values.update(overrides)
    return QualificationObservation(**values)


def test_successful_repetitions_count_unique_passing_repetition_ids() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1),
        _observation("base-00", 1),
        _observation("base-00", 2),
        _observation("base-00", 3, status="failed"),
    )

    report = build_observation_report(matrix, observations)

    assert ("base-00", 2) in report.successful_repetitions()
    assert ("base-00", 5, 2) in report.gaps()
    assert report.rejected_observation_count() == 1


def test_wrong_source_wrong_toolchain_and_pending_runs_do_not_count() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1, source_sha="b" * 40),
        _observation("base-00", 2, toolchain="KiCad 9.0.0"),
        _observation("base-00", 3, status="queued"),
    )

    report = build_observation_report(matrix, observations)

    assert report.successful_repetitions() == ()
    assert ("base-00", 5, 0) in report.gaps()
    assert report.rejected_observation_count() == 3


def test_required_native_kicad_observer_electrical_and_serialization_gates() -> None:
    matrix = _matrix()
    observations = (
        _observation("base-00", 1, native_kicad=False),
        _observation("base-00", 2, composition_observer_passed=False),
        _observation("base-00", 3, electrical_passed=False),
        _observation("base-00", 4, serialized_scene_verified=False),
        _observation("base-00", 5),
    )

    report = build_observation_report(matrix, observations)

    assert ("base-00", 1) in report.successful_repetitions()
    assert report.rejected_observation_count() == 4


def test_preserved_negative_does_not_require_composition_observer() -> None:
    matrix = _matrix()
    observation = _observation("V3-8", 1, composition_observer_passed=False)

    report = build_observation_report(matrix, (observation,))

    assert ("V3-8", 1) in report.successful_repetitions()
    assert all(case_id != "V3-8" for case_id, _, _ in report.gaps())


def test_unknown_case_and_out_of_range_repetition_are_rejected() -> None:
    matrix = _matrix()
    observations = (
        _observation("not-in-matrix", 1),
        _observation("base-00", 0),
        _observation("base-00", 6),
    )

    report = build_observation_report(matrix, observations)

    assert report.successful_repetitions() == ()
    assert report.rejected_observation_count() == 3


def _composition_plan() -> SemanticPlan:
    return SemanticPlan(
        blocks=(
            BlockPlan("input", "interface", (), frozenset(), ()),
            BlockPlan("stage", "filter", (), frozenset(), ()),
        ),
        edges=(SemanticEdge("signal", "input", "stage", "signal", ()),),
        owners={},
        signal_order=(),
    )


def test_runtime_observer_reads_emitted_block_envelopes_independently() -> None:
    report = observe_composition_evidence(
        _composition_plan(),
        {
            "variants": [
                {"fragment": "input", "placed_envelope": [0, 0, 10, 10]},
                {"fragment": "stage", "placed_envelope": [20, 0, 30, 10]},
            ]
        },
    )
    assert report.passed
    assert report.metrics.primary_stage_order_inversions == 0

    reversed_report = observe_composition_evidence(
        _composition_plan(),
        {
            "variants": [
                {"fragment": "input", "placed_envelope": [30, 0, 40, 10]},
                {"fragment": "stage", "placed_envelope": [0, 0, 10, 10]},
            ]
        },
    )
    assert not reversed_report.passed
    assert reversed_report.metrics.primary_stage_order_inversions == 1


def test_runtime_observer_reads_measured_packing_without_candidate_scores() -> None:
    def placed(block_id: str, rect: tuple[int, int, int, int]):
        return SimpleNamespace(
            fragment=SimpleNamespace(block=SimpleNamespace(id=block_id)),
            content_envelope=rect,
            envelope=rect,
        )

    packing = SimpleNamespace(
        fragments=(
            placed("input", (0, 0, 10, 10)),
            placed("stage", (20, 0, 30, 10)),
        )
    )
    report = observe_composition_packing(_composition_plan(), packing)
    assert report.passed
    assert report.metrics.visible_block_count == 2


def test_native_pin_observer_uses_emitted_geometry_not_production_envelopes() -> None:
    from ai_kicad.m2_semantics import PhysicalTerminalObligation

    original = _composition_plan()
    plan = SemanticPlan(
        blocks=original.blocks,
        edges=original.edges,
        owners={},
        signal_order=(),
        terminals=(
            PhysicalTerminalObligation(
                ("source-pin", "1"), ("source-pin", 1), "input",
                "Connector_Generic:Conn_01x01", 1, "P", 0, 0, "signal",
            ),
            PhysicalTerminalObligation(
                ("sink-pin", "2"), ("sink-pin", 1), "stage",
                "Device:R", 1, "P", 0, 0, "signal",
            ),
        ),
    )
    design = {
        "components": [
            {"id": "source-pin", "refdes": "J1"},
            {"id": "sink-pin", "refdes": "R1"},
        ],
    }
    native = {"pin_positions": {("J1", "1"): (0, 0), ("R1", "2"): (20, 0)}}
    observed = observe_native_pin_composition(plan, design, native)
    assert observed.passed
    assert observed.metrics.visible_block_count == 2

    tampered_production = {
        "variants": [
            {"fragment": "input", "placed_envelope": [100, 0, 110, 10]},
            {"fragment": "stage", "placed_envelope": [0, 0, 10, 10]},
        ]
    }
    assert not observe_composition_evidence(plan, tampered_production).passed
    assert observe_native_pin_composition(plan, design, native) == observed

    reversed_native = {"pin_positions": {("J1", "1"): (30, 0), ("R1", "2"): (0, 0)}}
    reversed_report = observe_native_pin_composition(plan, design, reversed_native)
    assert not reversed_report.passed
    assert reversed_report.metrics.primary_stage_order_inversions == 1


def test_native_pin_observer_marks_missing_block_geometry() -> None:
    from ai_kicad.m2_semantics import PhysicalTerminalObligation

    original = _composition_plan()
    plan = SemanticPlan(
        blocks=original.blocks,
        edges=original.edges,
        owners={},
        signal_order=(),
        terminals=(
            PhysicalTerminalObligation(
                ("source-pin", "1"), ("source-pin", 1), "input",
                "Connector_Generic:Conn_01x01", 1, "P", 0, 0, "signal",
            ),
        ),
    )
    design = {"components": [{"id": "source-pin", "refdes": "J1"}]}
    native = {"pin_positions": {("J1", "1"): (0, 0)}}
    report = observe_native_pin_composition(plan, design, native)
    assert not report.passed
    assert report.metrics.visible_block_count == 1
    assert any(item.kind == "missing_block_geometry" for item in report.violations)
