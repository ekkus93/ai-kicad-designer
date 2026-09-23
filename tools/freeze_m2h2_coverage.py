"""Preregister finite M2h2 interaction coverage and historical integrity."""

from __future__ import annotations

import hashlib
import json
import subprocess
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures/m2h2/development"
FACTORS = {
    "serial_depth": ("1", "2", "3+"),
    "parallel_breadth": ("1", "2", "3+"),
    "active_cores": ("0", "1", "2", "3+"),
    "shared_packages": ("0", "1", "2+"),
    "supply_consumers": ("1", "2", "3+"),
    "branch_degree": ("1", "2", "3+"),
    "reference": ("external", "internal", "distinct"),
    "support_count": ("0", "1-2", "3+"),
    "protected_paths": ("local", "cross", "mixed"),
    "distribution_consumers": ("1", "2", "3+"),
    "bands": ("one", "multiple", "interleaved"),
    "text_stress": ("nominal", "long"),
}
ROWS = {
    "I1": (("serial_depth", "branch_degree"),),
    "I2": (("reference", "distribution_consumers"),),
    "I3": (("active_cores", "bands"),),
    "I4": (("parallel_breadth", "protected_paths"),),
    "I5": (("supply_consumers", "support_count"),),
    "I6": (
        ("shared_packages", "reference"),
        ("text_stress", "support_count"),
        ("text_stress", "branch_degree"),
    ),
}
TRIPLES = {
    "I1": ("passive_intermediate", "active_successor", "multiple_bands"),
    "I2": ("internal_reference", "parked_input", "shunt_return"),
    "I3": ("two_tall_cores", "shared_package", "long_text"),
    "I4": ("unequal_consumers", "cross_fragment_bound", "sibling_vertical_order"),
    "I5": ("three_gateway_distribution", "multiple_shelves", "restricted_entry"),
}


def cell(row: str, pair: tuple[str, str], a: str, b: str) -> str:
    return f"{row}:{pair[0]}={a}|{pair[1]}={b}"


def all_cells() -> dict[str, list[str]]:
    return {
        row: [
            cell(row, pair, a, b)
            for pair in pairs
            for a, b in product(FACTORS[pair[0]], FACTORS[pair[1]])
        ]
        for row, pairs in ROWS.items()
    }


def cover(vector: dict[str, str]) -> set[str]:
    return {
        cell(row, pair, vector[pair[0]], vector[pair[1]])
        for row, pairs in ROWS.items()
        for pair in pairs
    }


def candidates() -> list[dict[str, str]]:
    baseline = {name: levels[0] for name, levels in FACTORS.items()}
    found: dict[tuple[str, ...], dict[str, str]] = {}
    for pairs in ROWS.values():
        for first, second in pairs:
            for a, b in product(FACTORS[first], FACTORS[second]):
                vector = dict(baseline)
                vector[first], vector[second] = a, b
                found[tuple(vector.values())] = vector
    # Finite cross-row assignments improve packing without random sampling.
    for index in range(81):
        vector = {
            name: levels[(index // (3 ** (offset % 4)) + offset) % len(levels)]
            for offset, (name, levels) in enumerate(FACTORS.items())
        }
        found[tuple(vector.values())] = vector
    return [found[key] for key in sorted(found)]


def greedy() -> list[dict]:
    required = set().union(*all_cells().values())
    remaining = set(required)
    options = candidates()
    selected = []
    while remaining:
        best = max(
            options,
            key=lambda vector: (
                len(cover(vector) & remaining),
                tuple(-FACTORS[name].index(vector[name]) for name in FACTORS),
            ),
        )
        newly = sorted(cover(best) & remaining)
        if not newly:
            raise RuntimeError(f"uncovered semantic cells: {sorted(remaining)}")
        selected.append(
            {
                "id": f"IC{len(selected) + 1:02d}",
                "factors": best,
                "planned_cells": newly,
                "result": "not_evaluated",
            }
        )
        remaining.difference_update(newly)
        options.remove(best)
    return selected


def historical_hashes() -> dict:
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "fixtures", "docs", "src", "tests"], cwd=ROOT
    ).split(b"\0")
    groups: dict[str, list[tuple[str, str]]] = {}
    for raw in files:
        if not raw:
            continue
        relative = raw.decode()
        if relative.startswith(("fixtures/m2h2/", ".local/", "research/legacy_openclaw/")):
            continue
        path = ROOT / relative
        if not path.is_file():
            continue
        group = relative.split("/", 2)[0]
        if group == "fixtures":
            group = "/".join(relative.split("/", 2)[:2])
        groups.setdefault(group, []).append(
            (relative, hashlib.sha256(path.read_bytes()).hexdigest())
        )
    return {
        group: {
            "file_count": len(entries),
            "sha256": hashlib.sha256(json.dumps(sorted(entries)).encode()).hexdigest(),
        }
        for group, entries in sorted(groups.items())
    }


def main() -> None:
    path = OUT / "interaction_coverage.json"
    hashes = OUT / "historical_integrity.json"
    if path.exists() or hashes.exists():
        raise SystemExit("M2h2 coverage freeze already exists; refusing to rewrite")
    if not (OUT / "manifest.json").is_file():
        raise SystemExit("freeze probes before coverage")
    required = all_cells()
    manifest = {
        "schema_version": "m2h2.interaction-coverage.1",
        "frozen_before_layout_tuning": True,
        "factors": FACTORS,
        "rows": {
            row: {
                "factor_pairs": pairs,
                "required_cells": required[row],
                "covered_cells": [],
                "unsupported_cells": [],
                "selected_triple": TRIPLES.get(row),
                "selected_triple_status": "not_evaluated" if row in TRIPLES else None,
            }
            for row, pairs in ROWS.items()
        },
        "selected_cases": greedy(),
        "coverage_rule": "A cell passes only after every expected invariant passes; planned cells are not covered.",
        "mutation_dimensions": [
            "80mm_below_exact_above",
            "spread_below_exact_above",
            "alternate_trunk",
            "reference_connector_present_absent",
            "unit_exchange",
            "set_permutation",
            "translate_reflect",
            "extra_consumer",
            "sibling_order",
        ],
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    hashes.write_text(
        json.dumps(
            {"schema_version": "m2h2.historical-integrity.1", "groups": historical_hashes()},
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
