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


def test_explicit_t_junction_endpoint_joins_visible_wire_components() -> None:
    # An emitted branch endpoint lies on a trunk interior: this is a visible
    # T-junction even when the trunk was serialized as a single long segment.
    trunk = ((0, 0), (20, 0))
    branch = ((10, 0), (10, 10))
    labels = (("t_junction", (0, 0), (10, 10)),)
    for segments in (
        (trunk, branch),
        (branch, trunk),
        ((trunk[1], trunk[0]), (branch[1], branch[0])),
    ):
        metrics = measure_routing_readability(
            segments,
            semantic_local_length=30,
            local_label_pairs=labels,
            direct_distance_limit=30,
        )
        assert metrics.label_mediated_local_disconnects == ()


def test_pure_wire_interior_crossing_stays_disconnected() -> None:
    # Interior/interior intersections must never invent a KiCad junction.
    trunk = ((0, 0), (20, 0))
    crossing = ((10, -10), (10, 10))
    for segments in ((trunk, crossing), (crossing, trunk)):
        metrics = measure_routing_readability(
            segments,
            semantic_local_length=40,
            local_label_pairs=(("not_a_junction", (0, 0), (10, 10)),),
            direct_distance_limit=40,
        )
        assert metrics.label_mediated_local_disconnects == ("not_a_junction",)


def test_visible_t_junction_branch_witness_is_split_order_invariant() -> None:
    # A single trunk and a split trunk must produce the same junction witness.
    trunk = ((0, 0), (20, 0))
    branch = ((10, 0), (10, 10))
    for segments in (
        (trunk, branch),
        (((0, 0), (10, 0)), ((10, 0), (20, 0)), branch),
        (branch, ((20, 0), (0, 0))),
        ((branch[1], branch[0]), ((20, 0), (10, 0)), ((10, 0), (0, 0))),
    ):
        metrics = measure_routing_readability(segments, semantic_local_length=30)
        assert metrics.branch_points == ((10, 0),)


def test_pure_crossing_or_duplicate_stroke_never_invents_branch() -> None:
    horizontal = ((0, 0), (20, 0))
    vertical = ((10, -10), (10, 10))
    for segments in (
        (horizontal, vertical),
        (horizontal, horizontal, vertical),
        (horizontal, ((5, 0), (15, 0))),
    ):
        metrics = measure_routing_readability(segments, semantic_local_length=50)
        assert metrics.branch_points == ()


def test_t_junction_sibling_arm_metric_is_split_and_direction_invariant() -> None:
    # The 10/10/18 arm lengths must not become 18/18 when the trunk is unsplit.
    trunk = ((0, 0), (20, 0))
    branch = ((10, 0), (10, 18))
    for segments in (
        (trunk, branch),
        (((0, 0), (10, 0)), ((10, 0), (20, 0)), branch),
        (branch, ((20, 0), (0, 0))),
        ((branch[1], branch[0]), ((20, 0), (10, 0)), ((10, 0), (0, 0))),
    ):
        metrics = measure_routing_readability(segments, semantic_local_length=38)
        assert metrics.branch_points == ((10, 0),)
        assert metrics.sibling_branch_geometry_inconsistency == 8


def test_sibling_branch_geometry_ignores_collinear_wire_segmentation() -> None:
    # A trunk and arm split into extra collinear strokes are the same geometry.
    unsplit = (((0, 0), (20, 0)), ((10, 0), (10, 10)))
    split = (
        ((0, 0), (5, 0)),
        ((5, 0), (10, 0)),
        ((10, 0), (15, 0)),
        ((15, 0), (20, 0)),
        ((10, 0), (10, 5)),
        ((10, 5), (10, 10)),
    )
    for segments in (unsplit, split, tuple((b, a) for a, b in reversed(split))):
        metrics = measure_routing_readability(segments, semantic_local_length=30)
        assert metrics.branch_points == ((10, 0),)
        assert metrics.sibling_branch_geometry_inconsistency == 0


