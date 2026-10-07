"""Independent repeated-structure composition observer."""
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class RepeatedMember:
    member_id: str
    channel_id: str
    semantic_slot: str
    center: tuple[int, int]
    orientation: int = 0

@dataclass(frozen=True)
class RepeatedStructureMetrics:
    row_alignment_variance: int
    column_alignment_variance: int
    corresponding_displacement_variance: int
    orientation_variance: int
    pitch_variance: int

def _spread(values):
    values = tuple(values)
    return 0 if not values else max(values) - min(values)

def measure_repeated_structure(members: tuple[RepeatedMember, ...]) -> RepeatedStructureMetrics:
    channels = defaultdict(list)
    slots = defaultdict(list)
    for member in members:
        channels[member.channel_id].append(member)
        slots[member.semantic_slot].append(member)
    row = sum(_spread(m.center[1] for m in group) for group in channels.values())
    column = sum(_spread(m.center[0] for m in group) for group in slots.values())
    orientation = sum(_spread(m.orientation for m in group) for group in slots.values())
    displacement = []
    for group in slots.values():
        ordered = sorted(group, key=lambda m: m.channel_id)
        displacement += [abs(b.center[1] - a.center[1]) for a, b in zip(ordered, ordered[1:])]
    pitches = []
    for group in channels.values():
        ordered = sorted(group, key=lambda m: (m.semantic_slot, m.member_id))
        pitches += [abs(b.center[0] - a.center[0]) for a, b in zip(ordered, ordered[1:])]
    return RepeatedStructureMetrics(row, column, _spread(displacement), orientation, _spread(pitches))
