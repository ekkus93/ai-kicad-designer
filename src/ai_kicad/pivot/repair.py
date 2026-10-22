"""Bounded candidate repair loop that never mutates the known-good input."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class RepairResult:
    status: str
    accepted: Path | None
    attempts: int
    diagnostics: list[str]


def bounded_repair(
    known_good: Path,
    work: Path,
    propose: Callable[[Path, int], None],
    validate: Callable[[Path], tuple[bool, str]],
    *,
    limit: int,
) -> RepairResult:
    work.mkdir(parents=True, exist_ok=False)
    original = known_good.read_bytes()
    diagnostics = []
    for attempt in range(1, limit + 1):
        candidate = work / f"candidate-{attempt}{known_good.suffix}"
        shutil.copy2(known_good, candidate)
        propose(candidate, attempt)
        passed, diagnostic = validate(candidate)
        diagnostics.append(diagnostic)
        if passed:
            if known_good.read_bytes() != original:
                raise RuntimeError("known-good input changed during repair")
            return RepairResult("PASS", candidate, attempt, diagnostics)
    if known_good.read_bytes() != original:
        raise RuntimeError("known-good input changed during repair")
    return RepairResult("BLOCKED", None, limit, diagnostics)