def test_branch_arm_stops_at_next_explicit_junction() -> None:
    # A long trunk contains two distinguishable branch owners, not one
    # artificially long sibling arm for the first branch.
    segments = (
        ((0, 0), (30, 0)),
        ((10, 0), (10, 5)),
        ((20, 0), (20, 20)),
    )
    metrics = measure_routing_readability(segments, semantic_local_length=55)
    assert metrics.branch_points == ((10, 0), (20, 0))
    assert metrics.sibling_branch_geometry_inconsistency == 10


def test_u_detour_metric_ignores_collinear_wire_splitting() -> None:
    unsplit = (
        ((0, 0), (10, 0)),
        ((10, 0), (10, 10)),
        ((10, 10), (0, 10)),
    )
    split = (
        ((0, 0), (5, 0)),
        ((5, 0), (10, 0)),
        ((10, 0), (10, 5)),
        ((10, 5), (10, 10)),
        ((10, 10), (5, 10)),
        ((5, 10), (0, 10)),
    )
    for route in (
        unsplit,
        split,
        tuple(reversed(split)),
        tuple((end, start) for start, end in reversed(split)),
    ):
        metrics = measure_routing_readability(route, semantic_local_length=30)
        assert metrics.u_shaped_detours == 1


def test_collinear_wire_merge_retains_explicit_t_junction() -> None:
    # A real branch must survive collinear simplification; adding a seam
    # cannot change its U-detour witnesses or branch topology.
    route = (
        ((0, 0), (5, 0)),
        ((5, 0), (10, 0)),
        ((5, 0), (5, 8)),
        ((10, 0), (10, 10)),
        ((10, 10), (0, 10)),
    )
    segmented = (
        route[0],
        route[1],
        route[2],
        ((10, 0), (10, 5)),
        ((10, 5), (10, 10)),
        route[4],
    )
    reference = measure_routing_readability(route, semantic_local_length=38)
    assert reference.branch_points == ((5, 0),)
    assert reference.u_shaped_detours == 2
    for candidate in (segmented, tuple((b, a) for a, b in reversed(segmented))):
        metrics = measure_routing_readability(candidate, semantic_local_length=38)
        assert metrics.branch_points == reference.branch_points
        assert metrics.u_shaped_detours == reference.u_shaped_detours


def test_bend_count_is_duplicate_and_collinear_split_invariant() -> None:
    elbow = (((0, 0), (10, 0)), ((10, 0), (10, 10)))
    variants = (
        elbow,
        elbow + (elbow[0], elbow[1]),
        (((0, 0), (5, 0)), ((5, 0), (10, 0)), elbow[1]),
        tuple((end, start) for start, end in reversed(elbow + (elbow[0],))),
    )
    for route in variants:
        metrics = measure_routing_readability(route, semantic_local_length=20)
        assert metrics.bend_count == 1


def test_bend_count_does_not_count_three_arm_tee_as_a_corner() -> None:
    trunk = ((0, 0), (20, 0))
    branch = ((10, 0), (10, 10))
    corner = ((10, 10), (20, 10))
    variants = (
        (trunk, branch, corner),
        (((0, 0), (10, 0)), ((10, 0), (20, 0)), branch, corner),
        (corner, branch, trunk, trunk),
    )
    for route in variants:
        metrics = measure_routing_readability(route, semantic_local_length=40)
        assert metrics.branch_points == ((10, 0),)
        assert metrics.bend_count == 1


def test_unrelated_crossing_count_deduplicates_reversed_strokes() -> None:
    horizontal = ((0, 0), (20, 0))
    vertical = ((10, -10), (10, 10))
    variants = (
        ((horizontal,), (vertical,)),
        ((horizontal, horizontal), (vertical, vertical)),
        ((((20, 0), (0, 0)), horizontal), (vertical, ((10, 10), (10, -10)))),
    )
    for primary, unrelated in variants:
        metrics = measure_routing_readability(
            primary,
            semantic_local_length=20,
            unrelated_segments=unrelated,
        )
        assert metrics.unrelated_crossings == 1
