from dataclasses import replace

import pytest

from ai_kicad.m2_composition_reproducibility import (
    RunFingerprint,
    compare_five_runs,
)


BASE = RunFingerprint(
    project_sha256="project",
    semantic_class="linear-flow",
    normalized_render_sha256="render",
    metric_vector_sha256="metrics",
    candidate_decision_sha256="candidate",
)


def test_five_identical_runs_pass() -> None:
    result = compare_five_runs((BASE,) * 5)
    assert result.passed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_sha256", "changed-project"),
        ("semantic_class", "changed-class"),
        ("normalized_render_sha256", "changed-render"),
        ("metric_vector_sha256", "changed-metrics"),
        ("candidate_decision_sha256", "changed-candidate"),
    ],
)
def test_each_reproducibility_dimension_is_independently_required(
    field: str,
    value: str,
) -> None:
    runs = (BASE, BASE, BASE, BASE, replace(BASE, **{field: value}))
    result = compare_five_runs(runs)
    assert not result.passed


def test_non_five_run_evidence_is_rejected() -> None:
    with pytest.raises(ValueError):
        compare_five_runs((BASE,) * 4)
