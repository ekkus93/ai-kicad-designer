from ai_kicad import m2_power_reference_composition_observer as obs


def test_shared_rail_dispersion_and_multi_consumer_span_are_reported() -> None:
    nodes = (
        obs.PowerReferenceNode("vin", "power_interface", (0, 80)),
        obs.PowerReferenceNode("rail", "supply", (20, 80)),
        obs.PowerReferenceNode("load_a", "signal", (40, 20)),
        obs.PowerReferenceNode("load_b", "signal", (100, 20)),
    )
    edges = (
        obs.PowerReferenceEdge("rail", "load_a", "supply"),
        obs.PowerReferenceEdge("rail", "load_b", "supply"),
    )

    metrics = obs.measure_power_reference_composition(nodes, edges, primary_row_y=20)

    supply = [item for item in metrics.infrastructure_dispersion if item.role == "supply"][0]
    assert (supply.node_count, supply.manhattan_diameter) == (1, 0)
    assert metrics.producer_coherence == (obs.ProducerCoherence("rail", "supply", 2, 140),)


def test_internal_reference_producer_and_support_coherence_are_measured() -> None:
    nodes = (
        obs.PowerReferenceNode("ref", "reference", (70, 90)),
        obs.PowerReferenceNode("load", "signal", (90, 40)),
        obs.PowerReferenceNode("c_ref", "decoupling", (75, 95), "ref"),
    )
    edges = (obs.PowerReferenceEdge("ref", "load", "reference"),)

    metrics = obs.measure_power_reference_composition(nodes, edges, primary_row_y=40)

    assert metrics.local_support_distances == (
        obs.LocalSupportDistance("c_ref", "ref", "decoupling", 10),
    )
    assert metrics.producer_coherence == (obs.ProducerCoherence("ref", "reference", 1, 70),)


def test_package_local_decoupling_detachment_is_a_precise_witness() -> None:
    compact = (
        obs.PowerReferenceNode("u1", "signal", (30, 30)),
        obs.PowerReferenceNode("c1", "decoupling", (35, 30), "u1"),
    )
    detached = (
        obs.PowerReferenceNode("u1", "signal", (30, 30)),
        obs.PowerReferenceNode("c1", "decoupling", (130, 30), "u1"),
    )

    before = obs.measure_power_reference_composition(compact)
    after = obs.measure_power_reference_composition(detached)

    assert before.local_support_distances[0].distance == 5
    assert after.local_support_distances[0].distance == 100


def test_power_and_reference_intrusions_into_primary_row_are_reported() -> None:
    nodes = (
        obs.PowerReferenceNode("in", "signal", (0, 20)),
        obs.PowerReferenceNode("vcc", "supply", (40, 24)),
        obs.PowerReferenceNode("vref", "reference", (70, 80)),
        obs.PowerReferenceNode("pwr", "power_interface", (90, 20)),
    )

    metrics = obs.measure_power_reference_composition(nodes, primary_row_y=20, primary_row_tolerance=5)

    assert metrics.primary_row_intrusions == (
        obs.PrimaryRowIntrusion("pwr", "power_interface", 0),
        obs.PrimaryRowIntrusion("vcc", "supply", 4),
    )


def test_fake_external_reference_without_semantic_evidence_is_flagged() -> None:
    nodes = (
        obs.PowerReferenceNode("real_ref", "reference", (20, 80), external=True),
        obs.PowerReferenceNode(
            "fake_ref", "reference", (40, 80), external=True, semantic_evidence=False
        ),
    )

    metrics = obs.measure_power_reference_composition(nodes)

    assert metrics.fake_external_references == ("fake_ref",)


def test_refdes_renaming_and_input_order_do_not_change_distances() -> None:
    first = (
        obs.PowerReferenceNode("u1", "signal", (10, 10)),
        obs.PowerReferenceNode("c1", "decoupling", (20, 15), "u1"),
    )
    renamed = (
        obs.PowerReferenceNode("z_cap", "decoupling", (20, 15), "z_pkg"),
        obs.PowerReferenceNode("z_pkg", "signal", (10, 10)),
    )

    first_metrics = obs.measure_power_reference_composition(first)
    renamed_metrics = obs.measure_power_reference_composition(renamed)

    assert first_metrics.local_support_distances[0].distance == 15
    assert renamed_metrics.local_support_distances[0].distance == 15
