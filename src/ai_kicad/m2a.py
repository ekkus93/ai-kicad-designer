"""Bounded multi-unit op-amp experiment; M1's compiler remains independent."""

from .assets import _extract_symbol
from .m2a_artifacts import (
    check_observed_layout,
    compare,
    emit,
    observe,
    one_xml,
    verify_serialized_scene,
)
from .m2a_constants import (
    ASSETS,
    FILES,
    PITCH,
    ROOT,
)
from .m2a_core import (
    Asset,
    Pin,
    Scene,
    _assert_scene_certificate,
    _member,
    _nm,
    _uid,
    certify_scene_geometry,
    certify_scene_inputs,
    check_layout,
    fixture,
    layout,
    load_assets,
    scene_geometry_digest,
    scene_input_digest,
    validate,
)
from .schematic import _mm

__all__ = [
    "ASSETS",
    "FILES",
    "PITCH",
    "ROOT",
    "Asset",
    "Pin",
    "Scene",
    "_assert_scene_certificate",
    "_extract_symbol",
    "_member",
    "_mm",
    "_nm",
    "_uid",
    "certify_scene_geometry",
    "certify_scene_inputs",
    "check_layout",
    "check_observed_layout",
    "compare",
    "emit",
    "fixture",
    "layout",
    "load_assets",
    "observe",
    "one_xml",
    "scene_geometry_digest",
    "scene_input_digest",
    "validate",
    "verify_serialized_scene",
]
