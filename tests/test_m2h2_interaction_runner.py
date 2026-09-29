"""Portable tests for M2h2 interaction qualification runner evidence shape."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_m2h2_i1 import (  # noqa: E402
    observed_structural_class,
    validate_coverage_ledger_evidence,
    validate_coverage_ledger_impossibilities,
)


def test_observed_structural_class_uses_selected_run_evidence_not_requested_label() -> None:
    signature = {
        "composition": {
            "structural_search": {
                "seeds": [
                    {
                        "seed": 0,
                        "placement_class": "requested-factor-label",
                        "structure": [["wrong", "seed"]],
                    },
                    {
                        "seed": 3,
                        "placement_class": "actual-observed-band",
                        "structure": [["actual", "seed"]],
                    },
                ]
            },
            "candidate_selection": {
                "selected_seed": 3,
                "selected_round": 2,
                "proved_candidates": [
                    {"seed": 0, "round": 0, "structure": [["wrong", "candidate"]]},
                    {"seed": 3, "round": 2, "structure": [["proved", "actual"]]},
                ],
            },
        }
    }

    assert observed_structural_class(signature) == {
        "source": "composition.candidate_selection",
        "selected_seed": 3,
        "selected_round": 2,
        "placement_class": "actual-observed-band",
        "structure": [["proved", "actual"]],
    }


def test_current_coverage_ledger_has_no_invalid_evidence_records() -> None:
    ledger = __import__("json").loads(
        (ROOT / "fixtures/m2h2/development/interaction_coverage.json").read_text()
    )

    validate_coverage_ledger_evidence(ledger)


def test_covered_cells_require_real_tool_evidence_not_parse_or_generation_only() -> None:
    ledger = {
        "rows": {
            "I1": {
                "covered_cells": [
                    {
                        "cell": "I1:serial_depth=1|branch_degree=1",
                        "real_tool_qualification_evidence": {
                            "schema_version": "m2h2.real-tool-evidence.1",
                            "locked_kicad_version": "10.0.6",
                            "exact_head_sha": "f" * 40,
                            "qualification_root": "fixtures/m2h2/interaction_final/run1",
                            "results_json": "fixtures/m2h2/interaction_final/results.json",
                            "case_id": "m2h2_i1_d1_b1",
                            "runs": ["fixtures/m2h2/interaction_final/m2h2_i1_d1_b1/run1"],
                        },
                    }
                ],
                "unsupported_cells": [],
            }
        }
    }
    validate_coverage_ledger_evidence(ledger)

    evidence = ledger["rows"]["I1"]["covered_cells"][0]["real_tool_qualification_evidence"]
    evidence["parse_success"] = True
    evidence["requested_factor_label"] = "I1:serial_depth=1|branch_degree=1"
    with pytest.raises(ValueError, match="parse/generation/planned-label"):
        validate_coverage_ledger_evidence(ledger)


def test_unsupported_cells_require_semantic_impossibility_not_layout_failure() -> None:
    ledger = {
        "rows": {
            "I3": {
                "unsupported_cells": [
                    {
                        "cell": "I3:active_cores=0|bands=interleaved",
                        "semantic_impossibility_witness": {
                            "schema_version": "m2h2.semantic-impossibility.1",
                            "kind": "semantic_impossibility",
                            "source": "semantic_model",
                            "proof": "A passive-only circuit has no active-core band class.",
                        },
                    }
                ]
            }
        }
    }
    validate_coverage_ledger_impossibilities(ledger)

    ledger["rows"]["I3"]["unsupported_cells"][0]["semantic_impossibility_witness"] = {
        "schema_version": "m2h2.semantic-impossibility.1",
        "kind": "semantic_impossibility",
        "source": "semantic_model",
        "proof": "This is not semantic proof when it cites a failed layout run.",
        "returncode": 2,
        "failure": "layout did not fit",
    }
    with pytest.raises(ValueError, match="layout/build failure keys"):
        validate_coverage_ledger_impossibilities(ledger)
