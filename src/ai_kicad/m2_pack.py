"""Deterministic measured-envelope packing for M2 fragments."""

from __future__ import annotations

from .m2_pack_beam import (
    _band_count,
    _branch_fanout_repack_candidates,
    _partial_beam_candidates,
    _retain_composition_seed_diversity,
)
from .m2_pack_constants import (
    BOTTOM,
    CANDIDATE_BUDGET,
    CHANNEL_GAP,
    ENVELOPE_OUTER_PADDING,
    LEFT,
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    MAX_PACKING_HEIGHT,
    MAX_PACKING_WIDTH,
    OUTPUT_FRONTIER_CLEARANCE,
    PLACEMENT_LEFT,
    RIGHT,
    TOP,
)
from .m2_pack_core import (
    Packing,
    PlacedFragment,
    _best_centroid_balanced_packing,
    _centroid_balanced_packing,
    _fanout_column_groups,
    _group_parallel_branch_columns,
    _group_power_fanout,
    _make_units,
    _place,
    _reference_escape_directions,
    _signal_chains,
    _topological,
    _translate_point,
    _typed_unit_order,
    _Unit,
    _worksheet_clearance_packing,
)
from .m2_pack_distribution import (
    _distribution_column_candidate,
    _measured_repack,
)
from .m2_pack_frontier import (
    _envelope_manhattan_gap,
    _interface_frontier_candidates,
    _local_signal_proximity_candidates,
)
from .m2_pack_layout import (
    _arrangements,
    _pack_shelves,
)
from .m2_pack_search import (
    pack_fragment_candidates,
    pack_fragments,
)
from .m2_pack_semantic import (
    _repeated_peer_alignment_candidates,
    _semantic_block_order_candidates,
    _structural_repack_candidates,
    _support_affinity_candidates,
)

__all__ = [
    "BOTTOM",
    "CANDIDATE_BUDGET",
    "CHANNEL_GAP",
    "ENVELOPE_OUTER_PADDING",
    "LEFT",
    "MAX_CONTENT_HEIGHT",
    "MAX_CONTENT_WIDTH",
    "MAX_PACKING_HEIGHT",
    "MAX_PACKING_WIDTH",
    "OUTPUT_FRONTIER_CLEARANCE",
    "PLACEMENT_LEFT",
    "RIGHT",
    "TOP",
    "Packing",
    "PlacedFragment",
    "_Unit",
    "_arrangements",
    "_band_count",
    "_best_centroid_balanced_packing",
    "_branch_fanout_repack_candidates",
    "_centroid_balanced_packing",
    "_distribution_column_candidate",
    "_envelope_manhattan_gap",
    "_fanout_column_groups",
    "_group_parallel_branch_columns",
    "_group_power_fanout",
    "_interface_frontier_candidates",
    "_local_signal_proximity_candidates",
    "_make_units",
    "_measured_repack",
    "_pack_shelves",
    "_partial_beam_candidates",
    "_place",
    "_reference_escape_directions",
    "_repeated_peer_alignment_candidates",
    "_retain_composition_seed_diversity",
    "_semantic_block_order_candidates",
    "_signal_chains",
    "_structural_repack_candidates",
    "_support_affinity_candidates",
    "_topological",
    "_translate_point",
    "_typed_unit_order",
    "_worksheet_clearance_packing",
    "pack_fragment_candidates",
    "pack_fragments",
]
