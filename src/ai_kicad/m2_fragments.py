"""Local geometry constructors for instance-based M2 schematic composition."""

from __future__ import annotations

from .m2_fragments_types import (
    Point,
    Rect,
)

from .m2_fragments_base import (
    FragmentVariant,
    PortAnchor,
    _body_rect,
    _clear_nonpassive_text,
    _component,
    _occupied_geometry,
    _placed_terminal_points,
    _relationship,
    _reservation_envelope,
    _terminal_net,
)
from .m2_fragments_builders import (
    _amplifier_fragment,
    _interface_fragment,
    _new_draft,
    _package_fragment,
    _passive_fragment,
    _power_stage_fragment,
    _reference_divider_fragment,
    _timer_fragment,
)
from .m2_fragments_geometry import (
    _finish,
)
from .m2_fragments_variants import (
    _access_alternatives,
    fragment_variants,
)

__all__ = [
    "FragmentVariant",
    "Point",
    "PortAnchor",
    "Rect",
    "_access_alternatives",
    "_amplifier_fragment",
    "_body_rect",
    "_clear_nonpassive_text",
    "_component",
    "_finish",
    "_interface_fragment",
    "_new_draft",
    "_occupied_geometry",
    "_package_fragment",
    "_passive_fragment",
    "_placed_terminal_points",
    "_power_stage_fragment",
    "_reference_divider_fragment",
    "_relationship",
    "_reservation_envelope",
    "_terminal_net",
    "_timer_fragment",
    "fragment_variants",
]
