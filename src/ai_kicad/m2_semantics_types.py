"""Shared constants and public type aliases for the facade."""

from __future__ import annotations

from typing import Literal

Occurrence = tuple[str, int]


Terminal = tuple[str, str]


PortRole = Literal[
    "signal_in",
    "signal_out",
    "power_in",
    "power_out",
    "reference",
    "passive",
]


EdgeKind = Literal[
    "signal",
    "power",
    "reference",
    "support",
    "feedback",
    "branch",
    "package",
]
