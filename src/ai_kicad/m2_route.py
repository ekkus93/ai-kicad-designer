"""Deterministic bounded route trees over fragment gateways and reservations."""

from __future__ import annotations

from .m2_route_build import (
    route_between_fragments,
)
from .m2_route_constants import (
    MAX_CANONICAL_LENGTH,
    MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE,
    MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH,
    MAX_ROUTE_STATES_PER_TAP,
    MAX_TAPS_PER_ATTACHMENT,
    MAX_TRACKS_PER_SIDE,
)
from .m2_route_core import (
    RouteBlockedConflict,
    RouteLengthBoundConflict,
    RouteTree,
    _advance,
    _bounded_tracks,
    _ceil_grid,
    _compact_collinear,
    _connect,
    _crosses,
    _direct_paths,
    _escape_obstacles,
    _floor_grid,
    _gateway,
    _gateway_channel,
    _interface_enclosures,
    _path_legal,
    _path_segments,
    _point_to_trunk_distance,
    _visibility_path,
)
from .m2_route_trees import (
    _distribution_initial_trees,
    _optional_local_visible_edges,
    _optional_reference_nets,
    _routable_edges,
    _route_class,
)

__all__ = [
    "MAX_CANONICAL_LENGTH",
    "MAX_LOCAL_VISIBLE_SIGNAL_DISTANCE",
    "MAX_LOCAL_VISIBLE_SIGNAL_ROUTE_LENGTH",
    "MAX_ROUTE_STATES_PER_TAP",
    "MAX_TAPS_PER_ATTACHMENT",
    "MAX_TRACKS_PER_SIDE",
    "RouteBlockedConflict",
    "RouteLengthBoundConflict",
    "RouteTree",
    "_advance",
    "_bounded_tracks",
    "_ceil_grid",
    "_compact_collinear",
    "_connect",
    "_crosses",
    "_direct_paths",
    "_distribution_initial_trees",
    "_escape_obstacles",
    "_floor_grid",
    "_gateway",
    "_gateway_channel",
    "_interface_enclosures",
    "_optional_local_visible_edges",
    "_optional_reference_nets",
    "_path_legal",
    "_path_segments",
    "_point_to_trunk_distance",
    "_routable_edges",
    "_route_class",
    "_visibility_path",
    "route_between_fragments",
]
