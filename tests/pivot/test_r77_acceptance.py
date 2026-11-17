"""The R7.7 acceptance tests, recomputed on the committed v11 baseline (task P6-011s)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "fixtures/pivot/experiments/review_baseline_v11_2026-11-17_run1"


def test_the_recorded_r77_results_reproduce(tmp_path):
    from tools.pivot import run_r77_acceptance

    recorded = json.loads((BASELINE / "r77_acceptance.json").read_text())
    # Measure a copy, so the committed record is never rewritten.
    (tmp_path / "drawings").symlink_to(BASELINE / "drawings")
    run_r77_acceptance.main(["--baseline", str(tmp_path)])
    again = json.loads((tmp_path / "r77_acceptance.json").read_text())
    assert again["summary"] == recorded["summary"]
    assert again["results"] == recorded["results"]


def test_r77_outcomes_on_the_v11_baseline():
    summary = json.loads((BASELINE / "r77_acceptance.json").read_text())["summary"]
    for test in ("u_turns", "regulator_flow", "timer_output", "power_blocks"):
        assert all(summary[test].values()), (test, summary[test])
    # B01 and B02 carry the owner-accepted +5.08 mm return-stub wire; B02 also the
    # multi-unit box-leave artefact (P6-011p correction, 2026-11-17).
    assert summary["no_regressions"] == {
        "B06": True,
        "B13": True,
        "B01": False,
        "B02": False,
        "B07": True,
    }
