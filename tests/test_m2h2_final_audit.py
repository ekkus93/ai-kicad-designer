"""Independent falsifications for final evidence conductor accounting."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_m2h2_final_artifact_audit import graph_distances, union_length


def test_union_charges_overlapping_reversed_and_subdivided_intervals_once():
    segments = [
        [[0, 0], [10, 0]],
        [[15, 0], [5, 0]],
        [[0, 0], [5, 0]],
        [[10, 0], [10, 4]],
        [[10, 4], [10, 2]],
        [[20, 0], [22, 0]],
    ]
    assert union_length(segments) == 21
    assert union_length(list(reversed(segments))) == 21
    assert union_length([]) == 0


def test_path_distance_splits_unsplit_t_and_keeps_detached_island_unreachable():
    segments = [[[0, 0], [10, 0]], [[5, 0], [5, 7]], [[20, 0], [25, 0]]]
    terminals = {(0, 0), (10, 0), (5, 7), (22, 0)}
    distances = graph_distances(segments, (0, 0), terminals)
    assert distances[(5, 7)] == 12
    assert distances[(10, 0)] == 10
    assert (22, 0) not in distances


def test_nonorthogonal_conductor_cannot_enter_union_accounting():
    with pytest.raises(ValueError, match="non-orthogonal"):
        union_length([[[0, 0], [1, 1]]])
