"""Audit workflows must evaluate the exact SHA of persisted qualification evidence."""

from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
AUDITS = [
    (
        "m2h2-final-artifact-audit.yml",
        "- name: Audit exact final evidence and report comparison diagnostics",
    ),
    (
        "m2h2-persisted-native-render-inventory.yml",
        "- name: Verify and hash native KiCad renders from persisted qualification",
    ),
]


@pytest.mark.parametrize(("workflow_name", "audit_step"), AUDITS)
def test_audit_checks_out_and_verifies_qualified_source_before_running(
    workflow_name: str, audit_step: str
) -> None:
    workflow = (WORKFLOWS / workflow_name).read_text()
    resolve = workflow.index("- name: Resolve exact persisted qualification root")
    checkout = workflow.index("- name: Check out exact persisted qualification source")
    ref = workflow.index("ref: ${{ steps.evidence.outputs.source_sha }}")
    verify = workflow.index("- name: Verify exact qualification source checkout")
    install = workflow.index("- name: Install exact qualification source")
    audit = workflow.index(audit_step)

    assert resolve < checkout < ref < verify < install < audit
    assert workflow.count("ref: ${{ steps.evidence.outputs.source_sha }}") == 1
    verify_block = workflow[verify:install]
    assert "git rev-parse HEAD" in verify_block
    assert '"$observed_sha" != "$SOURCE_SHA"' in verify_block
    assert "SOURCE_SHA: ${{ steps.evidence.outputs.source_sha }}" in verify_block
    assert "python -m pip install -e '.[dev]'" in workflow[install:audit]


@pytest.mark.parametrize(("workflow_name", "audit_step"), AUDITS)
def test_audit_preserves_external_evidence_and_uses_resolved_source_sha(
    workflow_name: str, audit_step: str
) -> None:
    workflow = (WORKFLOWS / workflow_name).read_text()
    resolve = workflow.index("- name: Resolve exact persisted qualification root")
    checkout = workflow.index("- name: Check out exact persisted qualification source")
    install = workflow.index("- name: Install exact qualification source")
    audit = workflow.index(audit_step)

    assert 'root="$HOME/m2h2-evidence/' in workflow[resolve:checkout]
    assert 'test -f "$root/qualification/results.json"' in workflow[resolve:checkout]
    assert 'test -f "$root/interactions/i1/results.json"' in workflow[resolve:checkout]
    assert 'test -f "$root/structural/a0_multiple/results.json"' in workflow[resolve:checkout]
    assert "python -m pip install -e '.[dev]'" not in workflow[:checkout]
    assert "SOURCE_SHA: ${{ steps.evidence.outputs.source_sha }}" in workflow[audit:]
    assert install < audit
