"""Independent functional grouping and locality oracle.

This module scores emitted placements from semantic block membership and visual
ownership only.  It is intentionally independent of production placement
scores, candidate ranks, fixture names, refdes strings, and literal net names.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

Point = tuple[int, int]
PenaltyVector = tuple[int, int, int, int, int]


@dataclass(frozen=True)
class GroupMember:
    member_id: str
    block_id: str
    center: Point
    owner_id: str | None = None
    ownership: str = "block"
    chain_rank: int | None = None
    label_mediated: bool = False


@dataclass(frozen=True)
class GroupingWitness:
    kind: str
    member_ids: tuple[str, ...]
    penalty: int


@dataclass(frozen=True)
class GroupingCandidateScore:
    candidate_id: str
    intra_block_penalty: int
    inter_block_penalty: int
    ownership_penalty: int
    series_order_penalty: int
    label_disconnect_penalty: int
    witnesses: tuple[GroupingWitness, ...]

    @property
    def penalty_vector(self) -> PenaltyVector:
        return (
            self.intra_block_penalty,
            self.inter_block_penalty,
            self.ownership_penalty,
            self.series_order_penalty,
            self.label_disconnect_penalty,
        )


def evaluate_grouping_candidate(
    candidate_id: str,
    members: tuple[GroupMember, ...],
    *,
    cohesion_limit: int = 40,
    separation_limit: int = 10,
    ownership_limit: int = 60,
) -> GroupingCandidateScore:
    """Score one placement candidate with deterministic grouping penalties."""
    by_id = {member.member_id: member for member in members}
    block_members = _by_block(members)
    witnesses: list[GroupingWitness] = []

    intra = _intra_block_penalty(block_members, cohesion_limit, witnesses)
    inter = _inter_block_penalty(block_members, separation_limit, witnesses)
    ownership = _ownership_penalty(members, by_id, ownership_limit, witnesses)
    series = _series_order_penalty(members, witnesses)
    label = _label_disconnect_penalty(members, by_id, ownership_limit, witnesses)

    return GroupingCandidateScore(
        candidate_id, intra, inter, ownership, series, label, tuple(witnesses)
    )


def non_dominated_grouping_candidates(
    scores: tuple[GroupingCandidateScore, ...],
) -> tuple[GroupingCandidateScore, ...]:
    """Return candidates not dominated by another score vector."""
    survivors = [score for score in scores if not _is_dominated(score, scores)]
    return tuple(sorted(survivors, key=lambda item: (item.penalty_vector, item.candidate_id)))


def _by_block(members: tuple[GroupMember, ...]) -> dict[str, tuple[GroupMember, ...]]:
    grouped: dict[str, list[GroupMember]] = {}
    for member in members:
        if member.ownership == "shared":
            continue
        grouped.setdefault(member.block_id, []).append(member)
    return {block_id: tuple(items) for block_id, items in grouped.items()}


def _intra_block_penalty(
    block_members: dict[str, tuple[GroupMember, ...]],
    cohesion_limit: int,
    witnesses: list[GroupingWitness],
) -> int:
    total = 0
    for block_id, members in sorted(block_members.items()):
        if len(members) < 2:
            continue
        diameter = max(
            _manhattan(first.center, second.center) for first, second in combinations(members, 2)
        )
        penalty = max(0, diameter - cohesion_limit)
        if penalty:
            total += penalty
            witnesses.append(
                GroupingWitness(
                    "intra_block_dispersion",
                    tuple(sorted(member.member_id for member in members)),
                    penalty,
                )
            )
    return total


def _inter_block_penalty(
    block_members: dict[str, tuple[GroupMember, ...]],
    separation_limit: int,
    witnesses: list[GroupingWitness],
) -> int:
    total = 0
    for left_id, right_id in combinations(sorted(block_members), 2):
        gap = _bbox_gap(block_members[left_id], block_members[right_id])
        penalty = max(0, separation_limit - gap)
        if penalty:
            total += penalty
            witnesses.append(
                GroupingWitness("inter_block_separation", (left_id, right_id), penalty)
            )
    return total


def _ownership_penalty(
    members: tuple[GroupMember, ...],
    by_id: dict[str, GroupMember],
    ownership_limit: int,
    witnesses: list[GroupingWitness],
) -> int:
    total = 0
    for member in sorted(members, key=lambda item: item.member_id):
        if member.ownership not in {"support", "feedback"} or member.owner_id is None:
            continue
        owner = by_id.get(member.owner_id)
        if owner is None:
            continue
        distance = _manhattan(member.center, owner.center)
        penalty = max(0, distance - ownership_limit)
        if penalty:
            total += penalty
            witnesses.append(
                GroupingWitness(
                    f"{member.ownership}_owner_distance",
                    (member.member_id, owner.member_id),
                    penalty,
                )
            )
    return total


def _series_order_penalty(
    members: tuple[GroupMember, ...], witnesses: list[GroupingWitness]
) -> int:
    total = 0
    ranked = sorted(
        (member for member in members if member.chain_rank is not None),
        key=lambda item: (item.block_id, item.chain_rank, item.member_id),
    )
    for previous, current in zip(ranked, ranked[1:], strict=False):
        if previous.block_id != current.block_id:
            continue
        if current.center[0] < previous.center[0]:
            penalty = previous.center[0] - current.center[0]
            total += penalty
            witnesses.append(
                GroupingWitness(
                    "passive_series_reversal",
                    (previous.member_id, current.member_id),
                    penalty,
                )
            )
    return total


def _label_disconnect_penalty(
    members: tuple[GroupMember, ...],
    by_id: dict[str, GroupMember],
    ownership_limit: int,
    witnesses: list[GroupingWitness],
) -> int:
    total = 0
    for member in sorted(members, key=lambda item: item.member_id):
        if not member.label_mediated or member.owner_id is None:
            continue
        owner = by_id.get(member.owner_id)
        if owner is None:
            continue
        distance = _manhattan(member.center, owner.center)
        penalty = max(0, distance - ownership_limit)
        if penalty:
            total += penalty
            witnesses.append(
                GroupingWitness(
                    "label_mediated_local_disconnect",
                    (member.member_id, owner.member_id),
                    penalty,
                )
            )
    return total


def _is_dominated(
    score: GroupingCandidateScore, scores: tuple[GroupingCandidateScore, ...]
) -> bool:
    for other in scores:
        if other.candidate_id == score.candidate_id:
            continue
        if _dominates(other.penalty_vector, score.penalty_vector):
            return True
    return False


def _dominates(left: PenaltyVector, right: PenaltyVector) -> bool:
    return all(a <= b for a, b in zip(left, right, strict=True)) and any(
        a < b for a, b in zip(left, right, strict=True)
    )


def _bbox_gap(left: tuple[GroupMember, ...], right: tuple[GroupMember, ...]) -> int:
    left_x = [member.center[0] for member in left]
    left_y = [member.center[1] for member in left]
    right_x = [member.center[0] for member in right]
    right_y = [member.center[1] for member in right]
    x_gap = max(0, max(min(right_x) - max(left_x), min(left_x) - max(right_x)))
    y_gap = max(0, max(min(right_y) - max(left_y), min(left_y) - max(right_y)))
    return x_gap + y_gap


def _manhattan(first: Point, second: Point) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
