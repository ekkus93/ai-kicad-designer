"""Small semantic analog profile: strict terminals, shared anchors, deterministic geometry."""

from .m2b_constants import (
    EXTRA,
    LOCKED_PIN_ROLES,
    POWER_STAGE_ASSETS,
)
from .m2b_evaluation import (
    active_layout,
    compare,
)
from .m2b_layout import (
    Draft,
    _turn,
    choose_text_slots,
    measure,
    orientation_for_flow,
    passive_layout,
    power_stage_layout,
    timing_layout,
)
from .m2b_observation import (
    _local_pin_number_rectangles,
    check_observed_layout,
    pin_number_rectangles,
)
from .m2b_validation import (
    _fields,
    _validate_power_assertions,
    assets,
    validate,
)

__all__ = [
    "EXTRA",
    "LOCKED_PIN_ROLES",
    "POWER_STAGE_ASSETS",
    "Draft",
    "_fields",
    "_local_pin_number_rectangles",
    "_turn",
    "_validate_power_assertions",
    "active_layout",
    "assets",
    "check_observed_layout",
    "choose_text_slots",
    "compare",
    "measure",
    "orientation_for_flow",
    "passive_layout",
    "pin_number_rectangles",
    "power_stage_layout",
    "timing_layout",
    "validate",
]
