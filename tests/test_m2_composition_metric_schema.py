from ai_kicad import m2_composition_metric_schema as schema


def test_default_metric_schema_is_versioned_and_contains_required_categories() -> None:
    metrics = schema.default_metric_definitions()

    assert schema.SCHEMA_NAME == "m2h2-human-readable-composition"
    assert schema.SCHEMA_VERSION.startswith("2026-10-07")
    categories = {metric.category for metric in metrics}
    assert {
        "semantic_flow",
        "interface_frontier",
        "functional_grouping",
        "visual_ownership",
        "feedback_readability",
        "power_reference",
        "repeated_structure",
        "page_utilization",
        "routing_clarity",
        "label_discipline",
    } <= categories


def test_metric_ids_are_unique_and_do_not_encode_fixture_names() -> None:
    metrics = schema.default_metric_definitions()
    metric_ids = [metric.metric_id for metric in metrics]

    assert len(metric_ids) == len(set(metric_ids))
    assert all("i4__b2_mixed" not in metric.metric_id for metric in metrics)
    assert all("case" not in metric.category for metric in metrics)


def test_manifest_hash_is_deterministic_for_source_and_evidence_order() -> None:
    first = schema.build_manifest(
        production_sha="a" * 40,
        qualification_sha="b" * 40,
        source_texts={"src/b.py": "B", "src/a_observer.py": "A"},
        evidence_roots=(
            schema.EvidenceRoot("baseline", "evidence/baseline", "baseline characterization"),
            schema.EvidenceRoot("final", "evidence/final", "fresh final qualification"),
        ),
    )
    second = schema.build_manifest(
        production_sha="a" * 40,
        qualification_sha="b" * 40,
        source_texts={"src/a_observer.py": "A", "src/b.py": "B"},
        evidence_roots=(
            schema.EvidenceRoot("final", "evidence/final", "fresh final qualification"),
            schema.EvidenceRoot("baseline", "evidence/baseline", "baseline characterization"),
        ),
    )

    assert first.canonical_json() == second.canonical_json()
    assert first.manifest_sha256() == second.manifest_sha256()


def test_source_hash_records_roles_without_using_scores_as_proof() -> None:
    manifest = schema.build_manifest(
        production_sha="c" * 40,
        qualification_sha="d" * 40,
        source_texts={
            "src/ai_kicad/m2_layout.py": "production",
            "src/ai_kicad/m2_flow_observer.py": "observer",
            "src/ai_kicad/m2_grid_oracle.py": "oracle",
        },
        evidence_roots=(),
    )

    roles = {record.path: record.role for record in manifest.source_hashes}
    assert roles["src/ai_kicad/m2_layout.py"] == "production"
    assert roles["src/ai_kicad/m2_flow_observer.py"] == "observer_or_oracle"
    assert roles["src/ai_kicad/m2_grid_oracle.py"] == "observer_or_oracle"
    assert "score" not in manifest.canonical_json().lower()
