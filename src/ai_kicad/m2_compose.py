"""Instance-based composition of qualified M2 schematic fragments."""

from __future__ import annotations

from .m2_compose_candidate import (
    LayoutBudgetError,
    StageGraph,
    _assemble_candidate,
    _missing_interface_output_routes,
    _missing_optional_reference_routes,
    _route_interface_enclosure_count,
    _source_marker_placement,
    _structural_signature,
    _translate,
    _translated_rect,
    stage_graph,
)
from .m2_compose_repairs import (
    ConductorLengthConflict,
    _distribution_repack,
    _reservation_growth_repack,
    _structural_repack,
    _substitution_repack,
)
from .m2_compose_workflow import (
    compose_layout,
    compose_with_evidence,
)

__all__ = [
    "ConductorLengthConflict",
    "LayoutBudgetError",
    "StageGraph",
    "_assemble_candidate",
    "_distribution_repack",
    "_missing_interface_output_routes",
    "_missing_optional_reference_routes",
    "_reservation_growth_repack",
    "_route_interface_enclosure_count",
    "_source_marker_placement",
    "_structural_repack",
    "_structural_signature",
    "_substitution_repack",
    "_translate",
    "_translated_rect",
    "compose_layout",
    "compose_with_evidence",
    "stage_graph",
]
