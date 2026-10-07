from ai_kicad.m2_functional_block_composition_observer import (
    FEEDBACK_ROLE,
    INTERFACE_ROLE,
    PRIMARY_ROLE,
    SUPPORT_ROLE,
    VisualBlockMember,
    measure_functional_block_composition,
)


def test_functional_block_metrics_report_dispersion_and_fragmentation() -> None:
    metrics = measure_functional_block_composition(
        (
            VisualBlockMember("U1", "amp", PRIMARY_ROLE, (0, 0), (0, 0, 10, 10)),
            VisualBlockMember("R1", "amp", PRIMARY_ROLE, (20, 0), (20, 0, 30, 10)),
            VisualBlockMember("C1", "filter", PRIMARY_ROLE, (100, 0), (100, 0, 110, 10)),
        ),
        adjacency_gap=0,
    )

    assert metrics.block_dispersion == {"amp": 20, "filter": 0}
    assert metrics.block_fragmentation == {"amp": 2, "filter": 1}


def test_support_negative_mutation_reports_owner_distance() -> None:
    metrics = measure_functional_block_composition(
        (
            VisualBlockMember("U1", "amp", PRIMARY_ROLE, (0, 0), (0, 0, 10, 10)),
            VisualBlockMember(
                "Cclose", "amp_support", SUPPORT_ROLE, (12, 0), (12, 0, 18, 6), "amp"
            ),
            VisualBlockMember(
                "Cfar", "amp_support", SUPPORT_ROLE, (100, 0), (100, 0, 106, 6), "amp"
            ),
        )
    )

    assert [(w.ref, w.owner_block_id, w.distance) for w in metrics.support_to_owner_distance] == [
        ("Cclose", "amp", 2),
        ("Cfar", "amp", 90),
    ]


def test_feedback_negative_mutation_reports_span_and_intrusion() -> None:
    metrics = measure_functional_block_composition(
        (
            VisualBlockMember("U1", "amp", PRIMARY_ROLE, (0, 0), (0, 0, 10, 10)),
            VisualBlockMember(
                "Rfb", "amp_feedback", FEEDBACK_ROLE, (100, 0), (100, 0, 110, 10), "amp"
            ),
            VisualBlockMember("U2", "unrelated", PRIMARY_ROLE, (50, 0), (45, -5, 55, 15)),
        )
    )

    assert [
        (w.ref, w.owner_block_id, w.span_width, w.span_height, w.intrusion_refs)
        for w in metrics.feedback_loop_span
    ] == [
        ("Rfb", "amp", 110, 10, ("U2",)),
    ]


def test_output_interface_negative_mutation_reports_detached_owner() -> None:
    metrics = measure_functional_block_composition(
        (
            VisualBlockMember("Uout", "final", PRIMARY_ROLE, (100, 0), (100, 0, 110, 10)),
            VisualBlockMember(
                "Jout", "output_interface", INTERFACE_ROLE, (0, 0), (0, 0, 10, 10), "final"
            ),
        )
    )

    assert [(w.ref, w.owner_block_id, w.distance) for w in metrics.interface_to_owner_distance] == [
        ("Jout", "final", 90),
    ]


def test_observer_has_no_production_score_input() -> None:
    assert "score" not in measure_functional_block_composition.__annotations__
