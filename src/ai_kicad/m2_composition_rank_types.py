"""Shared constants and public type aliases for the facade."""

from __future__ import annotations

Rect = tuple[int, int, int, int]


Point = tuple[int, int]


SemanticPenaltyVector = tuple[int, ...]


CompactnessPenaltyVector = tuple[int, int, int]


CandidateKey = tuple[int, ...]
