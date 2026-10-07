"""Frozen, complexity-aware composition tolerances for M2h2.

The thresholds here are expressed only in generic semantic/geometry terms.  They
are deliberately independent of fixture IDs, reference designators, net names,
and qualification groups.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Complexity:
    block_count: int
    visible_symbol_count: int
    semantic_edge_count: int

    def __post_init__(self) -> None:
        if min(self.block_count, self.visible_symbol_count, self.semantic_edge_count) < 0:
            raise ValueError("complexity counts must be non-negative")


@dataclass(frozen=True)
class CompositionTolerance:
    band: str
    minimum_occupied_ratio: float | None
    maximum_centroid_offset_mm: float
    maximum_whitespace_imbalance: float
    maximum_repeated_alignment_variance_mm: float
    maximum_normalized_bend_excess: float
    maximum_normalized_length_excess: float


# Tiny probes have no minimum utilization requirement, but all other dispersion,
# routing, and alignment limits remain active.
FROZEN_TOLERANCES = {
    "tiny": CompositionTolerance("tiny", None, 65.0, 0.85, 5.0, 3.0, 2.5),
    "small": CompositionTolerance("small", 0.025, 55.0, 0.75, 4.0, 2.5, 2.0),
    "medium": CompositionTolerance("medium", 0.055, 45.0, 0.65, 3.0, 2.0, 1.75),
    "dense": CompositionTolerance("dense", 0.10, 35.0, 0.55, 2.5, 1.5, 1.5),
}


def complexity_band(value: Complexity) -> str:
    """Classify semantic complexity using monotone generic corpus dimensions."""
    load = value.block_count * 3 + value.visible_symbol_count + value.semantic_edge_count
    if value.visible_symbol_count <= 3 and value.block_count <= 1 and load <= 8:
        return "tiny"
    if load <= 24:
        return "small"
    if load <= 60:
        return "medium"
    return "dense"


def tolerance_for(value: Complexity) -> CompositionTolerance:
    return FROZEN_TOLERANCES[complexity_band(value)]


def within_upper_bound(value: float, bound: float, *, grid_mm: float = 0.5) -> bool:
    """Inclusive exact boundary used by observer/oracle acceptance tests."""
    if grid_mm <= 0:
        raise ValueError("grid_mm must be positive")
    return value <= bound


def within_lower_bound(value: float, bound: float | None, *, grid_mm: float = 0.5) -> bool:
    """Inclusive minimum; None is the explicit tiny-probe utilization exemption."""
    if grid_mm <= 0:
        raise ValueError("grid_mm must be positive")
    return bound is None or value >= bound
