"""Portable tests for M2h2 interaction qualification runner evidence shape."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_m2h2_i1 import observed_structural_class  # noqa: E402


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
