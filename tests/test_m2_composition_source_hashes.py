import json

import pytest

from ai_kicad.m2_composition_source_hashes import (
    LOCKED_TOOLCHAIN,
    build_source_hash_manifest,
    classify_source_role,
)


def test_manifest_hashes_sources_deterministically() -> None:
    files = {
        "src/ai_kicad/m2_compose.py": "compose source\n",
        "src/ai_kicad/m2_graph_order_composition_oracle.py": "oracle source\n",
    }

    first = build_source_hash_manifest("a" * 40, files)
    second = build_source_hash_manifest("a" * 40, dict(reversed(tuple(files.items()))))

    assert first.canonical_json() == second.canonical_json()
    assert first.manifest_sha256() == second.manifest_sha256()
    assert first.locked_toolchain == LOCKED_TOOLCHAIN


def test_manifest_changes_when_source_content_changes() -> None:
    before = build_source_hash_manifest("b" * 40, {"src/ai_kicad/m2_compose.py": "one\n"})
    after = build_source_hash_manifest("b" * 40, {"src/ai_kicad/m2_compose.py": "two\n"})

    assert before.artifacts[0].sha256 != after.artifacts[0].sha256
    assert before.manifest_sha256() != after.manifest_sha256()


def test_source_roles_are_generic_not_fixture_specific() -> None:
    assert classify_source_role("src/ai_kicad/m2_compose.py") == "production_composition"
    assert (
        classify_source_role("src/ai_kicad/m2_tiny_grid_composition_oracle.py")
        == "observer_or_oracle"
    )
    assert classify_source_role("src/ai_kicad/m2_composition_structural_audit.py") == "audit"
    assert (
        classify_source_role("src/ai_kicad/m2_composition_candidate_evidence.py")
        == "evidence_schema"
    )


def test_manifest_json_preserves_artifact_inventory() -> None:
    manifest = build_source_hash_manifest(
        "c" * 40,
        {
            "src/ai_kicad/m2_compose.py": "compose\n",
            "src/ai_kicad/m2_composition_candidate_evidence.py": "evidence\n",
        },
    )
    decoded = json.loads(manifest.canonical_json())

    assert decoded["schema_version"] == "m2h2.composition-source-hashes.1"
    assert decoded["artifact_count"] == 2
    assert decoded["source_sha"] == "c" * 40
    assert [artifact["path"] for artifact in decoded["artifacts"]] == [
        "src/ai_kicad/m2_compose.py",
        "src/ai_kicad/m2_composition_candidate_evidence.py",
    ]


def test_out_of_scope_paths_are_rejected() -> None:
    with pytest.raises(ValueError, match=".local"):
        classify_source_role(".local/generated.py")
    with pytest.raises(ValueError, match="OpenClaw"):
        classify_source_role("research/legacy_openclaw/prototype.py")


def test_invalid_manifest_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="source_sha"):
        build_source_hash_manifest("not-a-sha", {"src/ai_kicad/m2_compose.py": "x"})
    with pytest.raises(ValueError, match="at least one"):
        build_source_hash_manifest("d" * 40, {})
