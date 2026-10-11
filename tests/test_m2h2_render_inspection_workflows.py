"""Keep native-render inspection independent of GitHub artifact storage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_inspection_uses_exact_source_matched_runner_evidence():
    for name, tag in (
        ("m2h2-base-render-inspection.yml", "[m2h2-base-render-audit]"),
        ("m2h2-structural-render-inspection.yml", "[m2h2-structural-render-audit]"),
    ):
        workflow = (ROOT / ".github" / "workflows" / name).read_text()
        assert "runs-on: self-hosted" in workflow
        assert "actions/download-artifact" not in workflow
        assert "m2h2-evidence" in workflow
        assert "identity_errors(payload)" in workflow
        assert "payload['git_head'] == sha" in workflow
        assert "ref: ${{ steps.evidence.outputs.source_sha }}" in workflow
        assert tag in workflow
        assert "[m2h2-audit-source:" in workflow
        assert "render_chunks(" in workflow
