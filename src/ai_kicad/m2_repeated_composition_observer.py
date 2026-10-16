"""Repeated-structure observer for M2h2 human-composition evidence."""

from __future__ import annotations

import itertools
from collections.abc import Hashable
from dataclasses import dataclass
from fractions import Fraction

Point = tuple[int, int]


@dataclass(frozen=True)
class RepeatedMember:
    semantic_role: Hashable
    channel: Hashable
    position: Point
    orientation: int = 0


@dataclass(frozen=True)
class RepeatedCompositionMetrics:
    channel_count: int
    corresponding_symbol_count: int
    row_alignment_variance: Fraction
    column_alignment_variance: Fraction
    corresponding_displacement_variance: Fraction
    orientation_variance: int
    pitch_variance: Fraction


def measure_repeated_composition(
    members: tuple[RepeatedMember, ...],
) -> RepeatedCompositionMetrics:
    """Measure repeated-channel geometry without using names or declaration order."""
    by_channel: dict[Hashable, dict[Hashable, RepeatedMember]] = {}
    for member in members:
        channel = by_channel.setdefault(member.channel, {})
        if member.semantic_role in channel:
            raise ValueError("duplicate semantic role in repeated channel")
        channel[member.semantic_role] = member

    channels = tuple(by_channel.values())
    if len(channels) < 2:
        return RepeatedCompositionMetrics(
            len(channels), 0, Fraction(0), Fraction(0), Fraction(0), 0, Fraction(0)
        )

    common_roles = set(channels[0])
    for channel in channels[1:]:
        common_roles.intersection_update(channel)
    roles = tuple(sorted(common_roles, key=repr))

    row_samples: list[int] = []
    column_samples: list[int] = []
    displacement_samples: list[int] = []
    orientations: list[int] = []
    channel_centers: list[Point] = []

    for channel in channels:
        selected = [channel[role] for role in roles]
        if selected:
            xs = [member.position[0] for member in selected]
            ys = [member.position[1] for member in selected]
            channel_centers.append((sum(xs) // len(xs), sum(ys) // len(ys)))
            row_samples.extend(ys)
            column_samples.extend(xs)
            orientations.extend(member.orientation % 360 for member in selected)

    for role in roles:
        points = sorted(
            (channel[role].position for channel in channels), key=lambda p: (p[1], p[0])
        )
        origin = points[0]
        displacement_samples.extend(
            abs(point[0] - origin[0]) + abs(point[1] - origin[1]) for point in points[1:]
        )

    # Physical center ordering keeps channel pitch independent of user-facing
    # names and the declaration sequence. Use y then x so a horizontal row of
    # channels remains ordered by its physical x coordinate.
    channel_centers.sort(key=lambda p: (p[1], p[0]))
    pitches = [
        abs(second[0] - first[0]) + abs(second[1] - first[1])
        for first, second in itertools.pairwise(channel_centers)
    ]

    return RepeatedCompositionMetrics(
        channel_count=len(channels),
        corresponding_symbol_count=len(roles),
        row_alignment_variance=_variance(row_samples),
        column_alignment_variance=_variance(column_samples),
        corresponding_displacement_variance=_variance(displacement_samples),
        orientation_variance=len(set(orientations)) - 1 if orientations else 0,
        pitch_variance=_variance(pitches),
    )


def _variance(values: list[int]) -> Fraction:
    if len(values) < 2:
        return Fraction(0)
    mean = Fraction(sum(values), len(values))
    return sum((Fraction(value) - mean) ** 2 for value in values) / len(values)
