from ai_kicad.m2_composition_candidate_rank import _local_signal_neighbor_gap


def test_empty_local_signal_pairs() -> None:
    assert _local_signal_neighbor_gap(type('P', (), {'blocks': (), 'presentation_nets': ()})(), {}) == 0
