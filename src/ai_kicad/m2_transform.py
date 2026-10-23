"""Orthogonal symbol transforms shared by planning and serialization checks."""

from __future__ import annotations


def transform_library_point(
    x: int, y: int, angle: int, mirror: str | None = None
) -> tuple[int, int]:
    """Transform a KiCad library point into sheet coordinates."""
    local_x, local_y = x, -y
    if mirror == "x":
        local_y = -local_y
    elif mirror == "y":
        local_x = -local_x
    elif mirror is not None:
        raise ValueError(f"unsupported KiCad mirror axis: {mirror}")
    try:
        return {
            0: (local_x, local_y),
            90: (local_y, -local_x),
            180: (-local_x, -local_y),
            270: (-local_y, local_x),
        }[angle]
    except KeyError as exc:
        raise ValueError(f"unsupported KiCad symbol angle: {angle}") from exc
