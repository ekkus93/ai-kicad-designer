"""Independent locality measurements for serialized KiCad component fields."""

from __future__ import annotations

import math

from ai_kicad.m2_text_layout import property_page_angle, text_extents
from ai_kicad.sexpr import children, one


def measure_field_locality(tree: list, maximum_mm: float = 25.4) -> dict:
    """Bound the nearest visible field edge's distance to its own symbol anchor."""
    if not math.isfinite(maximum_mm) or maximum_mm <= 0:
        raise ValueError("maximum field distance must be positive and finite")
    measured = []
    for symbol in children(tree, "symbol"):
        properties = {p[1]: p for p in children(symbol, "property")}
        reference = properties["Reference"][2]
        anchor = one(symbol, "at")
        sx, sy, rotation = float(anchor[1]), float(anchor[2]), int(float(anchor[3]))
        for field in ("Reference", "Value"):
            prop = properties.get(field)
            if prop is None or children(prop, "hide"):
                continue
            effects = children(prop, "effects")
            if effects and (children(effects[0], "hide") or "hide" in effects[0]):
                continue
            scale = 1.0
            if effects:
                size = one(one(effects[0], "font"), "size")
                scale = max(float(size[1]), float(size[2])) / 1.27
            at = one(prop, "at")
            x, y = float(at[1]), float(at[2])
            angle = property_page_angle(rotation, int(float(at[3])))
            width, height = text_extents(prop[2], angle)
            dx = max(0, abs(x - sx) - width / 2e6 * scale)
            dy = max(0, abs(y - sy) - height / 2e6 * scale)
            distance = math.hypot(dx, dy)
            if not all(math.isfinite(n) for n in (sx, sy, x, y, distance)):
                raise ValueError("nonfinite native field coordinate")
            measured.append(
                {
                    "reference": reference,
                    "unit": int(one(symbol, "unit")[1]),
                    "field": field,
                    "distance_mm": round(distance, 6),
                    "within_limit": distance <= maximum_mm,
                }
            )
    return {
        "maximum_mm": maximum_mm,
        "fields": measured,
        "witnesses": [item for item in measured if not item["within_limit"]],
    }


def measure_field_association(tree: list, minimum_owner_advantage_mm: float = 5.08) -> dict:
    """Catch a field that is substantially closer to another symbol than its owner.

    The margin is four drafting pitches. Smaller nearest-symbol differences remain a
    visual-review question because dense but valid symbol groups can put nearby
    component anchors close together.
    """
    if not math.isfinite(minimum_owner_advantage_mm) or minimum_owner_advantage_mm < 0:
        raise ValueError("minimum owner-advantage margin must be finite and nonnegative")

    symbols = []
    for symbol in children(tree, "symbol"):
        properties = {prop[1]: prop for prop in children(symbol, "property")}
        anchor = one(symbol, "at")
        symbols.append(
            (
                properties["Reference"][2],
                int(one(symbol, "unit")[1]),
                float(anchor[1]),
                float(anchor[2]),
                int(float(anchor[3])),
                properties,
            )
        )

    measured = []
    for reference, unit, sx, sy, symbol_angle, properties in symbols:
        for field in ("Reference", "Value"):
            prop = properties.get(field)
            if prop is None or children(prop, "hide"):
                continue
            effects = children(prop, "effects")
            if effects and (children(effects[0], "hide") or "hide" in effects[0]):
                continue
            scale = 1.0
            if effects:
                size = one(one(effects[0], "font"), "size")
                scale = max(float(size[1]), float(size[2])) / 1.27
            at = one(prop, "at")
            x, y = float(at[1]), float(at[2])
            angle = property_page_angle(symbol_angle, int(float(at[3])))
            width, height = text_extents(prop[2], angle)
            half_width, half_height = width / 2e6 * scale, height / 2e6 * scale

            def edge_distance(ax: float, ay: float) -> float:
                dx = max(0.0, abs(x - ax) - half_width)
                dy = max(0.0, abs(y - ay) - half_height)
                return math.hypot(dx, dy)

            owner_distance = edge_distance(sx, sy)
            other_distances = [
                (edge_distance(ox, oy), other_ref, other_unit)
                for other_ref, other_unit, ox, oy, _, _ in symbols
                if other_ref != reference
            ]
            nearest_other = min(other_distances, default=None)
            other_distance = nearest_other[0] if nearest_other is not None else math.inf
            owner_advantage = owner_distance - other_distance
            measured.append(
                {
                    "reference": reference,
                    "unit": unit,
                    "field": field,
                    "owner_edge_distance_mm": round(owner_distance, 6),
                    "nearest_other_reference": nearest_other[1] if nearest_other else None,
                    "nearest_other_unit": nearest_other[2] if nearest_other else None,
                    "nearest_other_edge_distance_mm": round(other_distance, 6),
                    "owner_advantage_mm": round(owner_advantage, 6),
                    "within_limit": owner_advantage <= minimum_owner_advantage_mm,
                }
            )
    return {
        "minimum_owner_advantage_mm": minimum_owner_advantage_mm,
        "fields": measured,
        "witnesses": [item for item in measured if not item["within_limit"]],
    }
