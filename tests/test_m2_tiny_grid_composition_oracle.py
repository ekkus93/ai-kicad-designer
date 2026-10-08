import pytest

from ai_kicad import m2_tiny_grid_composition_oracle as oracle


def test_connector_side_semantics_dominate_wrong_frontier() -> None:
    nodes = (
        oracle.TinyNode("in", "connector", side_preference="left"),
        oracle.TinyNode("out", "connector", side_preference="right"),
    )
    grid = ((0, 0), (10, 0))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(("in", (10, 0)), ("out", (0, 0))),
    )
    assert evidence.production_is_dominated
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.score_vector[0] == 20
    assert evidence.dominating_candidate_ids


def test_linear_stage_order_penalty_detects_reversal() -> None:
    nodes = (
        oracle.TinyNode("first", "stage", stage_index=0),
        oracle.TinyNode("second", "stage", stage_index=1),
    )
    grid = ((0, 0), (20, 0))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(("first", (20, 0)), ("second", (0, 0))),
    )
    assert evidence.production_is_dominated
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.score_vector[1] == 20


def test_incomparable_siblings_have_multiple_nondominated_orders() -> None:
    nodes = (
        oracle.TinyNode("sibling_a", "stage"),
        oracle.TinyNode("sibling_b", "stage"),
    )
    grid = ((0, 0), (20, 0))
    evidence = oracle.exhaustive_tiny_grid_oracle(nodes, grid)
    assert evidence.candidate_count == 2
    assert len(evidence.nondominated_candidates) == 2


def test_grouping_penalty_prefers_cohesive_functional_block() -> None:
    nodes = (
        oracle.TinyNode("amp", "stage", group_id="gain"),
        oracle.TinyNode("fb", "support", group_id="gain"),
        oracle.TinyNode("out", "connector", side_preference="right"),
    )
    grid = ((0, 0), (10, 0), (100, 0))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(("amp", (0, 0)), ("fb", (100, 0)), ("out", (10, 0))),
    )
    assert evidence.production_is_dominated
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.score_vector[2] == 100


@pytest.mark.parametrize(
    "grid",
    (
        ((0, 0), (0, 20)),
        ((0, 0), (20, 0)),
    ),
)
def test_repeated_role_alignment_accepts_row_or_column_grammar(
    grid: tuple[oracle.Point, ...],
) -> None:
    nodes = (
        oracle.TinyNode("a_in", "stage", repeated_role="input"),
        oracle.TinyNode("b_in", "stage", repeated_role="input"),
    )
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(("a_in", grid[0]), ("b_in", grid[1])),
    )
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.score_vector[3] == 0
    assert not evidence.production_is_dominated


def test_repeated_role_alignment_detects_off_axis_drift() -> None:
    nodes = tuple(
        oracle.TinyNode(f"stage_{index}", "stage", repeated_role="gain")
        for index in range(3)
    )
    grid = ((0, 0), (10, 10), (20, 20), (0, 10), (0, 20))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(
            ("stage_0", (0, 0)),
            ("stage_1", (10, 10)),
            ("stage_2", (20, 20)),
        ),
    )
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.score_vector[3] == 20
    assert evidence.production_is_dominated


def test_oracle_rejects_unbounded_candidate_counts() -> None:
    nodes = tuple(oracle.TinyNode(f"n{index}", "stage") for index in range(4))
    grid = tuple((index, 0) for index in range(8))
    with pytest.raises(ValueError, match="candidate bound exceeded"):
        oracle.exhaustive_tiny_grid_oracle(nodes, grid, max_candidates=10)


def test_lexicographic_frontier_precedes_lower_tier_compactness() -> None:
    nodes = (
        oracle.TinyNode("input", "connector", side_preference="left"),
        oracle.TinyNode("output", "connector", side_preference="right"),
    )
    grid = ((0, 0), (10, 0), (100, 0))
    result = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        production_positions=(("input", (10, 0)), ("output", (0, 0))),
    )
    # A more compact placement must not beat a strictly better side penalty.
    assert result.production_is_dominated
    assert result.nondominated_candidates[0].score_vector[0] == 0


