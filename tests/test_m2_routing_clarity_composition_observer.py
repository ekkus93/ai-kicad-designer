from ai_kicad import m2_routing_clarity_composition_observer as obs


def test_reports_bend_count_and_canonical_length() -> None:
    path = obs.RoutedPath("n1", ((0, 0), (20, 0), (20, 15), (40, 15)))
    metrics = obs.measure_routing_clarity((path,))
    assert metrics.routes == (obs.RouteLength("n1", 2, 55),)
    assert metrics.total_bend_count == 2
    assert metrics.total_canonical_length == 55


def test_reports_unrelated_wire_crossings() -> None:
    first = obs.RoutedPath("a", ((0, 10), (30, 10)), source_id="left")
    second = obs.RoutedPath("b", ((15, 0), (15, 20)), source_id="top")
    metrics = obs.measure_routing_clarity((first, second))
    assert metrics.unrelated_crossings == ("a:b",)


def test_reports_u_shaped_or_rectangular_detours() -> None:
    detour = obs.RoutedPath("loop", ((0, 0), (40, 0), (40, 30), (0, 30), (0, 5)))
    direct = obs.RoutedPath("direct", ((0, 0), (20, 0)))
    metrics = obs.measure_routing_clarity((detour, direct))
    assert metrics.u_shaped_detour_path_ids == ("loop",)


def test_reports_route_excursions_through_unrelated_blocks() -> None:
    path = obs.RoutedPath("n1", ((0, 20), (100, 20)), owner_block_id="amp")
    blocks = (
        obs.BlockArea("amp", 0, 0, 30, 30),
        obs.BlockArea("filter", 45, 10, 65, 30),
    )
    metrics = obs.measure_routing_clarity((path,), blocks=blocks)
    assert metrics.unrelated_block_excursions == (obs.RouteExcursion("n1", "filter"),)


def test_reports_sibling_branch_geometry_inconsistency() -> None:
    paths = (
        obs.RoutedPath("b1", ((0, 0), (30, 0)), role="branch", source_id="src"),
        obs.RoutedPath("b2", ((0, 0), (0, 60), (80, 60)), role="branch", source_id="src"),
    )
    metrics = obs.measure_routing_clarity(paths)
    assert metrics.sibling_branch_geometry_inconsistency == ("src",)


def test_reports_label_mediated_local_disconnects_but_not_global_distribution() -> None:
    local = obs.LabelUse("local", (10, 10), (30, 10))
    global_label = obs.LabelUse("rail", (10, 10), (180, 100), global_distribution=True)
    metrics = obs.measure_routing_clarity((), labels=(local, global_label))
    assert metrics.label_mediated_local_disconnects == (obs.LabelDisconnect("local", 20),)


def test_metric_values_are_rename_and_input_order_invariant() -> None:
    first_paths = (
        obs.RoutedPath("a", ((0, 0), (10, 0), (10, 20))),
        obs.RoutedPath("b", ((30, 0), (30, 20))),
    )
    second_paths = (
        obs.RoutedPath("renamed_b", ((30, 0), (30, 20))),
        obs.RoutedPath("renamed_a", ((0, 0), (10, 0), (10, 20))),
    )
    first = obs.measure_routing_clarity(first_paths)
    second = obs.measure_routing_clarity(second_paths)
    assert first.total_bend_count == second.total_bend_count
    assert first.total_canonical_length == second.total_canonical_length
