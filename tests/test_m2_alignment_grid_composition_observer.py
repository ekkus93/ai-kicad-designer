from ai_kicad import m2_alignment_grid_composition_observer as obs


def test_reports_meaningful_alignment_and_stage_baseline_deviation() -> None:
    items = (
        obs.PlacedItem("u1", "stage", (20, 50)),
        obs.PlacedItem("u2", "stage", (60, 50)),
        obs.PlacedItem("u3", "stage", (100, 65)),
    )
    metrics = obs.measure_alignment_grid_composition(items)
    assert metrics.meaningful_horizontal_alignment_lines == 1
    assert metrics.sequential_stage_baseline_deviation == 15


def test_reports_role_consistent_passive_alignment() -> None:
    items = (
        obs.PlacedItem("r1", "passive", (20, 30)),
        obs.PlacedItem("r2", "passive", (45, 30)),
        obs.PlacedItem("r3", "passive", (70, 45)),
    )
    metrics = obs.measure_alignment_grid_composition(items)
    assert metrics.role_passive_alignment_deviation == 15


def test_reports_connector_and_support_owner_offsets() -> None:
    items = (
        obs.PlacedItem("stage", "stage", (50, 50)),
        obs.PlacedItem("out", "connector", (110, 75), owner_id="stage"),
        obs.PlacedItem("decouple", "support", (55, 20), owner_id="stage"),
    )
    metrics = obs.measure_alignment_grid_composition(items)
    assert metrics.connector_signal_row_distance == (obs.OwnerDistance("out", "stage", 25),)
    assert metrics.support_owner_offset == (obs.OwnerDistance("decouple", "stage", 30),)


def test_preserves_kicad_grid_compatibility_evidence() -> None:
    items = (
        obs.PlacedItem("on_grid", "stage", (20, 30)),
        obs.PlacedItem("off_x", "stage", (22, 30)),
        obs.PlacedItem("off_y", "stage", (30, 33)),
    )
    metrics = obs.measure_alignment_grid_composition(items, grid_step=5)
    assert metrics.grid_violations == ("off_x", "off_y")


def test_detects_inconsistent_field_and_body_orientation_by_role() -> None:
    items = (
        obs.PlacedItem("r1", "passive", (20, 30), orientation="east", field_orientation="east"),
        obs.PlacedItem("r2", "passive", (45, 30), orientation="east", field_orientation="east"),
        obs.PlacedItem("r3", "passive", (70, 30), orientation="west", field_orientation="west"),
    )
    metrics = obs.measure_alignment_grid_composition(items)
    assert metrics.inconsistent_orientation_ids == ("r3",)
    assert metrics.inconsistent_field_orientation_ids == ("r3",)


def test_long_field_default_slots_are_reported_without_blocking_alternates() -> None:
    items = (
        obs.PlacedItem("long_default", "stage", (20, 30), field_length=40),
        obs.PlacedItem("long_alt", "stage", (60, 30), field_length=40, field_slot="alternate"),
    )
    metrics = obs.measure_alignment_grid_composition(items)
    assert metrics.long_field_default_slot_ids == ("long_default",)


def test_metric_values_are_refdes_and_input_order_invariant() -> None:
    original = (
        obs.PlacedItem("u1", "stage", (20, 40)),
        obs.PlacedItem("u2", "stage", (60, 50)),
    )
    renamed_reordered = (
        obs.PlacedItem("zzz", "stage", (60, 50)),
        obs.PlacedItem("aaa", "stage", (20, 40)),
    )
    first = obs.measure_alignment_grid_composition(original)
    second = obs.measure_alignment_grid_composition(renamed_reordered)
    assert first.sequential_stage_baseline_deviation == second.sequential_stage_baseline_deviation
    assert first.meaningful_horizontal_alignment_lines == second.meaningful_horizontal_alignment_lines