@pytest.mark.parametrize(
    "positions",
    (
        (("a", (0, 0)), ("a", (10, 0))),
        (("a", (0, 0)), ("missing", (10, 0))),
        (("a", (0, 0)), ("b", (0, 0))),
        (("a", (0, 0)), ("b", (20, 0))),
    ),
)
def test_illegal_production_placements_cannot_be_scored(positions: tuple) -> None:
    nodes = (oracle.TinyNode("a", "stage"), oracle.TinyNode("b", "stage"))
    with pytest.raises(ValueError, match="production positions"):
        oracle.exhaustive_tiny_grid_oracle(
            nodes,
            ((0, 0), (10, 0)),
            production_positions=positions,
        )


def test_channel_order_does_not_impose_cross_channel_precedence() -> None:
    nodes = (
        oracle.TinyNode("a_first", "stage", stage_index=0, channel_id="a"),
        oracle.TinyNode("a_last", "stage", stage_index=1, channel_id="a"),
        oracle.TinyNode("b_first", "stage", stage_index=0, channel_id="b"),
        oracle.TinyNode("b_last", "stage", stage_index=1, channel_id="b"),
    )
    positions = (
        ("a_first", (0, 0)),
        ("a_last", (10, 0)),
        ("b_first", (0, 10)),
        ("b_last", (10, 10)),
    )
    result = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        tuple(point for _, point in positions),
        production_positions=positions,
    )
    assert result.production_candidate is not None
    assert result.production_candidate.score_vector[1] == 0


def test_oracle_rejects_duplicate_nodes_and_grid_points() -> None:
    with pytest.raises(ValueError, match="duplicate tiny-grid node id"):
        oracle.exhaustive_tiny_grid_oracle(
            (oracle.TinyNode("a", "stage"), oracle.TinyNode("a", "stage")),
            ((0, 0), (10, 0)),
        )
    with pytest.raises(ValueError, match="duplicate grid point"):
        oracle.exhaustive_tiny_grid_oracle(
            (oracle.TinyNode("a", "stage"),),
            ((0, 0), (0, 0)),
        )


def test_branch_geometry_accepts_centered_equal_depth_fanout() -> None:
    nodes = (
        oracle.TinyNode("source", "stage"),
        oracle.TinyNode("left", "stage"),
        oracle.TinyNode("right", "stage"),
    )
    branch = oracle.TinyBranch("source", ("left", "right"))
    grid = ((0, 10), (20, 0), (20, 20))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        branches=(branch,),
        production_positions=(
            ("source", (0, 10)),
            ("left", (20, 0)),
            ("right", (20, 20)),
        ),
    )
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.branch_geometry_penalty == 0


def test_branch_geometry_penalizes_skewed_or_backtracking_fanout() -> None:
    nodes = (
        oracle.TinyNode("source", "stage"),
        oracle.TinyNode("left", "stage"),
        oracle.TinyNode("right", "stage"),
    )
    branch = oracle.TinyBranch("source", ("left", "right"))
    grid = ((20, 20), (0, 0), (40, 10))
    evidence = oracle.exhaustive_tiny_grid_oracle(
        nodes,
        grid,
        branches=(branch,),
        production_positions=(
            ("source", (20, 20)),
            ("left", (0, 0)),
            ("right", (40, 10)),
        ),
    )
    assert evidence.production_candidate is not None
    assert evidence.production_candidate.branch_geometry_penalty > 0
    assert evidence.production_candidate.score_vector[2] >= (
        evidence.production_candidate.branch_geometry_penalty
    )


@pytest.mark.parametrize(
    "branch",
    (
        oracle.TinyBranch("missing", ("a", "b")),
        oracle.TinyBranch("a", ("b",)),
        oracle.TinyBranch("a", ("a", "b")),
        oracle.TinyBranch("a", ("b", "missing")),
    ),
)
def test_illegal_branch_specifications_are_rejected(branch: oracle.TinyBranch) -> None:
    nodes = (oracle.TinyNode("a", "stage"), oracle.TinyNode("b", "stage"))
    with pytest.raises(ValueError, match="tiny branch"):
        oracle.exhaustive_tiny_grid_oracle(
            nodes,
            ((0, 0), (10, 0)),
            branches=(branch,),
        )
