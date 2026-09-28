"""Fail when Ruff formatting changes a selected original line range."""

from __future__ import annotations

import difflib
import os
import subprocess
import sys
from pathlib import Path

lo = int(os.environ["RANGE_LO"])
hi = int(os.environ["RANGE_HI"])
source = Path(os.environ["FORMAT_PATH"])
formatted = Path("/tmp/format_range_target.py")
formatted.write_text(source.read_text())
subprocess.run(
    [
        sys.executable,
        "-m",
        "ruff",
        "format",
        "--config",
        "pyproject.toml",
        str(formatted),
    ],
    check=True,
)
original_lines = source.read_text().splitlines()
formatted_lines = formatted.read_text().splitlines()
for tag, original_start, original_end, _formatted_start, _formatted_end in difflib.SequenceMatcher(
    a=original_lines,
    b=formatted_lines,
).get_opcodes():
    if tag != "equal" and original_start < hi and original_end >= lo - 1:
        diff = "\n".join(
            difflib.unified_diff(
                original_lines,
                formatted_lines,
                fromfile=str(source),
                tofile=f"ruff-format:{source}",
                lineterm="",
            )
        )
        raise AssertionError(
            f"Ruff formatting changed {source} original lines {lo}-{hi}.\n{diff}"
        )
