"""Allocate write-once experiment directories on the pivot branch."""

from __future__ import annotations

import re
from pathlib import Path


def create_experiment_dir(repository_root: Path, experiment_id: str) -> Path:
    """Create a new pivot experiment directory and reject protected paths."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", experiment_id):
        raise ValueError("invalid experiment ID")
    repository_root = repository_root.resolve()
    protected_root = (repository_root / "fixtures/m2h2").resolve()
    output_root = (repository_root / "fixtures/pivot/experiments").resolve()
    if output_root.is_relative_to(protected_root):
        raise ValueError("experiment root overlaps protected M2H2 fixture tree")
    if not output_root.is_relative_to(repository_root):
        raise ValueError("experiment root escapes repository")
    destination = output_root / experiment_id
    if not destination.resolve().is_relative_to(output_root):
        raise ValueError("experiment path escapes pivot experiment root")
    destination.mkdir(parents=True, exist_ok=False)
    return destination
