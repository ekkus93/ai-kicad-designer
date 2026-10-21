"""Deterministic semantic-first ranking for fully proved composition candidates.

This module is production scoring, not independent qualification evidence.  It
uses only generic semantic-plan roles and measured placement geometry.  Hard
electrical and M2h2 invariants are established before a candidate is ranked.
"""

from __future__ import annotations

from .m2_composition_rank_metrics import (
    _block_semantic_signature,
    _branch_readability_penalty,
    _center,
    _feedback_corridor_intrusions,
    _grid_units,
    _independent_output_owner_row_drift,
    _infrastructure_primary_row_intrusion,
    _interface_roles,
    _intra_block_dispersion,
    _local_signal_neighbor_gap,
    _passive_reference_axis_alignment_penalty,
    _placed_rects,
    _power_interface_distance,
    _rect_gap,
    _repeated_alignment_penalty,
    _segment_crosses_block,
    _shortest_elbow_intrusion_count,
    _signal_reachability,
    _signal_relations,
    _signal_row_alignment_components,
    _signal_row_alignment_penalties,
    _support_axis_alignment_penalty,
    _unrelated_block_proximity,
)
from .m2_composition_rank_scoring import (
    SemanticPenaltyBreakdown,
    _coalesced_route_segments,
    _field_slot_consistency_penalty,
    compactness_whitespace_penalties,
    composition_candidate_key,
    route_backtracking_penalty,
    route_branch_arm_spread,
    semantic_composition_penalties,
    semantic_composition_penalty_breakdown,
)
from .m2_composition_rank_types import (
    CandidateKey,
    CompactnessPenaltyVector,
    Point,
    Rect,
    SemanticPenaltyVector,
)

__all__ = [
    "CandidateKey",
    "CompactnessPenaltyVector",
    "Point",
    "Rect",
    "SemanticPenaltyBreakdown",
    "SemanticPenaltyVector",
    "_block_semantic_signature",
    "_branch_readability_penalty",
    "_center",
    "_coalesced_route_segments",
    "_feedback_corridor_intrusions",
    "_field_slot_consistency_penalty",
    "_grid_units",
    "_independent_output_owner_row_drift",
    "_infrastructure_primary_row_intrusion",
    "_interface_roles",
    "_intra_block_dispersion",
    "_local_signal_neighbor_gap",
    "_passive_reference_axis_alignment_penalty",
    "_placed_rects",
    "_power_interface_distance",
    "_rect_gap",
    "_repeated_alignment_penalty",
    "_segment_crosses_block",
    "_shortest_elbow_intrusion_count",
    "_signal_reachability",
    "_signal_relations",
    "_signal_row_alignment_components",
    "_signal_row_alignment_penalties",
    "_support_axis_alignment_penalty",
    "_unrelated_block_proximity",
    "compactness_whitespace_penalties",
    "composition_candidate_key",
    "route_backtracking_penalty",
    "route_branch_arm_spread",
    "semantic_composition_penalties",
    "semantic_composition_penalty_breakdown",
]
