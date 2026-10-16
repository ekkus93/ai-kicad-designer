"""Instance-based semantic planning for the qualified M2 schematic profile."""

from __future__ import annotations

from .m2_semantics_types import (
    Occurrence,
    Terminal,
    PortRole,
    EdgeKind,
)

from .m2_semantics_core import (
    BlockPlan,
    LocalSpanObligation,
    PhysicalTerminalObligation,
    PlacementConflict,
    PresentationNet,
    SemanticConstraint,
    SemanticEdge,
    SemanticPlan,
    SemanticPort,
    SignalPrecedence,
    _amp_block,
    _function,
    _indices,
    _port,
    check_placement_constraints,
)
from .m2_semantics_plan import (
    semantic_plan,
)

__all__ = [
    "BlockPlan",
    "EdgeKind",
    "LocalSpanObligation",
    "Occurrence",
    "PhysicalTerminalObligation",
    "PlacementConflict",
    "PortRole",
    "PresentationNet",
    "SemanticConstraint",
    "SemanticEdge",
    "SemanticPlan",
    "SemanticPort",
    "SignalPrecedence",
    "Terminal",
    "_amp_block",
    "_function",
    "_indices",
    "_port",
    "check_placement_constraints",
    "semantic_plan",
]
