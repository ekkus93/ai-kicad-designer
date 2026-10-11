"""The independent M2H2 audit must never erase historical run evidence."""

from pathlib import Path


def test_final_artifact_audit_has_source_and_attempt_scoped_immutable_output() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/m2h2-final-artifact-audit.yml").read_text()
    assert (
        'report="$root/audit/artifact_audit_${source_sha}_run${GITHUB_RUN_ID}_attempt${GITHUB_RUN_ATTEMPT}.json"'
        in workflow
    )
    assert 'test ! -e "$report"' in workflow
    assert 'echo "report=${report}" >> "$GITHUB_OUTPUT"' in workflow
    assert '--out "$REPORT_PATH"' in workflow
    assert "path: ${{ steps.evidence.outputs.report }}" in workflow
    assert (
        "name: m2h2-artifact-audit-${{ steps.evidence.outputs.source_sha }}-run${{ github.run_id }}-attempt${{ github.run_attempt }}"
        in workflow
    )
    assert 'rm -f "$root/audit/' not in workflow
