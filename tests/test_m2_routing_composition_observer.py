from ai_kicad.m2_routing_composition_observer import measure_routing_readability


def test_route_readability_reports_length_bends_and_excess() -> None:
    metrics = measure_routing_readability(
        (((0, 0), (10, 0)), ((10, 0), (10, 5))),
        semantic_local_length=10,
        semantic_local_bends=0,
    )

    assert metrics.route_length == 15
    assert metrics.bend_count == 1
    assert metrics.normalized_length_excess == 0.5
    assert metrics.normalized_bend_excess == 1.0


def test_route_readability_reports_branch_point_and_sibling_inconsistency() -> None:
    metrics = measure_routing_readability(
        (
            ((0, 0), (10, 0)),
            ((0, 0), (0, 5)),
            ((0, 0), (0, -20)),
        ),
        semantic_local_length=35,
    )

    assert metrics.branch_points == ((0, 0),)
    assert metrics.sibling_branch_geometry_inconsistency == 15


def test_route_readability_reports_crossings_detours_and_excursions() -> None:
    segments = (
        ((0, 0), (10, 0)),
        ((10, 0), (10, 10)),
        ((10, 10), (0, 10)),
        ((0, 10), (0, 20)),
    )
    metrics = measure_routing_readability(
        segments,
        semantic_local_length=20,
        unrelated_segments=(((5, -5), (5, 5)),),
        unrelated_blocks=((8, 8, 12, 12),),
    )

    assert metrics.unrelated_crossings == 1
    assert metrics.u_shaped_detours == 1
    assert metrics.route_excursions == (((10, 0), (10, 10)), ((10, 10), (0, 10)))


def test_route_readability_reports_local_label_disconnects_only_when_direct_is_clear() -> None:
    metrics = measure_routing_readability(
        (((0, 0), (5, 0)),),
        semantic_local_length=5,
        local_label_pairs=(
            ("near_missing", (0, 10), (5, 10)),
            ("near_direct", (0, 0), (5, 0)),
            ("far_missing", (0, 0), (200, 0)),
        ),
        direct_distance_limit=10,
    )

    assert metrics.label_mediated_local_disconnects == ("near_missing",)


def test_multisegment_visible_path_is_not_a_label_disconnect() -> None:
    segments = (
        ((0, 0), (10, 0)),
        ((10, 0), (10, 10)),
        ((10, 10), (20, 10)),
    )
    pairs = (
        ("connected", (0, 0), (20, 10)),
        ("missing", (0, 0), (20, 0)),
        ("distant", (0, 0), (100, 0)),
    )
    for candidate in (segments, tuple((end, start) for start, end in reversed(segments))):
        metrics = measure_routing_readability(
            candidate,
            semantic_local_length=30,
            local_label_pairs=pairs,
            direct_distance_limit=40,
        )
        assert metrics.label_mediated_local_disconnects == ("missing",)


def test_crossing_without_shared_endpoint_is_not_a_visible_connection() -> None:
    metrics = measure_routing_readability(
        (
            ((0, 5), (10, 5)),
            ((5, 0), (5, 10)),
        ),
        semantic_local_length=20,
        local_label_pairs=(("crossing", (0, 5), (5, 10)),),
        direct_distance_limit=20,
    )
    assert metrics.label_mediated_local_disconnects == ("crossing",)


def test_shared_endpoint_joins_visible_segments() -> None:
    metrics = measure_routing_readability(
        (
            ((0, 0), (10, 0)),
            ((10, 0), (10, 10)),
            ((10, 10), (20, 10)),
            ((20, 10), (20, 0)),
        ),
        semantic_local_length=40,
        local_label_pairs=(("connected", (0, 0), (20, 0)),),
        direct_distance_limit=40,
    )
    assert metrics.label_mediated_local_disconnects == ()


def test_unordered_reversed_u_detour() -> None:
    route = (((0, 0), (10, 0)), ((10, 0), (10, 10)), ((10, 10), (0, 10)))
    reordered = (route[2], route[0], route[1])
    reversed_route = tuple((end, start) for start, end in reversed(route))
    for variant in (route, reordered, reversed_route):
        metrics = measure_routing_readability(variant, semantic_local_length=30)
        assert metrics.u_shaped_detours == 1


def test_labels_on_wire_interiors_are_visibly_connected() -> None:
    segments = (
        ((0, 0), (20, 0)),
        ((20, 0), (20, 20)),
        ((20, 20), (40, 20)),
    )
    labels = (
        ("interior_same", (5, 0), (15, 0)),
        ("interior_multi", (5, 0), (30, 20)),
        ("endpoint_to_interior", (0, 0), (20, 12)),
    )
    for variant in (segments, tuple((b, a) for a, b in reversed(segments))):
        metrics = measure_routing_readability(
            variant, semantic_local_length=60, local_label_pairs=labels
        )
        assert metrics.label_mediated_local_disconnects == ()


def test_labels_at_unjoined_orthogonal_crossings_do_not_invent_junction() -> None:
    segments = (((0, 10), (20, 10)), ((10, 0), (10, 20)))
    labels = (
        ("ambiguous_crossing", (10, 10), (20, 10)),
        ("different_wires", (5, 10), (10, 5)),
        ("same_horizontal", (5, 10), (15, 10)),
    )
    metrics = measure_routing_readability(
        segments, semantic_local_length=40, local_label_pairs=labels
    )
    assert metrics.label_mediated_local_disconnects == ("ambiguous_crossing", "different_wires")


def test_local_label_disconnect_witnesses_deduplicate_and_sort() -> None:
    metrics = measure_routing_readability(
        (),
        semantic_local_length=0,
        local_label_pairs=(
            ("z", (0, 0), (10, 0)),
            ("a", (0, 0), (10, 0)),
            ("z", (0, 0), (10, 0)),
        ),
    )
    assert metrics.label_mediated_local_disconnects == ("a", "z")
